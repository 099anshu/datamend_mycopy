# Example: Benchmarking and CI/CD Regression Testing

This document shows how to use the benchmarking framework for evaluating anomaly detectors and running CI/CD regression tests.

## Example 1: Basic Benchmark

```python
from detectors.timercd import TimeRCDDetector
from evaluation.benchmarks import BenchmarkRunner, BenchmarkConfig, ThresholdStrategy

detector = TimeRCDDetector()
runner = BenchmarkRunner(detector)

config = BenchmarkConfig(
    dataset_type="synthetic",
    num_samples=30,
    seq_len=500,
    anomaly_sample_ratio=1.0,
    is_multivariate=True,
    num_features=5,
    seed=42,
)

result = runner.run(config)
eval_result = result.evaluation_result

print(f"Dataset hash: {result.dataset_hash}")
print(f"Execution time: {result.execution_time:.2f}s")
print(f"\nOverall Metrics:")
print(f"  F1: {eval_result.f1:.4f}")
print(f"  Precision: {eval_result.precision:.4f}")
print(f"  Recall: {eval_result.recall:.4f}")
print(f"  PR-AUC: {eval_result.pr_auc:.4f}")
print(f"  ROC-AUC: {eval_result.roc_auc:.4f}")
print(f"  Best threshold: {eval_result.best_threshold:.4f}")
```

## Example 2: Multivariate Benchmark with Per-Sensor Metrics

```python
detector = TimeRCDDetector()
runner = BenchmarkRunner(detector)

config = BenchmarkConfig(
    dataset_type="synthetic",
    num_samples=20,
    seq_len=1000,
    anomaly_sample_ratio=1.0,
    is_multivariate=True,
    num_features=5,
    seed=42,
)

result = runner.run(config)

print("Per-Sensor Metrics:")
for m in result.per_sensor_metrics:
    lat_str = ""
    if m.latency:
        lat_str = f", latency_median={m.latency.median_latency:.1f}"
    print(f"  {m.sensor_name}: F1={m.f1:.4f}, P={m.precision:.4f}, "
          f"R={m.recall:.4f}{lat_str}")

print("\nAggregate Metrics:")
agg = result.aggregate_metrics
print(f"  Macro F1: {agg.macro_f1:.4f}")
print(f"  Macro Precision: {agg.macro_precision:.4f}")
print(f"  Macro Recall: {agg.macro_recall:.4f}")
```

## Example 3: Threshold Strategy Comparison

```python
detector = TimeRCDDetector()
runner = BenchmarkRunner(detector)

base_config = BenchmarkConfig(
    dataset_type="synthetic",
    num_samples=30,
    seq_len=500,
    anomaly_sample_ratio=1.0,
    is_multivariate=False,
    seed=42,
)

strategies = [
    (ThresholdStrategy.BEST_F1, {}),
    (ThresholdStrategy.YOUDEN_J, {}),
    (ThresholdStrategy.FIXED_FPR, {"target_fpr": 0.05}),
    (ThresholdStrategy.FIXED_RECALL, {"target_recall": 0.90}),
]

for strategy, kwargs in strategies:
    config = BenchmarkConfig(**base_config.__dict__, threshold_strategy=strategy, **kwargs)
    result = runner.run(config)
    eval_result = result.evaluation_result
    print(f"{strategy.value:15s}: F1={eval_result.f1:.4f}, "
          f"P={eval_result.precision:.4f}, R={eval_result.recall:.4f}, "
          f"thresh={eval_result.best_threshold:.4f}")
```

## Example 4: Baseline Management

```python
detector = TimeRCDDetector()
runner = BenchmarkRunner(detector)

config = BenchmarkConfig(
    dataset_type="synthetic",
    num_samples=30,
    seq_len=500,
    anomaly_sample_ratio=1.0,
    is_multivariate=False,
    seed=42,
)

result = runner.run(config)

# Save as baseline
baseline_name = "timercd_synthetic_univariate_v1"
baseline_path = runner.save_baseline(result, baseline_name)
print(f"Saved baseline to: {baseline_path}")

# Load and compare
baseline = runner.load_baseline(baseline_name)
print(f"Loaded baseline: {baseline['timestamp']}")

# Compare (should pass - same result)
comparison = runner.compare_to_baseline(result, baseline_name, regression_threshold=0.05)
print(f"Comparison passed: {comparison['passed']}")
print(f"Regressions: {len(comparison['regressions'])}")
print(f"Improvements: {len(comparison['improvements'])}")
```

## Example 5: CI Benchmark Suite

```python
detector = TimeRCDDetector()
runner = BenchmarkRunner(detector)

configs = create_standard_configs()

print(f"Running {len(configs)} standard configurations...")
for i, config in enumerate(configs):
    result = runner.run(config)
    eval_result = result.evaluation_result

    baseline_name = get_baseline_name(config, "timercd")
    comparison = runner.compare_to_baseline(result, baseline_name, regression_threshold=0.05)

    status = "PASS" if comparison["passed"] else "FAIL"
    print(f"  [{i+1}] {config.dataset_type} "
          f"{'multi' if config.is_multivariate else 'uni'}: "
          f"F1={eval_result.f1:.4f} [{status}]")

print("\nNote: Run 'python scripts/generate_synthetic.py ci-benchmark' for full CI suite")
```

## Example 6: Multi-Detector Comparison (Placeholder)

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

result = runner.run(config)

print("TimeRCD Results:")
print(f"  F1: {result.evaluation_result.f1:.4f}")
print(f"  PR-AUC: {result.evaluation_result.pr_auc:.4f}")

print("\nTo add another detector:")
print("  1. Implement AnomalyDetector interface")
print("  2. Create BenchmarkRunner(detector, name='my_detector')")
print("  3. Run same configs and compare results")
```

## Example 7: Export Results

```python
import json

detector = TimeRCDDetector()
runner = BenchmarkRunner(detector)

config = BenchmarkConfig(
    dataset_type="synthetic",
    num_samples=20,
    seq_len=500,
    anomaly_sample_ratio=1.0,
    is_multivariate=True,
    num_features=3,
    seed=42,
)

result = runner.run(config)

# Export to JSON
output_path = "benchmark_results.json"
with open(output_path, "w") as f:
    json.dump(result.to_dict(), f, indent=2)

print(f"Exported results to {output_path}")

# Also save as baseline
runner.save_baseline(result, "example_multivariate_baseline")
```

## Running the Examples

Save the code snippets above as Python scripts and run them from the `ml-service` directory:

```bash
cd ml-service
python examples/benchmarking.py
```

## CI/CD Integration

Run the full CI benchmark suite from command line:

```bash
# Run CI benchmarks (compares against baselines)
python scripts/generate_synthetic.py ci-benchmark

# Update baselines after verified improvements
python scripts/generate_synthetic.py ci-benchmark --update-baselines

# Generate markdown report
python scripts/generate_synthetic.py ci-benchmark --output-report ci_report.md
```

## Key Concepts

- **BenchmarkConfig**: Defines dataset, detector, and evaluation parameters
- **BenchmarkRunner**: Executes benchmarks and computes metrics
- **ThresholdStrategy**: BEST_F1, YOUDEN_J, FIXED_FPR, FIXED_RECALL
- **Baseline Management**: Versioned baselines for regression detection
- **Per-Sensor Metrics**: Detailed metrics for each sensor in multivariate data
- **Aggregate Metrics**: Macro and micro averages across sensors