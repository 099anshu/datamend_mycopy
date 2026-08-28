"""Single-experiment runner for TimeRCD evaluation on TSDB and synthetic datasets.

Pipeline: Dataset (TSDB/Synthetic/Semi-synthetic) -> inject anomalies with known labels ->
optional PyGrinder missingness -> explicit missing-value handling ->
``TimeRCDDetector`` -> raw scores -> metrics (Precision/Recall/F1/PR-AUC/
ROC-AUC) -> concise printed result.

This runner calls the existing detector directly. It never calls the FastAPI
HTTP endpoints and never duplicates the detector implementation.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Optional

import numpy as np

from corruption.pygrinder import apply_corruption, handle_missing_values
from datasets.synthetic.anomalies import AnomalySpec, inject_multiple_anomalies
from datasets.synthetic.generator import generate_dataset
from datasets.synthetic.semi_synthetic import inject_anomalies_into_tsdb, InjectionConfig
from datasets.tsdb_loader import load_tsdb_dataset
from detectors.timercd import TimeRCDDetector
from evaluation.metrics import EvaluationResult, evaluate_all

ETT7 = ["HUFL", "HULL", "MUFL", "MULL", "LUFL", "LULL", "OT"]

# Supported missingness methods and the CLI flag that maps to their rate param.
_MISSINGNESS_RATE_PARAM = {"mcar": "p", "rdo": "p", "mnar_nonuniform": "p"}

# Dataset types
DATASET_TYPES = ["tsdb", "synthetic", "semi_synthetic"]


@dataclass
class ExperimentSpec:
    """Everything needed to reproduce one experiment."""

    dataset_type: str  # "tsdb", "synthetic", "semi_synthetic"
    dataset_name: str
    columns: tuple[str, ...]
    anomaly_rate: float
    seed: int
    missingness: Optional[tuple[str, dict]]  # (method, params); None = clean
    strategy: str
    # Synthetic-specific
    num_samples: int = 100
    seq_len: int | None = 1000
    is_multivariate: bool = False
    num_features: int | None = None
    use_attribute_set: bool = True
    metrics: tuple[str, ...] = ()
    # Semi-synthetic specific
    injection_config: Optional[InjectionConfig] = None


def run_experiment(
    dataset_type: str = "tsdb",
    dataset_name: str = "ETTh1",
    columns: tuple[str, ...] = tuple(ETT7),
    anomaly_rate: float = 0.01,
    seed: int = 0,
    missingness: Optional[tuple[str, dict]] = None,
    strategy: str = "reject",
    # Synthetic-specific
    num_samples: int = 100,
    seq_len: int | None = 1000,
    is_multivariate: bool = False,
    num_features: int | None = None,
    use_attribute_set: bool = True,
    metrics: tuple[str, ...] = (),
    # Semi-synthetic specific
    injection_config: Optional[InjectionConfig] = None,
) -> EvaluationResult:
    """Run one full evaluation and return the aggregated metrics.

    Args:
        dataset_type: "tsdb", "synthetic", or "semi_synthetic"
        dataset_name: TSDB dataset name (for tsdb and semi_synthetic)
        columns: Sensor columns to use (for tsdb)
        anomaly_rate: Anomaly injection rate (for tsdb)
        seed: Random seed
        missingness: (method, params) for apply_corruption or None for clean
        strategy: Missing-value handling strategy
        num_samples: Number of synthetic samples
        seq_len: Sequence length (None for random)
        is_multivariate: Generate multivariate synthetic data
        num_features: Number of features for multivariate
        use_attribute_set: Use attribute-based generation
        metrics: Specific anomaly types for synthetic
        injection_config: InjectionConfig for semi_synthetic

    ``missingness`` is ``(method, params)`` for ``apply_corruption`` or
    ``None`` for the clean baseline. ``strategy`` is passed to
    ``handle_missing_values``; use an imputation strategy (``ffill``,
    ``bfill``, ``mean``, ``interpolate``) when missingness is applied.
    """
    if dataset_type == "tsdb":
        return _run_tsdb_experiment(
            dataset_name, columns, anomaly_rate, seed, missingness, strategy
        )
    elif dataset_type == "synthetic":
        return _run_synthetic_experiment(
            num_samples, seq_len, anomaly_rate, seed, missingness, strategy,
            is_multivariate, num_features, use_attribute_set, metrics
        )
    elif dataset_type == "semi_synthetic":
        return _run_semi_synthetic_experiment(
            dataset_name, injection_config, seed, missingness, strategy
        )
    else:
        raise ValueError(f"Unknown dataset_type: {dataset_type}")


def _inject_tsdb_anomalies(
    data: np.ndarray,
    anomaly_rate: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Inject anomalies into TSDB data using new anomaly injection API.

    Matches the behavior of the old evaluation.anomaly_injection.inject_anomalies:
    - anomaly_rate is fraction of timestamps to perturb
    - chooses from spike, drop, contextual anomaly types
    - uses 3 sigma for spike/drop, 1 sigma for contextual
    """
    from datasets.synthetic.anomalies import AnomalySpec, inject_multiple_anomalies

    n_steps, n_features = data.shape
    anomaly_rate = float(anomaly_rate)
    if not 0.0 < anomaly_rate < 1.0:
        raise ValueError(f"anomaly_rate must be in (0, 1), got {anomaly_rate}")

    rng = np.random.default_rng(seed)
    k = min(int(round(n_steps * anomaly_rate)), n_steps)
    rows = rng.choice(n_steps, size=k, replace=False)

    column_std = np.std(data, axis=0)
    column_std = np.where(column_std == 0.0, 1.0, column_std)

    specs = []
    for row in rows:
        kind = rng.choice(["spike", "drop", "contextual"])
        if kind == "spike":
            specs.append(AnomalySpec("spike", int(row), 1, 3.0, "constant", "up"))
        elif kind == "drop":
            specs.append(AnomalySpec("drop", int(row), 1, 3.0, "constant", "down"))
        else:  # contextual
            specs.append(AnomalySpec("spike", int(row), 4, 1.0, "sinusoidal", "up"))

    modified = data.copy()
    modified, labels = inject_multiple_anomalies(modified, specs, rng=rng)
    return modified, labels.astype(bool)


