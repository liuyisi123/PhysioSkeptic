from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from physioskeptic.debate import PhysioSkepticDebate
from physioskeptic.llm_clients import MockLLMClient
from physioskeptic.patch_report import build_patch_report


def synthetic_signals(fs: int = 125, duration: int = 30) -> tuple[np.ndarray, np.ndarray]:
    t = np.arange(fs * duration) / fs
    hr_hz = 142 / 60
    # Irregular AF-like phase modulation for demo only.
    rng = np.random.default_rng(2027)
    phase_noise = np.cumsum(rng.normal(0, 0.002, size=t.size))
    ecg = 0.08 * np.sin(2 * np.pi * 1.0 * t)
    for beat in np.arange(0.4, duration, 1 / hr_hz):
        j = int((beat + rng.normal(0, 0.05)) * fs)
        if 2 <= j < len(ecg) - 3:
            ecg[j - 1:j + 2] += np.array([0.4, 1.2, 0.4])
    ppg = 0.5 * np.sin(2 * np.pi * hr_hz * t + phase_noise) + 0.05 * rng.normal(size=t.size)
    return ecg, ppg


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default="mock", choices=["mock"])
    args = parser.parse_args()
    ecg, ppg = synthetic_signals()
    report = build_patch_report("demo_0001", ecg, ppg).to_dict()
    engine = PhysioSkepticDebate(MockLLMClient(), ROOT / "prompts")
    result = engine.run(report)
    print(json.dumps({"route": result.route.value, "final": result.final, "transcript": result.transcript, "patch_report": report}, indent=2))


if __name__ == "__main__":
    main()
