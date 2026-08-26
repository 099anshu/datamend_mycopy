"""Univariate time series pattern generation.

Generates base time series with configurable trends, seasonality, noise, and
autoregressive structure.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from datasets.synthetic.attributes import PatternAttribute


@dataclass
class GenerationConfig:
    """Configuration for univariate time series generation."""

    length: int
    pattern: PatternAttribute
    seed: int | None = None


def generate_trend(length: int, trend_type: str, rng: np.random.Generator) -> np.ndarray:
    """Generate trend component."""
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
    """Generate seasonality component."""
    t = np.arange(length, dtype=float)
    signal = np.zeros(length)

    if seasonality_type == "none":
        return signal

    if seasonality_type == "single":
        for period in periods:
            if isinstance(period, (int, float)):
                # Random amplitude and phase for each period
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
    """Generate AR(p) noise process."""
    if order == 0 or not coeffs:
        return rng.normal(0, noise_level, size=length)

    # Ensure we have enough coefficients
    coeffs = list(coeffs) + [0.0] * max(0, order - len(coeffs))
    coeffs = coeffs[:order]

    # Generate innovations
    innovations = rng.normal(0, noise_level, size=length + order)
    signal = np.zeros(length + order)

    # Initialize with innovations
    signal[:order] = innovations[:order]

    # Generate AR process
    for i in range(order, length + order):
        ar_part = sum(c * signal[i - j - 1] for j, c in enumerate(coeffs))
        signal[i] = ar_part + innovations[i]

    return signal[order:]


def generate_base_series(config: GenerationConfig) -> np.ndarray:
    """Generate a base univariate time series without anomalies."""
    rng = np.random.default_rng(config.seed)
    pattern = config.pattern

    # Generate components
    trend = generate_trend(config.length, pattern.trend, rng)
    seasonality = generate_seasonality(
        config.length, pattern.seasonality, pattern.seasonality_periods, rng
    )
    noise = generate_ar_noise(
        config.length,
        pattern.autoregressive_order,
        pattern.autoregressive_coeffs,
        pattern.noise_level,
        rng,
    )

    # Combine components
    series = trend + seasonality + noise

    # Standardize to zero mean, unit variance for consistent anomaly magnitudes
    series = (series - series.mean()) / (series.std() + 1e-8)

    return series


def generate_univariate_series(
    length: int,
    pattern: PatternAttribute | None = None,
    seed: int | None = None,
) -> np.ndarray:
    """Convenience function to generate a univariate series."""
    if pattern is None:
        from datasets.synthetic.attributes import sample_pattern_attribute
        rng = np.random.default_rng(seed)
        pattern = sample_pattern_attribute(rng)

    config = GenerationConfig(length=length, pattern=pattern, seed=seed)
    return generate_base_series(config)