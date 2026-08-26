# Synthetic Dataset Generator

This module provides synthetic and semi-synthetic time series anomaly detection dataset generation for controlled evaluation with ground-truth labels.

## Module Structure

```
datasets/synthetic/
├── __init__.py              # Public API exports
├── generator.py             # Main generate_dataset() function
├── ts_generator.py          # Univariate time series patterns
├── ts_multi_generator.py    # Multivariate generation with DAG
├── anomalies.py             # Anomaly injection functions
├── attributes.py            # Attribute definitions and sampling
├── semi_synthetic.py        # TSDB anomaly injection
├── README.md                # This file
└── tests/                   # Unit tests
```

## Quick Start

```python
from datasets.synthetic import generate_dataset

# Univariate
dataset = generate_dataset(
    num_samples=100,
    seq_len=1000,
    anomaly_sample_ratio=1.0,
    is_multivariate=False,
    seed=42,
)

# Multivariate
dataset = generate_dataset(
    num_samples=50,
    seq_len=1000,
    anomaly_sample_ratio=1.0,
    is_multivariate=True,
    num_features=5,
    seed=42,
)
```

## Output Format

Each sample is a dictionary:

```python
{
    'normal_time_series': np.ndarray,  # Clean series (length,) or (length, n_features)
    'time_series': np.ndarray,         # Series with anomalies injected
    'labels': np.ndarray,              # Binary labels (1=anomaly, 0=normal)
    'attribute': dict,                 # Metadata
}
```

### Univariate Attribute Structure

```python
{
    'metric': str,           # Pattern type name
    'pattern': str,          # Base pattern type
    'anomalies': list[dict], # List of injected anomalies
}
```

### Multivariate Attribute Structure

```python
{
    'attribute_list': list[dict],  # Per-feature pattern attributes
    'num_features': int,           # Number of features
    'is_endogenous': list[int],    # Which features have incoming DAG edges
    'dag': list[list[int]],        # DAG adjacency matrix
    'anomalies': list[dict],       # List of injected anomalies with feature index
}
```

## Parameters

### `generate_dataset()`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `num_samples` | int | 1000 | Number of samples to generate |
| `seq_len` | int or None | None | Length of each time series. If None, randomly sampled 100-10000 |
| `anomaly_sample_ratio` | float | 0.5 | Fraction of samples containing anomalies (0.0-1.0) |
| `is_multivariate` | bool | False | Generate multivariate time series |
| `num_features` | int or None | None | Number of features (required if is_multivariate=True) |
| `activate_function` | bool | False | Reserved for future use |
| `metrics` | list[str] or None | None | Specific anomaly types to use |
| `use_attribute_set` | bool | False | Use ALL_ATTRIBUTE_SET for flexible generation |
| `seed` | int or None | None | Random seed for reproducibility |

## Supported Anomaly Types

| Type | Description | Duration | Magnitude (std) |
|------|-------------|----------|-----------------|
| `spike` | Point anomaly | 1-3 | 3-8 |
| `drop` | Point drop | 1-3 | 3-8 |
| `drift` | Gradual drift | 20-200 | 0.5-3 |
| `trend_break` | Trend slope change | 30-300 | 1-4 |
| `seasonality_break` | Seasonality disruption | 50-500 | 1-4 |
| `noise_increase` | Increased variance | 20-200 | 2-5 |
| `level_shift` | Permanent step change | 1 | 2-6 |
| `pattern_change` | Frequency/phase shift | 50-500 | 1-3 |

Get programmatically:
```python
from datasets.synthetic.generator import get_supported_anomaly_types
print(get_supported_anomaly_types())
```

## Supported Pattern Types

| Type | Trend | Seasonality | Noise |
|------|-------|-------------|-------|
| `stationary` | None | None | 0.1 |
| `linear_trend` | Linear | None | 0.1 |
| `quadratic_trend` | Quadratic | None | 0.1 |
| `single_seasonal` | None | Single | 0.1 |
| `multi_seasonal` | None | Multiple | 0.1 |
| `trend_and_seasonal` | Linear | Single | 0.15 |
| `high_noise` | None | None | 0.5 |
| `low_noise` | None | None | 0.02 |

Get programmatically:
```python
from datasets.synthetic.generator import get_supported_patterns
print(get_supported_patterns())
```

