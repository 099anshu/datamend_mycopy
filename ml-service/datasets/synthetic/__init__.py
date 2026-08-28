"""Synthetic Time Series Anomaly Detection Dataset Generator.

This module provides functionality for generating synthetic univariate and multivariate
time series datasets with configurable anomaly patterns, as well as semi-synthetic
evaluation by injecting anomalies into real TSDB data.
"""

from datasets.synthetic.generator import (
    generate_dataset,
    save_dataset,
    load_dataset,
    get_supported_anomaly_types,
    get_supported_patterns,
)
from datasets.synthetic.semi_synthetic import (
    inject_anomalies_into_tsdb,
    inject_anomalies_into_array,
    InjectionConfig,
)

__all__ = [
    "generate_dataset",
    "save_dataset",
    "load_dataset",
    "get_supported_anomaly_types",
    "get_supported_patterns",
    "inject_anomalies_into_tsdb",
    "inject_anomalies_into_array",
    "InjectionConfig",
]