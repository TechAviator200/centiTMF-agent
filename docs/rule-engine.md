# Rule Engine

## Overview

Compliance rules in centiTMF are defined as **data, not code** — in `backend/app/rules/seed_rules.json`. This keeps rules:

- **Auditable** — full change history in version control
- **Testable** — evaluate against any fact dict without a database
- **Explainable** — `facts_snapshot` is stored with every flag for traceability
- **Extensible** — add new rules without touching Python code

---

## Rule Definition Format

```json
{
  "rule_code": "TMF-001",
  "name": "FDA Form 1572 Missing",
  "description": "An active site must have a signed FDA Form 1572 on file.",
  "category": "Regulatory Documents",
  "severity": "HIGH",
  "risk_points": 10,
  "scope": "site",
  "enabled": true,
  "message_template": "FDA Form 1572 missing for Site {site_code}",
  "details": "21 CFR 312.53(c)(1) requires Form FDA 1572...",
  "condition": {
    "all": [
      {"fact": "site_activated", "op": "eq", "value": true},
      {"fact": "site_has_fda_1572", "op": "eq", "value": false}
    ]
  }
}
```

### Required Fields

| Field | Description |
|-------|-------------|
| `rule_code` | Unique identifier (e.g., `TMF-001`) |
| `name` | Human-readable name |
| `category` | Grouping label (e.g., `Regulatory Documents`) |
| `severity` | `CRITICAL` / `HIGH` / `MEDIUM` / `LOW` |
| `risk_points` | Points deducted from the 100-point readiness score |
| `scope` | `site` or `study` |
| `enabled` | `true` to activate |
| `message_template` | Title template; `{site_code}` is substituted at evaluation |
| `condition` | JSON condition tree |

---

## Fact Model

`FactBuilder.build(site, site_docs, study_docs, deviation_score)` produces:

```python
{
    # Identity
    "site_code": "004",
    "study_id": "...",
    "site_id": "...",

    # Site state
    "site_activated": True,
    "fpi_occurred": True,
    "has_enrolled_patients": True,
    "enrolled_count": 18,
    "days_since_activation": 90,

    # Site-scoped artifact presence
    # (each site must have its own copy)
    "site_has_fda_1572": False,
    "site_has_delegation_log": True,
    "site_has_irb_approval": True,
    "site_has_investigator_cv": False,
    "site_has_monitoring_visit_report": True,
    "site_has_sae_followup": False,
    "site_has_informed_consent": False,
    "site_has_siv_report": False,

    # Study-scoped (one copy covers all sites)
    "study_has_protocol": True,

    # Quality signals
    "site_has_unsigned_document": False,
    "unsigned_document_count": 0,

    # Deviation intelligence
    "deviation_score": 42.0,
    "has_high_deviation": False,
    "has_medium_deviation": True,
}
```

### Artifact Scoping

`STUDY_LEVEL_ARTIFACT_TYPES = {"Protocol"}` — the Protocol is study-scoped. One copy satisfies all sites. All other artifact types (FDA_1572, Delegation_Log, IRB_Approval, etc.) are **site-scoped**: each site needs its own copy.

This prevents false compliance when Site A's document is incorrectly credited to Sites B and C.

---

## Condition Operators

| Operator | Meaning |
|----------|---------|
| `eq` | Equal |
| `neq` | Not equal |
| `gt` / `gte` | Greater than / greater than or equal |
| `lt` / `lte` | Less than / less than or equal |
| `in` | Value is in list |
| `not_in` | Value not in list |
| `exists` | Fact is not None |
| `not_exists` | Fact is None |

Boolean groups:
- `{"all": [...]}` — ALL conditions must be true (AND)
- `{"any": [...]}` — ANY condition must be true (OR)

Conditions can be nested to arbitrary depth.

---

## Built-in Rules

| Code | Name | Severity | Risk Points |
|------|------|----------|-------------|
| TMF-001 | FDA Form 1572 Missing | HIGH | 10 |
| TMF-002 | Delegation Log Missing | HIGH | 10 |
| TMF-003 | IRB Approval Missing | HIGH | 10 |
| TMF-004 | Investigator CV Missing | MEDIUM | 5 |
| TMF-005 | Protocol Missing | CRITICAL | 20 |
| TMF-006 | Monitoring Visit Report Missing | MEDIUM | 5 |
| TMF-007 | SAE Follow-Up Missing | HIGH | 10 |
| TMF-008 | Informed Consent Missing | MEDIUM | 5 |
| TMF-009 | Site Initiation Visit Report Missing | MEDIUM | 5 |
| TMF-010 | Unsigned Regulatory Document | MEDIUM | 5 |

---

## Compliance Flag Generation

When a rule fires, a `ComplianceFlag` row is written with:

```python
ComplianceFlag(
    rule_code=rule["rule_code"],
    category=rule["category"],
    severity=rule["severity"],
    risk_level=rule["severity"],      # backward-compat alias
    risk_points=rule["risk_points"],
    title=rule["message_template"].format(site_code=site.site_code),
    facts_snapshot=facts,             # full fact dict for explainability
)
```

The `facts_snapshot` field enables audit-grade traceability — you can see exactly what the system knew about the site at the time the flag was generated.

---

## Adding a New Rule

1. Open `backend/app/rules/seed_rules.json`
2. Add a new entry to the `"rules"` array
3. Set `"enabled": true`
4. Write a test in `backend/app/tests/test_rule_engine.py`
5. Re-run the seed script or trigger a simulation to activate

No Python code changes are required for pure condition logic.

---

## Risk Scoring

Each compliance flag deducts `risk_points` from the base score of 100:

```
CRITICAL flag  →  −20 pts
HIGH flag      →  −10 pts
MEDIUM flag    →  −5  pts
LOW flag       →  −2  pts
```

Additional penalties apply for site clustering and multi-site deviation. See [architecture.md](architecture.md) for the full scoring model.
