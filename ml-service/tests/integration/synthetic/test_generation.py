"""Integration tests for synthetic dataset generation."""

import pytest
import numpy as np

from datasets.synthetic import generate_dataset, save_dataset, load_dataset
from detectors.timercd import TimeRCDDetector
from evaluation.benchmarks import BenchmarkRunner, BenchmarkConfig, ThresholdStrategy


@pytest.mark.integration
def test_basic_generation():
    """Test basic univariate generation."""
    dataset = generate_dataset(
        num_samples=5,
        seq_len=100,
        anomaly_sample_ratio=1.0,
        is_multivariate=False,
        seed=42,
    )

    assert len(dataset) == 5
    for sample in dataset:
        assert sample["time_series"].shape == (100,)
        assert sample["labels"].sum() > 0


@pytest.mark.integration
def test_multivariate_generation():
    """Test multivariate generation."""
    dataset = generate_dataset(
        num_samples=3,
        seq_len=200,
        anomaly_sample_ratio=1.0,
        is_multivariate=True,
        num_features=3,
        seed=42,
    )

    assert len(dataset) == 3
    for sample in dataset:
        assert sample["time_series"].shape == (200, 3)
        assert sample["labels"].shape == (200,)


@pytest.mark.integration
def test_specific_anomalies():
    """Test generation with specific anomaly types."""
    dataset = generate_dataset(
        num_samples=5,
        seq_len=100,
        anomaly_sample_ratio=1.0,
        is_multivariate=False,
        metrics=["spike", "drift"],
        seed=42,
    )

    anomaly_types = set()
    for sample in dataset:
        for anomaly in sample['attribute']['anomalies']:
            anomaly_types.add(anomaly['type'])

    assert anomaly_types == {"spike", "drift"}


@pytest.mark.integration
def test_save_load_dataset():
    """Test saving and loading dataset."""
    import tempfile
    import os

    dataset = generate_dataset(
        num_samples=3,
        seq_len=100,
        anomaly_sample_ratio=1.0,
        is_multivariate=False,
        seed=42,
    )

    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
        temp_path = f.name

    try:
        save_dataset(dataset, temp_path)
        loaded = load_dataset(temp_path)

        assert len(loaded) == len(dataset)
        for orig, loaded_sample in zip(dataset, loaded, strict=False):
            np.testing.assert_array_equal(orig["normal_time_series"], loaded_sample["normal_time_series"])
            np.testing.assert_array_equal(orig["time_series"], loaded_sample["time_series"])
            np.testing.assert_array_equal(orig["labels"], loaded_sample["labels"])
    finally:
        os.unlink(temp_path)


@pytest.mark.integration
def test_benchmark_synthetic():
    """Test benchmark on synthetic data."""
    detector = TimeRCDDetector()
    runner = BenchmarkRunner(detector)

    config = BenchmarkConfig(
        dataset_type="synthetic",
        num_samples=10,
        seq_len=100,
        anomaly_sample_ratio=1.0,
        is_multivariate=True,
        num_features=3,
        seed=42,
        threshold_strategy=ThresholdStrategy.BEST_F1,
    )

    result = runner.run(config)

    eval_result = result.evaluation_result
    assert 0 <= eval_result.f1 <= 1
    assert 0 <= eval_result.precision <= 1
    assert 0 <= eval_result.recall <= 1
    assert 0 <= eval_result.pr_auc <= 1
    assert 0 <= eval_result.roc_auc <= 1
    assert result.per_sensor_metrics is not None
    assert len(result.per_sensor_metrics) == 3


@pytest.mark.integration
def test_threshold_strategies():
    """Test different threshold strategies."""
    detector = TimeRCDDetector()
    runner = BenchmarkRunner(detector)

    base_config = BenchmarkConfig(
        dataset_type="synthetic",
        num_samples=10,
        seq_len=100,
        anomaly_sample_ratio=1.0,
        is_multivariate=False,
        seed=42,
    )

    strategies = [
        ThresholdStrategy.BEST_F1,
        ThresholdStrategy.YOUDEN_J,
        ThresholdStrategy.FIXED_FPR,
        ThresholdStrategy.FIXED_RECALL,
    ]

    for strategy in strategies:
        config = BenchmarkConfig(**base_config.__dict__, threshold_strategy=strategy)
        if strategy == ThresholdStrategy.FIXED_FPR:
            config.target_fpr = 0.05
        elif strategy == ThresholdStrategy.FIXED_RECALL:
            config.target_recall = 0.90

        result = runner.run(config)
        eval_result = result.evaluation_result
        assert 0 <= eval_result.f1 <= 1
        assert 0 <= eval_result.precision <= 1
        assert 0 <= eval_result.recall <= 1


@pytest.mark.integration
def test_baseline_management():
    """Test baseline save/load/compare."""
    detector = TimeRCDDetector()
    runner = BenchmarkRunner(detector)

    config = BenchmarkConfig(
        dataset_type="synthetic",
        num_samples=10,
        seq_len=100,
        anomaly_sample_ratio=1.0,
        is_multivariate=False,
        seed=42,
    )

    result = runner.run(config)

    baseline_name = "test_integration_baseline"
    baseline_path = runner.save_baseline(result, baseline_name)
    assert baseline_path.exists()

    baseline = runner.load_baseline(baseline_name)
    assert baseline is not None

    comparison = runner.compare_to_baseline(result, baseline_name, regression_threshold=0.05)
    assert comparison["passed"] is True
    assert len(comparison["regressions"]) == 0