def _run_tsdb_experiment(
    dataset_name: str,
    columns: tuple[str, ...],
    anomaly_rate: float,
    seed: int,
    missingness: Optional[tuple[str, dict]],
    strategy: str,
) -> EvaluationResult:
    """Run experiment on TSDB dataset with injected anomalies."""
    df = load_tsdb_dataset(dataset_name)
    data = df[list(columns)].to_numpy(dtype=np.float64)

    modified, labels = _inject_tsdb_anomalies(data, anomaly_rate=anomaly_rate, seed=seed)

    if missingness is not None:
        method, params = missingness
        modified = apply_corruption(modified, method, params)

    scores_input = handle_missing_values(modified, strategy)

    scores = TimeRCDDetector().detect(scores_input)
    scores = np.asarray(scores, dtype=np.float64).ravel()
    if scores.shape[0] != labels.shape[0]:
        raise RuntimeError(
            f"Detector returned {scores.shape[0]} scores for {labels.shape[0]} rows"
        )

    return evaluate_all(labels, scores)


def _run_synthetic_experiment(
    num_samples: int,
    seq_len: int | None,
    anomaly_rate: float,
    seed: int,
    missingness: Optional[tuple[str, dict]],
    strategy: str,
    is_multivariate: bool,
    num_features: int | None,
    use_attribute_set: bool,
    metrics: tuple[str, ...],
) -> EvaluationResult:
    """Run experiment on synthetic dataset."""
    dataset = generate_dataset(
        num_samples=num_samples,
        seq_len=seq_len,
        anomaly_sample_ratio=anomaly_rate,
        is_multivariate=is_multivariate,
        num_features=num_features,
        use_attribute_set=use_attribute_set,
        metrics=list(metrics) if metrics else None,
        seed=seed,
    )

    # Concatenate all samples
    all_data = np.concatenate([s["time_series"] for s in dataset], axis=0)
    all_labels = np.concatenate([s["labels"] for s in dataset], axis=0)

    if missingness is not None:
        method, params = missingness
        all_data = apply_corruption(all_data, method, params)

    scores_input = handle_missing_values(all_data, strategy)

    scores = TimeRCDDetector().detect(scores_input)
    scores = np.asarray(scores, dtype=np.float64).ravel()
    if scores.shape[0] != all_labels.shape[0]:
        raise RuntimeError(
            f"Detector returned {scores.shape[0]} scores for {all_labels.shape[0]} rows"
        )

    return evaluate_all(all_labels, scores)


