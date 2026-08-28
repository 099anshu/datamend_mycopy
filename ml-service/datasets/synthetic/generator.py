"""Main dataset generation API for synthetic time series anomaly detection.

Provides the generate_dataset function supporting univariate and multivariate
generation with attribute-based configuration.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any, Literal

import numpy as np

from datasets.synthetic.attributes import (
    ALL_ATTRIBUTE_SET,
    PATTERN_ATTRIBUTES,
    ANOMALY_ATTRIBUTES,
    PatternAttribute,
    AnomalyAttribute,
    sample_pattern_attribute,
    sample_anomaly_attributes,
    sample_multivariate_attributes,
)
from datasets.synthetic.anomalies import inject_multiple_anomalies, AnomalySpec
from datasets.synthetic.ts_generator import generate_univariate_series
from datasets.synthetic.ts_multi_generator import (
    generate_multivariate_series,
    inject_multivariate_anomalies,
)


def generate_dataset(
    num_samples: int = 1000,
    seq_len: int | None = None,
    anomaly_sample_ratio: float = 0.5,
    is_multivariate: bool = False,
    num_features: int | None = None,
    activate_function: bool = False,
    metrics: list[str] | None = None,
    use_attribute_set: bool = False,
    seed: int | None = None,
) -> list[dict[str, Any]]:
    """Generate synthetic time series dataset with anomalies.

    Args:
        num_samples: Number of samples to generate
        seq_len: Length of each time series. If None, randomly sampled 100-10000
        anomaly_sample_ratio: Fraction of samples containing anomalies (0.0-1.0)
        is_multivariate: Whether to generate multivariate time series
        num_features: Number of features for multivariate (required if is_multivariate)
        activate_function: Apply activation functions (for compatibility)
        metrics: List of anomaly types to use (e.g., ["spike", "drift"])
        use_attribute_set: Use ALL_ATTRIBUTE_SET for flexible generation
        seed: Random seed for reproducibility

    Returns:
        List of samples, each a dict with:
            - normal_time_series: np.ndarray (clean series)
            - time_series: np.ndarray (with anomalies)
            - labels: np.ndarray (binary, 1=anomaly)
            - attribute: dict (metadata about pattern and anomalies)
    """
    if seq_len is not None and seq_len < 1:
        raise ValueError("seq_len must be >= 1 or None")

    if anomaly_sample_ratio < 0.0 or anomaly_sample_ratio > 1.0:
        raise ValueError("anomaly_sample_ratio must be in [0.0, 1.0]")

    if is_multivariate and num_features is None:
        raise ValueError("num_features required when is_multivariate=True")

    if is_multivariate and num_features is not None and num_features < 1:
        raise ValueError("num_features must be >= 1")

    rng = np.random.default_rng(seed)
    dataset = []

    # Determine sequence lengths for each sample
    if seq_len is None:
        lengths = rng.integers(100, 10001, size=num_samples)
    else:
        lengths = np.full(num_samples, seq_len)

    # Determine which samples get anomalies
    num_anomalous_samples = int(num_samples * anomaly_sample_ratio)
    anomalous_indices = set(rng.choice(num_samples, size=num_anomalous_samples, replace=False))

    for i in range(num_samples):
        length = int(lengths[i])
        has_anomalies = i in anomalous_indices

        if is_multivariate:
            sample = _generate_multivariate_sample(
                length=length,
                num_features=num_features,
                has_anomalies=has_anomalies,
                metrics=metrics,
                use_attribute_set=use_attribute_set,
                rng=rng,
            )
        else:
            sample = _generate_univariate_sample(
                length=length,
                has_anomalies=has_anomalies,
                metrics=metrics,
                use_attribute_set=use_attribute_set,
                rng=rng,
            )

        dataset.append(sample)

    return dataset


def _generate_univariate_sample(
    length: int,
    has_anomalies: bool,
    metrics: list[str] | None,
    use_attribute_set: bool,
    rng: np.random.Generator,
) -> dict[str, Any]:
    """Generate a single univariate sample."""
    # Sample pattern attribute
    if use_attribute_set:
        pattern = sample_pattern_attribute(rng)
    else:
        pattern = rng.choice(PATTERN_ATTRIBUTES)

    # Generate clean series
    # Derive a seed for this sample from the main RNG
    sample_seed = int(rng.integers(0, 2**31))
    normal_series = generate_univariate_series(length=length, pattern=pattern, seed=sample_seed)

    # Prepare attribute metadata
    attribute = {
        "metric": pattern.name,
        "pattern": pattern.name,
        "anomalies": [],
    }

    if not has_anomalies:
        return {
            "normal_time_series": normal_series,
            "time_series": normal_series.copy(),
            "labels": np.zeros(length, dtype=int),
            "attribute": attribute,
        }

    # Determine number of anomalies (1-3 per sample)
    num_anomalies = rng.integers(1, 4)

    # Sample anomaly attributes
    anomaly_attrs = sample_anomaly_attributes(
        num_anomalies=num_anomalies,
        allowed_types=metrics,
        rng=rng,
    )

    # Generate anomaly specs
    specs = []
    for attr in anomaly_attrs:
        duration = rng.integers(attr.min_duration, attr.max_duration + 1)
        magnitude = rng.uniform(attr.min_magnitude, attr.max_magnitude)
        start_idx = rng.integers(0, max(1, length - duration))
        direction = rng.choice(["up", "down"])

        specs.append(AnomalySpec(
            anomaly_type=attr.name,
            start_idx=start_idx,
            duration=duration,
            magnitude=magnitude,
            shape=attr.shape,
            direction=direction,
        ))

        attribute["anomalies"].append({
            "type": attr.name,
            "start": start_idx,
            "duration": duration,
            "magnitude": magnitude,
            "shape": attr.shape,
            "direction": direction,
        })

    # Inject anomalies
    anomalous_series, labels = inject_multiple_anomalies(normal_series, specs, rng=rng)

    return {
        "normal_time_series": normal_series,
        "time_series": anomalous_series,
        "labels": labels,
        "attribute": attribute,
    }


def _generate_multivariate_sample(
    length: int,
    num_features: int,
    has_anomalies: bool,
    metrics: list[str] | None,
    use_attribute_set: bool,
    rng: np.random.Generator,
) -> dict[str, Any]:
    """Generate a single multivariate sample."""
    # Sample multivariate attributes (patterns + DAG)
    if use_attribute_set:
        attrs = sample_multivariate_attributes(num_features, rng)
    else:
        # Generate random patterns and DAG
        pattern_attrs = [rng.choice(PATTERN_ATTRIBUTES) for _ in range(num_features)]
        # Simple random DAG
        dag = np.zeros((num_features, num_features), dtype=int)
        for i in range(num_features):
            for j in range(i + 1, num_features):
                if rng.random() < 0.3:
                    dag[i, j] = 1
        is_endogenous = [int(dag[:, i].sum() > 0) for i in range(num_features)]
        if not any(is_endogenous):
            is_endogenous[rng.integers(0, num_features)] = 1
        attrs = {
            "attribute_list": pattern_attrs,
            "num_features": num_features,
            "is_endogenous": is_endogenous,
            "dag": dag.tolist(),
        }

    # Generate clean multivariate series
    from datasets.synthetic.ts_multi_generator import MultivariateConfig, generate_multivariate_base_series

    # Derive a seed for this sample
    sample_seed = int(rng.integers(0, 2**31))
    config = MultivariateConfig(
        length=length,
        num_features=num_features,
        pattern_attributes=attrs["attribute_list"],
        dag=np.array(attrs["dag"]),
        seed=sample_seed,
    )
    normal_series = generate_multivariate_base_series(config)

    # Prepare attribute metadata
    attribute = {
        "attribute_list": [
            {"pattern": p.name, "trend": p.trend, "seasonality": p.seasonality}
            for p in attrs["attribute_list"]
        ],
        "num_features": num_features,
        "is_endogenous": attrs["is_endogenous"],
        "dag": attrs["dag"],
        "anomalies": [],
    }

    if not has_anomalies:
        return {
            "normal_time_series": normal_series,
            "time_series": normal_series.copy(),
            "labels": np.zeros(length, dtype=int),
            "attribute": attribute,
        }

    # Determine number of anomaly sources (1-2 per sample)
    num_anomaly_sources = rng.integers(1, 3)

    # Choose features to inject anomalies (prefer endogenous for propagation)
    endogenous_features = [i for i, v in enumerate(attrs["is_endogenous"]) if v]
    if not endogenous_features:
        endogenous_features = list(range(num_features))

    anomaly_specs = []
    for _ in range(num_anomaly_sources):
        feature_idx = rng.choice(endogenous_features)

        # Sample anomaly type
        if metrics:
            anomaly_type = rng.choice(metrics)
        else:
            anomaly_type = rng.choice([a.name for a in ANOMALY_ATTRIBUTES])

        attr = next(a for a in ANOMALY_ATTRIBUTES if a.name == anomaly_type)
        duration = rng.integers(attr.min_duration, attr.max_duration + 1)
        magnitude = rng.uniform(attr.min_magnitude, attr.max_magnitude)
        start_idx = rng.integers(0, max(1, length - duration))
        direction = rng.choice(["up", "down"])

        anomaly_specs.append({
            "feature_idx": feature_idx,
            "anomaly_type": anomaly_type,
            "start_idx": start_idx,
            "duration": duration,
            "magnitude": magnitude,
            "shape": attr.shape,
            "direction": direction,
        })

        attribute["anomalies"].append({
            "feature": feature_idx,
            "type": anomaly_type,
            "start": start_idx,
            "duration": duration,
            "magnitude": magnitude,
            "shape": attr.shape,
            "direction": direction,
        })

    # Inject with DAG propagation
    anomalous_series, labels = inject_multivariate_anomalies(
        normal_series,
        anomaly_specs,
        attrs["is_endogenous"],
        np.array(attrs["dag"]),
        rng=rng,
    )

    return {
        "normal_time_series": normal_series,
        "time_series": anomalous_series,
        "labels": labels,
        "attribute": attribute,
    }


def save_dataset(dataset: list[dict[str, Any]], filepath: str | Path) -> None:
    """Save dataset to pickle file."""
    with open(filepath, "wb") as f:
        pickle.dump(dataset, f)


def load_dataset(filepath: str | Path) -> list[dict[str, Any]]:
    """Load dataset from pickle file."""
    with open(filepath, "rb") as f:
        return pickle.load(f)


def get_supported_anomaly_types() -> list[str]:
    """Get list of supported anomaly type names."""
    return [a.name for a in ANOMALY_ATTRIBUTES]


def get_supported_patterns() -> list[str]:
    """Get list of supported pattern names."""
    return [p.name for p in PATTERN_ATTRIBUTES]