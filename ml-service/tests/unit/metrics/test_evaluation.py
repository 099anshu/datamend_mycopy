import numpy as np
import pandas as pd
import pytest

from corruption.pygrinder import handle_missing_values
from datasets.synthetic.anomalies import (
    AnomalySpec,
    inject_multiple_anomalies,
    inject_anomaly,
)
from evaluation.metrics import (
    EvaluationResult,
    evaluate_all,
    evaluate_thresholds,
    precision_recall_f1,
    pr_auc,
    roc_auc,
)

ETTH1_COLUMNS = ["HUFL", "HULL", "MUFL", "MULL", "LUFL", "LULL", "OT"]


def _inject_random_anomalies(data: np.ndarray, anomaly_rate: float, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Helper to inject random anomalies using new API, matching old inject_anomalies behavior."""
    rng = np.random.default_rng(seed)
    n_steps, n_features = data.shape
    anomaly_rate = float(anomaly_rate)
    if not 0.0 < anomaly_rate < 1.0:
        raise ValueError(f"anomaly_rate must be in (0, 1), got {anomaly_rate}")

    k = min(int(round(n_steps * anomaly_rate)), n_steps)
    rows = rng.choice(n_steps, size=k, replace=False)

    column_std = np.std(data, axis=0)
    column_std = np.where(column_std == 0.0, 1.0, column_std)

    specs = []
    for row in rows:
        kind = rng.choice(["spike", "drop", "contextual"])
        if kind == "spike":
            specs.append(AnomalySpec("spike", int(row), 1, 3.0, "constant", "up"))
        elif kind == "drop":
            specs.append(AnomalySpec("drop", int(row), 1, 3.0, "constant", "down"))
        else:
            specs.append(AnomalySpec("spike", int(row), 4, 1.0, "sinusoidal", "up"))

    modified, labels = inject_multiple_anomalies(data.copy(), specs, rng=rng)
    return modified, labels.astype(bool)


@pytest.mark.parametrize("n_steps,rate", [(100, 0.01), (1000, 0.01), (500, 0.05)])
def test_injection_produces_expected_label_count(n_steps, rate):
    data = np.random.default_rng(0).normal(size=(n_steps, 3))
    modified, labels = _inject_random_anomalies(data, anomaly_rate=rate, seed=0)
    expected = min(int(round(n_steps * rate)), n_steps)
    assert labels.shape == (n_steps,)
    assert labels.dtype == bool
    assert int(labels.sum()) == expected
    assert modified.shape == data.shape


def test_labels_are_binary():
    data = np.random.default_rng(1).normal(size=(50, 2))
    _, labels = _inject_random_anomalies(data, anomaly_rate=0.1, seed=1)
    assert set(np.unique(labels)).issubset({False, True})


def test_injection_does_not_modify_array_input():
    data = np.random.default_rng(2).normal(size=(100, 3))
    original = data.copy()
    _inject_random_anomalies(data, anomaly_rate=0.02, seed=2)
    np.testing.assert_array_equal(data, original)


def test_injection_does_not_modify_dataframe_input():
    index = pd.date_range("2020-01-01", periods=100, freq="h")
    df = pd.DataFrame(
        np.random.default_rng(3).normal(size=(100, 2)),
        index=index,
        columns=["a", "b"],
    )
    original = df.copy()
    modified, labels = _inject_random_anomalies(df.to_numpy(), anomaly_rate=0.02, seed=3)
    modified_df = pd.DataFrame(modified, index=index, columns=["a", "b"])
    pd.testing.assert_frame_equal(df, original)
    assert isinstance(modified_df, pd.DataFrame)
    pd.testing.assert_index_equal(modified_df.index, index)
    pd.testing.assert_index_equal(modified_df.columns, df.columns)


def test_injection_reproducible_with_same_seed():
    data = np.random.default_rng(4).normal(size=(200, 3))
    first_modified, first_labels = _inject_random_anomalies(data, anomaly_rate=0.01, seed=42)
    second_modified, second_labels = _inject_random_anomalies(data, anomaly_rate=0.01, seed=42)
    np.testing.assert_array_equal(first_modified, second_modified)
    np.testing.assert_array_equal(first_labels, second_labels)


def test_metrics_on_known_predictions():
    y_true = np.array([True, True, False, False, True])
    y_pred = np.array([True, True, True, False, False])
    precision, recall, f1 = precision_recall_f1(y_true, y_pred)
    assert precision == pytest.approx(2 / 3)
    assert recall == pytest.approx(2 / 3)
    assert f1 == pytest.approx(2 / 3)


def test_metrics_zero_denominator_guards():
    assert precision_recall_f1([], []) == (0.0, 0.0, 0.0)
    assert precision_recall_f1([True, True], [False, False]) == (0.0, 0.0, 0.0)
    assert precision_recall_f1([False, False], [False, False]) == (0.0, 0.0, 0.0)


def test_pr_auc_roc_auc_perfect_separation():
    y_true = np.array([False, False, True, True])
    scores = np.array([0.1, 0.2, 0.9, 0.8])
    assert pr_auc(y_true, scores) == pytest.approx(1.0)
    assert roc_auc(y_true, scores) == pytest.approx(1.0)


def test_auc_single_class_guard():
    assert pr_auc([True, True, True], [0.5, 0.6, 0.7]) == 0.0
    assert roc_auc([False, False, False], [0.5, 0.6, 0.7]) == 0.0


def test_threshold_evaluation_per_threshold():
    y_true = np.array([True, True, False, False])
    scores = np.array([0.9, 0.6, 0.4, 0.2])
    thresholds = np.array([0.5, 0.7, 0.95])
    results = evaluate_thresholds(y_true, scores, thresholds)
    assert len(results) == 3
    assert [result.threshold for result in results] == [0.5, 0.7, 0.95]
    assert results[0].recall == pytest.approx(1.0)
    assert results[1].recall == pytest.approx(0.5)


def test_best_threshold_selection():
    y_true = np.array([True, True, True, False, False, False, False, False])
    scores = np.array([0.9, 0.8, 0.7, 0.6, 0.4, 0.3, 0.2, 0.1])
    result = evaluate_all(y_true, scores)
    assert isinstance(result, EvaluationResult)
    assert 0.0 <= result.best_threshold <= 1.0
    assert 0.0 <= result.precision <= 1.0
    assert 0.0 <= result.recall <= 1.0
    assert 0.0 <= result.f1 <= 1.0
    assert 0.0 <= result.pr_auc <= 1.0
    assert 0.0 <= result.roc_auc <= 1.0


def test_end_to_end_etth1_evaluation():
    from datasets.tsdb_loader import load_tsdb_dataset
    from detectors.timercd import TimeRCDDetector

    df = load_tsdb_dataset("ETTh1")
    data = df[ETTH1_COLUMNS].iloc[:500].to_numpy(dtype=float)
    modified, labels = _inject_random_anomalies(data, anomaly_rate=0.01, seed=0)
    filled = handle_missing_values(modified, "ffill")
    scores = TimeRCDDetector().detect(filled)
    assert len(scores) == len(labels)
    result = evaluate_all(labels, np.asarray(scores).ravel())
    assert 0.0 <= result.pr_auc <= 1.0
    assert 0.0 <= result.roc_auc <= 1.0