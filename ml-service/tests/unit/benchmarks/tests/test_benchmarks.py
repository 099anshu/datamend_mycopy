"""Tests for benchmark metrics and threshold selection."""

import numpy as np

from evaluation.benchmarks.metrics_ext import (
    ThresholdStrategy,
    select_threshold,
    compute_latency,
    compute_per_sensor_metrics,
    aggregate_metrics,
    evaluate_multivariate,
    PerSensorMetrics,
    AggregateMetrics,
)
from evaluation.metrics import evaluate_all


def test_select_threshold_best_f1():
    """Test best-F1 threshold selection."""
    # Create scores where we know the best threshold
    y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    scores = np.array([0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9])

    threshold, result = select_threshold(y_true, scores, ThresholdStrategy.BEST_F1)

    # Best F1 should be around 0.5 (separates 0.4 and 0.6)
    assert 0.4 <= threshold <= 0.6
    assert result.f1 > 0.5


def test_select_threshold_youdens_j():
    """Test Youden's J threshold selection."""
    y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    scores = np.array([0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9])

    threshold, result = select_threshold(y_true, scores, ThresholdStrategy.YOUDEN_J)

    # Youden's J maximizes TPR - FPR
    assert 0.4 <= threshold <= 0.6


def test_select_threshold_fixed_fpr():
    """Test fixed FPR threshold selection."""
    y_true = np.array([0] * 50 + [1] * 50)
    scores = np.concatenate([
        np.random.default_rng(42).uniform(0, 0.5, 50),
        np.random.default_rng(42).uniform(0.5, 1.0, 50),
    ])

    threshold, result = select_threshold(y_true, scores, ThresholdStrategy.FIXED_FPR, target_fpr=0.1)

    # At threshold, FPR should be <= 0.1
    predictions = scores >= threshold
    fp = np.sum((y_true == 0) & predictions)
    tn = np.sum((y_true == 0) & ~predictions)
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0

    assert fpr <= 0.1 + 1e-6


def test_select_threshold_fixed_recall():
    """Test fixed recall threshold selection."""
    y_true = np.array([0] * 50 + [1] * 50)
    scores = np.concatenate([
        np.random.default_rng(42).uniform(0, 0.5, 50),
        np.random.default_rng(42).uniform(0.5, 1.0, 50),
    ])

    threshold, result = select_threshold(y_true, scores, ThresholdStrategy.FIXED_RECALL, target_recall=0.9)

    # At threshold, recall should be >= 0.9
    predictions = scores >= threshold
    tp = np.sum((y_true == 1) & predictions)
    fn = np.sum((y_true == 1) & ~predictions)
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0

    assert recall >= 0.9 - 1e-6


def test_compute_latency():
    """Test latency computation."""
    # Anomaly from index 10-20, detected at 12
    y_true = np.zeros(50, dtype=bool)
    y_true[10:20] = True

    scores = np.zeros(50)
    scores[12:20] = 0.9  # Detected from 12 onwards

    latency = compute_latency(y_true, scores, threshold=0.5)

    # Onset at 10, detection at 12 -> latency = 2
    assert latency.median_latency == 2
    assert latency.detection_rate == 1.0


def test_compute_latency_multiple_anomalies():
    """Test latency with multiple anomalies."""
    y_true = np.zeros(100, dtype=bool)
    y_true[10:15] = True   # Anomaly 1
    y_true[50:55] = True   # Anomaly 2
    y_true[80:85] = True   # Anomaly 3

    scores = np.zeros(100)
    scores[12:15] = 0.9    # Detected at 12 (latency 2)
    scores[53:55] = 0.9    # Detected at 53 (latency 3)
    # Third anomaly not detected

    latency = compute_latency(y_true, scores, threshold=0.5)

    assert latency.median_latency == 2.5  # Median of [2, 3]
    assert latency.detection_rate == 2/3


def test_compute_latency_no_detection():
    """Test latency when no anomalies detected."""
    y_true = np.zeros(50, dtype=bool)
    y_true[10:20] = True
    scores = np.zeros(50)  # Never exceeds threshold

    latency = compute_latency(y_true, scores, threshold=0.5)

    assert latency.median_latency == 0
    assert latency.detection_rate == 0


