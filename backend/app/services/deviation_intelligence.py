"""
Protocol Deviation Intelligence Service
========================================

Analyzes cross-document patterns in protocol, monitoring reports, and deviation logs.
Generates per-site deviation scores and human-readable findings.

Uses full_text (when available) for accurate keyword analysis.
Falls back to text_excerpt if full_text is not populated.
"""
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DeviationSignal, Document, Site

logger = logging.getLogger("centitmf.deviation")

# (regex_pattern, risk_points, human_readable_finding_label)
_DEVIATION_RULES = [
    (r"major deviation|critical deviation",            20, "Critical/major deviations documented"),
    (r"protocol violation",                            20, "Protocol violations detected"),
    (r"blinding.{0,15}breach",                        20, "Blinding integrity breach"),
    (r"eligib.{0,20}criteria.{0,20}not met",          18, "Eligibility criteria violations"),
    (r"unreported.{0,15}adverse|sae.{0,15}not.{0,15}report", 15, "Unreported or late SAE reporting"),
    (r"gdp.{0,10}failure|data.{0,15}integrity",       12, "GDP/data integrity concerns"),
    (r"unauthorized.{0,15}procedure",                 12, "Unauthorized procedures performed"),
    (r"dose.{0,12}miss|dosing.{0,12}window",          10, "Dosing window non-compliance"),
    (r"window.{0,20}exceed|visit.{0,15}window",        8, "Visit/assessment window violations"),
    (r"protocol deviation|minor deviation",            7,  "Protocol deviations logged"),
    (r"missed.{0,15}assessment|missed.{0,15}visit",    6,  "Missed assessments or visits"),
    (r"incorrect.{0,15}dosing",                        6,  "Incorrect dosing documented"),
    (r"consent.{0,15}issue|consent.{0,15}irregulari", 6,  "Informed consent irregularities"),
    (r"incomplete.{0,15}source|source.{0,15}data",     5,  "Incomplete source data"),
    (r"late.{0,10}filing|documentation.{0,10}error",   4,  "Documentation or filing delays"),
    (r"corrective.{0,15}action|capa",                  3,  "CAPA or corrective actions open"),
    (r"query.{0,10}open",                              2,  "Open queries"),
]

_RELEVANT_ARTIFACT_TYPES = {
    "Monitoring_Visit_Report",
    "Deviation_Log",
    "Protocol",
    "SAE_Follow_Up",
}


def _get_text(doc: Document) -> str:
    return doc.full_text or doc.text_excerpt or ""


def _score_text(text: str) -> tuple[float, list[str]]:
    """
    Score deviation risk from combined document text.
    Returns (score 0-100, deduplicated findings list sorted by severity).
    """
    text_lower = text.lower()
    score = 0.0
    findings: list[str] = []

    for pattern, points, label in _DEVIATION_RULES:
        matches = re.findall(pattern, text_lower)
        if matches:
            # Diminishing returns for repeated matches
            contribution = points * (1 + 0.4 * (len(matches) - 1))
            score += contribution
            if label not in findings:
                findings.append(label)

    return min(round(score, 1), 100.0), findings


async def compute_deviation_intel(
    db: AsyncSession, study_id: str
) -> list[DeviationSignal]:
    """
    Analyze documents and compute deviation scores per site.
    Clears previous signals and writes fresh ones.
    """
    sites_result = await db.execute(select(Site).where(Site.study_id == study_id))
    sites = sites_result.scalars().all()

    if not sites:
        return []

    docs_result = await db.execute(
        select(Document).where(
            Document.study_id == study_id,
            Document.artifact_type.in_(_RELEVANT_ARTIFACT_TYPES),
        )
    )
    docs = docs_result.scalars().all()

    # Group docs by site_id (None = study-level)
    site_docs: dict[Optional[str], list[Document]] = {}
    for doc in docs:
        site_docs.setdefault(doc.site_id, []).append(doc)

    # Clear old signals
    old_result = await db.execute(
        select(DeviationSignal).where(DeviationSignal.study_id == study_id)
    )
    for sig in old_result.scalars().all():
        await db.delete(sig)
    await db.flush()

    new_signals: list[DeviationSignal] = []

    for site in sites:
        site_specific = site_docs.get(site.id, [])
        study_level = site_docs.get(None, [])
        all_relevant = site_specific + study_level

        combined = "\n\n".join(_get_text(d) for d in all_relevant)
        score, findings = _score_text(combined)

        # Penalty: enrolled site with no monitoring visit report on file
        if site.enrolled_count > 0:
            has_mvr = any(
                d.artifact_type == "Monitoring_Visit_Report" for d in site_specific
            )
            if not has_mvr:
                score = min(score + 20.0, 100.0)
                findings.insert(0, "No monitoring visit report on file for enrolled site")

        signal = DeviationSignal(
            id=str(uuid.uuid4()),
            study_id=study_id,
            site_id=site.id,
            score=score,
            top_findings_json={"findings": findings[:6]},
            created_at=datetime.now(timezone.utc),
        )
        db.add(signal)
        new_signals.append(signal)
        logger.info(f"Deviation score Site {site.site_code}: {score:.1f}")

    await db.flush()
    return new_signals