def _run_semi_synthetic_experiment(
    dataset_name: str,
    injection_config: Optional[InjectionConfig],
    seed: int,
    missingness: Optional[tuple[str, dict]],
    strategy: str,
) -> EvaluationResult:
    """Run experiment on semi-synthetic dataset (TSDB + injected anomalies)."""
    if injection_config is None:
        injection_config = InjectionConfig(seed=seed)
    else:
        injection_config.seed = seed

    # Use TimeRCD for clean window detection
    detector = TimeRCDDetector()

    result = inject_anomalies_into_tsdb(dataset_name, injection_config, detector=detector)

    data = result["time_series"]
    labels = result["labels"]

    if missingness is not None:
        method, params = missingness
        data = apply_corruption(data, method, params)

    scores_input = handle_missing_values(data, strategy)

    scores = TimeRCDDetector().detect(scores_input)
    scores = np.asarray(scores, dtype=np.float64).ravel()
    if scores.shape[0] != labels.shape[0]:
        raise RuntimeError(
            f"Detector returned {scores.shape[0]} scores for {labels.shape[0]} rows"
        )

    return evaluate_all(labels, scores)


def print_result(
    result: EvaluationResult,
    *,
    dataset_type: str,
    dataset_name: str,
    anomaly_rate: float,
    missingness: Optional[tuple[str, dict]],
    strategy: str,
) -> None:
    """Print a concise experiment result using only computed metric values."""
    if missingness is None:
        missingness_label = "None (clean)"
    else:
        method, params = missingness
        rate_param = _MISSINGNESS_RATE_PARAM.get(method)
        if rate_param is not None and rate_param in params:
            missingness_label = f"{method.upper()} {float(params[rate_param]):.0%}"
        else:
            missingness_label = method.upper()

    print(f"Dataset Type: {dataset_type}")
    print(f"Dataset: {dataset_name}")
    print(f"Anomaly rate: {anomaly_rate:.0%}")
    print(f"Missingness: {missingness_label}")
    print(f"Missing-value handling: {strategy}")
    print()
    print(f"Precision: {result.precision:.3f}")
    print(f"Recall:    {result.recall:.3f}")
    print(f"F1:        {result.f1:.3f}")
    print(f"PR-AUC:    {result.pr_auc:.3f}")
    print(f"ROC-AUC:   {result.roc_auc:.3f}")


