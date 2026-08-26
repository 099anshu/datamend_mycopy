"""Tests for semi-synthetic evaluation (TSDB injection)."""

import pytest

try:
    from datasets.synthetic.semi_synthetic import (
        inject_anomalies_into_tsdb,
        inject_anomalies_into_array,
        InjectionConfig,
        detect_clean_windows,
        select_injection_windows,
    )
    from detectors.timercd import TimeRCDDetector
    TSDB_AVAILABLE = True
except ImportError:
    TSDB_AVAILABLE = False

import numpy as np


@pytest.mark.skipif(not TSDB_AVAILABLE, reason="TSDB or TimeRCD not available")
def test_inject_anomalies_into_tsdb_basic():
    """Test basic TSDB anomaly injection."""
    config = InjectionConfig(
        anomaly_types=["spike"],
        anomaly_intensity=3.0,
        num_anomalies_per_sensor=2,
        seed=42,
    )

    result = inject_anomalies_into_tsdb("ETTh1", config)

    assert "normal_time_series" in result
    assert "time_series" in result
    assert "labels" in result
    assert "per_sensor_labels" in result
    assert "attribute" in result

    # Check shapes
    assert result["normal_time_series"].shape == result["time_series"].shape
    assert result["labels"].shape[0] == result["time_series"].shape[0]
    assert result["per_sensor_labels"].shape == result["time_series"].shape

    # Check attribute metadata
    attr = result["attribute"]
    assert attr["source_tsdb_dataset"] == "ETTh1"
    assert "sensor_names" in attr
    assert "target_sensors" in attr
    assert "injection_config" in attr
    assert "injection_windows" in attr


@pytest.mark.skipif(not TSDB_AVAILABLE, reason="TSDB or TimeRCD not available")
def test_inject_anomalies_targeted_sensors():
    """Test injection into specific sensors only."""
    config = InjectionConfig(
        target_sensors=["HUFL", "MUFL"],
        anomaly_types=["spike", "drift"],
        anomaly_intensity=3.0,
        num_anomalies_per_sensor=3,
        seed=42,
    )

    result = inject_anomalies_into_tsdb("ETTh1", config)

    # Only target sensors should have anomalies
    attr = result["attribute"]
    assert set(attr["target_sensors"]) == {"HUFL", "MUFL"}

    # Check per-sensor labels
    sensor_names = attr["sensor_names"]
    hufl_idx = sensor_names.index("HUFL")
    mull_idx = sensor_names.index("MULL")

    # HUFL should have anomalies
    assert result["per_sensor_labels"][:, hufl_idx].sum() > 0
    # MULL should not (not in target_sensors)
    assert result["per_sensor_labels"][:, mull_idx].sum() == 0


@pytest.mark.skipif(not TSDB_AVAILABLE, reason="TSDB or TimeRCD not available")
def test_inject_anomalies_different_placements():
    """Test random vs periodic placement."""
    # Random placement
    config_random = InjectionConfig(
        anomaly_types=["spike"],
        anomaly_intensity=3.0,
        num_anomalies_per_sensor=5,
        placement="random",
        seed=42,
    )
    result_random = inject_anomalies_into_tsdb("ETTh1", config_random)

    # Periodic placement
    config_periodic = InjectionConfig(
        anomaly_types=["spike"],
        anomaly_intensity=3.0,
        num_anomalies_per_sensor=5,
        placement="periodic",
        periodic_interval=500,
        seed=42,
    )
    result_periodic = inject_anomalies_into_tsdb("ETTh1", config_periodic)

    # Both should have anomalies
    assert result_random["labels"].sum() > 0
    assert result_periodic["labels"].sum() > 0


@pytest.mark.skipif(not TSDB_AVAILABLE, reason="TSDB or TimeRCD not available")
def test_inject_anomalies_intensity():
    """Test anomaly intensity parameter."""
    config_low = InjectionConfig(
        anomaly_types=["spike"],
        anomaly_intensity=1.0,
        num_anomalies_per_sensor=2,
        seed=42,
    )
    config_high = InjectionConfig(
        anomaly_types=["spike"],
        anomaly_intensity=5.0,
        num_anomalies_per_sensor=2,
        seed=42,
    )

    result_low = inject_anomalies_into_tsdb("ETTh1", config_low)
    result_high = inject_anomalies_into_tsdb("ETTh1", config_high)

    # High intensity should produce larger deviations
    diff_low = np.abs(result_low["time_series"] - result_low["normal_time_series"])
    diff_high = np.abs(result_high["time_series"] - result_high["normal_time_series"])

    max_diff_low = diff_low[result_low["labels"] == 1].max()
    max_diff_high = diff_high[result_high["labels"] == 1].max()

    assert max_diff_high > max_diff_low


def test_inject_anomalies_into_array():
    """Test injection into generic numpy array."""
    data = np.random.randn(200, 3)
    config = InjectionConfig(
        target_sensors=["sensor_0", "sensor_1"],
        anomaly_types=["spike", "drift"],
        anomaly_intensity=3.0,
        num_anomalies_per_sensor=2,
        seed=42,
        avoid_high_score_regions=False,  # Disable to ensure injection happens
    )

    result = inject_anomalies_into_array(data, config, sensor_names=["sensor_0", "sensor_1", "sensor_2"])

    assert result["normal_time_series"].shape == data.shape
    assert result["time_series"].shape == data.shape
    assert result["labels"].shape[0] == data.shape[0]
    assert result["per_sensor_labels"].shape == data.shape

    # Only target sensors should have anomalies
    assert result["per_sensor_labels"][:, 0].sum() > 0
    assert result["per_sensor_labels"][:, 1].sum() > 0
    assert result["per_sensor_labels"][:, 2].sum() == 0


def test_detect_clean_windows():
    """Test clean window detection."""
    # Create data with known anomaly region
    data = np.zeros((200, 3))
    data[100:150, 0] = 10.0  # Obvious anomaly in sensor 0

    # Mock detector that returns high scores for anomaly region
    class MockDetector:
        def detect(self, data):
            scores = np.zeros(len(data))
            scores[100:150] = 0.9  # High score in anomaly region
            return scores

    detector = MockDetector()
    clean_windows = detect_clean_windows(data, detector, window_size=50, threshold=0.7)

    # Clean windows should not include anomaly region
    for start, end in clean_windows:
        # Should not overlap with 100-150
        assert end <= 100 or start >= 150


def test_select_injection_windows():
    """Test injection window selection."""
    clean_windows = [(0, 100), (150, 200)]
    rng = np.random.default_rng(42)

    windows = select_injection_windows(
        clean_windows=clean_windows,
        num_anomalies=5,
        anomaly_duration_range=(10, 20),
        placement="random",
        periodic_interval=None,
        rng=rng,
    )

    assert len(windows) <= 5
    for start, end in windows:
        duration = end - start
        assert 10 <= duration <= 20
        # Should be within clean windows
        in_clean = any(cs <= start and end <= ce for cs, ce in clean_windows)
        assert in_clean


def test_select_injection_windows_periodic():
    """Test periodic injection window selection."""
    clean_windows = [(0, 500)]
    rng = np.random.default_rng(42)

    windows = select_injection_windows(
        clean_windows=clean_windows,
        num_anomalies=10,
        anomaly_duration_range=(10, 20),
        placement="periodic",
        periodic_interval=100,
        rng=rng,
    )

    assert len(windows) <= 10
    # Check roughly periodic spacing
    for i in range(1, len(windows)):
        spacing = windows[i][0] - windows[i-1][0]
        # Should be around 100 (allow some variance due to duration)
        assert 80 <= spacing <= 120