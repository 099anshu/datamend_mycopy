"""PyGrinder-based missingness corruption for the anomaly-detection pipeline.

All PyGrinder interaction lives here. The public functions are:

- ``apply_corruption``: corrupt a copy of a 2D ``(T, C)`` array.
- ``calc_missing_rate``: actual missing rate of a corrupted array.
- ``handle_missing_values``: apply an explicit, user-selected missing-value
  strategy (``reject`` default, ``ffill``, ``bfill``, ``mean``,
  ``interpolate``) to a copy of the data.

Method and parameter validation raises ``CorruptionConfigError`` (a
``ValueError``), which callers should map to HTTP 400. Missing-value handling
raises ``MissingValueHandlingError`` (also a ``ValueError``) when the user
selects ``reject`` (the default) while NaNs are present, or when a strategy
cannot fully impute the data.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
import pygrinder

SUPPORTED_METHODS = frozenset(
    {
        "mcar",
        "mar_logistic",
        "mnar_x",
        "mnar_t",
        "mnar_nonuniform",
        "rdo",
        "seq_missing",
        "block_missing",
    }
)

SUPPORTED_STRATEGIES = frozenset(
    {"reject", "ffill", "bfill", "mean", "interpolate"}
)

# Methods that require 3D input (n_samples, n_steps, n_features) in PyGrinder.
_NEEDS_3D = frozenset(
    {"mnar_x", "mnar_t", "mnar_nonuniform", "seq_missing", "block_missing"}
)

# Accepted parameters per method: (required, optional).
_METHOD_PARAMS: Dict[str, Tuple[frozenset, frozenset]] = {
    "mcar": (frozenset({"p"}), frozenset()),
    "rdo": (frozenset({"p"}), frozenset()),
    "mar_logistic": (frozenset({"obs_rate", "missing_rate"}), frozenset()),
    "mnar_x": (frozenset(), frozenset({"offset"})),
    "mnar_t": (frozenset(), frozenset({"cycle", "pos", "scale"})),
    "mnar_nonuniform": (frozenset({"p"}), frozenset({"increase_factor"})),
    "seq_missing": (frozenset({"p", "seq_len"}), frozenset()),
    "block_missing": (frozenset({"factor", "block_len", "block_width"}), frozenset()),
}

_DEFAULTS: Dict[str, Dict[str, float]] = {
    "mnar_x": {"offset": 0.0},
    "mnar_t": {"cycle": 20.0, "pos": 10.0, "scale": 3.0},
    "mnar_nonuniform": {"increase_factor": 0.5},
}


class CorruptionConfigError(ValueError):
    """Raised when a corruption method or its parameters are invalid."""


class MissingValueHandlingError(ValueError):
    """Raised when missing values cannot be handled under the selected strategy."""


def _require_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CorruptionConfigError(
            f"Parameter {name!r} must be a number, got {type(value).__name__}"
        )
    return float(value)


def _require_range(
    value: Any,
    name: str,
    lower: float = 0.0,
    upper: float = 1.0,
    *,
    lower_exclusive: bool = True,
    upper_exclusive: bool = True,
) -> float:
    value = _require_number(value, name)
    if lower_exclusive and value <= lower:
        raise CorruptionConfigError(
            f"Parameter {name!r} must be in ({lower}, {upper}), got {value}"
        )
    if not lower_exclusive and value < lower:
        raise CorruptionConfigError(
            f"Parameter {name!r} must be >= {lower}, got {value}"
        )
    if upper_exclusive and value >= upper:
        raise CorruptionConfigError(
            f"Parameter {name!r} must be in ({lower}, {upper}), got {value}"
        )
    if not upper_exclusive and value > upper:
        raise CorruptionConfigError(
            f"Parameter {name!r} must be <= {upper}, got {value}"
        )
    return value


def _require_positive_int(value: Any, name: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CorruptionConfigError(
            f"Parameter {name!r} must be an integer, got {type(value).__name__}"
        )
    if value < 1:
        raise CorruptionConfigError(f"Parameter {name!r} must be >= 1, got {value}")
    if value > maximum:
        raise CorruptionConfigError(
            f"Parameter {name!r} must be <= {maximum}, got {value}"
        )
    return value


def _validate_params(method: str, params: Dict[str, Any], X: np.ndarray) -> None:
    required, optional = _METHOD_PARAMS[method]
    unknown = set(params) - (required | optional)
    if unknown:
        names = ", ".join(sorted(unknown))
        raise CorruptionConfigError(
            f"Unsupported parameter(s) for method {method!r}: {names}"
        )
    missing = required - set(params)
    if missing:
        names = ", ".join(sorted(missing))
        raise CorruptionConfigError(
            f"Missing required parameter(s) for method {method!r}: {names}"
        )

    n_steps, n_features = X.shape
    if method in ("mcar", "rdo"):
        _require_range(params["p"], "p")
    elif method == "mar_logistic":
        _require_range(params["obs_rate"], "obs_rate")
        _require_range(params["missing_rate"], "missing_rate")
    elif method == "mnar_x":
        if "offset" in params:
            _require_number(params["offset"], "offset")
    elif method == "mnar_t":
        if "cycle" in params:
            _require_number(params["cycle"], "cycle")
        if "pos" in params:
            _require_number(params["pos"], "pos")
        if "scale" in params:
            _require_range(params["scale"], "scale", lower=0.0, lower_exclusive=False)
    elif method == "mnar_nonuniform":
        _require_range(params["p"], "p")
        if "increase_factor" in params:
            _require_range(
                params["increase_factor"],
                "increase_factor",
                lower=0.0,
                lower_exclusive=False,
            )
    elif method == "seq_missing":
        _require_range(params["p"], "p", upper_exclusive=False)
        _require_positive_int(params["seq_len"], "seq_len", n_steps)
    elif method == "block_missing":
        _require_range(params["factor"], "factor")
        _require_positive_int(params["block_len"], "block_len", n_steps)
        _require_positive_int(params["block_width"], "block_width", n_features)


def _resolve_params(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    resolved = dict(_DEFAULTS.get(method, {}))
    resolved.update(params)
    return resolved


def _call_pygrinder(method: str, X: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
    params = _resolve_params(method, params)
    if method == "mcar":
        return pygrinder.mcar(X, p=params["p"])
    if method == "rdo":
        return pygrinder.rdo(X, p=params["p"])
    if method == "mar_logistic":
        return pygrinder.mar_logistic(
            X, obs_rate=params["obs_rate"], missing_rate=params["missing_rate"]
        )
    if method == "mnar_x":
        return pygrinder.mnar_x(X, offset=params["offset"])
    if method == "mnar_t":
        return pygrinder.mnar_t(
            X, cycle=params["cycle"], pos=params["pos"], scale=params["scale"]
        )
    if method == "mnar_nonuniform":
        corrupted, _probabilities = pygrinder.mnar_nonuniform(
            X, p=params["p"], increase_factor=params["increase_factor"]
        )
        return corrupted
    if method == "seq_missing":
        return pygrinder.seq_missing(X, p=params["p"], seq_len=params["seq_len"])
    if method == "block_missing":
        return pygrinder.block_missing(
            X,
            factor=params["factor"],
            block_len=params["block_len"],
            block_width=params["block_width"],
        )
    raise CorruptionConfigError(f"Unhandled corruption method {method!r}")


def apply_corruption(
    X: np.ndarray, method: str, params: Dict[str, Any] | None = None
) -> np.ndarray:
    """Corrupt a copy of ``X`` using the given PyGrinder ``method``.

    Parameters
    ----------
    X:
        2D array of shape ``(T, C)``.
    method:
        One of :data:`SUPPORTED_METHODS`.
    params:
        Method-specific parameters. Keys are validated strictly per method.

    Returns
    -------
    Corrupted copy of ``X`` with NaNs inserted. The original ``X`` is never
    modified.
    """
    params = dict(params or {})
    if method not in SUPPORTED_METHODS:
        supported = ", ".join(sorted(SUPPORTED_METHODS))
        raise CorruptionConfigError(
            f"Unknown corruption method {method!r}. Supported methods: {supported}"
        )

    X = np.asarray(X, dtype=np.float64)
    if X.ndim != 2:
        raise CorruptionConfigError(
            f"Corruption expects a 2D array of shape (T, C), got shape {X.shape}"
        )

    _validate_params(method, params, X)

    if method in _NEEDS_3D:
        # PyGrinder's 3D-only methods destructure (n_samples, n_steps, n_features).
        X_3d = X[np.newaxis, :, :]
        corrupted = _call_pygrinder(method, X_3d, params)
        return np.asarray(corrupted, dtype=np.float64).reshape(X.shape)

    return np.asarray(_call_pygrinder(method, X, params), dtype=np.float64)


def calc_missing_rate(X: np.ndarray) -> float:
    """Actual missing rate of ``X`` in ``[0, 1]``."""
    return float(pygrinder.calc_missing_rate(X))


def handle_missing_values(
    X: np.ndarray, strategy: str = "reject"
) -> np.ndarray:
    """Apply an explicit missing-value handling strategy to a copy of ``X``.

    Strategies
    ----------
    ``reject``:
        Default. If ``X`` contains NaNs, raise ``MissingValueHandlingError``
        (TimeRCD does not support NaNs; the user must select an imputation
        strategy). Otherwise return ``X`` unchanged.
    ``ffill``:
        Per-column forward-fill; leading NaNs are back-filled.
    ``bfill``:
        Per-column backward-fill; trailing NaNs are forward-filled.
    ``mean``:
        Per-column ``fillna(column_mean)``.
    ``interpolate``:
        Per-column linear interpolation; leading NaNs are forward-filled and
        trailing NaNs are back-filled.

    The original ``X`` is never modified, rows are never dropped, and the
    output shape matches the input shape. No automatic or fallback imputation
    (e.g. filling with ``0``) is ever performed.
    """
    if strategy not in SUPPORTED_STRATEGIES:
        supported = ", ".join(sorted(SUPPORTED_STRATEGIES))
        raise CorruptionConfigError(
            f"Unknown missing-value handling strategy {strategy!r}. "
            f"Supported strategies: {supported}"
        )

    original_shape = np.asarray(X).shape
    X = np.asarray(X, dtype=np.float64)
    if X.ndim == 1:
        X = X.reshape(-1, 1)

    if not np.isnan(X).any():
        return X.reshape(original_shape)

    if strategy == "reject":
        raise MissingValueHandlingError(
            "Missing values are present, but TimeRCD does not support NaNs. "
            "Select an imputation strategy via 'missingValueHandling' "
            "('ffill', 'bfill', 'mean', or 'interpolate') before scoring."
        )

    frame = pd.DataFrame(X)
    if strategy == "ffill":
        frame = frame.ffill()
        frame = frame.bfill()
    elif strategy == "bfill":
        frame = frame.bfill()
        frame = frame.ffill()
    elif strategy == "mean":
        means = frame.mean()
        if means.isna().any():
            columns = [int(index) for index in means.index[means.isna()].tolist()]
            raise MissingValueHandlingError(
                f"Strategy 'mean' cannot impute column(s) with no observed values: {columns}"
            )
        frame = frame.fillna(means)
    elif strategy == "interpolate":
        frame = frame.interpolate(method="linear", limit_direction="both")
    else:
        raise CorruptionConfigError(
            f"Unhandled missing-value handling strategy {strategy!r}"
        )

    result = frame.to_numpy(dtype=np.float64)
    if np.isnan(result).any():
        raise MissingValueHandlingError(
            f"Strategy {strategy!r} could not fully impute the missing values. "
            "Select a different imputation strategy via 'missingValueHandling'."
        )
    return result.reshape(original_shape)
