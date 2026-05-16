"""Signal processing utilities for ECG--PPG windows.

The implementations are intentionally lightweight and dependency-minimal.
For final experiments, replace peak detectors with validated domain-specific
pipelines and lock their versions in the release manifest.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from scipy import signal


@dataclass(frozen=True)
class BeatPatches:
    """Container for beat-aligned patches extracted from a single signal channel.

    Attributes:
        peaks: Sample indices of detected R-peaks or systolic onsets.
        patches: Array of shape (N, Δ) — one row per beat, Δ = min inter-beat interval.
        windows_sec: List of (start_sec, end_sec) for each patch in signal time.
    """

    peaks: np.ndarray
    patches: np.ndarray
    windows_sec: list[tuple[float, float]]


def bandpass(x: np.ndarray, fs: int, low: float = 0.5, high: float = 40.0, order: int = 3) -> np.ndarray:
    """Apply a zero-phase Butterworth bandpass filter.

    Args:
        x: 1-D signal array.
        fs: Sampling frequency in Hz.
        low: Low-cut frequency in Hz.
        high: High-cut frequency in Hz.
        order: Filter order.

    Returns:
        Filtered signal of the same length as x.
    """
    nyq = 0.5 * fs
    b, a = signal.butter(order, [low / nyq, high / nyq], btype="band")
    return signal.filtfilt(b, a, x)


def detect_ecg_rpeaks(ecg: np.ndarray, fs: int = 125) -> np.ndarray:
    """Detect R-peak sample indices using a Pan-Tompkins-inspired energy detector.

    Implements the bandpass → differentiate → square → integrate → threshold pipeline
    from Pan & Tompkins (1985). This lightweight version is sufficient for smoke tests
    and demo; replace with a validated clinical detector for production use.

    Args:
        ecg: 1-D ECG signal (expected length 3750 for 30 s at 125 Hz).
        fs: Sampling frequency in Hz (default 125).

    Returns:
        Array of R-peak sample indices (int).
    """
    x = bandpass(np.asarray(ecg, dtype=float), fs, 5.0, 20.0)
    dx = np.diff(x, prepend=x[0])
    energy = signal.convolve(dx * dx, np.ones(max(1, int(0.12 * fs))) / max(1, int(0.12 * fs)), mode="same")
    distance = int(0.30 * fs)
    height = np.percentile(energy, 75)
    peaks, _ = signal.find_peaks(energy, distance=distance, height=height)
    return peaks.astype(int)


def detect_ppg_onsets(ppg: np.ndarray, fs: int = 125) -> np.ndarray:
    """Detect PPG systolic-onset sample indices via prominent peak detection.

    Identifies the systolic upstroke peaks after bandpass filtering. Used as a
    proxy for systolic onsets as described in paper §3.1 (PhysioPatch encoder).

    Args:
        ppg: 1-D PPG signal (expected length 3750 for 30 s at 125 Hz).
        fs: Sampling frequency in Hz (default 125).

    Returns:
        Array of systolic-onset sample indices (int).
    """
    x = bandpass(np.asarray(ppg, dtype=float), fs, 0.5, 8.0)
    distance = int(0.30 * fs)
    prominence = max(1e-6, 0.2 * np.std(x))
    peaks, _ = signal.find_peaks(x, distance=distance, prominence=prominence)
    return peaks.astype(int)


def make_beat_patches(x: np.ndarray, peaks: np.ndarray, fs: int = 125) -> BeatPatches:
    """Create one beat-aligned, right-padded patch per detected beat.

    Implements the PhysioPatch patching strategy from paper §3.1: each patch
    starts at the R-peak (or systolic onset), extends Δ samples to the right,
    and is zero-padded on the right if the signal ends before Δ samples.
    Δ = min inter-beat interval, clipped to [0.35 s, 1.5 s] at 125 Hz.

    Args:
        x: 1-D signal (ECG or PPG), shape (T,).
        peaks: Sorted array of peak sample indices.
        fs: Sampling frequency in Hz (default 125).

    Returns:
        BeatPatches with patches of shape (N, Δ).
    """
    x = np.asarray(x, dtype=float)
    peaks = np.asarray(peaks, dtype=int)
    if len(peaks) < 2:
        width = int(0.8 * fs)
    else:
        # Δ = min inter-beat interval in samples, clipped to physiological range
        width = int(np.clip(np.min(np.diff(peaks)), int(0.35 * fs), int(1.5 * fs)))
    patches = []
    windows = []
    for p in peaks:
        # Beat-aligned: patch starts at the peak, extends width samples to the right
        a, b = int(p), int(p) + width
        seg = np.zeros(width, dtype=float)
        aa, bb = max(a, 0), min(b, len(x))
        if bb > aa:
            seg[: bb - aa] = x[aa:bb]
        patches.append(seg)
        windows.append((max(0.0, a / fs), min(len(x) / fs, b / fs)))
    if not patches:
        return BeatPatches(peaks=peaks, patches=np.zeros((0, width)), windows_sec=[])
    return BeatPatches(peaks=peaks, patches=np.stack(patches), windows_sec=windows)


def heart_rate_from_peaks(peaks: np.ndarray, fs: int = 125) -> float:
    """Estimate mean heart rate in bpm from detected peak sample indices.

    Args:
        peaks: Sorted array of peak sample indices.
        fs: Sampling frequency in Hz (default 125).

    Returns:
        Mean HR in bpm, or float('nan') if fewer than 2 peaks are detected.
    """
    if len(peaks) < 2:
        return float("nan")
    ibi = np.diff(peaks) / fs
    return float(60.0 / np.mean(ibi))


def rr_cv_from_peaks(peaks: np.ndarray, fs: int = 125) -> float:
    """Compute RR-interval coefficient of variation (std / mean).

    Values above 0.10 indicate irregular rhythm (used in routing and conflict detection).

    Args:
        peaks: Sorted array of peak sample indices.
        fs: Sampling frequency in Hz (default 125).

    Returns:
        RR-CV (dimensionless), or float('nan') if fewer than 3 peaks are detected.
    """
    if len(peaks) < 3:
        return float("nan")
    ibi = np.diff(peaks) / fs
    return float(np.std(ibi) / (np.mean(ibi) + 1e-8))


def spectral_lf_hf(x: np.ndarray, fs: int = 125) -> float:
    """Compute spectral LF/HF power ratio from a PPG signal (autonomic balance indicator).

    LF band: 0.04–0.15 Hz (sympathetic/parasympathetic modulation).
    HF band: 0.15–0.40 Hz (respiratory/parasympathetic modulation).
    Reported as a Patch Report field (paper §3.2).

    Args:
        x: 1-D PPG signal.
        fs: Sampling frequency in Hz (default 125).

    Returns:
        LF/HF ratio (dimensionless, non-negative).
    """
    freqs, power = signal.welch(np.asarray(x, dtype=float), fs=fs, nperseg=min(256, len(x)))
    lf = power[(freqs >= 0.04) & (freqs < 0.15)].sum()
    hf = power[(freqs >= 0.15) & (freqs < 0.40)].sum()
    return float(lf / (hf + 1e-8))


def robust_quality(x: np.ndarray) -> float:
    """Compute a heuristic signal quality index (SQI) in [0, 1].

    Combines finiteness, saturation absence, and smoothness into a scalar
    quality score. Used as a proxy for the learned SQI head in offline analysis
    and the build_patch_report pipeline.

    Args:
        x: 1-D signal array (ECG or PPG segment).

    Returns:
        SQI in [0, 1]. Returns 0.0 for empty or non-finite signals.
    """
    x = np.asarray(x, dtype=float)
    if x.size == 0 or not np.isfinite(x).all():
        return 0.0
    finite = np.isfinite(x).mean()
    saturation = np.mean(np.abs(x) > 5 * (np.std(x) + 1e-8))
    smoothness = np.mean(np.abs(np.diff(x))) / (np.std(x) + 1e-8)
    q = finite * (1.0 - np.clip(saturation, 0, 1)) * np.exp(-0.08 * smoothness)
    return float(np.clip(q, 0.0, 1.0))
