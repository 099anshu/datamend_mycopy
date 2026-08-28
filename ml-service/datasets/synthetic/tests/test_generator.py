"""Tests for synthetic dataset generator."""

import numpy as np

from datasets.synthetic.generator import generate_dataset
from datasets.synthetic.attributes import get_supported_anomaly_types, get_supported_patterns


def test_generate_univariate_dataset():
    """Test univariate dataset generation."""
    dataset = generate_dataset(
        num_samples=10,
        seq_len=100,
        anomaly_sample_ratio=1.0,
        is_multivariate=False,
        seed=42,
    )

    assert len(dataset) == 10
    for sample in dataset:
        assert "normal_time_series" in sample
        assert "time_series" in sample
        assert "labels" in sample
        assert "attribute" in sample

        # Check shapes
        assert sample["normal_time_series"].shape == (100,)
        assert sample["time_series"].shape == (100,)
        assert sample["labels"].shape == (100,)
        assert sample["labels"].dtype == np.int64 or sample["labels"].dtype == np.int32

        # Check attribute structure
        assert "metric" in sample["attribute"]
        assert "anomalies" in sample["attribute"]
        assert "pattern" in sample["attribute"]


def test_generate_multivariate_dataset():
    """Test multivariate dataset generation."""
    dataset = generate_dataset(
        num_samples=5,
        seq_len=200,
        anomaly_sample_ratio=1.0,
        is_multivariate=True,
        num_features=3,
        seed=42,
    )

    assert len(dataset) == 5
    for sample in dataset:
        assert sample["normal_time_series"].shape == (200, 3)
        assert sample["time_series"].shape == (200, 3)
        assert sample["labels"].shape == (200,)

        # Check attribute structure for multivariate
        attr = sample["attribute"]
        assert "attribute_list" in attr
        assert "num_features" in attr
        assert "is_endogenous" in attr
        assert "dag" in attr
        assert attr["num_features"] == 3
        assert len(attr["attribute_list"]) == 3
        assert len(attr["is_endogenous"]) == 3
        assert len(attr["dag"]) == 3


def test_anomaly_sample_ratio():
    """Test anomaly sample ratio parameter."""
    # All normal
    dataset_normal = generate_dataset(
        num_samples=20,
        seq_len=100,
        anomaly_sample_ratio=0.0,
        is_multivariate=False,
        seed=42,
    )
    total_anomalies = sum(s["labels"].sum() for s in dataset_normal)
    assert total_anomalies == 0

    # All anomalous
    dataset_anomalous = generate_dataset(
        num_samples=20,
        seq_len=100,
        anomaly_sample_ratio=1.0,
        is_multivariate=False,
        seed=42,
    )
    total_anomalies = sum(s["labels"].sum() for s in dataset_anomalous)
    assert total_anomalies > 0

    # Mixed
    dataset_mixed = generate_dataset(
        num_samples=20,
        seq_len=100,
        anomaly_sample_ratio=0.5,
        is_multivariate=False,
        seed=42,
    )
    anomalous_samples = sum(1 for s in dataset_mixed if s["labels"].sum() > 0)
    # Should be approximately 10 (allow some variance)
    assert 5 <= anomalous_samples <= 15


def test_random_sequence_length():
    """Test random sequence length when seq_len=None."""
    dataset = generate_dataset(
        num_samples=5,
        seq_len=None,
        anomaly_sample_ratio=1.0,
        is_multivariate=False,
        seed=42,
    )

    lengths = [len(s["labels"]) for s in dataset]
    # All lengths should be between 100 and 10000
    assert all(100 <= l <= 10000 for l in lengths)


def test_specific_anomaly_types():
    """Test generating with specific anomaly types."""
    dataset = generate_dataset(
        num_samples=10,
        seq_len=100,
        anomaly_sample_ratio=1.0,
        is_multivariate=False,
        metrics=["spike", "drift"],
        seed=42,
    )

    for sample in dataset:
        for anomaly in sample["attribute"]["anomalies"]:
            assert anomaly["type"] in ["spike", "drift"]


def test_multivariate_specific_anomaly_types():
    """Test multivariate with specific anomaly types."""
    dataset = generate_dataset(
        num_samples=5,
        seq_len=100,
        anomaly_sample_ratio=1.0,
        is_multivariate=True,
        num_features=3,
        metrics=["spike", "level_shift"],
        seed=42,
    )

    for sample in dataset:
        for anomaly in sample["attribute"]["anomalies"]:
            assert anomaly["type"] in ["spike", "level_shift"]


def test_reproducibility():
    """Test that same seed produces identical results."""
    dataset1 = generate_dataset(
        num_samples=10,
        seq_len=100,
        anomaly_sample_ratio=1.0,
        is_multivariate=False,
        seed=42,
    )

    dataset2 = generate_dataset(
        num_samples=10,
        seq_len=100,
        anomaly_sample_ratio=1.0,
        is_multivariate=False,
        seed=42,
    )

    for s1, s2 in zip(dataset1, dataset2, strict=False):
        np.testing.assert_array_equal(s1["normal_time_series"], s2["normal_time_series"])
        np.testing.assert_array_equal(s1["time_series"], s2["time_series"])
        np.testing.assert_array_equal(s1["labels"], s2["labels"])


def test_get_supported_anomaly_types():
    """Test getting supported anomaly types."""
    types = get_supported_anomaly_types()
    assert "spike" in types
    assert "drift" in types
    assert "trend_break" in types
    assert "seasonality_break" in types
    assert "noise_increase" in types
    assert "level_shift" in types
    assert "pattern_change" in types


def test_get_supported_patterns():
    """Test getting supported pattern types."""
    patterns = get_supported_patterns()
    assert "stationary" in patterns
    assert "linear_trend" in patterns
    assert "single_seasonal" in patterns
    assert "multi_seasonal" in patterns


def test_multivariate_dag_structure():
    """Test that multivariate DAG is valid (no cycles)."""
    dataset = generate_dataset(
        num_samples=3,
        seq_len=100,
        anomaly_sample_ratio=1.0,
        is_multivariate=True,
        num_features=5,
        seed=42,
    )

    for sample in dataset:
        dag = np.array(sample["attribute"]["dag"])
        # Check upper triangular (DAG property)
        assert np.allclose(dag, np.triu(dag))
        # Check no self-loops
        assert np.all(np.diag(dag) == 0)


def test_save_load_dataset():
    """Test saving and loading dataset."""
    import tempfile
    import os

    dataset = generate_dataset(
        num_samples=5,
        seq_len=100,
        anomaly_sample_ratio=1.0,
        is_multivariate=False,
        seed=42,
    )

    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
        temp_path = f.name

    try:
        from datasets.synthetic.generator import save_dataset, load_dataset
        save_dataset(dataset, temp_path)
        loaded = load_dataset(temp_path)

        assert len(loaded) == len(dataset)
        for orig, loaded_sample in zip(dataset, loaded, strict=False):
            np.testing.assert_array_equal(orig["normal_time_series"], loaded_sample["normal_time_series"])
            np.testing.assert_array_equal(orig["time_series"], loaded_sample["time_series"])
            np.testing.assert_array_equal(orig["labels"], loaded_sample["labels"])
    finally:
        os.unlink(temp_path)