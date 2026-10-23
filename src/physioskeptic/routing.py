"""SQI-gated adaptive routing for the PhysioSkeptic debate pipeline.

Implements the three-tier routing policy below:
  FAST:     c_0 > 0.90 AND q̂ > 0.80 AND conflict = ∅
  DEEP:     q̂ < 0.50  OR  c_0 < 0.60  OR  conflict = MAJOR
  STANDARD: all other cases

Skeptic challenge count:
  n_chal = 3 - floor(2·q̂),  clipped to {1, 2, 3}

Review flag: c_final < τ_rev = 0.70
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any


class Route(str, Enum):
    """Debate routing tier."""

    FAST = "FAST"
    STANDARD = "STANDARD"
    DEEP = "DEEP"


@dataclass(frozen=True)
class RoutingConfig:
    """Thresholds for the SQI-gated routing policy.

    Attributes:
        fast_confidence: Minimum Proposer confidence c_0 for FAST routing (0.90).
        fast_quality: Minimum SQI q̂ for FAST routing (0.80).
        deep_quality: SQI q̂ below which DEEP routing is forced (0.50).
        deep_confidence: Proposer confidence c_0 below which DEEP routing is forced (0.60).
    """

    fast_confidence: float = 0.90
    fast_quality: float = 0.80
    deep_quality: float = 0.50
    deep_confidence: float = 0.60

    def __post_init__(self) -> None:
        thresholds = (
            self.fast_confidence,
            self.fast_quality,
            self.deep_quality,
            self.deep_confidence,
        )
        if not all(math.isfinite(x) and 0 <= x <= 1 for x in thresholds):
            raise ValueError("Routing thresholds must be finite values in [0, 1]")
        if self.deep_confidence > self.fast_confidence or self.deep_quality > self.fast_quality:
            raise ValueError("Deep thresholds cannot exceed the corresponding Fast thresholds")


def has_major_conflict(checker_output: dict[str, Any] | None) -> bool:
    """Return True if the Checker reported a MAJOR cross-modal conflict.

    Args:
        checker_output: JSON dict from the Checker role, or None for FAST-path bypass.

    Returns:
        True when checker_output["severity"] == "MAJOR" (case-insensitive).
    """
    if not checker_output:
        return False
    return str(checker_output.get("severity", "NONE")).upper() == "MAJOR"


def route_sample(
    c0: float,
    q_hat: float,
    checker_output: dict[str, Any] | None = None,
    cfg: RoutingConfig = RoutingConfig(),
) -> Route:
    """Determine the debate routing tier for a single sample.

    Priority order:
      1. FAST  if c_0 > fast_confidence AND q̂ > fast_quality AND conflict = ∅
      2. DEEP  if q̂ < deep_quality OR c_0 < deep_confidence OR conflict = MAJOR
      3. STANDARD otherwise

    Args:
        c0: Initial Proposer confidence in [0, 1].
        q_hat: Encoder SQI estimate q̂ ∈ [0, 1] from the Patch Report.
        checker_output: Checker JSON output dict, or None (treated as no conflict).
        cfg: Routing threshold configuration.

    Returns:
        Route enum value: FAST, STANDARD, or DEEP.
    """
    if not all(math.isfinite(x) and 0 <= x <= 1 for x in (c0, q_hat)):
        raise ValueError("Confidence and quality must be finite values in [0, 1]")
    conflict = has_major_conflict(checker_output)
    if c0 > cfg.fast_confidence and q_hat > cfg.fast_quality and not conflict:
        return Route.FAST
    if q_hat < cfg.deep_quality or c0 < cfg.deep_confidence or conflict:
        return Route.DEEP
    return Route.STANDARD


def challenge_count(q_hat: float) -> int:
    """Compute Skeptic challenge count n_chal from SQI estimate.

    Formula: n_chal = 3 - floor(2·q̂),  clipped to {1, 2, 3}.

    Examples:
        q̂ = 0.95 → 3 - floor(1.90) = 3 - 1 = 2
        q̂ = 0.61 → 3 - floor(1.22) = 3 - 1 = 2
        q̂ = 0.20 → 3 - floor(0.40) = 3 - 0 = 3
        q̂ = 0.00 → 3 - floor(0.00) = 3 - 0 = 3
        q̂ = 1.00 → 3 - floor(2.00) = 3 - 2 = 1

    Args:
        q_hat: SQI estimate q̂ ∈ [0, 1].

    Returns:
        Integer challenge count in {1, 2, 3}.
    """
    if not math.isfinite(q_hat) or not 0 <= q_hat <= 1:
        raise ValueError("Quality must be a finite value in [0, 1]")
    return int(max(1, min(3, 3 - math.floor(2 * q_hat))))
