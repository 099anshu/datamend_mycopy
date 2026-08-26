# Example: Synthetic Dataset Generation and Evaluation

This document shows how to use the synthetic dataset generation and benchmarking capabilities.

## Example 1: Basic Univariate Generation

```python
from datasets.synthetic import generate_dataset, save_dataset

dataset = generate_dataset(
    num_samples=10,
    seq_len=500,
    anomaly_sample_ratio=1.0,
    is_multivariate=False,
    seed=42,
)

print(f"Generated {len(dataset)} samples")
for i, sample in enumerate(dataset[:3]):
    print(f"  Sample {i}: length={len(sample['time_series'])}, "
          f"anomalies={sample['labels'].sum()}, "
          f"pattern={sample['attribute']['pattern']}")

save_dataset(dataset, "example_univariate.pkl")
print("Saved to example_univariate.pkl")
```

## Example 2: Multivariate Generation (5 features)

```python
dataset = generate_dataset(
    num_samples=5,
    seq_len=1000,
    anomaly_sample_ratio=1.0,
    is_multivariate=True,
    num_features=5,
    seed=42,
)

print(f"Generated {len(dataset)} samples")
sample = dataset[0]
print(f"  Shape: {sample['time_series'].shape}")
print(f"  Features: {sample['attribute']['num_features']}")
print(f"  DAG shape: {np.array(sample['attribute']['dag']).shape}")
print(f"  Endogenous: {sample['attribute']['is_endogenous']}")
print(f"  Anomalies injected: {len(sample['attribute']['anomalies'])}")

save_dataset(dataset, "example_multivariate.pkl")
print("Saved to example_multivariate.pkl")
```

## Example 3: Specific Anomaly Types (spike + drift)

```python
dataset = generate_dataset(
    num_samples=10,
    seq_len=500,
    anomaly_sample_ratio=1.0,
    is_multivariate=False,
    metrics=["spike", "drift"],
    seed=42,
)

anomaly_types = set()
for sample in dataset:
    for anomaly in sample['attribute']['anomalies']:
        anomaly_types.add(anomaly['type'])

print(f"Anomaly types used: {anomaly_types}")
assert anomaly_types == {"spike", "drift"}
```

## Example 4: Benchmark on Synthetic Data

```python
from detectors.timercd import TimeRCDDetector
from evaluation.benchmarks import BenchmarkRunner, BenchmarkConfig, ThresholdStrategy

detector = TimeRCDDetector()
runner = BenchmarkRunner(detector)

config = BenchmarkConfig(
    dataset_type="synthetic",
    num_samples=20,
    seq_len=500,
    anomaly_sample_ratio=1.0,
    is_multivariate=True,
    num_features=3,
    use_attribute_set=True,
    seed=42,
    threshold_strategy=ThresholdStrategy.BEST_F1,
)

result = runner.run(config)

eval_result = result.evaluation_result
print(f"F1: {eval_result.f1:.4f}")
print(f"Precision: {eval_result.precision:.4f}")
print(f"Recall: {eval_result.recall:.4f}")
print(f"PR-AUC: {eval_result.pr_auc:.4f}")
print(f"ROC-AUC: {eval_result.roc_auc:.4f}")
print(f"Best threshold: {eval_result.best_threshold:.4f}")

if result.per_sensor_metrics:
    print("\nPer-sensor metrics:")
    for m in result.per_sensor_metrics:
        print(f"  {m.sensor_name}: F1={m.f1:.4f}, P={m.precision:.4f}, R={m.recall:.4f}")

if result.latency:
    lat = result.latency
    print(f"\nLatency: median={lat.median_latency:.1f}, p95={lat.p95_latency:.1f}, "
          f"detection_rate={lat.detection_rate:.2%}")
```

## Example 5: Threshold Selection Strategies

```python
detector = TimeRCDDetector()
runner = BenchmarkRunner(detector)

config = BenchmarkConfig(
    dataset_type="synthetic",
    num_samples=20,
    seq_len=500,
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
    config.threshold_strategy = strategy
    if strategy == ThresholdStrategy.FIXED_FPR:
        config.target_fpr = 0.05
    elif strategy == ThresholdStrategy.FIXED_RECALL:
        config.target_recall = 0.90

    result = runner.run(config)
    eval_result = result.evaluation_result
    print(f"{strategy.value:15s}: F1={eval_result.f1:.4f}, "
          f"P={eval_result.precision:.4f}, R={eval_result.recall:.4f}, "
          f"thresh={eval_result.best_threshold:.4f}")
```

## Example 6: Fixed Threshold Evaluation (API default 0.8)

```python
detector = TimeRCDDetector()
runner = BenchmarkRunner(detector)

config = BenchmarkConfig(
    dataset_type="synthetic",
    num_samples=20,
    seq_len=500,
    anomaly_sample_ratio=1.0,
    is_multivariate=False,
    seed=42,
    custom_threshold=0.8,  # API default threshold
)

result = runner.run(config)
eval_result = result.evaluation_result
print(f"F1: {eval_result.f1:.4f}")
print(f"Precision: {eval_result.precision:.4f}")
print(f"Recall: {eval_result.recall:.4f}")
print(f"Threshold: {eval_result.best_threshold:.4f} (fixed)")
```

## Running the Examples

Save the code snippets above as Python scripts and run them from the `ml-service` directory:

```bash
cd ml-service
python examples/synthetic_generation.py
```