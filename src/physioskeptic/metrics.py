"""Evaluation metrics for PhysioSkeptic experiments (paper §4.2).

Primary metric:
  - Macro-F1 (macro-averaged F1 across SR, STACH, SBRAD, AF_FAMILY, PACE)

Secondary metrics:
  - AUROC   (one-vs-rest macro-averaged)
  - ECE     (Expected Calibration Error, 10 equal-width bins)
  - Brier   (multiclass Brier score)
  - NLL     (negative log-likelihood)

Statistical testing: Wilcoxon signed-rank + Bonferroni correction, p < 0.05.
Test windows are clustered within patients to avoid data leakage.
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import brier_score_loss, f1_score, log_loss, roc_auc_score


def macro_f1(y_true: list[str], y_pred: list[str]) -> float:
    """Compute macro-averaged F1 score across all rhythm classes (primary metric).

    Args:
        y_true: Ground-truth rhythm class labels (strings from RHYTHM_CLASSES).
        y_pred: Predicted rhythm class labels.

    Returns:
        Macro-F1 in [0, 1].
    """
    return float(f1_score(y_true, y_pred, average="macro"))


def expected_calibration_error(conf: np.ndarray, correct: np.ndarray, n_bins: int = 10) -> float:
    """Compute Expected Calibration Error (ECE) with equal-width bins (paper §4.2).

    Uses 10 bins as reported in the paper. ECE measures the gap between predicted
    confidence and empirical accuracy, weighted by bin occupancy.

    Args:
        conf: Predicted confidence scores in [0, 1], shape (N,).
        correct: Binary correctness indicators (1 = correct, 0 = wrong), shape (N,).
        n_bins: Number of equal-width calibration bins (default 10, per paper).

    Returns:
        ECE in [0, 1].
    """
    conf = np.asarray(conf, dtype=float)
    correct = np.asarray(correct, dtype=float)
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (conf > lo) & (conf <= hi)
        if mask.any():
            ece += mask.mean() * abs(conf[mask].mean() - correct[mask].mean())
    return float(ece)


def multiclass_auroc(y_true_idx: np.ndarray, prob: np.ndarray) -> float:
    """Compute macro-averaged one-vs-rest AUROC (paper §4.2).

    Args:
        y_true_idx: Integer class indices, shape (N,).
        prob: Predicted class probability matrix, shape (N, C).

    Returns:
        Macro OvR AUROC in [0, 1].
    """
    return float(roc_auc_score(y_true_idx, prob, multi_class="ovr", average="macro"))


def nll(y_true_idx: np.ndarray, prob: np.ndarray) -> float:
    """Compute multiclass negative log-likelihood (paper §4.2).

    Args:
        y_true_idx: Integer class indices, shape (N,).
        prob: Predicted class probability matrix, shape (N, C).

    Returns:
        NLL (nats per sample), lower is better.
    """
    return float(log_loss(y_true_idx, prob))


def multiclass_brier(y_true_idx: np.ndarray, prob: np.ndarray) -> float:
    """Compute multiclass Brier score as mean squared error over one-hot targets (paper §4.2).

    Args:
        y_true_idx: Integer class indices, shape (N,).
        prob: Predicted class probability matrix, shape (N, C).

    Returns:
        Brier score in [0, 2], lower is better.
    """
    y = np.zeros_like(prob)
    y[np.arange(len(y_true_idx)), y_true_idx] = 1.0
    return float(np.mean(np.sum((prob - y) ** 2, axis=1)))
