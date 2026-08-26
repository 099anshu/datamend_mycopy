"""Semi-synthetic evaluation: inject synthetic anomalies into real TSDB data.

This module enables controlled evaluation on real-world data by injecting
synthetic anomalies with known ground truth, preserving real noise,
seasonality, and cross-sensor correlations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd

from datasets.synthetic.anomalies import AnomalySpec, inject_anomaly, inject_multiple_anomalies
from datasets.tsdb_loader import load_tsdb_dataset


InjectionPlacement = Literal["random", "periodic"]


@dataclass
class InjectionConfig:
    """Configuration for anomaly injection into TSDB data."""

    target_sensors: list[str] | None = None  # None = all sensors
    anomaly_types: list[str] = field(default_factory=lambda: ["spike", "drift"])
    anomaly_intensity: float = 3.0  # Standard deviations
    anomaly_duration_range: tuple[int, int] = (10, 50)
    num_anomalies_per_sensor: int = 3
    placement: InjectionPlacement = "random"
    periodic_interval: int | None = None  # For periodic placement
    avoid_high_score_regions: bool = True  # Use TimeRCD to detect clean windows
    high_score_threshold: float = 0.7  # TimeRCD score threshold for "anomalous" regions
    window_size: int = 500  # Window for clean region detection
    seed: int | None = None


def detect_clean_windows(
    data: np.ndarray,
    detector,
    window_size: int = 500,
    threshold: float = 0.7,
    stride: int | None = None,
) -> list[tuple[int, int]]:
    """Detect clean windows in data using detector scores.

    Returns list of (start, end) indices for clean windows.
    """
    if stride is None:
        stride = window_size // 2

    scores = detector.detect(data)
    clean_windows = []

    for start in range(0, len(data) - window_size + 1, stride):
        end = start + window_size
        window_scores = scores[start:end]
        max_score = np.max(window_scores)

        if max_score < threshold:
            clean_windows.append((start, end))

    # Merge overlapping/adjacent windows
    if not clean_windows:
        return []

    merged = [clean_windows[0]]
    for start, end in clean_windows[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return merged


def select_injection_windows(
    clean_windows: list[tuple[int, int]],
    num_anomalies: int,
    anomaly_duration_range: tuple[int, int],
    placement: InjectionPlacement,
    periodic_interval: int | None,
    rng: np.random.Generator,
    series_length: int | None = None,
) -> list[tuple[int, int]]:
    """Select specific injection windows within clean regions."""
    if not clean_windows:
        # Fallback: use entire series if no clean windows found
        if series_length is not None:
            clean_windows = [(0, series_length)]
        else:
            return []

    injection_windows = []

    if placement == "periodic" and periodic_interval is not None:
        # Periodic placement
        for start, end in clean_windows:
            window_len = end - start
            max_start = start + window_len - anomaly_duration_range[1]
            if max_start <= start:
                continue

            for pos in range(start, max_start + 1, periodic_interval):
                if len(injection_windows) >= num_anomalies:
                    break
                duration = rng.integers(*anomaly_duration_range, endpoint=True)
                injection_windows.append((pos, pos + duration))

    else:
        # Random placement within clean windows
        # Flatten all available positions
        available_positions = []
        for start, end in clean_windows:
            window_len = end - start
            max_dur = anomaly_duration_range[1]
            if window_len < max_dur:
                continue
            available_positions.extend(range(start, end - max_dur + 1))

        if not available_positions:
            return []

        selected_starts = rng.choice(
            available_positions,
            size=min(num_anomalies, len(available_positions)),
            replace=False,
        )

        for start in selected_starts:
            duration = rng.integers(*anomaly_duration_range, endpoint=True)
            injection_windows.append((int(start), int(start) + duration))

    return injection_windows


def inject_anomalies_into_tsdb(
    dataset_name: str,
    config: InjectionConfig | None = None,
    detector=None,
) -> dict[str, Any]:
    """Inject synthetic anomalies into a TSDB dataset.

    Args:
        dataset_name: Name of TSDB dataset (ETTh1, ETTh2, ETTm1, ETTm2)
        config: Injection configuration
        detector: Optional TimeRCDDetector for clean window detection

    Returns:
        Dictionary with:
            - normal_time_series: Original clean data (n_samples, n_sensors)
            - time_series: Data with injected anomalies
            - labels: Binary labels per timestep (1 if any sensor anomalous)
            - per_sensor_labels: Binary labels per sensor per timestep (n_samples, n_sensors)
            - attribute: Metadata including source dataset, injection config, sensor names
    """
    if config is None:
        config = InjectionConfig()

    rng = np.random.default_rng(config.seed)

    # Load TSDB dataset
    df = load_tsdb_dataset(dataset_name)
    sensor_names = df.columns.tolist()
    data = df[sensor_names].to_numpy(dtype=float)
    timestamps = df.index.to_pydatetime().tolist()

    # Standardize each sensor for consistent anomaly intensity
    data_std = data.std(axis=0)
    data_mean = data.mean(axis=0)
    data_normalized = (data - data_mean) / (data_std + 1e-8)

    # Determine target sensors
    if config.target_sensors is None:
        target_indices = list(range(len(sensor_names)))
    else:
        target_indices = [sensor_names.index(s) for s in config.target_sensors]

    # Detect clean windows if detector provided and avoidance enabled
    clean_windows = []
    if config.avoid_high_score_regions and detector is not None:
        clean_windows = detect_clean_windows(
            data_normalized,
            detector,
            window_size=config.window_size,
            threshold=config.high_score_threshold,
        )

    # Prepare injection specs per target sensor
    all_specs_per_sensor: dict[int, list[AnomalySpec]] = {idx: [] for idx in target_indices}
    all_injection_windows: dict[int, list[tuple[int, int]]] = {idx: [] for idx in target_indices}

    for sensor_idx in target_indices:
        sensor_data = data_normalized[:, sensor_idx]

        # Select injection windows
        if config.placement == "periodic" and config.periodic_interval is not None:
            num_anomalies = config.num_anomalies_per_sensor
        else:
            num_anomalies = config.num_anomalies_per_sensor

        injection_windows = select_injection_windows(
            clean_windows=clean_windows,
            num_anomalies=num_anomalies,
            anomaly_duration_range=config.anomaly_duration_range,
            placement=config.placement,
            periodic_interval=config.periodic_interval,
            rng=rng,
            series_length=len(data_normalized),
        )

        all_injection_windows[sensor_idx] = injection_windows

        # Create anomaly specs for each window
        for start_idx, end_idx in injection_windows:
            duration = end_idx - start_idx
            anomaly_type = rng.choice(config.anomaly_types)
            magnitude = config.anomaly_intensity
            direction = rng.choice(["up", "down"])

            # Find matching anomaly attribute for shape
            from datasets.synthetic.attributes import ANOMALY_ATTRIBUTES
            attr = next(a for a in ANOMALY_ATTRIBUTES if a.name == anomaly_type)

            spec = AnomalySpec(
                anomaly_type=anomaly_type,
                start_idx=start_idx,
                duration=duration,
                magnitude=magnitude,
                shape=attr.shape,
                direction=direction,
            )
            all_specs_per_sensor[sensor_idx].append(spec)

    # Inject anomalies sensor by sensor
    anomalous_data = data_normalized.copy()
    per_sensor_labels = np.zeros_like(data_normalized, dtype=int)

    for sensor_idx in target_indices:
        specs = all_specs_per_sensor[sensor_idx]
        if specs:
            anomalous_data[:, sensor_idx], labels = inject_multiple_anomalies(
                anomalous_data[:, sensor_idx], specs, rng=rng
            )
            per_sensor_labels[:, sensor_idx] = labels

    # Aggregate labels: 1 if any sensor is anomalous at that timestep
    labels = (per_sensor_labels.sum(axis=1) > 0).astype(int)

    # Convert back to original scale
    anomalous_data_original = anomalous_data * data_std + data_mean
    normal_data_original = data_normalized * data_std + data_mean

    # Prepare attribute metadata
    attribute = {
        "source_tsdb_dataset": dataset_name,
        "sensor_names": sensor_names,
        "target_sensors": [sensor_names[i] for i in target_indices],
        "injection_config": {
            "anomaly_types": config.anomaly_types,
            "anomaly_intensity": config.anomaly_intensity,
            "anomaly_duration_range": config.anomaly_duration_range,
            "num_anomalies_per_sensor": config.num_anomalies_per_sensor,
            "placement": config.placement,
            "periodic_interval": config.periodic_interval,
            "avoid_high_score_regions": config.avoid_high_score_regions,
            "high_score_threshold": config.high_score_threshold,
        },
        "injection_windows": {
            sensor_names[idx]: windows for idx, windows in all_injection_windows.items()
        },
        "clean_windows_detected": len(clean_windows) > 0,
        "num_clean_windows": len(clean_windows),
        "timestamps": [ts.isoformat() for ts in timestamps],
    }

    return {
        "normal_time_series": normal_data_original,
        "time_series": anomalous_data_original,
        "labels": labels,
        "per_sensor_labels": per_sensor_labels,
        "attribute": attribute,
    }


def inject_anomalies_into_array(
    data: np.ndarray,
    config: InjectionConfig,
    sensor_names: list[str] | None = None,
    detector=None,
) -> dict[str, Any]:
    """Inject anomalies into a generic numpy array (non-TSDB).

    Args:
        data: Input array (n_samples, n_sensors)
        config: Injection configuration
        sensor_names: Optional sensor names
        detector: Optional detector for clean window detection

    Returns:
        Same format as inject_anomalies_into_tsdb
    """
    if sensor_names is None:
        sensor_names = [f"sensor_{i}" for i in range(data.shape[1])]

    # Standardize
    data_std = data.std(axis=0)
    data_mean = data.mean(axis=0)
    data_normalized = (data - data_mean) / (data_std + 1e-8)

    # Determine target sensors
    if config.target_sensors is None:
        target_indices = list(range(len(sensor_names)))
    else:
        target_indices = [sensor_names.index(s) for s in config.target_sensors]

    # Detect clean windows
    clean_windows = []
    if config.avoid_high_score_regions and detector is not None:
        clean_windows = detect_clean_windows(
            data_normalized,
            detector,
            window_size=config.window_size,
            threshold=config.high_score_threshold,
        )

    # Prepare injection specs
    all_specs_per_sensor: dict[int, list[AnomalySpec]] = {idx: [] for idx in target_indices}
    all_injection_windows: dict[int, list[tuple[int, int]]] = {idx: [] for idx in target_indices}

    rng = np.random.default_rng(config.seed)

    for sensor_idx in target_indices:
        if config.placement == "periodic" and config.periodic_interval is not None:
            num_anomalies = config.num_anomalies_per_sensor
        else:
            num_anomalies = config.num_anomalies_per_sensor

        injection_windows = select_injection_windows(
            clean_windows=clean_windows,
            num_anomalies=num_anomalies,
            anomaly_duration_range=config.anomaly_duration_range,
            placement=config.placement,
            periodic_interval=config.periodic_interval,
            rng=rng,
            series_length=len(data_normalized),
        )

        all_injection_windows[sensor_idx] = injection_windows

        for start_idx, end_idx in injection_windows:
            duration = end_idx - start_idx
            anomaly_type = rng.choice(config.anomaly_types)
            magnitude = config.anomaly_intensity
            direction = rng.choice(["up", "down"])

            from datasets.synthetic.attributes import ANOMALY_ATTRIBUTES
            attr = next(a for a in ANOMALY_ATTRIBUTES if a.name == anomaly_type)

            spec = AnomalySpec(
                anomaly_type=anomaly_type,
                start_idx=start_idx,
                duration=duration,
                magnitude=magnitude,
                shape=attr.shape,
                direction=direction,
            )
            all_specs_per_sensor[sensor_idx].append(spec)

    # Inject
    anomalous_data = data_normalized.copy()
    per_sensor_labels = np.zeros_like(data_normalized, dtype=int)

    for sensor_idx in target_indices:
        specs = all_specs_per_sensor[sensor_idx]
        if specs:
            anomalous_data[:, sensor_idx], labels = inject_multiple_anomalies(
                anomalous_data[:, sensor_idx], specs, rng=rng
            )
            per_sensor_labels[:, sensor_idx] = labels

    labels = (per_sensor_labels.sum(axis=1) > 0).astype(int)

    # Convert back
    anomalous_data_original = anomalous_data * data_std + data_mean
    normal_data_original = data_normalized * data_std + data_mean

    attribute = {
        "source": "array",
        "sensor_names": sensor_names,
        "target_sensors": [sensor_names[i] for i in target_indices],
        "injection_config": {
            "anomaly_types": config.anomaly_types,
            "anomaly_intensity": config.anomaly_intensity,
            "anomaly_duration_range": config.anomaly_duration_range,
            "num_anomalies_per_sensor": config.num_anomalies_per_sensor,
            "placement": config.placement,
            "periodic_interval": config.periodic_interval,
            "avoid_high_score_regions": config.avoid_high_score_regions,
            "high_score_threshold": config.high_score_threshold,
        },
        "injection_windows": {
            sensor_names[idx]: windows for idx, windows in all_injection_windows.items()
        },
        "clean_windows_detected": len(clean_windows) > 0,
        "num_clean_windows": len(clean_windows),
    }

    return {
        "normal_time_series": normal_data_original,
        "time_series": anomalous_data_original,
        "labels": labels,
        "per_sensor_labels": per_sensor_labels,
        "attribute": attribute,
    }