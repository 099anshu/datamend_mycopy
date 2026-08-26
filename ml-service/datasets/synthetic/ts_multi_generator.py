"""Multivariate time series generation with DAG-based causal structure.

Generates correlated multivariate time series using linear Gaussian structural
equation models (SEM) over a directed acyclic graph (DAG).
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np

from datasets.synthetic.attributes import PatternAttribute, sample_multivariate_attributes
from datasets.synthetic.ts_generator import GenerationConfig, generate_base_series


@dataclass
class MultivariateConfig:
    """Configuration for multivariate time series generation."""

    length: int
    num_features: int
    pattern_attributes: list[PatternAttribute]
    dag: np.ndarray  # Adjacency matrix (upper triangular for DAG)
    edge_weights: np.ndarray | None = None  # Weight for each edge
    noise_levels: np.ndarray | None = None  # Noise per feature
    seed: int | None = None


def generate_dag_weights(
    dag: np.ndarray,
    weight_range: tuple[float, float] = (0.3, 0.8),
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Generate random weights for DAG edges."""
    if rng is None:
        rng = np.random.default_rng()

    weights = np.zeros_like(dag, dtype=float)
    edges = np.where(dag > 0)
    for i, j in zip(edges[0], edges[1], strict=False):
        weights[i, j] = rng.uniform(*weight_range)
    return weights


def topological_order(dag: np.ndarray) -> list[int]:
    """Get topological ordering of nodes in DAG."""
    G = nx.DiGraph(dag)
    return list(nx.topological_sort(G))


def generate_multivariate_base_series(config: MultivariateConfig) -> np.ndarray:
    """Generate multivariate base series using linear Gaussian SEM."""
    rng = np.random.default_rng(config.seed)
    num_features = config.num_features
    length = config.length

    # Generate noise for each feature
    if config.noise_levels is None:
        noise_levels = np.array([p.noise_level for p in config.pattern_attributes])
    else:
        noise_levels = config.noise_levels

    # Generate independent noise innovations for each feature
    innovations = np.zeros((length, num_features))
    for i in range(num_features):
        pattern = config.pattern_attributes[i]
        innovations[:, i] = generate_ar_noise(
            length,
            pattern.autoregressive_order,
            pattern.autoregressive_coeffs,
            noise_levels[i],
            rng,
        )

    # Generate edge weights if not provided
    if config.edge_weights is None:
        edge_weights = generate_dag_weights(config.dag, rng=rng)
    else:
        edge_weights = config.edge_weights

    # Generate series following topological order (parents before children)
    series = np.zeros((length, num_features))
    order = topological_order(config.dag)

    for node in order:
        # Start with own innovations
        series[:, node] = innovations[:, node]

        # Add contributions from parents
        parents = np.where(config.dag[:, node] > 0)[0]
        for parent in parents:
            series[:, node] += edge_weights[parent, node] * series[:, parent]

        # Add trend and seasonality for this feature
        pattern = config.pattern_attributes[node]
        trend = generate_trend(length, pattern.trend, rng)
        seasonality = generate_seasonality(
            length, pattern.seasonality, pattern.seasonality_periods, rng
        )
        series[:, node] += trend + seasonality

    # Standardize each feature to zero mean, unit variance
    for i in range(num_features):
        std = series[:, i].std()
        if std > 1e-8:
            series[:, i] = (series[:, i] - series[:, i].mean()) / std

    return series


def generate_trend(length: int, trend_type: str, rng: np.random.Generator) -> np.ndarray:
    """Generate trend component (copied from ts_generator for independence)."""
    t = np.arange(length, dtype=float)

    if trend_type == "none":
        return np.zeros(length)

    if trend_type == "linear":
        slope = rng.uniform(-0.01, 0.01)
        return slope * t

    if trend_type == "quadratic":
        coeff = rng.uniform(-0.0001, 0.0001)
        return coeff * t**2

    raise ValueError(f"Unknown trend type: {trend_type}")


