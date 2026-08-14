"""Detection metrics computed from raw anomaly scores and binary labels.

Threshold-based metrics (Precision, Recall, F1) operate on ``score >= t``
predictions so evaluations can search over thresholds independently of the
fixed ``0.8`` threshold used by the FastAPI API. Curve-based metrics
(PR-AUC, ROC-AUC) use ``scikit-learn``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from sklearn.metrics import auc, precision_recall_curve, roc_curve


@dataclass(frozen=True)
class ThresholdResult:
    """Metrics for a single decision threshold."""

    threshold: float
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True)
class EvaluationResult:
    """Aggregated metrics for one evaluation run."""

    precision: float
    recall: float
    f1: float
    pr_auc: float
    roc_auc: float
    best_threshold: float
    thresholds: List[ThresholdResult]

    @property
    def best(self) -> ThresholdResult:
        """The threshold result selected as best (highest F1)."""
        return self.thresholds[self.best_index]

    @property
    def best_index(self) -> int:
        for index, result in enumerate(self.thresholds):
            if result.threshold == self.best_threshold:
                return index
        raise ValueError("best_threshold not found in thresholds")


def _as_bool_labels(y_true) -> np.ndarray:
    return np.asarray(y_true, dtype=bool)


def _as_float_scores(scores) -> np.ndarray:
    return np.asarray(scores, dtype=np.float64).ravel()


def _guard_matching_lengths(y_true: np.ndarray, scores: np.ndarray) -> None:
    if y_true.shape[0] != scores.shape[0]:
        raise ValueError(
            "labels and scores must have the same length: "
            f"got {y_true.shape[0]} labels and {scores.shape[0]} scores"
        )


def precision_recall_f1(
    y_true, y_pred, *, epsilon: float = 1e-12
) -> tuple[float, float, float]:
    """Precision, Recall, and F1 for binary predictions.

    Zero-denominator cases yield ``0.0``: F1 is ``0`` when no positives are
    predicted and when no positives exist at all.
    """
    labels = _as_bool_labels(y_true)
    preds = _as_bool_labels(y_pred)
    _guard_matching_lengths(labels, preds.astype(np.float64))

    true_positives = float(np.count_nonzero(labels & preds))
    predicted_positives = float(np.count_nonzero(preds))
    actual_positives = float(np.count_nonzero(labels))

    precision = true_positives / predicted_positives if predicted_positives else 0.0
    recall = true_positives / actual_positives if actual_positives else 0.0
    f1 = 2.0 * precision * recall / (precision + recall + epsilon)
    return precision, recall, f1


def pr_auc(y_true, scores) -> float:
    """Area under the precision-recall curve from raw scores."""
    labels = _as_bool_labels(y_true)
    scores_ = _as_float_scores(scores)
    _guard_matching_lengths(labels, scores_)

    if labels.sum() == 0 or labels.sum() == labels.shape[0]:
        return 0.0

    precision, recall, _ = precision_recall_curve(labels, scores_)
    return float(auc(recall, precision))


def roc_auc(y_true, scores) -> float:
    """Area under the ROC curve from raw scores."""
    labels = _as_bool_labels(y_true)
    scores_ = _as_float_scores(scores)
    _guard_matching_lengths(labels, scores_)

    if labels.sum() == 0 or labels.sum() == labels.shape[0]:
        return 0.0

    fpr, tpr, _ = roc_curve(labels, scores_)
    return float(auc(fpr, tpr))


def evaluate_thresholds(
    y_true, scores, thresholds: Optional[np.ndarray] = None
) -> List[ThresholdResult]:
    """Evaluate Precision/Recall/F1 for every threshold in ``thresholds``.

    Predictions use ``score >= threshold``. By default the ``[0, 1]`` range is
    scanned with 101 equally spaced thresholds.
    """
    labels = _as_bool_labels(y_true)
    scores_ = _as_float_scores(scores)
    _guard_matching_lengths(labels, scores_)

    if thresholds is None:
        thresholds = np.linspace(0.0, 1.0, 101)

    results: List[ThresholdResult] = []
    for threshold in thresholds:
        predictions = scores_ >= float(threshold)
        precision, recall, f1 = precision_recall_f1(labels, predictions)
        results.append(
            ThresholdResult(
                threshold=float(threshold),
                precision=precision,
                recall=recall,
                f1=f1,
            )
        )
    return results


def _best_threshold(results: List[ThresholdResult]) -> float:
    """Highest F1, tie-broken by higher precision."""
    best = max(results, key=lambda result: (result.f1, result.precision))
    return best.threshold


def evaluate_all(
    y_true,
    scores,
    thresholds: Optional[np.ndarray] = None,
    *,
    best_threshold: Optional[float] = None,
) -> EvaluationResult:
    """Compute all metrics for one evaluation run.

    ``best_threshold`` overrides automatic selection (highest F1, tie-broken
    by precision); the Precision/Recall/F1 in the result then reflect that
    threshold.
    """
    labels = _as_bool_labels(y_true)
    scores_ = _as_float_scores(scores)
    _guard_matching_lengths(labels, scores_)

    threshold_results = evaluate_thresholds(labels, scores_, thresholds)
    selected = (
        float(best_threshold) if best_threshold is not None else _best_threshold(threshold_results)
    )

    if best_threshold is not None:
        predictions = scores_ >= selected
        precision, recall, f1 = precision_recall_f1(labels, predictions)
    else:
        chosen = next(
            (result for result in threshold_results if result.threshold == selected),
            None,
        )
        if chosen is None:
            precision, recall, f1 = precision_recall_f1(labels, scores_ >= selected)
        else:
            precision, recall, f1 = chosen.precision, chosen.recall, chosen.f1

    return EvaluationResult(
        precision=precision,
        recall=recall,
        f1=f1,
        pr_auc=pr_auc(labels, scores_),
        roc_auc=roc_auc(labels, scores_),
        best_threshold=selected,
        thresholds=threshold_results,
    )