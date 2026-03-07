"""
Tests for app.rules.rule_engine — FactBuilder and RuleEvaluator.

These are pure unit tests: no database, no network.
"""
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

import pytest

from app.rules.rule_engine import FactBuilder, RuleEvaluator, evaluate_rule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_site(
    site_code="001",
    activated_at=None,
    fpi_at=None,
    enrolled_count=0,
    irb_approved_at=None,
):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id="site-uuid-001",
        study_id="study-uuid",
        site_code=site_code,
        activated_at=activated_at or now - timedelta(days=30),
        fpi_at=fpi_at,
        enrolled_count=enrolled_count,
        irb_approved_at=irb_approved_at or now - timedelta(days=35),
    )


def _make_doc(artifact_type: str, has_signature: bool | None = True, site_id: str = "site-uuid-001"):
    return SimpleNamespace(
        id="doc-uuid",
        artifact_type=artifact_type,
        has_signature=has_signature,
        site_id=site_id,
    )


# ---------------------------------------------------------------------------
# FactBuilder tests
# ---------------------------------------------------------------------------

class TestFactBuilder:
    def test_basic_facts_for_activated_site(self):
        site = _make_site(enrolled_count=10)
        site.fpi_at = datetime.now(timezone.utc) - timedelta(days=20)
        facts = FactBuilder.build(site, [], [])

        assert facts["site_activated"] is True
        assert facts["fpi_occurred"] is True
        assert facts["has_enrolled_patients"] is True
        assert facts["enrolled_count"] == 10
        assert facts["days_since_activation"] is not None
        assert facts["days_since_activation"] >= 29

    def test_inactive_site_no_fpi(self):
        site = _make_site(enrolled_count=0)
        site.activated_at = None
        site.fpi_at = None
        facts = FactBuilder.build(site, [], [])

        assert facts["site_activated"] is False
        assert facts["fpi_occurred"] is False
        assert facts["has_enrolled_patients"] is False
        assert facts["days_since_activation"] is None

    def test_site_specific_docs_detected(self):
        site = _make_site()
        site_docs = [
            _make_doc("FDA_1572"),
            _make_doc("Delegation_Log"),
        ]
        facts = FactBuilder.build(site, site_docs, [])

        assert facts["site_has_fda_1572"] is True
        assert facts["site_has_delegation_log"] is True
        assert facts["site_has_irb_approval"] is False
        assert facts["site_has_investigator_cv"] is False

    def test_protocol_is_study_scoped(self):
        site = _make_site()
        protocol_doc = _make_doc("Protocol", site_id=None)
        protocol_doc.site_id = None

        # Site docs do NOT contain protocol; study-level docs do
        facts = FactBuilder.build(site, [], [protocol_doc])
        assert facts["study_has_protocol"] is True

    def test_protocol_not_in_site_docs_unless_study_level(self):
        site = _make_site()
        # Protocol in site docs shouldn't satisfy "study_has_protocol"
        # unless it's also picked up by the fallback logic
        facts_no_protocol = FactBuilder.build(site, [], [])
        assert facts_no_protocol["study_has_protocol"] is False

    def test_unsigned_document_detection(self):
        site = _make_site()
        site_docs = [
            _make_doc("FDA_1572", has_signature=False),  # unsigned regulatory doc
            _make_doc("Delegation_Log", has_signature=True),
        ]
        facts = FactBuilder.build(site, site_docs, [])

        assert facts["site_has_unsigned_document"] is True
        assert facts["unsigned_document_count"] == 1

    def test_all_signed_no_flag(self):
        site = _make_site()
        site_docs = [
            _make_doc("FDA_1572", has_signature=True),
            _make_doc("Delegation_Log", has_signature=True),
        ]
        facts = FactBuilder.build(site, site_docs, [])

        assert facts["site_has_unsigned_document"] is False
        assert facts["unsigned_document_count"] == 0

    def test_deviation_score_facts(self):
        site = _make_site()
        facts = FactBuilder.build(site, [], [], deviation_score=70.0)

        assert facts["deviation_score"] == 70.0
        assert facts["has_high_deviation"] is True
        assert facts["has_medium_deviation"] is True

    def test_no_deviation_score_defaults(self):
        site = _make_site()
        facts = FactBuilder.build(site, [], [], deviation_score=None)

        assert facts["deviation_score"] == 0.0
        assert facts["has_high_deviation"] is False


# ---------------------------------------------------------------------------
# RuleEvaluator tests
# ---------------------------------------------------------------------------

