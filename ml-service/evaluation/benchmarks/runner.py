"""Benchmark runner for evaluating anomaly detectors on labeled datasets."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from datasets.synthetic.generator import generate_dataset
from datasets.synthetic.semi_synthetic import inject_anomalies_into_tsdb, InjectionConfig
from detectors.base import AnomalyDetector
from evaluation.benchmarks.metrics_ext import (
    ThresholdStrategy,
    evaluate_multivariate,
    LatencyResult,
    PerSensorMetrics,
    AggregateMetrics,
    compute_latency,
)
from evaluation.metrics import EvaluationResult, evaluate_all


@dataclass
class BenchmarkConfig:
    """Configuration for a benchmark run."""

    dataset_type: str  # "synthetic", "semi_synthetic", "tsdb_injection"
    num_samples: int = 100
    seq_len: int | None = 1000
    anomaly_sample_ratio: float = 1.0
    is_multivariate: bool = False
    num_features: int | None = None
    use_attribute_set: bool = True
    metrics: list[str] | None = None
    seed: int = 42

    # Semi-synthetic specific
    tsdb_dataset: str | None = None
    injection_config: InjectionConfig | None = None

    # Detector specific
    detector_name: str = "timercd"
    detector_variant: str | None = None  # "uni" or "multi"

    # Evaluation
    threshold_strategy: ThresholdStrategy = ThresholdStrategy.BEST_F1
    target_fpr: float = 0.05
    target_recall: float = 0.90
    custom_threshold: float | None = None


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""

    config: BenchmarkConfig
    detector_name: str
    dataset_hash: str
    evaluation_result: EvaluationResult | None = None
    per_sensor_metrics: list[PerSensorMetrics] | None = None
    aggregate_metrics: AggregateMetrics | None = None
    latency: LatencyResult | None = None
    execution_time: float = 0.0
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "config": {
                "dataset_type": self.config.dataset_type,
                "num_samples": self.config.num_samples,
                "seq_len": self.config.seq_len,
                "anomaly_sample_ratio": self.config.anomaly_sample_ratio,
                "is_multivariate": self.config.is_multivariate,
                "num_features": self.config.num_features,
                "use_attribute_set": self.config.use_attribute_set,
                "metrics": self.config.metrics,
                "seed": self.config.seed,
                "tsdb_dataset": self.config.tsdb_dataset,
                "detector_name": self.config.detector_name,
                "detector_variant": self.config.detector_variant,
                "threshold_strategy": self.config.threshold_strategy.value,
                "target_fpr": self.config.target_fpr,
                "target_recall": self.config.target_recall,
                "custom_threshold": self.config.custom_threshold,
            },
            "detector_name": self.detector_name,
            "dataset_hash": self.dataset_hash,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp,
        }

        if self.evaluation_result:
            result["evaluation"] = {
                "precision": self.evaluation_result.precision,
                "recall": self.evaluation_result.recall,
                "f1": self.evaluation_result.f1,
                "pr_auc": self.evaluation_result.pr_auc,
                "roc_auc": self.evaluation_result.roc_auc,
                "best_threshold": self.evaluation_result.best_threshold,
            }

        if self.per_sensor_metrics:
            result["per_sensor"] = [
                {
                    "sensor": m.sensor_name,
                    "precision": m.precision,
                    "recall": m.recall,
                    "f1": m.f1,
                    "pr_auc": m.pr_auc,
                    "roc_auc": m.roc_auc,
                    "best_threshold": m.best_threshold,
                    "latency": {
                        "median": m.latency.median_latency if m.latency else None,
                        "p95": m.latency.p95_latency if m.latency else None,
                        "mean": m.latency.mean_latency if m.latency else None,
                        "max": m.latency.max_latency if m.latency else None,
                        "detection_rate": m.latency.detection_rate if m.latency else None,
                    } if m.latency else None,
                }
                for m in self.per_sensor_metrics
            ]

        if self.aggregate_metrics:
            result["aggregate"] = {
                "macro_precision": self.aggregate_metrics.macro_precision,
                "macro_recall": self.aggregate_metrics.macro_recall,
                "macro_f1": self.aggregate_metrics.macro_f1,
                "macro_pr_auc": self.aggregate_metrics.macro_pr_auc,
                "macro_roc_auc": self.aggregate_metrics.macro_roc_auc,
                "micro_precision": self.aggregate_metrics.micro_precision,
                "micro_recall": self.aggregate_metrics.micro_recall,
                "micro_f1": self.aggregate_metrics.micro_f1,
                "micro_pr_auc": self.aggregate_metrics.micro_pr_auc,
                "micro_roc_auc": self.aggregate_metrics.micro_roc_auc,
            }

        if self.latency:
            result["latency"] = {
                "median": self.latency.median_latency,
                "p95": self.latency.p95_latency,
                "mean": self.latency.mean_latency,
                "max": self.latency.max_latency,
                "detection_rate": self.latency.detection_rate,
            }

        return result


class BenchmarkRunner:
    """Runs benchmarks on anomaly detectors with labeled datasets."""

    def __init__(
        self,
        detector: AnomalyDetector,
        detector_name: str = "timercd",
        baseline_dir: str | Path | None = None,
    ):
        self.detector = detector
        self.detector_name = detector_name
        self.baseline_dir = Path(baseline_dir) if baseline_dir else Path("evaluation/benchmarks/baselines")
        self.baseline_dir.mkdir(parents=True, exist_ok=True)

    def _generate_dataset_hash(self, config: BenchmarkConfig) -> str:
        """Generate deterministic hash for dataset configuration."""
        config_str = f"{config.dataset_type}_{config.num_samples}_{config.seq_len}_" \
                     f"{config.anomaly_sample_ratio}_{config.is_multivariate}_" \
                     f"{config.num_features}_{config.use_attribute_set}_" \
                     f"{config.metrics}_{config.seed}"
        if config.tsdb_dataset:
            config_str += f"_{config.tsdb_dataset}"
        if config.injection_config:
            config_str += f"_{config.injection_config.anomaly_types}_" \
                          f"{config.injection_config.anomaly_intensity}"
        return hashlib.md5(config_str.encode()).hexdigest()[:12]

    def _load_or_generate_dataset(self, config: BenchmarkConfig) -> tuple[np.ndarray, np.ndarray, list[str] | None]:
        """Generate or load dataset based on config. Returns (data, labels, sensor_names)."""
        if config.dataset_type == "synthetic":
            dataset = generate_dataset(
                num_samples=config.num_samples,
                seq_len=config.seq_len,
                anomaly_sample_ratio=config.anomaly_sample_ratio,
                is_multivariate=config.is_multivariate,
                num_features=config.num_features,
                use_attribute_set=config.use_attribute_set,
                metrics=config.metrics,
                seed=config.seed,
            )
            # Concatenate all samples
            all_data = np.concatenate([s["time_series"] for s in dataset], axis=0)
            all_labels = np.concatenate([s["labels"] for s in dataset], axis=0)
            sensor_names = None
            if config.is_multivariate and dataset:
                sensor_names = [f"feature_{i}" for i in range(config.num_features)]

        elif config.dataset_type == "semi_synthetic":
            if config.tsdb_dataset is None:
                raise ValueError("tsdb_dataset required for semi_synthetic type")
            if config.injection_config is None:
                config.injection_config = InjectionConfig()

            # We need a detector for clean window detection
            from detectors.timercd import TimeRCDDetector
            detector = TimeRCDDetector()

            result = inject_anomalies_into_tsdb(
                config.tsdb_dataset,
                config.injection_config,
                detector=detector,
            )
            all_data = result["time_series"]
            all_labels = result["labels"]
            sensor_names = result["attribute"]["sensor_names"]

        else:
            raise ValueError(f"Unknown dataset_type: {config.dataset_type}")

        return all_data, all_labels, sensor_names

    def run(self, config: BenchmarkConfig) -> BenchmarkResult:
        """Run a single benchmark configuration."""
        start_time = time.time()
        dataset_hash = self._generate_dataset_hash(config)

        # Load/generate dataset
        data, labels, sensor_names = self._load_or_generate_dataset(config)

        # Run detector
        scores = self.detector.detect(data)

        # Evaluate
        if config.is_multivariate and sensor_names and len(sensor_names) > 1:
            # Multivariate evaluation
            if config.custom_threshold is not None:
                per_sensor, aggregate = evaluate_multivariate(
                    labels, scores, sensor_names,
                    threshold=config.custom_threshold,
                    y_true=labels,
                    scores=scores,
                )
                # Get overall evaluation at custom threshold
                eval_result = evaluate_all(labels.ravel(), scores.ravel(), best_threshold=config.custom_threshold)
            else:
                per_sensor, aggregate = evaluate_multivariate(
                    labels, scores, sensor_names,
                    strategy=config.threshold_strategy,
                    target_fpr=config.target_fpr,
                    target_recall=config.target_recall,
                    y_true=labels,
                    scores=scores,
                )
                # Overall evaluation using best threshold from first sensor
                best_threshold = per_sensor[0].best_threshold
                eval_result = evaluate_all(labels.ravel(), scores.ravel(), best_threshold=best_threshold)

            # Overall latency
            label_diff = np.diff(labels.ravel().astype(int), prepend=0)
            anomaly_onsets = np.where(label_diff == 1)[0].tolist()
            latency = None
            if anomaly_onsets:
                latency = compute_latency(
                    labels.ravel(), scores.ravel(),
                    per_sensor[0].best_threshold, anomaly_onsets
                )

            result = BenchmarkResult(
                config=config,
                detector_name=self.detector_name,
                dataset_hash=dataset_hash,
                evaluation_result=eval_result,
                per_sensor_metrics=per_sensor,
                aggregate_metrics=aggregate,
                latency=latency,
                execution_time=time.time() - start_time,
            )
        else:
            # Univariate evaluation
            if config.custom_threshold is not None:
                eval_result = evaluate_all(
                    labels, scores, best_threshold=config.custom_threshold
                )
            else:
                eval_result = evaluate_all(
                    labels, scores,
                    strategy=config.threshold_strategy,
                    target_fpr=config.target_fpr,
                    target_recall=config.target_recall,
                )

            # Latency
            label_diff = np.diff(labels.astype(int), prepend=0)
            anomaly_onsets = np.where(label_diff == 1)[0].tolist()
            latency = None
            if anomaly_onsets:
                latency = compute_latency(
                    labels, scores, eval_result.best_threshold, anomaly_onsets
                )

            result = BenchmarkResult(
                config=config,
                detector_name=self.detector_name,
                dataset_hash=dataset_hash,
                evaluation_result=eval_result,
                latency=latency,
                execution_time=time.time() - start_time,
            )

        return result

    def run_multiple(self, configs: list[BenchmarkConfig]) -> list[BenchmarkResult]:
        """Run multiple benchmark configurations."""
        return [self.run(config) for config in configs]

    def save_baseline(self, result: BenchmarkResult, name: str | None = None) -> Path:
        """Save benchmark result as baseline."""
        if name is None:
            name = f"{self.detector_name}_{result.dataset_hash}"

        baseline_path = self.baseline_dir / f"{name}.json"
        with open(baseline_path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        return baseline_path

    def load_baseline(self, name: str) -> dict[str, Any] | None:
        """Load baseline by name."""
        baseline_path = self.baseline_dir / f"{name}.json"
        if not baseline_path.exists():
            return None
        with open(baseline_path) as f:
            return json.load(f)

    def compare_to_baseline(
        self,
        result: BenchmarkResult,
        baseline_name: str,
        regression_threshold: float = 0.05,
    ) -> dict[str, Any]:
        """Compare result to baseline, return regression report."""
        baseline = self.load_baseline(baseline_name)
        if baseline is None:
            return {"error": f"Baseline {baseline_name} not found"}

        report = {"regressions": [], "improvements": [], "passed": True}

        # Compare key metrics
        metrics_to_compare = [
            ("f1", "F1 Score"),
            ("precision", "Precision"),
            ("recall", "Recall"),
            ("pr_auc", "PR-AUC"),
            ("roc_auc", "ROC-AUC"),
        ]

        for metric_key, metric_name in metrics_to_compare:
            current = getattr(result.evaluation_result, metric_key, None)
            baseline_val = baseline.get("evaluation", {}).get(metric_key)

            if current is not None and baseline_val is not None:
                diff = current - baseline_val
                rel_diff = diff / baseline_val if baseline_val != 0 else 0

                if rel_diff < -regression_threshold:
                    report["regressions"].append({
                        "metric": metric_name,
                        "current": current,
                        "baseline": baseline_val,
                        "absolute_diff": diff,
                        "relative_diff": rel_diff,
                    })
                    report["passed"] = False
                elif rel_diff > regression_threshold:
                    report["improvements"].append({
                        "metric": metric_name,
                        "current": current,
                        "baseline": baseline_val,
                        "absolute_diff": diff,
                        "relative_diff": rel_diff,
                    })

        return report