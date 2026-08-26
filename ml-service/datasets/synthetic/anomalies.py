"""Anomaly injection functions for synthetic time series generation.

Supports various anomaly types: spike, drop, drift, trend_break, seasonality_break,
noise_increase, level_shift, pattern_change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np


AnomalyShape = Literal["constant", "linear", "exponential", "sinusoidal"]


@dataclass
class AnomalySpec:
    """Specification for a single anomaly injection."""

    anomaly_type: str
    start_idx: int
    duration: int
    magnitude: float  # in standard deviations
    shape: AnomalyShape = "constant"
    direction: Literal["up", "down", "both"] = "up"


def generate_anomaly_shape(
    duration: int,
    shape: AnomalyShape,
    magnitude: float,
    direction: Literal["up", "down", "both"] = "up",
) -> np.ndarray:
    """Generate the temporal shape of an anomaly."""
    t = np.arange(duration, dtype=float)
    if duration > 1:
        t = t / (duration - 1)  # Normalize to [0, 1]

    if shape == "constant":
        values = np.ones(duration)
    elif shape == "linear":
        values = t
    elif shape == "exponential":
        values = 1 - np.exp(-5 * t)
    elif shape == "sinusoidal":
        values = np.sin(2 * np.pi * t)
    else:
        raise ValueError(f"Unknown shape: {shape}")

    # Apply direction
    if direction == "down":
        values = -values
    elif direction == "both":
        # Random direction per anomaly
        pass  # Will be handled by caller

    return values * magnitude


def inject_spike(
    series: np.ndarray,
    start_idx: int,
    duration: int,
    magnitude: float,
    direction: Literal["up", "down"] = "up",
) -> tuple[np.ndarray, np.ndarray]:
    """Inject spike anomaly (point or short-duration)."""
    result = series.copy()
    labels = np.zeros_like(series, dtype=int)
    print(labels.sum(), len(labels), labels.sum()/len(labels))

    end_idx = min(start_idx + duration, len(series))
    actual_duration = end_idx - start_idx

    if actual_duration <= 0:
        return result, labels

    anomaly_values = generate_anomaly_shape(actual_duration, "constant", magnitude, direction)
    result[start_idx:end_idx] += anomaly_values
    labels[start_idx:end_idx] = 1

    return result, labels


def inject_drift(
    series: np.ndarray,
    start_idx: int,
    duration: int,
    magnitude: float,
    direction: Literal["up", "down"] = "up",
) -> tuple[np.ndarray, np.ndarray]:
    """Inject gradual drift anomaly."""
    result = series.copy()
    labels = np.zeros_like(series, dtype=int)

    end_idx = min(start_idx + duration, len(series))
    actual_duration = end_idx - start_idx

    if actual_duration <= 0:
        return result, labels

    anomaly_values = generate_anomaly_shape(actual_duration, "linear", magnitude, direction)
    result[start_idx:end_idx] += anomaly_values
    labels[start_idx:end_idx] = 1

    return result, labels


def inject_trend_break(
    series: np.ndarray,
    start_idx: int,
    duration: int,
    magnitude: float,
    direction: Literal["up", "down"] = "up",
) -> tuple[np.ndarray, np.ndarray]:
    """Inject trend break (change in slope)."""
    result = series.copy()
    labels = np.zeros_like(series, dtype=int)

    end_idx = min(start_idx + duration, len(series))
    actual_duration = end_idx - start_idx

    if actual_duration <= 0:
        return result, labels

    # Trend break: linear change that persists
    anomaly_values = generate_anomaly_shape(actual_duration, "linear", magnitude, direction)
    result[start_idx:end_idx] += anomaly_values
    labels[start_idx:end_idx] = 1

    return result, labels


def inject_seasonality_break(
    series: np.ndarray,
    start_idx: int,
    duration: int,
    magnitude: float,
    period: int = 24,
) -> tuple[np.ndarray, np.ndarray]:
    """Inject seasonality break (disrupt periodic pattern)."""
    result = series.copy()
    labels = np.zeros_like(series, dtype=int)

    end_idx = min(start_idx + duration, len(series))
    actual_duration = end_idx - start_idx

    if actual_duration <= 0:
        return result, labels

    t = np.arange(actual_duration)
    # Sinusoidal disruption of seasonal pattern
    anomaly_values = magnitude * np.sin(2 * np.pi * t / period)
    result[start_idx:end_idx] += anomaly_values
    labels[start_idx:end_idx] = 1

    return result, labels


def inject_noise_increase(
    series: np.ndarray,
    start_idx: int,
    duration: int,
    magnitude: float,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Inject increased noise variance."""
    if rng is None:
        rng = np.random.default_rng()

    result = series.copy()
    labels = np.zeros_like(series, dtype=int)

    end_idx = min(start_idx + duration, len(series))
    actual_duration = end_idx - start_idx

    if actual_duration <= 0:
        return result, labels

    # Add extra noise scaled by magnitude
    extra_noise = rng.normal(0, magnitude, size=actual_duration)
    result[start_idx:end_idx] += extra_noise
    labels[start_idx:end_idx] = 1

    return result, labels


