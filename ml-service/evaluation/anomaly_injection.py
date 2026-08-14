"""Reproducible synthetic anomaly injection for TSDB datasets.

The injector works on 2D numeric data ``(T, C)`` (a DataFrame or an array).
It returns a *copy* with anomalies perturbed at a configurable rate plus a
binary ground-truth label vector of shape ``(T,)`` marking exactly the
anomalous timestamps.

Supported anomaly types
-----------------------
- ``spike``: add ``+3 * std`` to every column at the injected timestamp.
- ``drop``: add ``-3 * std`` to every column at the injected timestamp.
- ``contextual``: shift a short window by a bounded amount so the shape is
  anomalous while values stay plausible.

Rate semantics
--------------
``anomaly_rate`` is the fraction of *timestamps* that are anomalous:
``k = int(round(T * anomaly_rate))`` distinct timestamps are chosen. Labels
are ``1`` at exactly those timestamps and ``0`` elsewhere.

The original input is never modified. A random seed makes the selection and
perturbations fully reproducible.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd

ANOMALY_TYPES = ("spike", "drop", "contextual")

_SPIKE_DROP_SIGMA = 3.0
_CONTEXTUAL_WINDOW = 4
_CONTEXTUAL_SHIFT_SIGMA = 1.0


def _validate_rate(anomaly_rate: float, n_steps: int) -> float:
    if isinstance(anomaly_rate, bool) or not isinstance(anomaly_rate, (int, float)):
        raise TypeError(f"anomaly_rate must be a number, got {type(anomaly_rate).__name__}")
    anomaly_rate = float(anomaly_rate)
    if not 0.0 < anomaly_rate < 1.0:
        raise ValueError(f"anomaly_rate must be in (0, 1), got {anomaly_rate}")
    if n_steps < 1:
        raise ValueError(f"data must have at least one row, got {n_steps}")
    return anomaly_rate


def _as_matrix(data) -> Tuple[np.ndarray, bool]:
    if isinstance(data, pd.DataFrame):
        return data.to_numpy(dtype=np.float64), True
    return np.asarray(data, dtype=np.float64), False


def _perturb_spike(values: np.ndarray, column_std: np.ndarray) -> None:
    values += _SPIKE_DROP_SIGMA * column_std


def _perturb_drop(values: np.ndarray, column_std: np.ndarray) -> None:
    values -= _SPIKE_DROP_SIGMA * column_std


def _perturb_contextual(modified: np.ndarray, rng: np.random.Generator, row: int) -> None:
    end = min(row + _CONTEXTUAL_WINDOW, modified.shape[0])
    window = modified[row:end, :]
    column_std = np.std(window, axis=0)
    column_std = np.where(column_std == 0.0, 1.0, column_std)
    shift = rng.normal(0.0, _CONTEXTUAL_SHIFT_SIGMA, size=window.shape)
    modified[row:end, :] = window + shift * column_std


def inject_anomalies(
    data,
    anomaly_rate: float = 0.01,
    seed: int = 0,
    anomaly_types=ANOMALY_TYPES,
) -> Tuple[pd.DataFrame | np.ndarray, np.ndarray]:
    """Inject synthetic anomalies into a copy of ``data``.

    Parameters
    ----------
    data:
        2D input, either a ``pd.DataFrame`` (output keeps its index/columns
        and returns a DataFrame) or a numeric array ``(T, C)``.
    anomaly_rate:
        Fraction of timestamps (rows) to perturb, in ``(0, 1)``.
    seed:
        Random seed for reproducible selection and perturbations.
    anomaly_types:
        Iterable of anomaly types to choose from; any subset of
        ``spike``, ``drop``, ``contextual``.

    Returns
    -------
    ``(modified, labels)`` where ``modified`` is a copy of ``data`` with the
    same shape/index and ``labels`` is a boolean array of shape ``(T,)`` with
    ``True`` exactly at the anomalous timestamps.
    """
    matrix, was_frame = _as_matrix(data)
    n_steps, n_features = matrix.shape
    anomaly_rate = _validate_rate(anomaly_rate, n_steps)

    unknown_types = set(anomaly_types) - set(ANOMALY_TYPES)
    if unknown_types:
        raise ValueError(
            f"Unknown anomaly type(s): {sorted(unknown_types)}. "
            f"Supported types: {ANOMALY_TYPES}"
        )
    anomaly_types = tuple(anomaly_types)
    if not anomaly_types:
        raise ValueError("at least one anomaly type must be provided")

    rng = np.random.default_rng(seed)
    modified = matrix.copy()
    labels = np.zeros(n_steps, dtype=bool)

    k = min(int(round(n_steps * anomaly_rate)), n_steps)
    rows = rng.choice(n_steps, size=k, replace=False)

    column_std = np.std(matrix, axis=0)
    column_std = np.where(column_std == 0.0, 1.0, column_std)

    for row in rows:
        kind = anomaly_types[int(rng.integers(0, len(anomaly_types)))]
        if kind == "spike":
            _perturb_spike(modified[row, :], column_std)
        elif kind == "drop":
            _perturb_drop(modified[row, :], column_std)
        else:
            _perturb_contextual(modified, rng, int(row))
        labels[int(row)] = True

    if was_frame:
        return pd.DataFrame(modified, index=data.index, columns=data.columns), labels
    return modified, labels