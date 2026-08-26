"""Tests for anomaly injection functions."""

import numpy as np

from datasets.synthetic.anomalies import (
    inject_spike,
    inject_drift,
    inject_trend_break,
    inject_seasonality_break,
    inject_noise_increase,
    inject_level_shift,
    inject_pattern_change,
    inject_multiple_anomalies,
    AnomalySpec,
)


def test_inject_spike():
    """Test spike injection."""
    series = np.zeros(100)
    result, labels = inject_spike(series, start_idx=50, duration=3, magnitude=5.0)

    assert np.allclose(result[:50], 0)
    assert np.allclose(result[53:], 0)
    assert np.allclose(result[50:53], 5.0)
    assert np.allclose(labels[50:53], 1)
    assert np.allclose(labels[:50], 0)
    assert np.allclose(labels[53:], 0)


def test_inject_spike_down():
    """Test spike injection with down direction."""
    series = np.zeros(100)
    result, labels = inject_spike(series, start_idx=50, duration=2, magnitude=5.0, direction="down")

    assert np.allclose(result[50:52], -5.0)


def test_inject_drift():
    """Test drift injection."""
    series = np.zeros(100)
    result, labels = inject_drift(series, start_idx=20, duration=30, magnitude=2.0)

    # Drift should be linear from 0 to magnitude
    assert result[19] == 0
    assert result[50] == 0  # End of drift
    # Check linear increase
    drift_values = result[20:50]
    expected = np.linspace(0, 2.0, 30)
    np.testing.assert_allclose(drift_values, expected, rtol=1e-5)


def test_inject_trend_break():
    """Test trend break injection."""
    series = np.zeros(100)
    result, labels = inject_trend_break(series, start_idx=30, duration=40, magnitude=3.0)

    assert np.allclose(result[:30], 0)
    assert np.allclose(result[70:], 0)  # Returns to 0 after duration (linear shape 0->3->0)
    assert labels[30:70].sum() == 40
    # Check linear ramp up
    assert result[30] == 0
    assert result[69] == 3.0 * 39/39  # Full magnitude at end of duration


def test_inject_seasonality_break():
    """Test seasonality break injection."""
    series = np.zeros(100)
    result, labels = inject_seasonality_break(series, start_idx=10, duration=20, magnitude=1.5, period=10)

    assert np.allclose(result[:10], 0)
    assert np.allclose(result[30:], 0)
    assert labels[10:30].sum() == 20
    # Check sinusoidal pattern
    assert not np.allclose(result[10:30], 0)


def test_inject_noise_increase():
    """Test noise increase injection."""
    rng = np.random.default_rng(42)
    series = np.zeros(100)
    result, labels = inject_noise_increase(series, start_idx=40, duration=20, magnitude=2.0, rng=rng)

    assert np.allclose(result[:40], 0)
    assert np.allclose(result[60:], 0)
    assert labels[40:60].sum() == 20
    # Noise should have been added
    assert not np.allclose(result[40:60], 0)


def test_inject_level_shift():
    """Test level shift injection."""
    series = np.zeros(100)
    result, labels = inject_level_shift(series, start_idx=50, magnitude=4.0)

    assert np.allclose(result[:50], 0)
    assert np.allclose(result[50:], 4.0)
    assert labels[50:].sum() == 50


def test_inject_level_shift_down():
    """Test level shift down."""
    series = np.zeros(100)
    result, labels = inject_level_shift(series, start_idx=50, magnitude=4.0, direction="down")

    assert np.allclose(result[50:], -4.0)


def test_inject_pattern_change():
    """Test pattern change injection."""
    series = np.zeros(100)
    result, labels = inject_pattern_change(series, start_idx=25, duration=50, magnitude=2.0)

    assert np.allclose(result[:25], 0)
    assert np.allclose(result[75:], 0)
    assert labels[25:75].sum() == 50


def test_inject_multiple_anomalies():
    """Test injecting multiple anomalies."""
    series = np.zeros(200)

    specs = [
        AnomalySpec("spike", 50, 3, 5.0),
        AnomalySpec("drift", 100, 20, 2.0),
        AnomalySpec("level_shift", 150, 1, 3.0),  # duration=1 (ignored for level_shift)
    ]

    result, labels = inject_multiple_anomalies(series, specs)

    # Check all anomaly regions are labeled
    assert labels[50:53].sum() == 3
    assert labels[100:120].sum() == 20
    assert labels[150:].sum() == 50

    # Check total anomalies
    assert labels.sum() == 73


def test_multiple_anomalies_overlap():
    """Test overlapping anomalies combine correctly."""
    series = np.zeros(100)

    specs = [
        AnomalySpec("spike", 50, 10, 5.0),
        AnomalySpec("spike", 55, 10, 3.0),  # Overlaps with first
    ]

    result, labels = inject_multiple_anomalies(series, specs)

    # In overlap region (55-60), both anomalies apply
    assert result[55] == 8.0  # 5 + 3
    assert labels[55] == 1


def test_anomaly_spec_dataclass():
    """Test AnomalySpec dataclass."""
    spec = AnomalySpec(
        anomaly_type="spike",
        start_idx=10,
        duration=5,
        magnitude=3.0,
        shape="constant",
        direction="up",
    )
    assert spec.anomaly_type == "spike"
    assert spec.start_idx == 10
    assert spec.duration == 5
    assert spec.magnitude == 3.0
    assert spec.shape == "constant"
    assert spec.direction == "up"


def test_edge_cases():
    """Test edge cases."""
    # Anomaly at end of series
    series = np.zeros(100)
    result, labels = inject_spike(series, start_idx=98, duration=5, magnitude=2.0)
    assert labels[98:].sum() == 2  # Only 2 points fit

    # Anomaly at start
    result, labels = inject_spike(series, start_idx=0, duration=5, magnitude=2.0)
    assert labels[:5].sum() == 5

    # Zero duration
    result, labels = inject_spike(series, start_idx=50, duration=0, magnitude=2.0)
    assert labels.sum() == 0

    # Start beyond series length
    result, labels = inject_spike(series, start_idx=150, duration=5, magnitude=2.0)
    assert labels.sum() == 0