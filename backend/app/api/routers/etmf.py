"""
eTMF Dashboard Router
=====================

Provides a study-level eTMF health summary across four dimensions:
  - Completeness  (expected vs present artifacts)
  - Timeliness    (overdue / stale documents)
  - Quality       (signature gaps, QC issues)
  - Risk          (inspection readiness score, top flags, high-risk sites)
  - Audit Readiness (top findings, recommended actions)

All data is derived from existing compliance flags, documents, and
simulation records — no additional storage is required.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ComplianceFlag,
    DeviationSignal,
    Document,
    InspectionSimulation,
    Site,
    Study,
)
from app.db.session import get_db

router = APIRouter(prefix="/api/etmf", tags=["etmf"])

# TMF rule codes that correspond to missing required artifacts
_MISSING_ARTIFACT_RULES = {
    "TMF-001", "TMF-002", "TMF-003", "TMF-004",
    "TMF-005", "TMF-006", "TMF-007", "TMF-008", "TMF-009",
}
_MONITORING_OVERDUE_RULE = "TMF-006"
_UNSIGNED_DOC_RULE = "TMF-010"

# How many expected required docs per activated site (excluding enrollment-gated ones)
_REQUIRED_PER_ACTIVE_SITE = 5   # TMF-001..005, 009 (FDA 1572, Delegation Log, IRB, CV, Protocol, SIV)
# Additional docs required per enrolled site
_REQUIRED_PER_ENROLLED_SITE = 3  # TMF-006..008 (MVR, SAE Follow-Up, Informed Consent)

# Docs older than 2 years from today are considered stale
_STALE_THRESHOLD_DAYS = 730


class CompletenessStats(BaseModel):
    expected_artifacts: int
    present_artifacts: int
    completeness_pct: float
    missing_critical_count: int


class TimelinessStats(BaseModel):
    overdue_monitoring_reports: int
    stale_documents: int
    late_filings_count: int


class QualityStats(BaseModel):
    unsigned_documents: int
    qc_issue_count: int


class TopFinding(BaseModel):
    rule_code: str
    title: str
    severity: str
    site_code: Optional[str]
    risk_points: int


class AuditReadiness(BaseModel):
    top_findings: list[TopFinding]
    recommended_actions: list[str]


class RiskStats(BaseModel):
    readiness_score: Optional[float]
    highest_risk_sites: list[str]
    open_critical_flags: int
    open_high_flags: int


class ETMFDashboardOut(BaseModel):
    study_id: str
    as_of: str
    completeness: CompletenessStats
    timeliness: TimelinessStats
    quality: QualityStats
    risk: RiskStats
    audit_readiness: AuditReadiness


@router.get("/studies/{study_id}/dashboard", response_model=ETMFDashboardOut)
async def get_etmf_dashboard(study_id: str, db: AsyncSession = Depends(get_db)):
    """
    Return the eTMF health dashboard for a study.

    Aggregates compliance flags, deviation signals, and documents to produce
    Completeness / Timeliness / Quality / Risk / Audit-Readiness metrics.
    """
    study = await db.get(Study, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=_STALE_THRESHOLD_DAYS)

    # ── Load raw data ─────────────────────────────────────────────────────────

    sites_result = await db.execute(select(Site).where(Site.study_id == study_id))
    sites = list(sites_result.scalars().all())

    flags_result = await db.execute(
        select(ComplianceFlag).where(ComplianceFlag.study_id == study_id)
    )
    flags = list(flags_result.scalars().all())

    docs_result = await db.execute(
        select(Document).where(Document.study_id == study_id)
    )
    docs = list(docs_result.scalars().all())

    # Latest simulation
    sim_result = await db.execute(
        select(InspectionSimulation)
        .where(InspectionSimulation.study_id == study_id)
        .order_by(InspectionSimulation.created_at.desc())
        .limit(1)
    )
    sim = sim_result.scalars().first()

    # Site lookup for flag → site_code
    site_map: dict[str, str] = {s.id: s.site_code for s in sites}

    # ── Completeness ──────────────────────────────────────────────────────────

    activated_sites = [s for s in sites if s.activated_at]
    enrolled_sites = [s for s in activated_sites if s.enrolled_count > 0]

    expected = (
        len(activated_sites) * _REQUIRED_PER_ACTIVE_SITE
        + len(enrolled_sites) * _REQUIRED_PER_ENROLLED_SITE
    )
    # Missing = flags for TMF-001..009 (one flag per missing artifact per site)
    missing_artifact_flags = [f for f in flags if f.rule_code in _MISSING_ARTIFACT_RULES]
    present = max(0, expected - len(missing_artifact_flags))
    completeness_pct = (present / expected * 100) if expected > 0 else 100.0
    missing_critical_count = sum(
        1 for f in missing_artifact_flags if f.severity in ("HIGH", "CRITICAL")
    )

    # ── Timeliness ────────────────────────────────────────────────────────────

    overdue_mvr = sum(1 for f in flags if f.rule_code == _MONITORING_OVERDUE_RULE)

    stale_docs = sum(
        1 for d in docs
        if d.doc_date and d.doc_date.replace(tzinfo=timezone.utc) < stale_cutoff
    )

    late_filings_count = overdue_mvr + stale_docs

    # ── Quality ───────────────────────────────────────────────────────────────

    unsigned_count = sum(1 for d in docs if d.has_signature is False)
    qc_issue_count = sum(1 for f in flags if f.rule_code == _UNSIGNED_DOC_RULE)

    # ── Risk ──────────────────────────────────────────────────────────────────

    open_critical = sum(1 for f in flags if f.severity == "CRITICAL")
    open_high = sum(1 for f in flags if f.severity == "HIGH")

    # Highest-risk sites: sort by (high+critical flags, then total flags)
    flag_high_per_site: dict[str, int] = {}
    flag_total_per_site: dict[str, int] = {}
    for f in flags:
        if f.site_id:
            flag_total_per_site[f.site_id] = flag_total_per_site.get(f.site_id, 0) + 1
            if f.severity in ("HIGH", "CRITICAL"):
                flag_high_per_site[f.site_id] = flag_high_per_site.get(f.site_id, 0) + 1

    sorted_sites = sorted(
        [s for s in sites if s.id in flag_total_per_site],
        key=lambda s: (flag_high_per_site.get(s.id, 0), flag_total_per_site.get(s.id, 0)),
        reverse=True,
    )
    highest_risk_sites = [s.site_code for s in sorted_sites[:3]]

    readiness_score = sim.risk_score if sim else None

    # ── Audit Readiness ───────────────────────────────────────────────────────

    top_flags = sorted(flags, key=lambda f: f.risk_points, reverse=True)[:5]
    top_findings = [
        TopFinding(
            rule_code=f.rule_code,
            title=f.title,
            severity=f.severity,
            site_code=site_map.get(f.site_id) if f.site_id else None,
            risk_points=f.risk_points,
        )
        for f in top_flags
    ]

    recommended_actions = _build_recommended_actions(flags, missing_artifact_flags, unsigned_count, sim)

    return ETMFDashboardOut(
        study_id=study_id,
        as_of=now.isoformat(),
        completeness=CompletenessStats(
            expected_artifacts=expected,
            present_artifacts=present,
            completeness_pct=round(completeness_pct, 1),
            missing_critical_count=missing_critical_count,
        ),
        timeliness=TimelinessStats(
            overdue_monitoring_reports=overdue_mvr,
            stale_documents=stale_docs,
            late_filings_count=late_filings_count,
        ),
        quality=QualityStats(
            unsigned_documents=unsigned_count,
            qc_issue_count=qc_issue_count,
        ),
        risk=RiskStats(
            readiness_score=round(readiness_score, 1) if readiness_score is not None else None,
            highest_risk_sites=highest_risk_sites,
            open_critical_flags=open_critical,
            open_high_flags=open_high,
        ),
        audit_readiness=AuditReadiness(
            top_findings=top_findings,
            recommended_actions=recommended_actions,
        ),
    )


def _build_recommended_actions(
    flags: list,
    missing_artifact_flags: list,
    unsigned_count: int,
    sim,
) -> list[str]:
    """Derive a concise, prioritized list of recommended actions from flag data."""
    actions: list[str] = []

    has_missing_regulatory = any(
        f.rule_code in {"TMF-001", "TMF-003"} for f in flags
    )
    has_missing_delegation = any(f.rule_code == "TMF-002" for f in flags)
    has_missing_mvr = any(f.rule_code == "TMF-006" for f in flags)
    has_missing_consent = any(f.rule_code == "TMF-008" for f in flags)
    has_missing_sae = any(f.rule_code == "TMF-007" for f in flags)

    if has_missing_regulatory:
        actions.append("Obtain and file missing regulatory documents (FDA 1572, IRB Approval) for all activated sites")
    if has_missing_delegation:
        actions.append("Update Delegation of Authority Logs to reflect current site personnel")
    if has_missing_consent:
        actions.append("File current IRB-approved Informed Consent Forms at all enrolled sites")
    if has_missing_sae:
        actions.append("Complete and file SAE follow-up reports for all enrolled sites")
    if has_missing_mvr:
        actions.append("Schedule and document monitoring visits for sites with enrolled patients")
    if unsigned_count > 0:
        actions.append(f"Obtain signatures on {unsigned_count} unsigned document(s) before inspection")
    if not sim:
        actions.append("Run an Inspection Simulation to generate a full readiness risk score")
    elif sim.risk_score < 60:
        actions.append("Address HIGH and CRITICAL compliance flags to improve inspection readiness score")

    if not actions:
        actions.append("No critical actions required — maintain current document filing cadence")

    return actions[:5]  # keep the list concise
