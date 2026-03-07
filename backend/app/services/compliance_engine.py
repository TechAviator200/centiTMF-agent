"""
Compliance Engine
=================

Evaluates data-driven rules against site fact models.

Architecture:
  1. Load rules from app/rules/seed_rules.json (+ DB for persistence)
  2. Build a fact dict per site using FactBuilder
  3. Evaluate each rule condition against the fact dict via RuleEvaluator
  4. Generate ComplianceFlag for each triggered rule
  5. Store facts_snapshot on each flag for explainability

Replaces the previous hardcoded TMF_RULES tuple approach.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ComplianceFlag, ComplianceRule, DeviationSignal, Document, Site
from app.rules.rule_engine import FactBuilder, evaluate_rule, load_rules

logger = logging.getLogger("centitmf.compliance")


async def _get_or_upsert_rules(db: AsyncSession) -> list[dict]:
    """
    Ensure rules from seed_rules.json are persisted in DB.
    Returns list of rule dicts.
    """
    rules = load_rules()
    rule_codes = [r["rule_code"] for r in rules]

    existing_result = await db.execute(
        select(ComplianceRule.rule_code).where(ComplianceRule.rule_code.in_(rule_codes))
    )
    existing_codes = {row[0] for row in existing_result.all()}

    for rule in rules:
        if rule["rule_code"] not in existing_codes:
            db_rule = ComplianceRule(
                id=str(uuid.uuid4()),
                rule_code=rule["rule_code"],
                name=rule["name"],
                description=rule.get("description"),
                category=rule["category"],
                severity=rule["severity"],
                scope=rule.get("scope", "site"),
                enabled=rule.get("enabled", True),
                risk_points=rule.get("risk_points", 5),
                message_template=rule["message_template"],
                details=rule.get("details"),
                condition_json=rule.get("condition"),
                created_at=datetime.now(timezone.utc),
            )
            db.add(db_rule)

    await db.flush()
    return rules


async def compute_compliance_flags(
    db: AsyncSession, study_id: str
) -> list[ComplianceFlag]:
    """
    Main entry point.

    For each activated site in the study:
    1. Build a fact dict from site state + documents
    2. Evaluate all enabled rules
    3. Generate flags for triggered rules

    Clears previous flags before writing new ones.
    Returns all new ComplianceFlag objects.
    """
    rules = await _get_or_upsert_rules(db)

    # Load sites
    sites_result = await db.execute(select(Site).where(Site.study_id == study_id))
    sites = sites_result.scalars().all()

    if not sites:
        logger.warning(f"No sites found for study {study_id}")
        return []

    # Load all documents for this study
    docs_result = await db.execute(
        select(Document).where(Document.study_id == study_id)
    )
    all_docs = docs_result.scalars().all()

    # Split into study-level (site_id=None) and per-site
    study_level_docs = [d for d in all_docs if d.site_id is None]
    site_docs_map: dict[str, list[Document]] = {}
    for doc in all_docs:
        if doc.site_id:
            site_docs_map.setdefault(doc.site_id, []).append(doc)

    # Load latest deviation signals per site
    dev_result = await db.execute(
        select(DeviationSignal).where(DeviationSignal.study_id == study_id)
    )
    dev_signals = dev_result.scalars().all()
    dev_score_map: dict[str, float] = {}
    for sig in dev_signals:
        if sig.site_id:
            # Keep the most recent signal per site (should already be latest)
            if sig.site_id not in dev_score_map or sig.score > dev_score_map[sig.site_id]:
                dev_score_map[sig.site_id] = sig.score

    # Clear old flags for this study
    old_flags_result = await db.execute(
        select(ComplianceFlag).where(ComplianceFlag.study_id == study_id)
    )
    for flag in old_flags_result.scalars().all():
        await db.delete(flag)
    await db.flush()

    new_flags: list[ComplianceFlag] = []

    for site in sites:
        site_docs = site_docs_map.get(site.id, [])
        deviation_score = dev_score_map.get(site.id, 0.0)

        # Build fact dict for this site
        facts = FactBuilder.build(
            site=site,
            site_docs=site_docs,
            study_docs=study_level_docs,
            deviation_score=deviation_score,
        )

        logger.debug(f"Facts for Site {site.site_code}: {facts}")

        # Evaluate each rule
        for rule in rules:
            fired = evaluate_rule(rule, facts)
            if not fired:
                continue

            title = rule["message_template"].format(
                site_code=site.site_code,
                study_id=study_id,
            )

            flag = ComplianceFlag(
                id=str(uuid.uuid4()),
                study_id=study_id,
                site_id=site.id,
                rule_code=rule["rule_code"],
                category=rule.get("category"),
                severity=rule["severity"],
                risk_level=rule["severity"],  # backward compat alias
                risk_points=rule.get("risk_points", 5),
                title=title,
                details=rule.get("details"),
                facts_snapshot=facts,
                created_at=datetime.now(timezone.utc),
            )
            db.add(flag)
            new_flags.append(flag)
            logger.info(
                f"Flag [{rule['severity']}] {rule['rule_code']} — "
                f"Site {site.site_code}: {title}"
            )

    await db.flush()
    logger.info(
        f"Compliance evaluation complete: {len(new_flags)} flags for study {study_id}"
    )
    return new_flags


# Keep backward-compatible name used by routers and simulation
compute_missing_docs = compute_compliance_flags
