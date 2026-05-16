"""Skepticism-aware student distillation skeleton (paper §3.4).

Distills the five-role GPT-5.2 teacher into a compact student model
(Llama-3.2-1B-Instruct + PhysioPatch encoder) via LoRA rank-16 on all
attention projections.

Loss function (paper §3.4):
  L_distill = α·CE(y, ŷ_T) + β·KL(p̃_T ∥ p̃_S) + δ1·MSE(c_T, c_S) + δ2·KL(A*_low ∥ A_S)

Coefficients (paper §3.4):
  α = 1.0  (cross-entropy on hard teacher labels)
  β = 0.5  (KL on soft teacher distribution p̃)
  δ1 = 0.3 (MSE on beat-level confidence vector)
  δ2 = 0.2 (KL on low-quality attention map)

Training settings:
  20 epochs, batch size 64, lr = 2e-4, LoRA rank 16 on all attention projections.

Teacher JSONL fields expected:
  sample_id, soft_distribution, calibrated_confidence, low_quality_attention, uncertainty_type
"""
from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the distillation entry point."""
    p = argparse.ArgumentParser(
        description="Skepticism-aware student distillation (paper §3.4). "
                    "Connects teacher JSONL annotations to the LoRA-finetuning loop."
    )
    p.add_argument(
        "--teacher-jsonl",
        required=True,
        help="Path to teacher annotation JSONL. Each line must contain: "
             "sample_id, soft_distribution, calibrated_confidence, "
             "low_quality_attention, uncertainty_type.",
    )
    p.add_argument(
        "--outdir",
        required=True,
        help="Output directory for student checkpoint and training logs.",
    )
    return p.parse_args()


def main() -> None:
    """Entry point for student distillation.

    Creates the output directory and writes a configuration stub documenting
    the expected teacher JSONL format and paper loss coefficients.
    Connect your credentialed dataset loader and LoRA training loop before
    running full distillation.

    Loss coefficients (paper §3.4):
      (α, β, δ1, δ2) = (1.0, 0.5, 0.3, 0.2)
    """
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "README.txt").write_text(
        "Student distillation skeleton (PhysioSkeptic paper §3.4).\n\n"
        "Model: Llama-3.2-1B-Instruct + PhysioPatch encoder, LoRA rank 16 on all attention projections.\n\n"
        "Loss: α·CE(y, ŷ_T) + β·KL(p̃_T∥p̃_S) + δ1·MSE(c_T, c_S) + δ2·KL(A*_low∥A_S)\n"
        "Coefficients: (α, β, δ1, δ2) = (1.0, 0.5, 0.3, 0.2)\n\n"
        "Training: 20 epochs, batch 64, lr=2e-4.\n\n"
        "Expected teacher JSONL fields per line:\n"
        "  sample_id           — window identifier\n"
        "  soft_distribution   — dict mapping class name → teacher probability\n"
        "  calibrated_confidence — scalar Arbiter confidence (c_final)\n"
        "  low_quality_attention — list of per-beat attention weights A*_low\n"
        "  uncertainty_type    — one of: signal_quality, cross_modal, ambiguous, none\n"
    )
    print(f"Prepared student distillation directory at {outdir}")


if __name__ == "__main__":
    main()
