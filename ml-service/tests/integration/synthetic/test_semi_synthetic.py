"""Integration tests for semi-synthetic evaluation."""

import pytest
import numpy as np

try:
    from datasets.synthetic import inject_anomalies_into_tsdb, InjectionConfig
    from detectors.timercd import TimeRCDDetector
    from evaluation.benchmarks import BenchmarkRunner, BenchmarkConfig, ThresholdStrategy
    TSDB_AVAILABLE = True
except ImportError:
    TSDB_AVAILABLE = False


@pytest.mark.skipif(not TSDB_AVAILABLE, reason="TSDB or TimeRCD not available")
@pytest.mark.integration
def test_inject_anomalies_basic():
    """Test basic TSDB anomaly injection."""
    config = InjectionConfig(
        anomaly_types=["spike"],
        anomaly_intensity=3.0,
        num_anomalies_per_sensor=2,
        seed=42,
    )

    detector = TimeRCDDetector()
    result = inject_anomalies_into_tsdb("ETTh1", config, detector=detector)

    assert "normal_time_series" in result
    assert "time_series" in result
    assert "labels" in result
    assert "per_sensor_labels" in result
    assert "attribute" in result

    assert result["normal_time_series"].shape == result["time_series"].shape
    assert result["labels"].shape[0] == result["time_series"].shape[0]
    assert result["per_sensor_labels"].shape == result["time_series"].shape


@pytest.mark.skipif(not TSDB_AVAILABLE, reason="TSDB or TimeRCD not available")
@pytest.mark.integration
def test_inject_anomalies_targeted():
    """Test injection into specific sensors only."""
    config = InjectionConfig(
        target_sensors=["HUFL", "MUFL"],
        anomaly_types=["spike", "drift"],
        anomaly_intensity=3.0,
        num_anomalies_per_sensor=3,
        seed=42,
    )

    detector = TimeRCDDetector()
    result = inject_anomalies_into_tsdb("ETTh1", config, detector=detector)

    attr = result["attribute"]
    assert set(attr["target_sensors"]) == {"HUFL", "MUFL"}

    sensor_names = attr["sensor_names"]
    hufl_idx = sensor_names.index("HUFL")
    mull_idx = sensor_names.index("MULL")

    assert result["per_sensor_labels"][:, hufl_idx].sum() > 0
    assert result["per_sensor_labels"][:, mull_idx].sum() == 0


@pytest.mark.skipif(not TSDB_AVAILABLE, reason="TSDB or TimeRCD not available")
@pytest.mark.integration
def test_inject_anomalies_benchmark():
    """Test benchmark on semi-synthetic data."""
    detector = TimeRCDDetector()
    runner = BenchmarkRunner(detector)

    config = BenchmarkConfig(
        dataset_type="semi_synthetic",
        tsdb_dataset="ETTh1",
        injection_config=InjectionConfig(
            anomaly_types=["spike", "drift"],
            anomaly_intensity=3.0,
            num_anomalies_per_sensor=5,
            seed=42,
        ),
        threshold_strategy=ThresholdStrategy.BEST_F1,
    )

    result = runner.run(config)

    eval_result = result.evaluation_result
    assert 0 <= eval_result.f1 <= 1
    assert 0 <= eval_result.precision <= 1
    assert 0 <= eval_result.recall <= 1
    assert 0 <= eval_result.pr_auc <= 1
    assert 0 <= eval_result.roc_auc <= 1

    if result.per_sensor_metrics:
        for m in result.per_sensor_metrics:
            if m.f1 > 0:
                assert 0 <= m.f1 <= 1