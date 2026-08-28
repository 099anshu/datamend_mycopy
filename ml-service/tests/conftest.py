"""Shared test fixtures for ml-service tests."""

import pytest
import numpy as np

from datasets.tsdb_loader import load_tsdb_dataset

ETTH1_COLUMNS = ["HUFL", "HULL", "MUFL", "MULL", "LUFL", "LULL", "OT"]


@pytest.fixture(scope="session")
def etth1_data() -> np.ndarray:
    """Load ETTh1 dataset as numpy array (session-scoped)."""
    df = load_tsdb_dataset("ETTh1")
    return df[ETTH1_COLUMNS].to_numpy(dtype=np.float64)


@pytest.fixture(scope="session")
def detector():
    """TimeRCDDetector instance (session-scoped). Lazy import to avoid requiring time_rcd."""
    from detectors.timercd import TimeRCDDetector
    return TimeRCDDetector()


@pytest.fixture(scope="function")
def rng_seed() -> int:
    """Fixed random seed for reproducible tests."""
    return 42


@pytest.fixture(scope="function")
def rng(rng_seed: int) -> np.random.Generator:
    """Random number generator with fixed seed."""
    return np.random.default_rng(rng_seed)