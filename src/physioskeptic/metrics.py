"""Evaluation metrics for PhysioSkeptic experiments.

Primary metric:
  - Macro-F1 (macro-averaged F1 across SR, STACH, SBRAD, AF_FAMILY, PACE)

Secondary metrics:
  - AUROC   (one-vs-rest macro-averaged)
  - ECE     (Expected Calibration Error, 10 equal-width bins)
  - Brier   (multiclass Brier score)
  - NLL     (negative log-likelihood)

These functions operate on supplied predictions. They do not perform patient
splitting, clustered inference or significance testing.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import f1_score, log_loss, roc_auc_score

RHYTHM_CLASSES = ("SR", "STACH", "SBRAD", "AF_FAMILY", "PACE")


def _validate_probabilities(y_true_idx: np.ndarray, prob: np.ndarray):
    target = np.asarray(y_true_idx)
    values = np.asarray(prob, dtype=float)
    if (
        values.ndim != 2
        or values.shape[0] == 0
        or values.shape[1] < 2
        or target.ndim != 1
        or len(target) != len(values)
    ):
        raise ValueError("Expected N integer labels and an N by C probability matrix")
    if (
        not np.issubdtype(target.dtype, np.integer)
        or np.any(target < 0)
        or np.any(target >= values.shape[1])
    ):
        raise ValueError("Reference labels must be valid integer class indices")
    if (
        not np.isfinite(values).all()
        or np.any(values < 0)
        or np.any(values > 1)
        or not np.allclose(values.sum(axis=1), 1.0)
    ):
        raise ValueError("Probabilities must be finite, nonnegative and sum to one per row")
    return target, values


def macro_f1(y_true: list[str], y_pred: list[str]) -> float:
    """Compute macro-averaged F1 score across all rhythm classes (primary metric).

    Args:
        y_true: Ground-truth rhythm class labels (strings from RHYTHM_CLASSES).
        y_pred: Predicted rhythm class labels.

    Returns:
        Macro-F1 in [0, 1].
    """
    if not len(y_true) or len(y_true) != len(y_pred):
        raise ValueError("Reference and predicted labels must have the same nonzero length")
    if not (set(y_true) | set(y_pred)).issubset(RHYTHM_CLASSES):
        raise ValueError("Unknown rhythm class")
    return float(
        f1_score(y_true, y_pred, labels=list(RHYTHM_CLASSES), average="macro", zero_division=0)
    )


def expected_calibration_error(conf: np.ndarray, correct: np.ndarray, n_bins: int = 10) -> float:
    """Compute Expected Calibration Error (ECE) with equal-width bins.

    Uses 10 bins as reported in the paper. ECE measures the gap between predicted
    confidence and empirical accuracy, weighted by bin occupancy.

    Args:
        conf: Predicted confidence scores in [0, 1], shape (N,).
        correct: Binary correctness indicators (1 = correct, 0 = wrong), shape (N,).
        n_bins: Number of equal-width calibration bins (default 10, by default).

    Returns:
        ECE in [0, 1].
    """
    conf = np.asarray(conf, dtype=float)
    correct = np.asarray(correct, dtype=float)
    if (
        conf.ndim != 1
        or correct.shape != conf.shape
        or conf.size == 0
        or not isinstance(n_bins, int)
        or n_bins < 1
        or not np.isfinite(conf).all()
        or not np.isfinite(correct).all()
        or np.any(conf < 0)
        or np.any(conf > 1)
        or not np.isin(correct, [0, 1]).all()
    ):
        raise ValueError("ECE requires aligned finite confidence and binary correctness arrays")
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for index, (lo, hi) in enumerate(zip(bins[:-1], bins[1:])):
        mask = ((conf >= lo) if index == 0 else (conf > lo)) & (conf <= hi)
        if mask.any():
            ece += mask.mean() * abs(conf[mask].mean() - correct[mask].mean())
    return float(ece)


def multiclass_auroc(y_true_idx: np.ndarray, prob: np.ndarray) -> float:
    """Compute macro-averaged one-vs-rest AUROC.

    Args:
        y_true_idx: Integer class indices, shape (N,).
        prob: Predicted class probability matrix, shape (N, C).

    Returns:
        Macro OvR AUROC in [0, 1].
    """
    y_true_idx, prob = _validate_probabilities(y_true_idx, prob)
    if len(np.unique(y_true_idx)) != prob.shape[1]:
        raise ValueError("Macro AUROC requires positive and negative examples for every class")
    if prob.shape[1] == 2:
        return float(roc_auc_score(y_true_idx, prob[:, 1]))
    return float(roc_auc_score(y_true_idx, prob, multi_class="ovr", average="macro"))


def nll(y_true_idx: np.ndarray, prob: np.ndarray) -> float:
    """Compute multiclass negative log-likelihood.

    Args:
        y_true_idx: Integer class indices, shape (N,).
        prob: Predicted class probability matrix, shape (N, C).

    Returns:
        NLL (nats per sample), lower is better.
    """
    y_true_idx, prob = _validate_probabilities(y_true_idx, prob)
    return float(log_loss(y_true_idx, prob, labels=np.arange(prob.shape[1])))


def multiclass_brier(y_true_idx: np.ndarray, prob: np.ndarray) -> float:
    """Compute multiclass Brier score as mean squared error over one-hot targets.

    Args:
        y_true_idx: Integer class indices, shape (N,).
        prob: Predicted class probability matrix, shape (N, C).

    Returns:
        Brier score in [0, 2], lower is better.
    """
    y_true_idx, prob = _validate_probabilities(y_true_idx, prob)
    y = np.zeros_like(prob)
    y[np.arange(len(y_true_idx)), y_true_idx] = 1.0
    return float(np.mean(np.sum((prob - y) ** 2, axis=1)))
