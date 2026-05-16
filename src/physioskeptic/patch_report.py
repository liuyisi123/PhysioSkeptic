"""Deterministic Patch Report generation for PhysioSkeptic.

The Patch Report is a structured JSON summary (paper §3.2) that routes signal
quality and beat-level evidence to the five-role LLM debate without transmitting
raw waveforms.  Fields:
  - q̂ ∈ [0, 1]                 — scalar SQI for FAST/DEEP routing
  - c ∈ [0, 1]^N               — per-beat confidence vector
  - low-confidence beats        — (index, time window, attention weight) for beats where c_i < 0.40
  - ECG P-wave detection ratio  — sinus-origin proxy
  - LF/HF ratio                 — spectral autonomic indicator from PPG
  - cross-modal consistency     — HR difference, rhythm-morphology conflict flag
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

import numpy as np
from jsonschema import validate

from .signal_processing import (
    detect_ecg_rpeaks,
    detect_ppg_onsets,
    heart_rate_from_peaks,
    make_beat_patches,
    robust_quality,
    rr_cv_from_peaks,
    spectral_lf_hf,
)


@dataclass
class LowConfidenceBeat:
    """A single beat with confidence below the low-confidence threshold (c_i < 0.40).

    Attributes:
        beat_index: Zero-based index into the per-beat confidence vector.
        time_window_sec: (start_sec, end_sec) of the patch in signal time.
        confidence: Beat-level confidence c_i ∈ [0, 1].
        attention: Attention weight assigned by the encoder (1 - c_i proxy).
    """

    beat_index: int
    time_window_sec: tuple[float, float]
    confidence: float
    attention: float = 0.0


@dataclass
class PatchReport:
    """Full Patch Report (paper §3.2) for a single 30-second ECG/PPG window.

    Attributes:
        sample_id: Unique identifier for this window.
        fs: Sampling frequency in Hz (125 Hz per paper).
        duration_sec: Signal duration in seconds (30 s per paper).
        q_hat: Scalar SQI estimate q̂ ∈ [0, 1] used for routing.
        beat_confidences: Per-beat confidence vector c ∈ [0, 1]^N.
        hr_ecg: Heart rate estimated from ECG R-peaks (bpm).
        hr_ppg: Heart rate estimated from PPG systolic onsets (bpm).
        rr_cv: RR-interval coefficient of variation (dimensionless).
        p_wave_ratio: Fraction of beats with detectable P-wave energy (sinus proxy).
        lf_hf: PPG spectral LF/HF ratio (autonomic balance indicator).
        low_confidence_beats: Beats where c_i < 0.40 (index, window, attention).
        cross_signal_consistency: Dict with hr_diff_bpm, rhythm_morphology_conflict,
            confidence_quality_mismatch flags.
        patch_descriptors: Natural-language qualitative cues for LLM prompts.
    """

    sample_id: str
    fs: int
    duration_sec: float
    q_hat: float
    beat_confidences: list[float]
    hr_ecg: float
    hr_ppg: float
    rr_cv: float
    p_wave_ratio: float
    lf_hf: float
    low_confidence_beats: list[LowConfidenceBeat]
    cross_signal_consistency: dict[str, Any]
    patch_descriptors: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict (validates against patch_report.schema.json)."""
        d = asdict(self)
        d["low_confidence_beats"] = [asdict(b) for b in self.low_confidence_beats]
        return d

    def to_json(self) -> str:
        """Serialize to a formatted JSON string."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


def estimate_p_wave_ratio(ecg_patches: np.ndarray) -> float:
    """Estimate the fraction of beats with detectable P-wave energy.

    Computes a sinus-origin proxy based on pre-QRS energy in each beat patch.
    The manuscript uses ECG-derived P-wave detection; this heuristic provides a
    stable, dependency-free approximation for the public release.

    A beat is counted as having P-wave support when its pre-QRS standard deviation
    exceeds 10% of the beat's overall standard deviation.

    Args:
        ecg_patches: Beat patch array of shape (N, L).

    Returns:
        Fraction of beats with P-wave support, in [0, 1].
    """
    if ecg_patches.size == 0:
        return 0.0
    n = ecg_patches.shape[1]
    pre = ecg_patches[:, max(0, n // 2 - n // 5): max(1, n // 2 - n // 12)]
    whole = ecg_patches
    ratio = np.mean(np.std(pre, axis=1) > 0.10 * (np.std(whole, axis=1) + 1e-8))
    return float(np.clip(ratio, 0.0, 1.0))


def build_patch_report(sample_id: str, ecg: np.ndarray, ppg: np.ndarray, fs: int = 125) -> PatchReport:
    """Build a Patch Report from a 30-second ECG/PPG window (paper §3.2).

    Processing pipeline:
      1. R-peak detection (Pan-Tompkins) and PPG systolic-onset detection.
      2. Beat-aligned, right-padded patches (Δ = min inter-beat interval).
      3. Per-beat confidence c_i = 0.5·q̂ + 0.5·SQI(patch_i), clipped to [0, 1].
      4. Low-confidence beats: c_i < 0.40 (reported with beat index, window, attention).
      5. Cross-modal consistency: HR difference, rhythm-morphology conflict.
         Conflict flag is True when rr_cv > 0.10 (irregular) AND p_wave_ratio < 0.85
         (weak sinus support) — indicating irregular rhythm without clear AF/sinus origin.

    Args:
        sample_id: Unique window identifier string.
        ecg: 1-D ECG array, length fs*30 = 3750 at 125 Hz.
        ppg: 1-D PPG array, length fs*30 = 3750 at 125 Hz.
        fs: Sampling frequency in Hz (default 125).

    Returns:
        PatchReport dataclass instance.
    """
    duration = len(ecg) / fs
    rpeaks = detect_ecg_rpeaks(ecg, fs)
    ppg_peaks = detect_ppg_onsets(ppg, fs)
    ecg_bp = make_beat_patches(ecg, rpeaks, fs)
    q_ecg = robust_quality(ecg)
    q_ppg = robust_quality(ppg)
    q_hat = float(np.mean([q_ecg, q_ppg]))
    hr_ecg = heart_rate_from_peaks(rpeaks, fs)
    hr_ppg = heart_rate_from_peaks(ppg_peaks, fs)
    rr_cv = rr_cv_from_peaks(rpeaks, fs)
    if not np.isfinite(rr_cv):
        rr_cv = rr_cv_from_peaks(ppg_peaks, fs)
    p_wave = estimate_p_wave_ratio(ecg_bp.patches)
    lf_hf = spectral_lf_hf(ppg, fs)

    # Per-beat confidence vector c ∈ [0, 1]^N  (paper §3.2)
    beat_conf: list[float] = []
    for seg in ecg_bp.patches:
        conf = float(np.clip(0.5 * q_hat + 0.5 * robust_quality(seg), 0.0, 1.0))
        beat_conf.append(conf)

    # Low-confidence beats: c_i < 0.40 with attention weight = 1 - c_i
    low: list[LowConfidenceBeat] = []
    for i, conf in enumerate(beat_conf):
        if conf < 0.40:
            low.append(
                LowConfidenceBeat(
                    beat_index=i,
                    time_window_sec=ecg_bp.windows_sec[i],
                    confidence=conf,
                    attention=float(1.0 - conf),
                )
            )

    hr_diff = abs(hr_ppg - hr_ecg) if np.isfinite(hr_ppg) and np.isfinite(hr_ecg) else float("nan")

    # Rhythm-morphology conflict: irregular RR intervals (rr_cv > 0.10) combined
    # with weak P-wave support (p_wave_ratio < 0.85) — ambiguous sinus/AF boundary.
    rhythm_morphology_conflict = bool((rr_cv > 0.10) and (p_wave < 0.85))

    consistency: dict[str, Any] = {
        "hr_diff_bpm": hr_diff,
        "rhythm_morphology_conflict": rhythm_morphology_conflict,
        "confidence_quality_mismatch": bool(
            np.mean(beat_conf) > 0.80 and q_hat < 0.50
        ) if beat_conf else False,
    }

    descriptors: list[str] = []
    if np.isfinite(hr_ecg) and hr_ecg > 100:
        descriptors.append("rapid ventricular rate")
    if np.isfinite(hr_ecg) and hr_ecg < 60:
        descriptors.append("slow ventricular rate")
    if rr_cv > 0.10:
        descriptors.append("irregular intervals")
    if p_wave < 0.85:
        descriptors.append("limited P-wave support")
    if q_hat < 0.50:
        descriptors.append("low signal quality")

    return PatchReport(
        sample_id=sample_id,
        fs=fs,
        duration_sec=duration,
        q_hat=q_hat,
        beat_confidences=beat_conf,
        hr_ecg=hr_ecg,
        hr_ppg=hr_ppg,
        rr_cv=float(rr_cv),
        p_wave_ratio=p_wave,
        lf_hf=lf_hf,
        low_confidence_beats=low,
        cross_signal_consistency=consistency,
        patch_descriptors=descriptors,
    )


def validate_patch_report(report: dict[str, Any], schema_path: str | Path) -> None:
    """Validate a patch report dict against the JSON schema.

    Args:
        report: Dict produced by PatchReport.to_dict().
        schema_path: Path to patch_report.schema.json.

    Raises:
        jsonschema.ValidationError: If the report does not conform to the schema.
    """
    schema = json.loads(Path(schema_path).read_text())
    validate(instance=report, schema=schema)
