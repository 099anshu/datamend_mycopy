"""Single-experiment runner for TimeRCD evaluation on TSDB datasets.

Pipeline: TSDB dataset -> inject synthetic anomalies with known labels ->
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
from datasets.tsdb_loader import load_tsdb_dataset
from detectors.timercd import TimeRCDDetector
from evaluation.anomaly_injection import inject_anomalies
from evaluation.metrics import EvaluationResult, evaluate_all

ETT7 = ["HUFL", "HULL", "MUFL", "MULL", "LUFL", "LULL", "OT"]

# Supported missingness methods and the CLI flag that maps to their rate param.
_MISSINGNESS_RATE_PARAM = {"mcar": "p", "rdo": "p", "mnar_nonuniform": "p"}


@dataclass
class ExperimentSpec:
    """Everything needed to reproduce one experiment."""

    dataset_name: str
    columns: tuple[str, ...]
    anomaly_rate: float
    seed: int
    missingness: Optional[tuple[str, dict]]  # (method, params); None = clean
    strategy: str


def run_experiment(
    dataset_name: str = "ETTh1",
    columns: tuple[str, ...] = tuple(ETT7),
    anomaly_rate: float = 0.01,
    seed: int = 0,
    missingness: Optional[tuple[str, dict]] = None,
    strategy: str = "reject",
) -> EvaluationResult:
    """Run one full evaluation and return the aggregated metrics.

    ``missingness`` is ``(method, params)`` for ``apply_corruption`` or
    ``None`` for the clean baseline. ``strategy`` is passed to
    ``handle_missing_values``; use an imputation strategy (``ffill``,
    ``bfill``, ``mean``, ``interpolate``) when missingness is applied.
    """
    df = load_tsdb_dataset(dataset_name)
    data = df[list(columns)].to_numpy(dtype=np.float64)

    modified, labels = inject_anomalies(data, anomaly_rate=anomaly_rate, seed=seed)

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


def print_result(
    result: EvaluationResult,
    *,
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
    return ExperimentSpec(
        dataset_name=args.dataset,
        columns=tuple(args.columns),
        anomaly_rate=args.anomaly_rate,
        seed=args.seed,
        missingness=missingness,
        strategy=args.strategy,
    )


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="evaluation.evaluate_timercd",
        description="Run one TimeRCD anomaly-detection evaluation on a TSDB dataset.",
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
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point: run one experiment and print the result."""
    args = _parse_args(argv)
    spec = _build_spec(args)
    result = run_experiment(
        dataset_name=spec.dataset_name,
        columns=spec.columns,
        anomaly_rate=spec.anomaly_rate,
        seed=spec.seed,
        missingness=spec.missingness,
        strategy=spec.strategy,
    )
    print_result(
        result,
        dataset_name=spec.dataset_name,
        anomaly_rate=spec.anomaly_rate,
        missingness=spec.missingness,
        strategy=spec.strategy,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())