class TestRuleEvaluator:
    def test_eq_true(self):
        assert RuleEvaluator.evaluate({"fact": "site_activated", "op": "eq", "value": True}, {"site_activated": True})

    def test_eq_false(self):
        assert not RuleEvaluator.evaluate({"fact": "site_activated", "op": "eq", "value": True}, {"site_activated": False})

    def test_neq(self):
        assert RuleEvaluator.evaluate({"fact": "score", "op": "neq", "value": 0}, {"score": 42})

    def test_gt(self):
        assert RuleEvaluator.evaluate({"fact": "count", "op": "gt", "value": 5}, {"count": 10})
        assert not RuleEvaluator.evaluate({"fact": "count", "op": "gt", "value": 5}, {"count": 5})

    def test_gte(self):
        assert RuleEvaluator.evaluate({"fact": "count", "op": "gte", "value": 5}, {"count": 5})
        assert not RuleEvaluator.evaluate({"fact": "count", "op": "gte", "value": 5}, {"count": 4})

    def test_lt_lte(self):
        assert RuleEvaluator.evaluate({"fact": "x", "op": "lt", "value": 10}, {"x": 9})
        assert RuleEvaluator.evaluate({"fact": "x", "op": "lte", "value": 10}, {"x": 10})

    def test_in_operator(self):
        assert RuleEvaluator.evaluate({"fact": "zone", "op": "in", "value": ["HIGH", "CRITICAL"]}, {"zone": "HIGH"})
        assert not RuleEvaluator.evaluate({"fact": "zone", "op": "in", "value": ["HIGH", "CRITICAL"]}, {"zone": "LOW"})

    def test_not_in_operator(self):
        assert RuleEvaluator.evaluate({"fact": "zone", "op": "not_in", "value": ["HIGH"]}, {"zone": "LOW"})

    def test_exists_operator(self):
        assert RuleEvaluator.evaluate({"fact": "x", "op": "exists"}, {"x": 5})
        assert not RuleEvaluator.evaluate({"fact": "x", "op": "exists"}, {"x": None})

    def test_not_exists_operator(self):
        assert RuleEvaluator.evaluate({"fact": "x", "op": "not_exists"}, {"x": None})
        assert not RuleEvaluator.evaluate({"fact": "x", "op": "not_exists"}, {"x": 5})

    def test_all_group_all_true(self):
        cond = {"all": [
            {"fact": "a", "op": "eq", "value": True},
            {"fact": "b", "op": "eq", "value": True},
        ]}
        assert RuleEvaluator.evaluate(cond, {"a": True, "b": True})

    def test_all_group_partial_false(self):
        cond = {"all": [
            {"fact": "a", "op": "eq", "value": True},
            {"fact": "b", "op": "eq", "value": True},
        ]}
        assert not RuleEvaluator.evaluate(cond, {"a": True, "b": False})

    def test_any_group_one_true(self):
        cond = {"any": [
            {"fact": "a", "op": "eq", "value": True},
            {"fact": "b", "op": "eq", "value": True},
        ]}
        assert RuleEvaluator.evaluate(cond, {"a": False, "b": True})

    def test_any_group_all_false(self):
        cond = {"any": [
            {"fact": "a", "op": "eq", "value": True},
            {"fact": "b", "op": "eq", "value": True},
        ]}
        assert not RuleEvaluator.evaluate(cond, {"a": False, "b": False})

    def test_nested_condition(self):
        cond = {"all": [
            {"fact": "site_activated", "op": "eq", "value": True},
            {"any": [
                {"fact": "site_has_fda_1572", "op": "eq", "value": False},
                {"fact": "site_has_delegation_log", "op": "eq", "value": False},
            ]},
        ]}
        facts = {"site_activated": True, "site_has_fda_1572": False, "site_has_delegation_log": True}
        assert RuleEvaluator.evaluate(cond, facts)

    def test_unknown_operator_returns_false(self):
        assert not RuleEvaluator.evaluate({"fact": "x", "op": "unknown_op", "value": 1}, {"x": 1})

    def test_missing_fact_does_not_crash(self):
        # Missing fact → actual=None; eq True → False, not crashing
        assert not RuleEvaluator.evaluate({"fact": "missing", "op": "eq", "value": True}, {})


# ---------------------------------------------------------------------------
# evaluate_rule convenience wrapper
# ---------------------------------------------------------------------------

class TestEvaluateRule:
    def _rule(self, condition, enabled=True, severity="HIGH"):
        return {
            "rule_code": "TEST-001",
            "name": "Test Rule",
            "severity": severity,
            "risk_points": 10,
            "category": "Test",
            "message_template": "Test {site_code}",
            "enabled": enabled,
            "condition": condition,
        }

    def test_disabled_rule_never_fires(self):
        rule = self._rule({"fact": "site_activated", "op": "eq", "value": True}, enabled=False)
        assert not evaluate_rule(rule, {"site_activated": True})

    def test_empty_condition_never_fires(self):
        rule = self._rule({})
        assert not evaluate_rule(rule, {"site_activated": True})

    def test_tmf001_fda_1572_missing(self):
        rule = self._rule({
            "all": [
                {"fact": "site_activated", "op": "eq", "value": True},
                {"fact": "site_has_fda_1572", "op": "eq", "value": False},
            ]
        })
        # Should fire: activated, no 1572
        assert evaluate_rule(rule, {"site_activated": True, "site_has_fda_1572": False})
        # Should NOT fire: has 1572
        assert not evaluate_rule(rule, {"site_activated": True, "site_has_fda_1572": True})
        # Should NOT fire: not activated
        assert not evaluate_rule(rule, {"site_activated": False, "site_has_fda_1572": False})

    def test_load_and_evaluate_seed_rules(self):
        from app.rules.rule_engine import load_rules
        rules = load_rules()
        assert len(rules) > 0, "seed_rules.json must contain at least one rule"

        # Check each rule has required fields
        for rule in rules:
            assert "rule_code" in rule
            assert "severity" in rule
            assert "condition" in rule

        # TMF-001: activated site with no FDA 1572 should fire
        tmf001 = next(r for r in rules if r["rule_code"] == "TMF-001")
        facts = {"site_activated": True, "site_has_fda_1572": False}
        assert evaluate_rule(tmf001, facts)

        facts_ok = {"site_activated": True, "site_has_fda_1572": True}
        assert not evaluate_rule(tmf001, facts_ok)
