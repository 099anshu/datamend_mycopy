"""Extended metrics for benchmarking: threshold selection, latency, per-sensor metrics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

import numpy as np
from sklearn.metrics import precision_recall_curve, roc_curve

from evaluation.metrics import (
    EvaluationResult,
    ThresholdResult,
    evaluate_all,
    evaluate_thresholds,
    precision_recall_f1,
    pr_auc,
    roc_auc,
)


class ThresholdStrategy(str, Enum):
    """Threshold selection strategies."""

    BEST_F1 = "best_f1"
    FIXED_FPR = "fixed_fpr"
    FIXED_RECALL = "fixed_recall"
    YOUDEN_J = "youdens_j"


@dataclass(frozen=True)
class LatencyResult:
    """Detection latency statistics."""

    median_latency: float
    p95_latency: float
    mean_latency: float
    max_latency: float
    detection_rate: float  # Fraction of anomalies detected


def select_threshold(
    y_true: np.ndarray,
    scores: np.ndarray,
    strategy: ThresholdStrategy | str = ThresholdStrategy.BEST_F1,
    target_fpr: float = 0.05,
    target_recall: float = 0.90,
    thresholds: np.ndarray | None = None,
) -> tuple[float, ThresholdResult]:
    """Select optimal threshold using specified strategy.

    Args:
        y_true: Binary labels
        scores: Anomaly scores
        strategy: Selection strategy
        target_fpr: Target FPR for fixed_fpr strategy
        target_recall: Target recall for fixed_recall strategy
        thresholds: Custom thresholds to evaluate

    Returns:
        Tuple of (selected_threshold, ThresholdResult at that threshold)
    """
    if isinstance(strategy, str):
        strategy = ThresholdStrategy(strategy)

    threshold_results = evaluate_thresholds(y_true, scores, thresholds)

    if strategy == ThresholdStrategy.BEST_F1:
        # Highest F1, tie-broken by precision
        best = max(threshold_results, key=lambda r: (r.f1, r.precision))
        return best.threshold, best

    if strategy == ThresholdStrategy.YOUDEN_J:
        # Youden's J = TPR - FPR = Recall - FPR
        # Need to compute FPR for each threshold
        y_true_bool = np.asarray(y_true, dtype=bool)
        scores_flat = np.asarray(scores, dtype=np.float64).ravel()

        best_j = -1.0
        best_threshold = threshold_results[0].threshold
        best_result = threshold_results[0]

        for result in threshold_results:
            predictions = scores_flat >= result.threshold
            tp = np.count_nonzero(y_true_bool & predictions)
            fp = np.count_nonzero(~y_true_bool & predictions)
            tn = np.count_nonzero(~y_true_bool & ~predictions)
            fn = np.count_nonzero(y_true_bool & ~predictions)

            tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
            j = tpr - fpr

            if j > best_j:
                best_j = j
                best_threshold = result.threshold
                best_result = result

        return best_threshold, best_result

    if strategy == ThresholdStrategy.FIXED_FPR:
        # Find threshold achieving target FPR (or closest below)
        y_true_bool = np.asarray(y_true, dtype=bool)
        scores_flat = np.asarray(scores, dtype=np.float64).ravel()

        best_threshold = threshold_results[0].threshold
        best_result = threshold_results[0]
        best_fpr = -1.0  # Start with -1 so any valid FPR >= 0 is better

        for result in threshold_results:
            predictions = scores_flat >= result.threshold
            fp = np.count_nonzero(~y_true_bool & predictions)
            tn = np.count_nonzero(~y_true_bool & ~predictions)

            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

            if fpr <= target_fpr and fpr > best_fpr:
                best_fpr = fpr
                best_threshold = result.threshold
                best_result = result

        return best_threshold, best_result

    if strategy == ThresholdStrategy.FIXED_RECALL:
        # Find threshold achieving target recall (or closest above)
        y_true_bool = np.asarray(y_true, dtype=bool)
        scores_flat = np.asarray(scores, dtype=np.float64).ravel()

        best_threshold = threshold_results[-1].threshold
        best_result = threshold_results[-1]
        best_recall = 2.0  # Start with > 1 so any valid recall <= 1 is better

        for result in threshold_results:
            predictions = scores_flat >= result.threshold
            tp = np.count_nonzero(y_true_bool & predictions)
            fn = np.count_nonzero(y_true_bool & ~predictions)

            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

            if recall >= target_recall and recall < best_recall:
                best_recall = recall
                best_threshold = result.threshold
                best_result = result

        return best_threshold, best_result

    # Default to best F1
    best = max(threshold_results, key=lambda r: (r.f1, r.precision))
    return best.threshold, best


def compute_latency(
    y_true: np.ndarray,
    scores: np.ndarray,
    threshold: float,
    anomaly_onsets: list[int] | None = None,
) -> LatencyResult:
    """Compute detection latency metrics.

    Args:
        y_true: Binary labels (1 = anomaly)
        scores: Anomaly scores
        threshold: Decision threshold
        anomaly_onsets: Optional list of anomaly onset indices.
                       If not provided, inferred from label transitions 0->1.

    Returns:
        LatencyResult with median, p95, mean, max latency in timesteps
    """
    predictions = np.asarray(scores) >= threshold
    y_true = np.asarray(y_true, dtype=bool)

    # Find anomaly onsets if not provided
    if anomaly_onsets is None:
        # Onset = transition from 0 to 1 in labels
        label_diff = np.diff(y_true.astype(int), prepend=0)
        anomaly_onsets = np.where(label_diff == 1)[0].tolist()

    if not anomaly_onsets:
        return LatencyResult(
            median_latency=0.0,
            p95_latency=0.0,
            mean_latency=0.0,
            max_latency=0.0,
            detection_rate=0.0,
        )

    latencies = []
    detected = 0

    for onset in anomaly_onsets:
        # Find first detection after onset
        future_predictions = predictions[onset:]
        detection_indices = np.where(future_predictions)[0]

        if len(detection_indices) > 0:
            latency = detection_indices[0]
            latencies.append(latency)
            detected += 1

    if not latencies:
        return LatencyResult(
            median_latency=0.0,
            p95_latency=0.0,
            mean_latency=0.0,
            max_latency=0.0,
            detection_rate=0.0,
        )

    latencies = np.array(latencies)
    detection_rate = detected / len(anomaly_onsets)

    return LatencyResult(
        median_latency=float(np.median(latencies)),
        p95_latency=float(np.percentile(latencies, 95)),
        mean_latency=float(np.mean(latencies)),
        max_latency=float(np.max(latencies)),
        detection_rate=detection_rate,
    )


@dataclass(frozen=True)
class PerSensorMetrics:
    """Metrics for a single sensor."""

    sensor_name: str
    precision: float
    recall: float
    f1: float
    pr_auc: float
    roc_auc: float
    best_threshold: float
    latency: LatencyResult | None = None


@dataclass(frozen=True)
class AggregateMetrics:
    """Aggregated metrics across sensors."""

    macro_precision: float
    macro_recall: float
    macro_f1: float
    macro_pr_auc: float
    macro_roc_auc: float
    micro_precision: float
    micro_recall: float
    micro_f1: float
    micro_pr_auc: float
    micro_roc_auc: float


def compute_per_sensor_metrics(
    y_true: np.ndarray,  # (n_samples, n_sensors) or (n_samples,)
    scores: np.ndarray,  # (n_samples, n_sensors) or (n_samples,)
    sensor_names: list[str] | None = None,
    threshold: float | None = None,
    strategy: ThresholdStrategy = ThresholdStrategy.BEST_F1,
    **strategy_kwargs,
) -> list[PerSensorMetrics]:
    """Compute metrics per sensor for multivariate data.

    Args:
        y_true: Binary labels, shape (n_samples,) or (n_samples, n_sensors)
        scores: Anomaly scores, shape (n_samples,) or (n_samples, n_sensors)
        sensor_names: Optional sensor names
        threshold: Fixed threshold (if None, use strategy)
        strategy: Threshold selection strategy if threshold not provided

    Returns:
        List of PerSensorMetrics per sensor
    """
    y_true = np.asarray(y_true)
    scores = np.asarray(scores)

    # Handle univariate case
    if y_true.ndim == 1:
        y_true = y_true.reshape(-1, 1)
    if scores.ndim == 1:
        scores = scores.reshape(-1, 1)

    n_samples, n_sensors = y_true.shape
    assert scores.shape == (n_samples, n_sensors)

    if sensor_names is None:
        sensor_names = [f"sensor_{i}" for i in range(n_sensors)]

    results = []

    for i in range(n_sensors):
        sensor_y_true = y_true[:, i]
        sensor_scores = scores[:, i]

        # Skip if no anomalies in this sensor
        if sensor_y_true.sum() == 0:
            results.append(PerSensorMetrics(
                sensor_name=sensor_names[i],
                precision=0.0,
                recall=0.0,
                f1=0.0,
                pr_auc=0.0,
                roc_auc=0.0,
                best_threshold=0.5,
                latency=None,
            ))
            continue

        # Select threshold
        if threshold is not None:
            sensor_threshold = threshold
            threshold_results = evaluate_thresholds(sensor_y_true, sensor_scores)
            chosen = next((r for r in threshold_results if r.threshold == threshold), None)
            if chosen is None:
                # Compute at threshold
                preds = sensor_scores >= threshold
                precision, recall, f1 = precision_recall_f1(sensor_y_true, preds)
                sensor_result = ThresholdResult(
                    threshold=threshold,
                    precision=precision,
                    recall=recall,
                    f1=f1,
                )
            else:
                sensor_result = chosen
        else:
            sensor_threshold, sensor_result = select_threshold(
                sensor_y_true, sensor_scores, strategy, **strategy_kwargs
            )

        # Compute latency
        label_diff = np.diff(sensor_y_true.astype(int), prepend=0)
        anomaly_onsets = np.where(label_diff == 1)[0].tolist()
        latency = compute_latency(sensor_y_true, sensor_scores, sensor_threshold, anomaly_onsets)

        results.append(PerSensorMetrics(
            sensor_name=sensor_names[i],
            precision=sensor_result.precision,
            recall=sensor_result.recall,
            f1=sensor_result.f1,
            pr_auc=pr_auc(sensor_y_true, sensor_scores),
            roc_auc=roc_auc(sensor_y_true, sensor_scores),
            best_threshold=sensor_threshold,
            latency=latency,
        ))

    return results


def aggregate_metrics(
    per_sensor: list[PerSensorMetrics],
    y_true: np.ndarray | None = None,
    scores: np.ndarray | None = None,
) -> AggregateMetrics:
    """Compute macro and micro aggregate metrics from per-sensor results.

    Macro: Average of per-sensor metrics
    Micro: Global metrics computed on flattened (sample, sensor) pairs
    """
    if not per_sensor:
        return AggregateMetrics(
            macro_precision=0.0, macro_recall=0.0, macro_f1=0.0,
            macro_pr_auc=0.0, macro_roc_auc=0.0,
            micro_precision=0.0, micro_recall=0.0, micro_f1=0.0,
            micro_pr_auc=0.0, micro_roc_auc=0.0,
        )

    # Macro averages
    macro_precision = np.mean([m.precision for m in per_sensor])
    macro_recall = np.mean([m.recall for m in per_sensor])
    macro_f1 = np.mean([m.f1 for m in per_sensor])
    macro_pr_auc = np.mean([m.pr_auc for m in per_sensor])
    macro_roc_auc = np.mean([m.roc_auc for m in per_sensor])

    # Micro averages - compute from raw data if provided
    if y_true is not None and scores is not None:
        y_true_flat = np.asarray(y_true).ravel()
        scores_flat = np.asarray(scores).ravel()
        micro_precision, micro_recall, micro_f1 = precision_recall_f1(
            y_true_flat, scores_flat >= 0.5  # Use default threshold for micro
        )
        micro_pr_auc = pr_auc(y_true_flat, scores_flat)
        micro_roc_auc = roc_auc(y_true_flat, scores_flat)
    else:
        # Fallback: approximate from macro (not ideal but maintains compatibility)
        micro_precision = macro_precision
        micro_recall = macro_recall
        micro_f1 = macro_f1
        micro_pr_auc = macro_pr_auc
        micro_roc_auc = macro_roc_auc

    return AggregateMetrics(
        macro_precision=macro_precision,
        macro_recall=macro_recall,
        macro_f1=macro_f1,
        macro_pr_auc=macro_pr_auc,
        macro_roc_auc=macro_roc_auc,
        micro_precision=micro_precision,
        micro_recall=micro_recall,
        micro_f1=micro_f1,
        micro_pr_auc=micro_pr_auc,
        micro_roc_auc=micro_roc_auc,
    )


def evaluate_multivariate(
    y_true: np.ndarray,
    scores: np.ndarray,
    sensor_names: list[str] | None = None,
    threshold: float | None = None,
    strategy: ThresholdStrategy = ThresholdStrategy.BEST_F1,
    **strategy_kwargs,
) -> tuple[list[PerSensorMetrics], AggregateMetrics]:
    """Full multivariate evaluation with per-sensor and aggregate metrics."""
    per_sensor = compute_per_sensor_metrics(
        y_true, scores, sensor_names, threshold, strategy, **strategy_kwargs
    )
    aggregate = aggregate_metrics(per_sensor, y_true, scores)
    return per_sensor, aggregate