def _build_spec(args: argparse.Namespace) -> ExperimentSpec:
    missingness = None
    if args.missingness is not None:
        rate_param = _MISSINGNESS_RATE_PARAM.get(args.missingness)
        if rate_param is None:
            raise ValueError(
                f"Missingness method {args.missingness!r} is not supported by the "
                "experiment CLI. Supported: mcar, rdo, mnar_nonuniform"
            )
        if args.p is None:
            raise ValueError(f"Missingness method {args.missingness!r} requires --p")
        missingness = (args.missingness, {rate_param: args.p})

    injection_config = None
    if args.dataset_type == "semi_synthetic":
        injection_config = InjectionConfig(
            target_sensors=args.sensors.split(",") if args.sensors else None,
            anomaly_types=args.injection_metrics.split(",") if args.injection_metrics else ["spike", "drift"],
            anomaly_intensity=args.injection_intensity,
            anomaly_duration_range=(args.injection_min_duration, args.injection_max_duration),
            num_anomalies_per_sensor=args.injection_count,
            placement=args.injection_placement,
            periodic_interval=args.injection_periodic_interval,
            avoid_high_score_regions=not args.injection_no_avoid,
            high_score_threshold=args.injection_threshold,
            seed=args.seed,
        )

    return ExperimentSpec(
        dataset_type=args.dataset_type,
        dataset_name=args.dataset,
        columns=tuple(args.columns),
        anomaly_rate=args.anomaly_rate,
        seed=args.seed,
        missingness=missingness,
        strategy=args.strategy,
        num_samples=args.num_samples,
        seq_len=args.seq_len,
        is_multivariate=args.multivariate,
        num_features=args.num_features,
        use_attribute_set=args.use_attribute_set,
        metrics=tuple(args.metrics.split(",")) if args.metrics else (),
        injection_config=injection_config,
    )


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="evaluation.experiment_runner",
        description="Run one TimeRCD anomaly-detection evaluation on TSDB, synthetic, or semi-synthetic datasets.",
    )
    parser.add_argument(
        "--dataset-type",
        choices=DATASET_TYPES,
        default="tsdb",
        help="Dataset type: tsdb (original), synthetic (generated), semi_synthetic (TSDB + injection)"
    )
    parser.add_argument("--dataset", default="ETTh1")
    parser.add_argument("--columns", nargs="+", default=ETT7)
    parser.add_argument("--anomaly-rate", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--missingness",
        choices=sorted(_MISSINGNESS_RATE_PARAM),
        default=None,
        help="PyGrinder missingness method; omit for a clean baseline",
    )
    parser.add_argument(
        "--p", type=float, default=None, help="Missingness rate parameter (e.g. 0.10)"
    )
    parser.add_argument(
        "--strategy",
        choices=["reject", "ffill", "bfill", "mean", "interpolate"],
        default="reject",
    )

    # Synthetic dataset options
    parser.add_argument("--num-samples", type=int, default=100)
    parser.add_argument("--seq-len", type=int, default=1000)
    parser.add_argument("--multivariate", action="store_true")
    parser.add_argument("--num-features", type=int, default=5)
    parser.add_argument("--use-attribute-set", action="store_true", default=True)
    parser.add_argument("--metrics", type=str, default=None,
                        help="Comma-separated anomaly types for synthetic data")

    # Semi-synthetic injection options
    parser.add_argument("--sensors", type=str, default=None,
                        help="Comma-separated target sensors for semi-synthetic")
    parser.add_argument("--injection-metrics", type=str, default=None,
                        help="Comma-separated anomaly types for injection")
    parser.add_argument("--injection-intensity", type=float, default=3.0)
    parser.add_argument("--injection-min-duration", type=int, default=10)
    parser.add_argument("--injection-max-duration", type=int, default=50)
    parser.add_argument("--injection-count", type=int, default=3)
    parser.add_argument("--injection-placement", choices=["random", "periodic"], default="random")
    parser.add_argument("--injection-periodic-interval", type=int, default=None)
    parser.add_argument("--injection-no-avoid", action="store_true",
                        help="Don't avoid high-score regions")
    parser.add_argument("--injection-threshold", type=float, default=0.7)

    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point: run one experiment and print the result."""
    args = _parse_args(argv)
    spec = _build_spec(args)
    result = run_experiment(
        dataset_type=spec.dataset_type,
        dataset_name=spec.dataset_name,
        columns=spec.columns,
        anomaly_rate=spec.anomaly_rate,
        seed=spec.seed,
        missingness=spec.missingness,
        strategy=spec.strategy,
        num_samples=spec.num_samples,
        seq_len=spec.seq_len,
        is_multivariate=spec.is_multivariate,
        num_features=spec.num_features,
        use_attribute_set=spec.use_attribute_set,
        metrics=spec.metrics,
        injection_config=spec.injection_config,
    )
    print_result(
        result,
        dataset_type=spec.dataset_type,
        dataset_name=spec.dataset_name,
        anomaly_rate=spec.anomaly_rate,
        missingness=spec.missingness,
        strategy=spec.strategy,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())