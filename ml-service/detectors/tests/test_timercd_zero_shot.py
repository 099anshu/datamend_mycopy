import os

import numpy as np
import pytest

from detectors.timercd import DEFAULT_WIN_SIZE, TimeRCDDetector

HF_REPO_ID = "thu-sail-lab/Time-RCD"
CHECKPOINT_FILES = {
    "uni": "best_model/pretrain_checkpoint_best_uni.pth",
    "multi": "best_model/pretrain_checkpoint_best_multi.pth",
}


def _cached_checkpoint(variant: str) -> str:
    from huggingface_hub import hf_hub_download

    return hf_hub_download(
        repo_id=HF_REPO_ID,
        filename=CHECKPOINT_FILES[variant],
        local_files_only=True,
    )


def _sample(rows: int = 128, cols: int = 2, seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).normal(size=(rows, cols))


@pytest.fixture(scope="module")
def detector() -> TimeRCDDetector:
    return TimeRCDDetector()


def test_scores_are_float_in_unit_interval_one_per_timestep(detector):
    data = _sample()
    scores = detector.detect(data)
    assert scores.shape == (data.shape[0],)
    assert np.issubdtype(np.asarray(scores).dtype, np.floating)
    assert np.all((scores >= 0.0) & (scores <= 1.0))


def test_return_logits_drive_anomaly_score(detector):
    data = _sample()
    scores, logits = detector.detect(data, return_logits=True)
    assert scores.shape == (data.shape[0],)
    assert logits.shape == (data.shape[0],)

    expected = 1.0 / (1.0 + np.exp(-logits))
    np.testing.assert_allclose(scores, expected, atol=1e-6)


def test_inference_does_not_train(detector):
    import torch

    data = _sample()
    detector.detect(data)

    assert detector._models is not None
    model = detector._models["multi"]
    before = {k: v.clone() for k, v in model._tester.model.state_dict().items()}

    detector.detect(_sample(seed=1))

    after = model._tester.model.state_dict()
    for key, tensor_before in before.items():
        torch.testing.assert_close(tensor_before, after[key])


def test_short_input_handled_gracefully(detector):
    data = _sample(rows=64, cols=2)
    assert data.shape[0] < DEFAULT_WIN_SIZE
    scores = detector.detect(data)
    assert scores.shape == (64,)
    assert np.all((scores >= 0.0) & (scores <= 1.0))


def test_checkpoint_override_valid_path(monkeypatch):
    checkpoint = _cached_checkpoint("multi")
    monkeypatch.setenv("TIMERCD_CHECKPOINT_PATH", checkpoint)
    data = _sample()
    detector = TimeRCDDetector()
    scores = detector.detect(data)
    assert scores.shape == (data.shape[0],)


def test_checkpoint_override_missing_path_raises(monkeypatch, tmp_path):
    missing = str(tmp_path / "does-not-exist.pth")
    monkeypatch.setenv("TIMERCD_CHECKPOINT_PATH", missing)
    detector = TimeRCDDetector()
    with pytest.raises(FileNotFoundError, match="does not exist"):
        detector.detect(_sample())


def test_checkpoint_env_read_at_construction(monkeypatch):
    monkeypatch.delenv("TIMERCD_CHECKPOINT_PATH", raising=False)
    detector = TimeRCDDetector()
    assert detector._checkpoint_path is None


def test_win_size_default_is_5000(detector):
    assert DEFAULT_WIN_SIZE == 5000
    assert detector._win_size == 5000