## Semi-Synthetic Evaluation

Inject synthetic anomalies into real TSDB data for evaluation with ground truth on realistic data.

```python
from datasets.synthetic import inject_anomalies_into_tsdb, InjectionConfig
from detectors.timercd import TimeRCDDetector

config = InjectionConfig(
    target_sensors=["HUFL", "MUFL"],  # None = all sensors
    anomaly_types=["spike", "drift"],
    anomaly_intensity=3.0,  # Standard deviations
    anomaly_duration_range=(10, 50),
    num_anomalies_per_sensor=3,
    placement="random",  # or "periodic"
    periodic_interval=500,  # For periodic placement
    avoid_high_score_regions=True,  # Use TimeRCD to find clean windows
    high_score_threshold=0.7,
    seed=42,
)

detector = TimeRCDDetector()  # For clean window detection
result = inject_anomalies_into_tsdb("ETTh1", config, detector=detector)
```

### `InjectionConfig` Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `target_sensors` | list[str] or None | None | Sensors to inject into (None = all) |
| `anomaly_types` | list[str] | ["spike", "drift"] | Anomaly types to use |
| `anomaly_intensity` | float | 3.0 | Magnitude in standard deviations |
| `anomaly_duration_range` | tuple[int, int] | (10, 50) | Min/max anomaly duration |
| `num_anomalies_per_sensor` | int | 3 | Number of anomalies per target sensor |
| `placement` | "random" or "periodic" | "random" | Temporal placement strategy |
| `periodic_interval` | int or None | None | Interval for periodic placement |
| `avoid_high_score_regions` | bool | True | Avoid injecting over detector high-score regions |
| `high_score_threshold` | float | 0.7 | TimeRCD score threshold for "anomalous" |
| `window_size` | int | 500 | Window size for clean region detection |
| `seed` | int or None | None | Random seed |

## Saving and Loading

```python
from datasets.synthetic import save_dataset, load_dataset

save_dataset(dataset, "dataset.pkl")
loaded = load_dataset("dataset.pkl")
```

## CLI Usage

```bash
# Generate synthetic data
python scripts/generate_synthetic.py generate --num-samples 100 --output data.pkl

# Inject into TSDB
python scripts/generate_synthetic.py inject-tsdb ETTh1 --intensity 3.0 --output semi.pkl

# Run benchmark
python scripts/generate_synthetic.py benchmark --type synthetic --multivariate

# CI regression testing
python scripts/generate_synthetic.py ci-benchmark
```

## Integration with Evaluation

```python
from evaluation.benchmarks import BenchmarkRunner, BenchmarkConfig, ThresholdStrategy
from detectors.timercd import TimeRCDDetector

detector = TimeRCDDetector()
runner = BenchmarkRunner(detector)

config = BenchmarkConfig(
    dataset_type="synthetic",
    num_samples=50,
    seq_len=1000,
    is_multivariate=True,
    num_features=5,
    threshold_strategy=ThresholdStrategy.BEST_F1,
)

result = runner.run(config)
print(f"F1: {result.evaluation_result.f1:.4f}")
print(f"PR-AUC: {result.evaluation_result.pr_auc:.4f}")

# Save baseline for regression testing
runner.save_baseline(result, "timercd_synthetic_baseline")
```

## Reproducibility

All generation functions accept a `seed` parameter for deterministic results:

```python
# Same seed = identical output
dataset1 = generate_dataset(num_samples=10, seq_len=100, seed=42)
dataset2 = generate_dataset(num_samples=10, seq_len=100, seed=42)
assert np.array_equal(dataset1[0]["time_series"], dataset2[0]["time_series"])
```

## Multivariate DAG Structure

Multivariate generation uses a Directed Acyclic Graph (DAG) to model causal relationships between features:

- **DAG Generation**: Erdős-Rényi random graph with edge probability ~2/n_features
- **Endogenous Features**: Features with incoming edges (influenced by others)
- **Anomaly Propagation**: Anomalies on endogenous features propagate to descendants with 50% magnitude attenuation
- **Structural Equation Model**: Linear Gaussian SEM: X = W * X + noise (solved in topological order)

The DAG ensures realistic cross-feature correlations and enables testing of multivariate anomaly propagation detection.