def inject_level_shift(
    series: np.ndarray,
    start_idx: int,
    magnitude: float,
    direction: Literal["up", "down"] = "up",
) -> tuple[np.ndarray, np.ndarray]:
    """Inject permanent level shift (step change)."""
    result = series.copy()
    labels = np.zeros_like(series, dtype=int)

    if start_idx >= len(series):
        return result, labels

    shift = magnitude if direction == "up" else -magnitude
    result[start_idx:] += shift
    labels[start_idx:] = 1

    return result, labels


def inject_pattern_change(
    series: np.ndarray,
    start_idx: int,
    duration: int,
    magnitude: float,
    new_frequency: float = 0.5,
) -> tuple[np.ndarray, np.ndarray]:
    """Inject pattern change (frequency/phase shift in seasonal component)."""
    result = series.copy()
    labels = np.zeros_like(series, dtype=int)

    end_idx = min(start_idx + duration, len(series))
    actual_duration = end_idx - start_idx

    if actual_duration <= 0:
        return result, labels

    t = np.arange(actual_duration)
    # Add a different frequency component
    anomaly_values = magnitude * np.sin(2 * np.pi * new_frequency * t / duration)
    result[start_idx:end_idx] += anomaly_values
    labels[start_idx:end_idx] = 1

    return result, labels


# Mapping from anomaly type name to injection function
ANOMALY_INJECTORS: dict[str, callable] = {
    "spike": inject_spike,
    "drop": inject_spike,  # Same as spike but direction down
    "drift": inject_drift,
    "trend_break": inject_trend_break,
    "seasonality_break": inject_seasonality_break,
    "noise_increase": inject_noise_increase,
    "level_shift": inject_level_shift,
    "pattern_change": inject_pattern_change,
}


def inject_anomaly(
    series: np.ndarray,
    spec: AnomalySpec,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Inject a single anomaly according to specification."""
    injector = ANOMALY_INJECTORS.get(spec.anomaly_type)
    if injector is None:
        raise ValueError(f"Unknown anomaly type: {spec.anomaly_type}")

    # Handle drop as spike with down direction
    if spec.anomaly_type == "drop":
        return injector(series, spec.start_idx, spec.duration, spec.magnitude, direction="down")

    # For spike, use specified direction
    if spec.anomaly_type == "spike":
        return injector(series, spec.start_idx, spec.duration, spec.magnitude, direction=spec.direction)

    # For other types, pass relevant parameters
    if spec.anomaly_type in ("drift", "trend_break"):
        return injector(series, spec.start_idx, spec.duration, spec.magnitude, direction=spec.direction)

    if spec.anomaly_type == "seasonality_break":
        return injector(series, spec.start_idx, spec.duration, spec.magnitude)

    if spec.anomaly_type == "noise_increase":
        return injector(series, spec.start_idx, spec.duration, spec.magnitude, rng=rng)

    if spec.anomaly_type == "level_shift":
        return injector(series, spec.start_idx, spec.magnitude, direction=spec.direction)

    if spec.anomaly_type == "pattern_change":
        return injector(series, spec.start_idx, spec.duration, spec.magnitude)

    # Default fallback
    return injector(series, spec.start_idx, spec.duration, spec.magnitude)


def inject_multiple_anomalies(
    series: np.ndarray,
    specs: list[AnomalySpec],
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Inject multiple anomalies sequentially."""
    result = series.copy()
    combined_labels = np.zeros_like(series, dtype=int)

    for spec in specs:
        result, labels = inject_anomaly(result, spec, rng=rng)
        combined_labels = np.maximum(combined_labels, labels)

    return result, combined_labels