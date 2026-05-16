"""Controlled signal corruption utilities for robustness experiments (paper §4.3).

Implements three corruption families applied to ECG/PPG windows at multiple severity
levels to evaluate model robustness under realistic acquisition artifacts:
  - Gaussian noise (additive white noise, parameterized by SNR in dB)
  - Baseline wander (low-frequency sinusoidal drift)
  - Motion artifact (burst noise simulating movement transients)
"""
from __future__ import annotations

import numpy as np


def gaussian_noise(x: np.ndarray, snr_db: float, rng: np.random.Generator | None = None) -> np.ndarray:
    """Add zero-mean Gaussian noise at a specified signal-to-noise ratio.

    Noise power is calibrated to achieve the requested SNR relative to the
    input signal power.

    Args:
        x: 1-D signal array (ECG or PPG).
        snr_db: Target SNR in dB. Lower values = more noise.
        rng: Optional NumPy Generator for reproducibility (default: seed 0).

    Returns:
        Noisy signal of the same shape as x.
    """
    rng = rng or np.random.default_rng(0)
    power = np.mean(np.asarray(x) ** 2) + 1e-8
    noise_power = power / (10 ** (snr_db / 10))
    return np.asarray(x) + rng.normal(0, np.sqrt(noise_power), size=len(x))


def baseline_wander(x: np.ndarray, fs: int = 125, amplitude: float = 0.2, freq: float = 0.33) -> np.ndarray:
    """Add sinusoidal baseline wander (low-frequency respiratory artifact).

    Simulates electrode motion or respiratory-frequency baseline drift commonly
    seen in ambulatory ECG/PPG recordings.

    Args:
        x: 1-D signal array.
        fs: Sampling frequency in Hz (default 125).
        amplitude: Peak-to-peak wander amplitude in signal units (default 0.2).
        freq: Wander frequency in Hz (default 0.33 Hz ≈ 20 breaths/min).

    Returns:
        Signal with added baseline wander, same shape as x.
    """
    t = np.arange(len(x)) / fs
    return np.asarray(x) + amplitude * np.sin(2 * np.pi * freq * t)


def motion_artifact(x: np.ndarray, severity: float = 0.2, rng: np.random.Generator | None = None) -> np.ndarray:
    """Add burst-noise motion artifacts simulating movement transients.

    Injects a severity-dependent number of short Gaussian noise bursts into
    random positions of the signal to simulate motion-induced artifacts.

    Args:
        x: 1-D signal array.
        severity: Artifact severity in [0, 1]. Controls burst count, width, and amplitude.
        rng: Optional NumPy Generator for reproducibility (default: seed 0).

    Returns:
        Signal with added motion bursts, same shape as x.
    """
    rng = rng or np.random.default_rng(0)
    y = np.asarray(x, dtype=float).copy()
    n = len(y)
    bursts = max(1, int(severity * 10))
    for _ in range(bursts):
        start = rng.integers(0, max(1, n - 20))
        width = rng.integers(10, max(11, int(0.8 * severity * n)))
        end = min(n, start + width)
        y[start:end] += rng.normal(0, severity * (np.std(y) + 1e-8), size=end - start)
    return y