def generate_seasonality(
    length: int,
    seasonality_type: str,
    periods: list[int] | list[list[int]],
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate seasonality component (copied from ts_generator for independence)."""
    t = np.arange(length, dtype=float)
    signal = np.zeros(length)

    if seasonality_type == "none":
        return signal

    if seasonality_type == "single":
        for period in periods:
            if isinstance(period, (int, float)):
                amplitude = rng.uniform(0.5, 2.0)
                phase = rng.uniform(0, 2 * np.pi)
                signal += amplitude * np.sin(2 * np.pi * t / period + phase)

    elif seasonality_type == "multiple":
        for period_group in periods:
            if isinstance(period_group, list):
                for period in period_group:
                    amplitude = rng.uniform(0.3, 1.5)
                    phase = rng.uniform(0, 2 * np.pi)
                    signal += amplitude * np.sin(2 * np.pi * t / period + phase)

    return signal


def generate_ar_noise(
    length: int,
    order: int,
    coeffs: list[float],
    noise_level: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate AR(p) noise process (copied from ts_generator for independence)."""
    if order == 0 or not coeffs:
        return rng.normal(0, noise_level, size=length)

    coeffs = list(coeffs) + [0.0] * max(0, order - len(coeffs))
    coeffs = coeffs[:order]

    innovations = rng.normal(0, noise_level, size=length + order)
    signal = np.zeros(length + order)
    signal[:order] = innovations[:order]

    for i in range(order, length + order):
        ar_part = sum(c * signal[i - j - 1] for j, c in enumerate(coeffs))
        signal[i] = ar_part + innovations[i]

    return signal[order:]


def generate_multivariate_series(
    length: int,
    num_features: int,
    seed: int | None = None,
) -> tuple[np.ndarray, dict]:
    """Convenience function to generate multivariate series with random attributes."""
    rng = np.random.default_rng(seed)
    attrs = sample_multivariate_attributes(num_features, rng)

    config = MultivariateConfig(
        length=length,
        num_features=num_features,
        pattern_attributes=attrs["attribute_list"],
        dag=np.array(attrs["dag"]),
        seed=seed,
    )

    series = generate_multivariate_base_series(config)
    return series, attrs


def inject_multivariate_anomalies(
    series: np.ndarray,
    anomaly_specs: list[dict],
    is_endogenous: list[int],
    dag: np.ndarray,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Inject anomalies into multivariate series with DAG propagation.

    Args:
        series: Base multivariate series (length, num_features)
        anomaly_specs: List of anomaly specifications, each with:
            - feature_idx: int (which feature to inject)
            - anomaly_type: str
            - start_idx: int
            - duration: int
            - magnitude: float
        is_endogenous: List indicating which features have incoming edges
        dag: DAG adjacency matrix
        rng: Random generator

    Returns:
        Tuple of (anomalous_series, labels) where labels is (length,) binary
    """
    from datasets.synthetic.anomalies import inject_anomaly, AnomalySpec

    if rng is None:
        rng = np.random.default_rng()

    result = series.copy()
    labels = np.zeros(series.shape[0], dtype=int)

    # Convert specs to AnomalySpec objects and inject
    for spec_dict in anomaly_specs:
        spec = AnomalySpec(
            anomaly_type=spec_dict["anomaly_type"],
            start_idx=spec_dict["start_idx"],
            duration=spec_dict["duration"],
            magnitude=spec_dict["magnitude"],
            shape=spec_dict.get("shape", "constant"),
            direction=spec_dict.get("direction", "up"),
        )
        feature_idx = spec_dict["feature_idx"]

        # Inject on target feature
        result[:, feature_idx], feat_labels = inject_anomaly(
            result[:, feature_idx], spec, rng=rng
        )
        labels = np.maximum(labels, feat_labels)

        # Propagate to descendants if this is an endogenous anomaly source
        if is_endogenous[feature_idx]:
            descendants = get_descendants(feature_idx, dag)
            for desc in descendants:
                # Propagate with attenuated magnitude
                prop_spec = AnomalySpec(
                    anomaly_type=spec_dict["anomaly_type"],
                    start_idx=spec_dict["start_idx"],
                    duration=spec_dict["duration"],
                    magnitude=spec_dict["magnitude"] * 0.5,  # Attenuation
                    shape=spec_dict.get("shape", "constant"),
                    direction=spec_dict.get("direction", "up"),
                )
                result[:, desc], desc_labels = inject_anomaly(
                    result[:, desc], prop_spec, rng=rng
                )
                labels = np.maximum(labels, desc_labels)

    return result, labels


def get_descendants(node: int, dag: np.ndarray) -> list[int]:
    """Get all descendants of a node in DAG."""
    G = nx.DiGraph(dag)
    return list(nx.descendants(G, node))