# Example: Semi-Synthetic Evaluation (TSDB + Injected Anomalies)

This document shows how to use semi-synthetic evaluation - injecting synthetic anomalies into real TSDB data for supervised evaluation on realistic data.

## Example 1: Semi-Synthetic ETTh1 (All Sensors)

```python
from datasets.synthetic import inject_anomalies_into_tsdb, InjectionConfig
from detectors.timercd import TimeRCDDetector

config = InjectionConfig(
    anomaly_types=["spike", "drift"],
    anomaly_intensity=3.0,
    num_anomalies_per_sensor=5,
    placement="random",
    avoid_high_score_regions=True,
    seed=42,
)

detector = TimeRCDDetector()
result = inject_anomalies_into_tsdb("ETTh1", config, detector=detector)

print(f"Sensors: {len(result['attribute']['sensor_names'])}")
print(f"Target sensors: {result['attribute']['target_sensors']}")
print(f"Shape: {result['time_series'].shape}")
print(f"Anomalous timesteps: {result['labels'].sum()} / {len(result['labels'])} "
      f"({result['labels'].mean()*100:.2f}%)")

# Per-sensor anomaly counts
print("\nPer-sensor anomalies:")
for i, sensor in enumerate(result['attribute']['sensor_names']):
    n_anom = result['per_sensor_labels'][:, i].sum()
    if n_anom > 0:
        print(f"  {sensor}: {n_anom}")
```

## Example 2: Targeted Injection (HUFL, MUFL only)

```python
config = InjectionConfig(
    target_sensors=["HUFL", "MUFL"],
    anomaly_types=["spike", "drift", "trend_break"],
    anomaly_intensity=4.0,
    num_anomalies_per_sensor=3,
    placement="periodic",
    periodic_interval=1000,
    seed=42,
)

detector = TimeRCDDetector()
result = inject_anomalies_into_tsdb("ETTh1", config, detector=detector)

print(f"Target sensors: {result['attribute']['target_sensors']}")
print(f"Anomalous timesteps: {result['labels'].sum()}")

# Verify only target sensors have anomalies
sensor_names = result['attribute']['sensor_names']
for sensor in ["HUFL", "MUFL"]:
    idx = sensor_names.index(sensor)
    n_anom = result['per_sensor_labels'][:, idx].sum()
    print(f"  {sensor}: {n_anom} anomalies")

for sensor in ["HULL", "MULL", "LUFL", "LULL", "OT"]:
    idx = sensor_names.index(sensor)
    n_anom = result['per_sensor_labels'][:, idx].sum()
    assert n_anom == 0, f"{sensor} should have 0 anomalies"
print("  Non-target sensors: 0 anomalies (verified)")
```

## Example 3: Benchmark on Semi-Synthetic ETTh1

```python
from detectors.timercd import TimeRCDDetector
from evaluation.benchmarks import BenchmarkRunner, BenchmarkConfig, ThresholdStrategy

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
print(f"F1: {eval_result.f1:.4f}")
print(f"Precision: {eval_result.precision:.4f}")
print(f"Recall: {eval_result.recall:.4f}")
print(f"PR-AUC: {eval_result.pr_auc:.4f}")
print(f"ROC-AUC: {eval_result.roc_auc:.4f}")

if result.per_sensor_metrics:
    print("\nPer-sensor metrics:")
    for m in result.per_sensor_metrics:
        if m.f1 > 0:
            print(f"  {m.sensor_name}: F1={m.f1:.4f}, P={m.precision:.4f}, R={m.recall:.4f}")
```

## Example 4: Clean TSDB vs Semi-Synthetic Comparison

```python
detector = TimeRCDDetector()
runner = BenchmarkRunner(detector)

# Semi-synthetic with known ground truth
semi_config = BenchmarkConfig(
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

semi_result = runner.run(semi_config)
print(f"Semi-synthetic (with ground truth):")
print(f"  F1: {semi_result.evaluation_result.f1:.4f}")
print(f"  PR-AUC: {semi_result.evaluation_result.pr_auc:.4f}")

print("\nNote: Clean TSDB has no ground truth, so supervised metrics")
print("cannot be computed. Semi-synthetic enables supervised evaluation")
print("on realistic data with known anomaly locations.")
```

## Example 5: Injection Configuration Variations

```python
detector = TimeRCDDetector()

configs = [
    ("Low intensity (1 std)", InjectionConfig(anomaly_intensity=1.0, seed=42)),
    ("Medium intensity (3 std)", InjectionConfig(anomaly_intensity=3.0, seed=42)),
    ("High intensity (5 std)", InjectionConfig(anomaly_intensity=5.0, seed=42)),
]

for name, config in configs:
    result = inject_anomalies_into_tsdb("ETTh1", config, detector=detector)
    diff = np.abs(result["time_series"] - result["normal_time_series"])
    max_diff = diff[result["labels"] == 1].max() if result["labels"].sum() > 0 else 0
    print(f"  {name}: max anomaly magnitude = {max_diff:.2f}")
```

## Running the Examples

Save the code snippets above as Python scripts and run them from the `ml-service` directory:

```bash
cd ml-service
python examples/semi_synthetic_evaluation.py
```

## Key Concepts

- **Semi-synthetic evaluation**: Inject synthetic anomalies with known ground truth into real TSDB data
- **Clean window detection**: Uses TimeRCD scores to avoid injecting over potentially real anomalies
- **Targeted injection**: Choose specific sensors for anomaly injection
- **Configurable intensity**: Control anomaly magnitude in standard deviations
- **Placement strategies**: Random or periodic anomaly placement