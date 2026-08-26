"""Attribute definitions and sampling for synthetic time series generation.

Defines the attribute space for generating diverse time series patterns and anomalies.
Based on common TSAD benchmark characteristics (NAB, Yahoo S5, UCI, ETT).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class PatternAttribute:
    """Base pattern configuration for time series generation."""

    name: str
    trend: str = "none"  # none, linear, quadratic
    trend_slope_range: tuple[float, float] = (-0.01, 0.01)
    trend_coeff_range: tuple[float, float] = (-0.0001, 0.0001)
    seasonality: str = "none"  # none, single, multiple
    seasonality_periods: list[int] = field(default_factory=list)
    noise_level: float = 0.1
    autoregressive_order: int = 0
    autoregressive_coeffs: list[float] = field(default_factory=list)


@dataclass
class AnomalyAttribute:
    """Anomaly type configuration."""

    name: str
    min_duration: int = 1
    max_duration: int = 50
    min_magnitude: float = 1.0  # in std deviations
    max_magnitude: float = 5.0
    shape: str = "constant"  # constant, linear, exponential, sinusoidal


# Base pattern attributes
PATTERN_ATTRIBUTES: list[PatternAttribute] = [
    PatternAttribute(
        name="stationary",
        trend="none",
        seasonality="none",
        noise_level=0.1,
        autoregressive_order=1,
        autoregressive_coeffs=[0.7],
    ),
    PatternAttribute(
        name="linear_trend",
        trend="linear",
        trend_slope_range=(-0.01, 0.01),
        seasonality="none",
        noise_level=0.1,
        autoregressive_order=1,
        autoregressive_coeffs=[0.5],
    ),
    PatternAttribute(
        name="quadratic_trend",
        trend="quadratic",
        trend_coeff_range=(-0.0001, 0.0001),
        seasonality="none",
        noise_level=0.1,
        autoregressive_order=1,
        autoregressive_coeffs=[0.5],
    ),
    PatternAttribute(
        name="single_seasonal",
        trend="none",
        seasonality="single",
        seasonality_periods=[24, 48, 96, 168],  # hourly, 2h, 4h, weekly
        noise_level=0.1,
        autoregressive_order=1,
        autoregressive_coeffs=[0.3],
    ),
    PatternAttribute(
        name="multi_seasonal",
        trend="none",
        seasonality="multiple",
        seasonality_periods=[[24, 168], [48, 336], [24, 168, 720]],  # daily+weekly, etc.
        noise_level=0.1,
        autoregressive_order=1,
        autoregressive_coeffs=[0.3],
    ),
    PatternAttribute(
        name="trend_and_seasonal",
        trend="linear",
        trend_slope_range=(-0.005, 0.005),
        seasonality="single",
        seasonality_periods=[24, 48, 168],
        noise_level=0.15,
        autoregressive_order=1,
        autoregressive_coeffs=[0.4],
    ),
    PatternAttribute(
        name="high_noise",
        trend="none",
        seasonality="none",
        noise_level=0.5,
        autoregressive_order=2,
        autoregressive_coeffs=[0.5, -0.2],
    ),
    PatternAttribute(
        name="low_noise",
        trend="none",
        seasonality="none",
        noise_level=0.02,
        autoregressive_order=1,
        autoregressive_coeffs=[0.9],
    ),
]

# Anomaly type attributes
ANOMALY_ATTRIBUTES: list[AnomalyAttribute] = [
    AnomalyAttribute(
        name="spike",
        min_duration=1,
        max_duration=3,
        min_magnitude=3.0,
        max_magnitude=8.0,
        shape="constant",
    ),
    AnomalyAttribute(
        name="drop",
        min_duration=1,
        max_duration=3,
        min_magnitude=3.0,
        max_magnitude=8.0,
        shape="constant",
    ),
    AnomalyAttribute(
        name="drift",
        min_duration=20,
        max_duration=200,
        min_magnitude=0.5,
        max_magnitude=3.0,
        shape="linear",
    ),
    AnomalyAttribute(
        name="trend_break",
        min_duration=30,
        max_duration=300,
        min_magnitude=1.0,
        max_magnitude=4.0,
        shape="linear",
    ),
    AnomalyAttribute(
        name="seasonality_break",
        min_duration=50,
        max_duration=500,
        min_magnitude=1.0,
        max_magnitude=4.0,
        shape="sinusoidal",
    ),
    AnomalyAttribute(
        name="noise_increase",
        min_duration=20,
        max_duration=200,
        min_magnitude=2.0,
        max_magnitude=5.0,
        shape="constant",
    ),
    AnomalyAttribute(
        name="level_shift",
        min_duration=1,
        max_duration=1,
        min_magnitude=2.0,
        max_magnitude=6.0,
        shape="constant",
    ),
    AnomalyAttribute(
        name="pattern_change",
        min_duration=50,
        max_duration=500,
        min_magnitude=1.0,
        max_magnitude=3.0,
        shape="sinusoidal",
    ),
]


# Combined attribute set for unified sampling
ALL_ATTRIBUTE_SET: dict[str, Any] = {
    "patterns": PATTERN_ATTRIBUTES,
    "anomalies": ANOMALY_ATTRIBUTES,
}


def sample_pattern_attribute(rng: np.random.Generator | None = None) -> PatternAttribute:
    """Sample a random pattern attribute from the set."""
    if rng is None:
        rng = np.random.default_rng()
    return rng.choice(PATTERN_ATTRIBUTES)


def sample_anomaly_attributes(
    num_anomalies: int,
    allowed_types: list[str] | None = None,
    rng: np.random.Generator | None = None,
) -> list[AnomalyAttribute]:
    """Sample anomaly attributes for injection."""
    if rng is None:
        rng = np.random.default_rng()

    available = ANOMALY_ATTRIBUTES
    if allowed_types is not None:
        available = [a for a in ANOMALY_ATTRIBUTES if a.name in allowed_types]
        if not available:
            raise ValueError(f"No anomaly attributes match allowed types: {allowed_types}")

    return [rng.choice(available) for _ in range(num_anomalies)]


def sample_multivariate_attributes(
    num_features: int,
    rng: np.random.Generator | None = None,
) -> dict[str, Any]:
    """Sample attributes for multivariate generation including DAG structure."""
    if rng is None:
        rng = np.random.default_rng()

    # Sample pattern for each feature (can be same or different)
    pattern_attrs = [sample_pattern_attribute(rng) for _ in range(num_features)]

    # Generate random DAG using Erdős-Rényi model
    # Edge probability ~ 2/num_features for sparse connectivity
    edge_prob = min(0.5, 2.0 / num_features)
    dag = np.zeros((num_features, num_features), dtype=int)
    for i in range(num_features):
        for j in range(i + 1, num_features):
            if rng.random() < edge_prob:
                dag[i, j] = 1

    # Ensure DAG property (no cycles) - already satisfied by upper triangular
    # Determine endogenous features (those with incoming edges)
    is_endogenous = [int(dag[:, i].sum() > 0) for i in range(num_features)]
    # Ensure at least one endogenous for anomaly propagation
    if not any(is_endogenous):
        is_endogenous[rng.integers(0, num_features)] = 1

    return {
        "attribute_list": pattern_attrs,
        "num_features": num_features,
        "is_endogenous": is_endogenous,
        "dag": dag.tolist(),
    }


def get_supported_anomaly_types() -> list[str]:
    """Get list of supported anomaly type names."""
    return [a.name for a in ANOMALY_ATTRIBUTES]


def get_supported_patterns() -> list[str]:
    """Get list of supported pattern names."""
    return [p.name for p in PATTERN_ATTRIBUTES]