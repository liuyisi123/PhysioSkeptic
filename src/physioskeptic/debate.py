"""Five-role PhysioSkeptic debate orchestration (paper §3.3).

Role sequence and routing logic:
  FAST path:     Proposer → Checker → Arbiter
  STANDARD path: Proposer → Checker → Skeptic → Arbiter
  DEEP path:     Proposer → Checker → Skeptic → Advocate → Arbiter

Routing is determined by the Checker output and q̂ from the Patch Report:
  FAST     if c_0 > 0.90 AND q̂ > 0.80 AND conflict = ∅
  DEEP     if q̂ < 0.50  OR  c_0 < 0.60  OR  conflict = MAJOR
  STANDARD otherwise

Skeptic challenge count: n_chal = 3 - floor(2·q̂) ∈ {1, 2, 3}  (Eq. 5)
Review flag: c_final < τ_rev = 0.70

All inter-role messages are structured JSON validated against role output schemas.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import yaml

from .llm_clients import BaseLLMClient
from .routing import Route, challenge_count, route_sample


@dataclass
class DebateResult:
    """Result of one complete PhysioSkeptic debate session.

    Attributes:
        route: The routing tier used (FAST, STANDARD, or DEEP).
        transcript: Ordered list of role JSON outputs (append-only debate log).
        final: Arbiter's final JSON output (rhythm, confidence, review_recommended).
    """

    route: Route
    transcript: list[dict[str, Any]]
    final: dict[str, Any]


def load_prompt(path: str | Path) -> dict[str, Any]:
    """Load a role prompt template from a YAML file.

    Args:
        path: Path to a YAML prompt file (e.g., prompts/proposer.yaml).

    Returns:
        Dict with keys: role, system, user_template, output_schema.
    """
    return yaml.safe_load(Path(path).read_text())


class PhysioSkepticDebate:
    """Orchestrator for the five-role PhysioSkeptic debate pipeline (paper §3.3).

    Loads all role prompt templates at construction, then runs the full
    debate sequence for each sample according to the SQI-gated routing policy.

    Args:
        llm: LLM backend implementing BaseLLMClient.complete_json().
        prompt_dir: Directory containing role YAML files (proposer, checker,
                    skeptic, advocate, arbiter).
        review_threshold: Arbiter confidence threshold below which expert review
                          is recommended (τ_rev = 0.70, paper §3.3).
    """

    def __init__(
        self,
        llm: BaseLLMClient,
        prompt_dir: str | Path,
        review_threshold: float = 0.70,
    ) -> None:
        self.llm = llm
        self.prompt_dir = Path(prompt_dir)
        self.review_threshold = review_threshold
        self.prompts = {p.stem: load_prompt(p) for p in self.prompt_dir.glob("*.yaml")}

    def _call(self, name: str, **kwargs: Any) -> dict[str, Any]:
        """Invoke one role by name, formatting its user template with kwargs.

        Args:
            name: Role stem matching the YAML filename (e.g., "proposer").
            **kwargs: Template variables for user_template.format(**kwargs).

        Returns:
            Parsed JSON response dict from the LLM backend.
        """
        tpl = self.prompts[name]
        user = tpl["user_template"].format(**kwargs)
        return self.llm.complete_json(tpl["role"], tpl["system"], user, tpl.get("output_schema"))

    def run(
        self,
        patch_report: dict[str, Any],
        classes: list[str] | None = None,
    ) -> DebateResult:
        """Run the full five-role debate for one Patch Report (paper §3.3).

        Args:
            patch_report: Validated Patch Report dict (from PatchReport.to_dict()).
            classes: Rhythm class list. Defaults to [SR, STACH, SBRAD, AF_FAMILY, PACE].

        Returns:
            DebateResult with routing tier, full transcript, and Arbiter final output.
        """
        classes = classes or ["SR", "STACH", "SBRAD", "AF_FAMILY", "PACE"]
        report_str = json.dumps(patch_report, ensure_ascii=False, indent=2)
        transcript: list[dict[str, Any]] = []

        # Step 1: Proposer generates initial rhythm hypothesis
        proposer = self._call("proposer", classes=classes, patch_report=report_str)
        transcript.append(proposer)

        # Step 2: Checker audits cross-modal consistency; routing is decided here
        checker = self._call("checker", proposer_output=json.dumps(proposer), patch_report=report_str)
        depth = route_sample(float(proposer["confidence"]), float(patch_report["q_hat"]), checker)

        # FAST path: skip Skeptic and Advocate, go directly to Arbiter
        if depth == Route.FAST:
            final = self._call(
                "arbiter",
                review_threshold=self.review_threshold,
                transcript=json.dumps(transcript),
                patch_report=report_str,
            )
            transcript.append(final)
            return DebateResult(depth, transcript, final)

        # STANDARD and DEEP: Skeptic issues n_chal targeted challenges (Eq. 5)
        transcript.append(checker)
        n_chal = challenge_count(float(patch_report["q_hat"]))
        skeptic = self._call(
            "skeptic",
            n_chal=n_chal,
            proposer_output=json.dumps(proposer),
            checker_output=json.dumps(checker),
            patch_report=report_str,
        )
        transcript.append(skeptic)

        # DEEP only: Advocate responds to each Skeptic challenge
        if depth == Route.DEEP:
            advocate = self._call(
                "advocate",
                proposer_output=json.dumps(proposer),
                skeptic_output=json.dumps(skeptic),
                patch_report=report_str,
            )
            transcript.append(advocate)

        # Arbiter resolves rhythm, calibrates confidence, flags review if c_final < τ_rev
        final = self._call(
            "arbiter",
            review_threshold=self.review_threshold,
            transcript=json.dumps(transcript),
            patch_report=report_str,
        )
        transcript.append(final)
        return DebateResult(depth, transcript, final)
