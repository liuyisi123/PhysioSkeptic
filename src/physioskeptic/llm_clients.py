"""LLM client interfaces for the PhysioSkeptic debate pipeline.

The mock client is executable offline. Provider integration is an extension
point; the repository does not guarantee any provider's retention settings.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import json
import re
from typing import Any


class BaseLLMClient(ABC):
    """Abstract base for all LLM backends used in the debate pipeline.

    Concrete implementations must produce valid JSON output, use a fixed model
    snapshot, and log prompt template hashes and sample IDs for reproducibility.
    """

    @abstractmethod
    def complete_json(
        self,
        role: str,
        system: str,
        user: str,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a structured prompt and return the parsed JSON response.

        Args:
            role: Debate role name (e.g., "Proposer"), used for output validation.
            system: System instruction string from the role's YAML template.
            user: Formatted user message with Patch Report and role-specific context.
            schema: Optional JSON Schema dict for response validation.

        Returns:
            Parsed JSON dict conforming to the role's output_schema.

        Raises:
            NotImplementedError: Must be overridden by subclasses.
        """
        raise NotImplementedError


class MockLLMClient(BaseLLMClient):
    """Deterministic mock backend for unit tests and demos.

    Returns fixed, schema-valid JSON responses keyed on debate role and simple
    keyword heuristics. Does not call any external API.
    """

    def complete_json(
        self,
        role: str,
        system: str,
        user: str,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a deterministic mock response for the given debate role.

        Args:
            role: Debate role name.
            system: System prompt (ignored in mock mode).
            user: Formatted user message (used for simple keyword routing).
            schema: Output schema (not enforced in mock mode).

        Returns:
            Mock JSON dict matching the role's output_schema.
        """
        lower = user.lower()
        if role == "Proposer":
            if "irregular" in lower or ("p_wave_ratio" in lower and "0.31" in lower):
                rhythm = "AF_FAMILY"
                conf = 0.83
            elif "rapid" in lower:
                rhythm = "STACH"
                conf = 0.82
            else:
                rhythm = "SR"
                conf = 0.78
            return {
                "role": "Proposer",
                "rhythm": rhythm,
                "confidence": conf,
                "evidence": [
                    {
                        "report_field": "hr_ecg",
                        "value": "see report",
                        "interpretation": "rate evidence",
                    },
                    {
                        "report_field": "rr_cv",
                        "value": "see report",
                        "interpretation": "regularity evidence",
                    },
                    {
                        "report_field": "p_wave_ratio",
                        "value": "see report",
                        "interpretation": "sinus-origin evidence",
                    },
                ],
            }
        if role == "Checker":
            severity = "MAJOR" if "rr_cv" in lower and "p_wave_ratio" in lower else "NONE"
            conflicts = (
                [
                    {
                        "kind": "rhythm_morphology",
                        "cited_fields": ["rr_cv", "p_wave_ratio"],
                        "rationale": "irregular intervals with weak sinus support",
                    }
                ]
                if severity == "MAJOR"
                else []
            )
            return {"role": "Checker", "severity": severity, "conflicts": conflicts}
        if role == "Skeptic":
            match = re.search(r"n_chal:\s*([123])\b", user)
            n = int(match.group(1)) if match else 1
            return {
                "role": "Skeptic",
                "challenges": [
                    {
                        "target_evidence_index": i,
                        "strength": "strong",
                        "cited_report_fields": [
                            "low_confidence_beats",
                            "q_hat",
                            "rr_cv",
                            "p_wave_ratio",
                        ],
                        "alternative_interpretation": "AF_FAMILY may better explain irregularity and weak P-wave support.",
                    }
                    for i in range(n)
                ],
            }
        if role == "Advocate":
            return {
                "role": "Advocate",
                "revised_confidence": 0.61,
                "retained_claims": ["rapid ventricular rate"],
                "conceded_claims": ["sinus-origin claim"],
                "responses": ["Concede sinus origin due to low P-wave support."],
            }
        if role == "Arbiter":
            rhythm = "AF_FAMILY" if "conceded" in lower or "irregular" in lower else "SR"
            conf = 0.61 if rhythm == "AF_FAMILY" else 0.78
            return {
                "role": "Arbiter",
                "rhythm": rhythm,
                "confidence": conf,
                "review_recommended": conf < 0.70,
                "uncertainty": "cross_modal" if conf < 0.70 else "none",
                "reasoning_summary": (
                    "Decision is grounded in Patch Report quality, RR variability, and P-wave support."
                ),
            }
        return json.loads("{}")


class OpenAICompatibleClient(BaseLLMClient):
    """Extension interface for an explicitly configured provider integration."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    def complete_json(
        self,
        role: str,
        system: str,
        user: str,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Raise until an authorized provider SDK integration is implemented."""
        raise NotImplementedError(
            "Implement a provider client with an explicit model revision and decoding settings. "
            "Use MockLLMClient for the offline examples."
        )
