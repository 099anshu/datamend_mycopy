"""Deprecated alias for evaluate_timercd.

This module is deprecated. Use evaluation.experiment_runner instead.
"""

import warnings
from evaluation.experiment_runner import main, run_experiment

warnings.warn(
    "evaluation.evaluate_timercd is deprecated and will be removed in a future version. "
    "Use evaluation.experiment_runner instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["main", "run_experiment"]