"""
Inspection Simulation Service
==============================

Produces a 0-100 inspection readiness score for a study.

Scoring model (from product spec):
  Base score: 100 (perfect readiness)
  Deductions:
    CRITICAL flag: -20 each
    HIGH flag:     -10 each
    MEDIUM flag:   -5 each
    LOW flag:      -2 each
  Penalty modifiers:
    Site cluster (3+ flags at one site):      -10 per affected site (max 2 sites)
    Multiple high-deviation sites (2+):       -10
  Deviation contribution:
    Per site with score > 60:                 -5
  Floor: 0

Vulnerable zone classification:
  80-100: LOW RISK
  60-79:  MEDIUM RISK
  40-59:  HIGH RISK
  0-39:   CRITICAL RISK
"""
import logging
import uuid
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ComplianceFlag,
    DeviationSignal,
    InspectionSimulation,
    Site,
)
from app.services.compliance_engine import compute_compliance_flags
from app.services.deviation_intelligence import compute_deviation_intel
from app.services.llm import generate_inspection_narrative

logger = logging.getLogger("centitmf.simulation")

SEVERITY_DEDUCTIONS = {
    "CRITICAL": 20,
    "HIGH": 10,
    "MEDIUM": 5,
    "LOW": 2,
}


def _classify_zone(score: float) -> str:
    if score >= 80:
        return "LOW"
    elif score >= 60:
        return "MEDIUM"
    elif score >= 40:
        return "HIGH"
    else:
        return "CRITICAL"


def compute_risk_score(
    flags: list[ComplianceFlag],
    signals: list[DeviationSignal],
) -> tuple[float, dict]:
    """
    Compute inspection readiness score and breakdown dict.
    Returns (score, breakdown).
    """
    base = 100.0

    # Flag deductions
    flag_deduction = sum(SEVERITY_DEDUCTIONS.get(f.severity, 5) for f in flags)

    # Cluster penalty: sites with 3+ flags each get -10 (max 2 sites)
    flags_per_site: Counter = Counter(f.site_id for f in flags if f.site_id)
    cluster_sites = [sid for sid, count in flags_per_site.items() if count >= 3]
    cluster_penalty = min(len(cluster_sites), 2) * 10

    # High-deviation sites
    high_dev_sites = [s for s in signals if s.score >= 60.0]
    multi_site_dev_penalty = 10 if len(high_dev_sites) >= 2 else 0

    # Per-site deviation penalty
    per_site_dev_penalty = len(high_dev_sites) * 5

    total_deduction = (
        flag_deduction
        + cluster_penalty
        + multi_site_dev_penalty
        + per_site_dev_penalty
    )

    score = max(0.0, round(base - total_deduction, 1))

    breakdown = {
        "base_score": base,
        "flag_deduction": flag_deduction,
        "cluster_penalty": cluster_penalty,
        "multi_site_deviation_penalty": multi_site_dev_penalty,
        "per_site_deviation_penalty": per_site_dev_penalty,
        "total_deduction": total_deduction,
        "cluster_sites_count": len(cluster_sites),
        "high_deviation_sites_count": len(high_dev_sites),
    }

    return score, breakdown


async def run_inspection_simulation(
    db: AsyncSession, study_id: str
) -> InspectionSimulation:
    """
    Full inspection simulation pipeline:
    1. Re-run compliance engine (flags refreshed)
    2. Re-run deviation intelligence (signals refreshed)
    3. Compute composite readiness score
    4. Build results summary
    5. Generate narrative (LLM or deterministic)
    6. Persist and return InspectionSimulation
    """
    logger.info(f"Starting inspection simulation for study {study_id}")

    # 1 & 2: Refresh flags and deviation signals
    flags = await compute_compliance_flags(db, study_id)
    signals = await compute_deviation_intel(db, study_id)

    # 3: Score
    risk_score, breakdown = compute_risk_score(flags, signals)

    # 4: Build results payload
    site_ids = list({f.site_id for f in flags if f.site_id})
    sites_result = await db.execute(
        select(Site.id, Site.site_code).where(Site.id.in_(site_ids))
    )
    id_to_code = {row[0]: row[1] for row in sites_result.all()}

    top_flags = [
        {
            "rule_code": f.rule_code,
            "severity": f.severity,
            "risk_level": f.risk_level,
            "risk_points": f.risk_points,
            "category": f.category,
            "title": f.title,
            "site_id": f.site_id,
            "site_code": id_to_code.get(f.site_id, "Study") if f.site_id else "Study",
        }
        for f in sorted(flags, key=lambda x: SEVERITY_DEDUCTIONS.get(x.severity, 0), reverse=True)[:12]
    ]

    missing_artifacts = list({f.title for f in flags})[:12]

    high_dev_signals = sorted(
        [s for s in signals if s.score >= 40],
        key=lambda x: x.score,
        reverse=True,
    )

    # Load site codes for all signals
    all_sig_site_ids = [s.site_id for s in signals if s.site_id]
    if all_sig_site_ids:
        extra_sites_result = await db.execute(
            select(Site.id, Site.site_code).where(Site.id.in_(all_sig_site_ids))
        )
        for row in extra_sites_result.all():
            id_to_code.setdefault(row[0], row[1])

    site_deviation_scores = [
        {
            "site_id": s.site_id,
            "site_code": id_to_code.get(s.site_id, "?") if s.site_id else "?",
            "score": s.score,
            "findings": (s.top_findings_json or {}).get("findings", []),
        }
        for s in sorted(signals, key=lambda x: x.score, reverse=True)
    ]

    by_severity = Counter(f.severity for f in flags)
    results = {
        "risk_score": risk_score,
        "total_flags": len(flags),
        "critical_flags": by_severity.get("CRITICAL", 0),
        "high_flags": by_severity.get("HIGH", 0),
        "medium_flags": by_severity.get("MEDIUM", 0),
        "low_flags": by_severity.get("LOW", 0),
        "scoring_breakdown": breakdown,
        "top_flags": top_flags,
        "missing_artifacts": missing_artifacts,
        "high_deviation_sites": [
            id_to_code.get(s.site_id, s.site_id) for s in high_dev_signals[:5] if s.site_id
        ],
        "site_deviation_scores": site_deviation_scores,
    }

    # 5: Narrative
    narrative = await generate_inspection_narrative(risk_score, results)

    # 6: Persist
    sim = InspectionSimulation(
        id=str(uuid.uuid4()),
        study_id=study_id,
        risk_score=risk_score,
        vulnerable_zone=_classify_zone(risk_score),
        results_json=results,
        narrative=narrative,
        created_at=datetime.now(timezone.utc),
    )
    db.add(sim)
    await db.flush()

    logger.info(
        f"Simulation complete for study {study_id}: "
        f"score={risk_score}, zone={sim.vulnerable_zone}, "
        f"flags={len(flags)}, signals={len(signals)}"
    )
    return sim
