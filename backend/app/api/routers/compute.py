from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.common import ComplianceFlagOut, DeviationSignalOut
from app.services.compliance_engine import compute_compliance_flags
from app.services.deviation_intelligence import compute_deviation_intel

router = APIRouter(prefix="/api/compute", tags=["compute"])


class MissingDocsResponse(BaseModel):
    study_id: str
    flags_generated: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    flags: list[ComplianceFlagOut]


class DeviationIntelResponse(BaseModel):
    study_id: str
    signals_generated: int
    signals: list[DeviationSignalOut]


@router.post("/missing-docs", response_model=MissingDocsResponse)
async def run_missing_docs(
    study_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Re-evaluate compliance rules for all sites in a study.
    Clears and regenerates all compliance flags.
    """
    try:
        flags = await compute_compliance_flags(db, study_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return MissingDocsResponse(
        study_id=study_id,
        flags_generated=len(flags),
        critical_count=sum(1 for f in flags if f.severity == "CRITICAL"),
        high_count=sum(1 for f in flags if f.severity == "HIGH"),
        medium_count=sum(1 for f in flags if f.severity == "MEDIUM"),
        low_count=sum(1 for f in flags if f.severity == "LOW"),
        flags=[ComplianceFlagOut.model_validate(f) for f in flags],
    )


@router.post("/deviation-intel", response_model=DeviationIntelResponse)
async def run_deviation_intel(
    study_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Re-run deviation intelligence analysis for all sites in a study.
    """
    try:
        signals = await compute_deviation_intel(db, study_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return DeviationIntelResponse(
        study_id=study_id,
        signals_generated=len(signals),
        signals=[DeviationSignalOut.model_validate(s) for s in signals],
    )
