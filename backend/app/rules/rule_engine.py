"""
centiTMF Rule Engine
====================

Two components:

1. FactBuilder — builds a normalized fact dict from site + document state
2. RuleEvaluator — evaluates a JSON condition tree against a fact dict

Fact model drives rule evaluation rather than raw DB joins.
This makes rules auditable, testable, and explainable.

Fact dict shape (site-scoped):
{
    "site_code": "004",
    "study_id": "...",
    "site_id": "...",
    "site_activated": True,
    "fpi_occurred": True,
    "has_enrolled_patients": True,
    "enrolled_count": 18,
    "days_since_activation": 90,

    # Artifact presence (site-scoped = only docs explicitly for this site)
    "site_has_fda_1572": False,
    "site_has_delegation_log": True,
    "site_has_irb_approval": False,
    "site_has_investigator_cv": False,
    "site_has_monitoring_visit_report": True,
    "site_has_sae_followup": False,
    "site_has_informed_consent": False,
    "site_has_siv_report": False,

    # Study-scoped artifact presence (any site, or site_id=None)
    "study_has_protocol": True,

    # Quality signals
    "site_has_unsigned_document": True,
    "deviation_score": 65.0,
    "has_high_deviation": True,
}

Condition operators: eq, neq, gt, gte, lt, lte, in, not_in, exists, not_exists
Boolean groups: all, any
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("centitmf.rule_engine")

# Artifact types that count as study-scoped (one copy covers all sites)
STUDY_LEVEL_ARTIFACT_TYPES = {"Protocol"}

# Mapping from fact key → artifact_type
ARTIFACT_FACT_MAP = {
    "site_has_fda_1572": "FDA_1572",
    "site_has_delegation_log": "Delegation_Log",
    "site_has_irb_approval": "IRB_Approval",
    "site_has_investigator_cv": "Investigator_CV",
    "site_has_monitoring_visit_report": "Monitoring_Visit_Report",
    "site_has_sae_followup": "SAE_Follow_Up",
    "site_has_informed_consent": "Informed_Consent",
    "site_has_siv_report": "Site_Activation",
}

RULES_PATH = Path(__file__).parent / "seed_rules.json"


def load_rules() -> list[dict]:
    """Load rule definitions from seed_rules.json."""
    with open(RULES_PATH) as f:
        data = json.load(f)
    return [r for r in data["rules"] if r.get("enabled", True)]


# ---------------------------------------------------------------------------
# Fact Builder
# ---------------------------------------------------------------------------

class FactBuilder:
    """
    Builds a normalized fact dict for a single site.

    Parameters:
        site — Site ORM object
        site_docs — Document objects assigned to this specific site
        study_docs — Document objects with site_id=None (study-level)
        deviation_score — float from latest DeviationSignal, or None
    """

    @staticmethod
    def build(
        site: Any,
        site_docs: list[Any],
        study_docs: list[Any],
        deviation_score: float | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)

        site_doc_types = {d.artifact_type for d in site_docs}
        study_doc_types = {d.artifact_type for d in study_docs}

        # Days calculations
        days_since_activation = None
        if site.activated_at:
            delta = now - site.activated_at
            days_since_activation = max(0, delta.days)

        facts: dict[str, Any] = {
            # Identity
            "site_code": site.site_code,
            "study_id": site.study_id,
            "site_id": site.id,

            # State
            "site_activated": site.activated_at is not None,
            "fpi_occurred": site.fpi_at is not None,
            "has_enrolled_patients": site.enrolled_count > 0,
            "enrolled_count": site.enrolled_count,
            "days_since_activation": days_since_activation,

            # Study-scoped artifacts (site_id=None covers all sites)
            "study_has_protocol": "Protocol" in study_doc_types,

            # Deviation signal
            "deviation_score": deviation_score or 0.0,
            "has_high_deviation": (deviation_score or 0.0) >= 60.0,
            "has_medium_deviation": (deviation_score or 0.0) >= 30.0,
        }

        # Site-scoped artifact presence facts
        for fact_key, artifact_type in ARTIFACT_FACT_MAP.items():
            facts[fact_key] = artifact_type in site_doc_types

        # Override with study-level protocol if present and not site-specific
        if not facts["study_has_protocol"]:
            # Also check if protocol was uploaded directly to a site (edge case)
            facts["study_has_protocol"] = "Protocol" in site_doc_types

        # Quality: unsigned document detection
        unsigned = [
            d for d in site_docs
            if d.has_signature is False
            and d.artifact_type in {
                "FDA_1572", "Delegation_Log", "IRB_Approval", "Investigator_CV"
            }
        ]
        facts["site_has_unsigned_document"] = len(unsigned) > 0
        facts["unsigned_document_count"] = len(unsigned)

        return facts


# ---------------------------------------------------------------------------
# Rule Evaluator
# ---------------------------------------------------------------------------

class RuleEvaluator:
    """
    Evaluates a JSON condition tree against a fact dict.

    Condition format:
        {"all": [...conditions...]}
        {"any": [...conditions...]}
        {"fact": "field_name", "op": "eq", "value": true}

    Supported operators:
        eq, neq, gt, gte, lt, lte, in, not_in, exists, not_exists
    """

    @classmethod
    def evaluate(cls, condition: dict, facts: dict[str, Any]) -> bool:
        if "all" in condition:
            return all(cls.evaluate(c, facts) for c in condition["all"])
        if "any" in condition:
            return any(cls.evaluate(c, facts) for c in condition["any"])

        fact_name = condition.get("fact")
        op = condition.get("op")
        expected = condition.get("value")
        actual = facts.get(fact_name)

        try:
            return cls._apply_op(op, actual, expected)
        except Exception as e:
            logger.warning(f"Rule eval error for fact={fact_name} op={op}: {e}")
            return False

    @staticmethod
    def _apply_op(op: str, actual: Any, expected: Any) -> bool:
        if op == "eq":
            return actual == expected
        if op == "neq":
            return actual != expected
        if op == "gt":
            return actual is not None and actual > expected
        if op == "gte":
            return actual is not None and actual >= expected
        if op == "lt":
            return actual is not None and actual < expected
        if op == "lte":
            return actual is not None and actual <= expected
        if op == "in":
            return actual in (expected or [])
        if op == "not_in":
            return actual not in (expected or [])
        if op == "exists":
            return actual is not None
        if op == "not_exists":
            return actual is None
        raise ValueError(f"Unknown operator: {op}")


# ---------------------------------------------------------------------------
# Convenience: evaluate a single rule dict against facts
# ---------------------------------------------------------------------------

def evaluate_rule(rule: dict, facts: dict[str, Any]) -> bool:
    """
    Returns True if the rule's condition fires (i.e., a violation was detected).
    Returns False if conditions not met or rule is disabled.
    """
    if not rule.get("enabled", True):
        return False
    condition = rule.get("condition") or {}
    if not condition:
        return False
    return RuleEvaluator.evaluate(condition, facts)
