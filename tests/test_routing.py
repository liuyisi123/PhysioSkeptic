"""Unit tests for SQI-gated routing and challenge count (paper §3.3).

Tests cover:
  - route_sample: FAST/STANDARD/DEEP boundary conditions and conflict handling
  - challenge_count: Eq. (5) formula n_chal = 3 - floor(2·q̂) ∈ {1, 2, 3}
  - has_major_conflict: conflict flag extraction from Checker output
"""
import pytest

from physioskeptic.routing import (
    Route,
    RoutingConfig,
    challenge_count,
    has_major_conflict,
    route_sample,
)


# ---------------------------------------------------------------------------
# has_major_conflict
# ---------------------------------------------------------------------------


def test_no_conflict_none():
    assert has_major_conflict(None) is False


def test_no_conflict_empty():
    assert has_major_conflict({}) is False


def test_no_conflict_severity_none():
    assert has_major_conflict({"severity": "NONE"}) is False


def test_no_conflict_severity_minor():
    assert has_major_conflict({"severity": "MINOR"}) is False


def test_major_conflict():
    assert has_major_conflict({"severity": "MAJOR"}) is True


def test_major_conflict_lowercase():
    assert has_major_conflict({"severity": "major"}) is True


# ---------------------------------------------------------------------------
# route_sample: FAST routing
# ---------------------------------------------------------------------------


def test_fast_route_exact_thresholds():
    # c_0 > 0.90, q̂ > 0.80, no conflict → FAST
    assert route_sample(0.95, 0.90, {"severity": "NONE"}) == Route.FAST


def test_fast_route_no_checker():
    # checker_output=None treated as no conflict
    assert route_sample(0.95, 0.85, None) == Route.FAST


def test_fast_route_blocked_by_major_conflict():
    # c_0 and q̂ both high but MAJOR conflict → DEEP
    assert route_sample(0.92, 0.88, {"severity": "MAJOR"}) == Route.DEEP


def test_fast_route_blocked_by_low_confidence():
    # c_0 below fast_confidence threshold → not FAST
    result = route_sample(0.89, 0.85, {"severity": "NONE"})
    assert result != Route.FAST


def test_fast_route_blocked_by_low_quality():
    # q̂ below fast_quality threshold → not FAST
    result = route_sample(0.95, 0.79, {"severity": "NONE"})
    assert result != Route.FAST


# ---------------------------------------------------------------------------
# route_sample: DEEP routing
# ---------------------------------------------------------------------------


def test_deep_route_low_quality():
    # q̂ < 0.50 → DEEP regardless of c_0
    assert route_sample(0.95, 0.40, {"severity": "NONE"}) == Route.DEEP


def test_deep_route_low_confidence():
    # c_0 < 0.60 → DEEP regardless of q̂
    assert route_sample(0.55, 0.80, {"severity": "NONE"}) == Route.DEEP


def test_deep_route_major_conflict():
    # MAJOR conflict → DEEP regardless of c_0 and q̂
    assert route_sample(0.95, 0.90, {"severity": "MAJOR"}) == Route.DEEP


def test_deep_route_boundary_quality():
    # q̂ exactly at deep_quality threshold (0.50): not < 0.50, so not forced DEEP
    result = route_sample(0.80, 0.50, {"severity": "NONE"})
    assert result == Route.STANDARD


def test_deep_route_boundary_confidence():
    # c_0 exactly at deep_confidence threshold (0.60): not < 0.60, so not forced DEEP
    result = route_sample(0.60, 0.70, {"severity": "NONE"})
    assert result == Route.STANDARD


# ---------------------------------------------------------------------------
# route_sample: STANDARD routing
# ---------------------------------------------------------------------------


def test_standard_route():
    # c_0 in (0.60, 0.90], q̂ in (0.50, 0.80], no conflict → STANDARD
    assert route_sample(0.80, 0.70, {"severity": "NONE"}) == Route.STANDARD


def test_standard_route_minor_conflict():
    # MINOR conflict does not force DEEP or block STANDARD
    assert route_sample(0.80, 0.70, {"severity": "MINOR"}) == Route.STANDARD


# ---------------------------------------------------------------------------
# route_sample: custom RoutingConfig
# ---------------------------------------------------------------------------


def test_custom_config_fast():
    cfg = RoutingConfig(fast_confidence=0.80, fast_quality=0.70, deep_quality=0.40, deep_confidence=0.50)
    assert route_sample(0.85, 0.75, {"severity": "NONE"}, cfg) == Route.FAST


def test_custom_config_deep():
    cfg = RoutingConfig(fast_confidence=0.95, fast_quality=0.90, deep_quality=0.60, deep_confidence=0.70)
    assert route_sample(0.65, 0.55, {"severity": "NONE"}, cfg) == Route.DEEP


# ---------------------------------------------------------------------------
# challenge_count: Eq. (5)  n_chal = 3 - floor(2·q̂), clipped to {1, 2, 3}
# ---------------------------------------------------------------------------


def test_challenge_count_high_quality():
    # q̂ = 0.95 → 3 - floor(1.90) = 3 - 1 = 2
    assert challenge_count(0.95) == 2


def test_challenge_count_mid_quality():
    # q̂ = 0.61 → 3 - floor(1.22) = 3 - 1 = 2
    assert challenge_count(0.61) == 2


def test_challenge_count_low_quality():
    # q̂ = 0.20 → 3 - floor(0.40) = 3 - 0 = 3
    assert challenge_count(0.20) == 3


def test_challenge_count_zero():
    # q̂ = 0.00 → 3 - floor(0.00) = 3 - 0 = 3
    assert challenge_count(0.00) == 3


def test_challenge_count_one():
    # q̂ = 1.00 → 3 - floor(2.00) = 3 - 2 = 1 (minimum clamp)
    assert challenge_count(1.00) == 1


def test_challenge_count_boundary_half():
    # q̂ = 0.50 → 3 - floor(1.00) = 3 - 1 = 2
    assert challenge_count(0.50) == 2


def test_challenge_count_always_in_range():
    import numpy as np
    for q in np.linspace(0.0, 1.0, 101):
        n = challenge_count(float(q))
        assert 1 <= n <= 3, f"challenge_count({q:.2f}) = {n} out of {{1,2,3}}"
