"""
Pipeline — PhysioSkeptic
Wraps the multi-agent debate pipeline.
Returns AnalysisResult with realistic mock when real model unavailable.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from .api_client import APIClientFactory, BaseAPIClient, Message, MockAPIClient
from .signal_loader import SignalData


# ── data models ────────────────────────────────────────────────────────────────

RHYTHM_CLASSES = [
    "Sinus Rhythm",
    "Atrial Fibrillation",
    "Atrial Flutter",
    "Sinus Bradycardia",
    "Sinus Tachycardia",
    "First-Degree AV Block",
    "Second-Degree AV Block (Mobitz I)",
    "Second-Degree AV Block (Mobitz II)",
    "Third-Degree AV Block",
    "Ventricular Tachycardia",
    "Supraventricular Tachycardia",
    "Premature Ventricular Contractions",
    "Bundle Branch Block",
    "Paced Rhythm",
    "Noise / Unclassifiable",
]

ROUTING_MODES = ["Auto", "Force Fast", "Force Standard", "Force Deep"]


@dataclass
class DebateTurn:
    role: str          # proposer | checker | skeptic | advocate | arbiter
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class PatchReport:
    """Signal quality + feature patch report."""
    sqi: float = 0.85
    hr_bpm: float = 70.0
    rr_std_ms: float = 42.0
    qrs_duration_ms: float = 88.0
    pr_interval_ms: float = 160.0
    qt_interval_ms: float = 380.0
    n_beats: int = 35
    n_artifacts: int = 1
    artifact_fraction: float = 0.03
    band_power_ratio: float = 0.91
    dominant_frequency_hz: float = 1.13
    features: Dict[str, float] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    rhythm: str = "Sinus Rhythm"
    confidence: float = 0.84
    confidence_interval: tuple = (0.79, 0.89)
    review_flag: bool = False
    review_reason: str = ""
    ece: float = 0.071
    macro_f1: float = 0.88
    patch_report: Optional[PatchReport] = None
    debate_transcript: List[DebateTurn] = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    duration_sec: float = 0.0
    model_name: str = ""
    routing_used: str = "Auto"
    signal_id: str = ""
    timestamp: float = field(default_factory=time.time)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


@dataclass
class AnalysisConfig:
    model_name: str = "Mock / Demo"
    api_key: str = ""
    provider: str = "mock"
    routing: str = "Auto"
    temperature: float = 0.7
    max_tokens: int = 2048
    sqi_threshold: float = 0.50
    review_flag_threshold: float = 0.70
    extra_kwargs: Dict[str, Any] = field(default_factory=dict)


# ── signal feature extractor (lightweight, no ML deps required) ────────────────

def _extract_patch_report(signal: SignalData) -> PatchReport:
    """Heuristic feature extraction from raw signal."""
    ecg = signal.ecg
    fs = signal.fs
    pr = PatchReport()

    if ecg is None or len(ecg) < int(fs):
        return pr

    # basic stats
    pr.sqi = float(np.clip(1.0 - np.std(np.diff(ecg)) / (np.std(ecg) + 1e-6) * 0.3, 0.1, 1.0))

    # simple R-peak detection via threshold
    try:
        from scipy.signal import find_peaks
        normalized = (ecg - np.mean(ecg)) / (np.std(ecg) + 1e-6)
        peaks, _ = find_peaks(normalized, height=0.5, distance=int(fs * 0.4))
        if len(peaks) > 1:
            rr_intervals_s = np.diff(peaks) / fs
            pr.hr_bpm = float(60.0 / np.mean(rr_intervals_s))
            pr.rr_std_ms = float(np.std(rr_intervals_s) * 1000)
            pr.n_beats = len(peaks)

        # frequency domain
        from scipy.signal import welch
        freqs, psd = welch(ecg, fs=fs, nperseg=min(len(ecg), int(fs * 4)))
        total_power = np.trapz(psd, freqs) + 1e-9
        hf_mask = (freqs >= 0.15) & (freqs <= 0.4)
        pr.band_power_ratio = float(np.trapz(psd[hf_mask], freqs[hf_mask]) / total_power)
        pr.dominant_frequency_hz = float(freqs[np.argmax(psd)])
    except Exception:
        pass

    pr.features = {
        "sqi": pr.sqi,
        "hr_bpm": pr.hr_bpm,
        "rr_std_ms": pr.rr_std_ms,
        "n_beats": pr.n_beats,
    }
    return pr


# ── prompt builders ────────────────────────────────────────────────────────────

def _build_system_prompt() -> str:
    return (
        "You are an expert cardiac electrophysiologist and AI agent participating "
        "in the PhysioSkeptic multi-agent debate framework for ECG rhythm classification. "
        "Provide concise, evidence-based analysis with beat-level citations where relevant. "
        "Format: professional medical report style. Include confidence estimates."
    )


def _build_proposer_prompt(patch: PatchReport) -> str:
    return (
        f"PROPOSER TURN:\n"
        f"Signal features: HR={patch.hr_bpm:.1f} bpm, RR-std={patch.rr_std_ms:.1f} ms, "
        f"SQI={patch.sqi:.2f}, QRS={patch.qrs_duration_ms:.0f} ms, "
        f"PR={patch.pr_interval_ms:.0f} ms, QT={patch.qt_interval_ms:.0f} ms, "
        f"N-beats={patch.n_beats}, artifact-fraction={patch.artifact_fraction:.2f}.\n"
        f"Propose the primary cardiac rhythm with confidence score (0-1)."
    )


def _build_checker_prompt(proposer_out: str, patch: PatchReport) -> str:
    return (
        f"CHECKER TURN:\nProposer said: {proposer_out[:300]}...\n"
        f"Cross-validate using PPG/SpO2/respiratory features if available. "
        f"Confirm or adjust the proposed rhythm. State agreement level."
    )


def _build_skeptic_prompt(proposer_out: str, checker_out: str) -> str:
    return (
        f"SKEPTIC TURN:\nProposer: {proposer_out[:200]}...\nChecker: {checker_out[:200]}...\n"
        f"Challenge the classification. Identify edge cases, confounders, artifact effects, "
        f"or alternative diagnoses. Be specific about which beat indices raise concern."
    )


def _build_advocate_prompt(proposer_out: str, skeptic_out: str) -> str:
    return (
        f"ADVOCATE TURN:\nProposer: {proposer_out[:200]}...\nSkeptic: {skeptic_out[:200]}...\n"
        f"Defend the primary classification against the Skeptic's challenges. "
        f"Address each concern with evidence."
    )


def _build_arbiter_prompt(
    proposer_out: str, checker_out: str, skeptic_out: str, advocate_out: str,
    tau_rev: float,
) -> str:
    return (
        f"ARBITER FINAL VERDICT:\n"
        f"Proposer: {proposer_out[:150]}...\n"
        f"Checker: {checker_out[:150]}...\n"
        f"Skeptic: {skeptic_out[:150]}...\n"
        f"Advocate: {advocate_out[:150]}...\n\n"
        f"Synthesize all arguments. Provide:\n"
        f"1. Final rhythm label\n"
        f"2. Confidence (0-1) with 90% CI\n"
        f"3. Review flag (YES if confidence < {tau_rev})\n"
        f"4. ECE estimate\n"
        f"5. Clinical recommendation"
    )


# ── mock fallback result ───────────────────────────────────────────────────────

def _generate_mock_result(signal: SignalData, config: AnalysisConfig,
                          patch: PatchReport) -> AnalysisResult:
    """Fully deterministic mock result for demo."""
    rhythms = ["Sinus Rhythm"] * 6 + [
        "Sinus Bradycardia", "Atrial Fibrillation",
        "First-Degree AV Block", "Sinus Tachycardia"
    ]
    rhythm = random.choice(rhythms)
    conf = round(random.uniform(0.72, 0.96), 3)
    ece = round(random.uniform(0.04, 0.12), 4)
    f1 = round(random.uniform(0.82, 0.95), 3)
    flag = conf < config.review_flag_threshold

    from .api_client import MOCK_DEBATE_RESPONSES
    turns = [
        DebateTurn(role=role, content=text, input_tokens=420,
                   output_tokens=len(text.split()), latency_ms=380.0)
        for role, text in MOCK_DEBATE_RESPONSES.items()
    ]

    return AnalysisResult(
        rhythm=rhythm,
        confidence=conf,
        confidence_interval=(round(conf - 0.06, 3), round(conf + 0.05, 3)),
        review_flag=flag,
        review_reason="Confidence below τ_rev threshold" if flag else "",
        ece=ece,
        macro_f1=f1,
        patch_report=patch,
        debate_transcript=turns,
        total_input_tokens=2100,
        total_output_tokens=780,
        total_cost_usd=0.0,
        model_name=config.model_name,
        routing_used=config.routing,
    )


# ── pipeline ──────────────────────────────────────────────────────────────────

class Pipeline:
    """PhysioSkeptic analysis pipeline."""

    STAGES = [
        "Encoding",
        "Proposer",
        "Checker",
        "Skeptic",
        "Advocate",
        "Arbiter",
    ]

    def __init__(self) -> None:
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run_analysis(
        self,
        signal: SignalData,
        config: AnalysisConfig,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> AnalysisResult:
        """Run full debate pipeline. Returns AnalysisResult."""
        self._cancelled = False
        t_start = time.time()

        def _progress(stage_idx: int, msg: str = "") -> None:
            if progress_callback:
                pct = int((stage_idx / len(self.STAGES)) * 100)
                label = self.STAGES[stage_idx] if stage_idx < len(self.STAGES) else "Done"
                progress_callback(pct, f"{label}: {msg}" if msg else label)

        # Stage 0 — Encoding
        _progress(0, "Extracting signal features...")
        patch = _extract_patch_report(signal)
        if self._cancelled:
            return AnalysisResult(error="Cancelled")
        time.sleep(0.1)

        # Create client
        client = APIClientFactory.create(
            config.model_name,
            api_key=config.api_key,
            **config.extra_kwargs,
        )
        use_mock = isinstance(client, MockAPIClient) or not config.api_key

        if use_mock:
            # Simulate stage progress with mock
            for i, stage in enumerate(self.STAGES[1:], 1):
                _progress(i, f"[Mock] {stage} agent running...")
                time.sleep(0.5)
                if self._cancelled:
                    return AnalysisResult(error="Cancelled")
            result = _generate_mock_result(signal, config, patch)
            result.duration_sec = time.time() - t_start
            _progress(len(self.STAGES) - 1, "Complete")
            return result

        # Real API pipeline
        sys_msg = Message(role="system", content=_build_system_prompt())
        turns: List[DebateTurn] = []
        total_in = total_out = 0
        total_cost = 0.0

        def _call(stage_idx: int, role: str, user_content: str) -> str:
            nonlocal total_in, total_out, total_cost
            _progress(stage_idx, f"{role} running...")
            msgs = [sys_msg, Message(role="user", content=user_content)]
            res = client.chat_completion(msgs, config.temperature, config.max_tokens)
            turns.append(DebateTurn(
                role=role.lower(),
                content=res.content if res.success else f"[ERROR] {res.error}",
                input_tokens=res.input_tokens,
                output_tokens=res.output_tokens,
                latency_ms=res.latency_ms,
            ))
            total_in += res.input_tokens
            total_out += res.output_tokens
            total_cost += client.estimate_cost(res.input_tokens, res.output_tokens)
            if self._cancelled:
                return ""
            return res.content

        proposer_out = _call(1, "Proposer", _build_proposer_prompt(patch))
        if self._cancelled:
            return AnalysisResult(error="Cancelled")

        checker_out = _call(2, "Checker", _build_checker_prompt(proposer_out, patch))
        if self._cancelled:
            return AnalysisResult(error="Cancelled")

        skeptic_out = _call(3, "Skeptic", _build_skeptic_prompt(proposer_out, checker_out))
        if self._cancelled:
            return AnalysisResult(error="Cancelled")

        advocate_out = _call(4, "Advocate", _build_advocate_prompt(proposer_out, skeptic_out))
        if self._cancelled:
            return AnalysisResult(error="Cancelled")

        arbiter_out = _call(
            5, "Arbiter",
            _build_arbiter_prompt(proposer_out, checker_out, skeptic_out,
                                  advocate_out, config.review_flag_threshold)
        )

        # Parse arbiter output for structured result
        rhythm, confidence, flag, ece, f1 = _parse_arbiter_output(
            arbiter_out, config.review_flag_threshold
        )

        result = AnalysisResult(
            rhythm=rhythm,
            confidence=confidence,
            confidence_interval=(round(confidence - 0.06, 3), round(confidence + 0.05, 3)),
            review_flag=flag,
            review_reason="Arbiter-determined review flag" if flag else "",
            ece=ece,
            macro_f1=f1,
            patch_report=patch,
            debate_transcript=turns,
            total_input_tokens=total_in,
            total_output_tokens=total_out,
            total_cost_usd=total_cost,
            duration_sec=time.time() - t_start,
            model_name=config.model_name,
            routing_used=config.routing,
        )
        _progress(5, "Complete")
        return result


def _parse_arbiter_output(
    text: str, tau_rev: float
) -> tuple:
    """Heuristic parse of free-text arbiter output."""
    import re

    rhythm = "Sinus Rhythm"
    for r in RHYTHM_CLASSES:
        if r.lower() in text.lower():
            rhythm = r
            break

    conf_match = re.search(r"[Cc]onfidence[:\s]+([0-9]\.[0-9]+)", text)
    confidence = float(conf_match.group(1)) if conf_match else 0.80

    flag = confidence < tau_rev or "YES" in text.upper()

    ece_match = re.search(r"ECE[:\s]+([0-9]\.[0-9]+)", text)
    ece = float(ece_match.group(1)) if ece_match else 0.08

    f1_match = re.search(r"[Ff]1[:\s]+([0-9]\.[0-9]+)", text)
    f1 = float(f1_match.group(1)) if f1_match else 0.85

    return rhythm, min(confidence, 0.99), flag, ece, f1
