from collections import Counter
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ComplianceFlag, ComplianceRule, DeviationSignal, Document, Site, Study
from app.db.session import get_db
from app.schemas.common import ComplianceFlagOut, SiteOut, SimulationOut

router = APIRouter(prefix="/api/studies", tags=["studies"])


# ── Extended schemas ──────────────────────────────────────────────────────────

class SiteRiskSummary(BaseModel):
    """Lightweight risk summary attached to each site in the study view."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    study_id: str
    site_code: str
    activated_at: Optional[datetime]
    irb_approved_at: Optional[datetime]
    fpi_at: Optional[datetime]
    enrolled_count: int
    flag_count: int = 0
    high_flag_count: int = 0
    deviation_score: Optional[float] = None


class StudyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    phase: Optional[str]
    sponsor: Optional[str]
    created_at: datetime


class StudyDetailOut(StudyOut):
    sites: list[SiteRiskSummary] = []
    flag_counts: dict[str, int] = {}
    latest_simulation: Optional[dict[str, Any]] = None


class SiteDetailOut(SiteOut):
    compliance_flags: list[ComplianceFlagOut] = []
    deviation_score: Optional[float] = None
    deviation_findings: list[str] = []


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[StudyOut])
async def list_studies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Study).order_by(Study.created_at.desc()))
    return result.scalars().all()


@router.get("/{study_id}", response_model=StudyDetailOut)
async def get_study(study_id: str, db: AsyncSession = Depends(get_db)):
    study = await db.get(Study, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    # Sites
    sites_result = await db.execute(select(Site).where(Site.study_id == study_id))
    sites = sites_result.scalars().all()

    # All flags for this study
    flags_result = await db.execute(
        select(ComplianceFlag).where(ComplianceFlag.study_id == study_id)
    )
    flags = flags_result.scalars().all()

    flags_per_site = Counter(f.site_id for f in flags if f.site_id)
    high_per_site = Counter(
        f.site_id for f in flags if f.site_id and f.severity in ("HIGH", "CRITICAL")
    )

    # Latest deviation signal per site
    dev_result = await db.execute(
        select(DeviationSignal).where(DeviationSignal.study_id == study_id)
    )
    dev_scores: dict[str, float] = {}
    for sig in dev_result.scalars().all():
        if sig.site_id:
            if sig.site_id not in dev_scores or sig.score > dev_scores[sig.site_id]:
                dev_scores[sig.site_id] = sig.score

    site_summaries = [
        SiteRiskSummary(
            id=s.id,
            study_id=s.study_id,
            site_code=s.site_code,
            activated_at=s.activated_at,
            irb_approved_at=s.irb_approved_at,
            fpi_at=s.fpi_at,
            enrolled_count=s.enrolled_count,
            flag_count=flags_per_site.get(s.id, 0),
            high_flag_count=high_per_site.get(s.id, 0),
            deviation_score=dev_scores.get(s.id),
        )
        for s in sites
    ]

    flag_counts = {
        "CRITICAL": sum(1 for f in flags if f.severity == "CRITICAL"),
        "HIGH": sum(1 for f in flags if f.severity == "HIGH"),
        "MEDIUM": sum(1 for f in flags if f.severity == "MEDIUM"),
        "LOW": sum(1 for f in flags if f.severity == "LOW"),
        "TOTAL": len(flags),
    }

    # Latest simulation (lightweight)
    from app.db.models import InspectionSimulation
    sim_result = await db.execute(
        select(InspectionSimulation)
        .where(InspectionSimulation.study_id == study_id)
        .order_by(InspectionSimulation.created_at.desc())
        .limit(1)
    )
    sim = sim_result.scalars().first()
    latest_simulation = None
    if sim:
        latest_simulation = {
            "id": sim.id,
            "risk_score": sim.risk_score,
            "vulnerable_zone": sim.vulnerable_zone,
            "created_at": sim.created_at.isoformat(),
        }

    return StudyDetailOut(
        id=study.id,
        name=study.name,
        phase=study.phase,
        sponsor=study.sponsor,
        created_at=study.created_at,
        sites=site_summaries,
        flag_counts=flag_counts,
        latest_simulation=latest_simulation,
    )


@router.get("/{study_id}/sites", response_model=list[SiteOut])
async def list_sites(study_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Site).where(Site.study_id == study_id))
    return result.scalars().all()


@router.get("/{study_id}/sites/{site_id}", response_model=SiteDetailOut)
async def get_site(study_id: str, site_id: str, db: AsyncSession = Depends(get_db)):
    site = await db.get(Site, site_id)
    if not site or site.study_id != study_id:
        raise HTTPException(status_code=404, detail="Site not found")

    flags_result = await db.execute(
        select(ComplianceFlag).where(
            ComplianceFlag.study_id == study_id,
            ComplianceFlag.site_id == site_id,
        ).order_by(ComplianceFlag.risk_points.desc())
    )
    flags = flags_result.scalars().all()

    dev_result = await db.execute(
        select(DeviationSignal)
        .where(
            DeviationSignal.study_id == study_id,
            DeviationSignal.site_id == site_id,
        )
        .order_by(DeviationSignal.created_at.desc())
        .limit(1)
    )
    dev = dev_result.scalars().first()

    return SiteDetailOut(
        id=site.id,
        study_id=site.study_id,
        site_code=site.site_code,
        activated_at=site.activated_at,
        irb_approved_at=site.irb_approved_at,
        fpi_at=site.fpi_at,
        enrolled_count=site.enrolled_count,
        compliance_flags=flags,
        deviation_score=dev.score if dev else None,
        deviation_findings=(dev.top_findings_json or {}).get("findings", []) if dev else [],
    )


@router.get("/rules/all", response_model=list[dict])
async def list_rules(db: AsyncSession = Depends(get_db)):
    """Return all compliance rules loaded in the system."""
    result = await db.execute(
        select(ComplianceRule).order_by(ComplianceRule.rule_code)
    )
    rules = result.scalars().all()
    return [
        {
            "rule_code": r.rule_code,
            "name": r.name,
            "category": r.category,
            "severity": r.severity,
            "risk_points": r.risk_points,
            "scope": r.scope,
            "enabled": r.enabled,
            "description": r.description,
        }
        for r in rules
    ]