def test_compute_per_sensor_metrics_univariate():
    """Test per-sensor metrics with univariate data."""
    y_true = np.zeros(50)
    y_true[10:20] = 1
    scores = np.zeros(50)
    scores[12:20] = 0.9

    results = compute_per_sensor_metrics(y_true, scores, sensor_names=["sensor_0"])

    assert len(results) == 1
    assert results[0].sensor_name == "sensor_0"
    assert results[0].f1 > 0
    assert results[0].latency is not None


def test_compute_per_sensor_metrics_multivariate():
    """Test per-sensor metrics with multivariate data."""
    y_true = np.zeros((50, 3))
    y_true[10:20, 0] = 1  # Anomaly only in sensor 0
    y_true[30:40, 1] = 1  # Anomaly only in sensor 1

    scores = np.zeros((50, 3))
    scores[12:20, 0] = 0.9
    scores[33:40, 1] = 0.9

    results = compute_per_sensor_metrics(y_true, scores, sensor_names=["A", "B", "C"])

    assert len(results) == 3
    assert results[0].sensor_name == "A"
    assert results[0].f1 > 0  # Has anomaly
    assert results[1].sensor_name == "B"
    assert results[1].f1 > 0  # Has anomaly
    assert results[2].sensor_name == "C"
    assert results[2].f1 == 0  # No anomaly


def test_compute_per_sensor_metrics_with_fixed_threshold():
    """Test per-sensor metrics with fixed threshold."""
    y_true = np.zeros((50, 2))
    y_true[10:20, 0] = 1
    y_true[30:40, 1] = 1

    scores = np.zeros((50, 2))
    scores[12:20, 0] = 0.9
    scores[33:40, 1] = 0.9

    results = compute_per_sensor_metrics(
        y_true, scores, threshold=0.8
    )

    assert len(results) == 2
    assert results[0].best_threshold == 0.8
    assert results[1].best_threshold == 0.8


def test_aggregate_metrics():
    """Test aggregate metrics computation."""
    per_sensor = [
        PerSensorMetrics("A", 0.8, 0.7, 0.75, 0.85, 0.9, 0.5),
        PerSensorMetrics("B", 0.9, 0.8, 0.85, 0.9, 0.95, 0.6),
        PerSensorMetrics("C", 0.7, 0.6, 0.65, 0.75, 0.85, 0.4),
    ]

    aggregate = aggregate_metrics(per_sensor)

    assert abs(aggregate.macro_precision - 0.8) < 1e-6
    assert abs(aggregate.macro_recall - 0.7) < 1e-6
    assert abs(aggregate.macro_f1 - 0.75) < 1e-6


def test_evaluate_multivariate():
    """Test full multivariate evaluation."""
    y_true = np.zeros((100, 3))
    y_true[10:20, 0] = 1
    y_true[30:40, 1] = 1
    y_true[50:60, 2] = 1

    scores = np.zeros((100, 3))
    scores[12:20, 0] = 0.9
    scores[33:40, 1] = 0.9
    scores[52:60, 2] = 0.9

    per_sensor, aggregate = evaluate_multivariate(y_true, scores)

    assert len(per_sensor) == 3
    assert aggregate.macro_f1 > 0


def test_latency_result_dataclass():
    """Test LatencyResult dataclass."""
    from evaluation.benchmarks.metrics_ext import LatencyResult

    lr = LatencyResult(
        median_latency=2.5,
        p95_latency=5.0,
        mean_latency=3.0,
        max_latency=10.0,
        detection_rate=0.8,
    )
    assert lr.median_latency == 2.5
    assert lr.detection_rate == 0.8


def test_per_sensor_metrics_dataclass():
    """Test PerSensorMetrics dataclass."""
    psm = PerSensorMetrics(
        sensor_name="test",
        precision=0.8,
        recall=0.7,
        f1=0.75,
        pr_auc=0.85,
        roc_auc=0.9,
        best_threshold=0.5,
    )
    assert psm.sensor_name == "test"
    assert psm.latency is None