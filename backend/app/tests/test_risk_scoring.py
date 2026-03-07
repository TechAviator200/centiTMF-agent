"""
Tests for app.services.inspection_simulation — compute_risk_score and _classify_zone.

Pure unit tests — no database, no async.
"""
from types import SimpleNamespace

import pytest

from app.services.inspection_simulation import _classify_zone, compute_risk_score


# ---------------------------------------------------------------------------
# Helpers — lightweight stand-ins for ORM objects
# ---------------------------------------------------------------------------

def _flag(severity: str, site_id: str | None = "site-001"):
    return SimpleNamespace(severity=severity, site_id=site_id)


def _signal(score: float, site_id: str | None = "site-001"):
    return SimpleNamespace(score=score, site_id=site_id)


# ---------------------------------------------------------------------------
# Zone classification
# ---------------------------------------------------------------------------

class TestClassifyZone:
    def test_low_risk(self):
        assert _classify_zone(100) == "LOW"
        assert _classify_zone(80) == "LOW"

    def test_medium_risk(self):
        assert _classify_zone(79) == "MEDIUM"
        assert _classify_zone(60) == "MEDIUM"

    def test_high_risk(self):
        assert _classify_zone(59) == "HIGH"
        assert _classify_zone(40) == "HIGH"

    def test_critical_risk(self):
        assert _classify_zone(39) == "CRITICAL"
        assert _classify_zone(0) == "CRITICAL"


# ---------------------------------------------------------------------------
# Score computation
# ---------------------------------------------------------------------------

class TestComputeRiskScore:
    def test_no_flags_no_signals_perfect_score(self):
        score, breakdown = compute_risk_score([], [])
        assert score == 100.0
        assert breakdown["flag_deduction"] == 0
        assert breakdown["cluster_penalty"] == 0

    def test_single_high_flag(self):
        flags = [_flag("HIGH")]
        score, breakdown = compute_risk_score(flags, [])
        assert score == 90.0
        assert breakdown["flag_deduction"] == 10

    def test_single_critical_flag(self):
        flags = [_flag("CRITICAL")]
        score, breakdown = compute_risk_score(flags, [])
        assert score == 80.0
        assert breakdown["flag_deduction"] == 20

    def test_medium_and_low_flags(self):
        flags = [_flag("MEDIUM"), _flag("LOW")]
        score, breakdown = compute_risk_score(flags, [])
        # -5 (MEDIUM) -2 (LOW) = -7
        assert score == 93.0
        assert breakdown["flag_deduction"] == 7

    def test_multiple_severities_combined(self):
        flags = [
            _flag("CRITICAL"),  # -20
            _flag("HIGH"),      # -10
            _flag("MEDIUM"),    # -5
            _flag("LOW"),       # -2
        ]
        score, breakdown = compute_risk_score(flags, [])
        assert score == 63.0
        assert breakdown["flag_deduction"] == 37

    def test_cluster_penalty_single_site_3_flags(self):
        flags = [_flag("HIGH", "site-001")] * 3
        score, breakdown = compute_risk_score(flags, [])
        # Flag deduction: 3 * 10 = 30; cluster: 1 site * 10 = 10
        assert breakdown["cluster_penalty"] == 10
        assert score == 60.0

    def test_cluster_penalty_capped_at_two_sites(self):
        # 3 flags on site-A, 3 flags on site-B, 3 flags on site-C
        flags = (
            [_flag("MEDIUM", "site-A")] * 3 +
            [_flag("MEDIUM", "site-B")] * 3 +
            [_flag("MEDIUM", "site-C")] * 3
        )
        score, breakdown = compute_risk_score(flags, [])
        # Cluster hits 3 sites, but capped at 2 → 20 penalty
        assert breakdown["cluster_penalty"] == 20

    def test_no_cluster_penalty_under_threshold(self):
        flags = [_flag("HIGH", "site-001")] * 2  # only 2 flags, not 3
        score, breakdown = compute_risk_score(flags, [])
        assert breakdown["cluster_penalty"] == 0

    def test_high_deviation_single_site(self):
        signals = [_signal(70.0)]
        score, breakdown = compute_risk_score([], signals)
        # 1 high-dev site: per-site -5; no multi-site penalty (<2)
        assert breakdown["per_site_deviation_penalty"] == 5
        assert breakdown["multi_site_deviation_penalty"] == 0
        assert score == 95.0

    def test_high_deviation_two_sites_triggers_multi_penalty(self):
        signals = [_signal(65.0, "site-A"), _signal(75.0, "site-B")]
        score, breakdown = compute_risk_score([], signals)
        # multi-site: -10; per-site: 2 * -5 = -10
        assert breakdown["multi_site_deviation_penalty"] == 10
        assert breakdown["per_site_deviation_penalty"] == 10
        assert score == 80.0

    def test_low_deviation_no_penalty(self):
        signals = [_signal(30.0), _signal(50.0)]  # both below 60.0 threshold
        score, breakdown = compute_risk_score([], signals)
        assert breakdown["per_site_deviation_penalty"] == 0
        assert breakdown["multi_site_deviation_penalty"] == 0
        assert score == 100.0

    def test_score_floored_at_zero(self):
        # Enough flags to drive score negative
        flags = [_flag("CRITICAL")] * 10  # -200 deduction
        score, _ = compute_risk_score(flags, [])
        assert score == 0.0

    def test_breakdown_total_deduction_matches(self):
        flags = [_flag("HIGH"), _flag("MEDIUM")]
        signals = [_signal(70.0)]
        score, breakdown = compute_risk_score(flags, signals)
        expected_total = (
            breakdown["flag_deduction"] +
            breakdown["cluster_penalty"] +
            breakdown["multi_site_deviation_penalty"] +
            breakdown["per_site_deviation_penalty"]
        )
        assert breakdown["total_deduction"] == expected_total
        assert score == max(0.0, round(100.0 - expected_total, 1))

    def test_study_level_flags_no_site_id(self):
        # Flags with site_id=None shouldn't count toward cluster
        flags = [_flag("HIGH", None)] * 5
        score, breakdown = compute_risk_score(flags, [])
        assert breakdown["cluster_penalty"] == 0  # None site_id excluded from cluster
        assert score == 50.0  # 5 * -10 = -50
