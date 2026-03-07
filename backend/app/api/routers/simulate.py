from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import InspectionSimulation
from app.db.session import get_db
from app.schemas.common import SimulationOut
from app.services.inspection_simulation import run_inspection_simulation

router = APIRouter(prefix="/api/simulate", tags=["simulate"])


@router.post("/inspection", response_model=SimulationOut)
async def simulate_inspection(
    study_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Run a full FDA inspection simulation for a study.
    Re-evaluates compliance rules, deviation intelligence, and
    generates a 0-100 inspection readiness score with narrative.
    """
    try:
        sim = await run_inspection_simulation(db, study_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return SimulationOut.model_validate(sim)


@router.get("/simulations", response_model=list[SimulationOut])
async def list_simulations(
    study_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(InspectionSimulation).order_by(
        InspectionSimulation.created_at.desc()
    )
    if study_id:
        query = query.where(InspectionSimulation.study_id == study_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/simulations/{simulation_id}", response_model=SimulationOut)
async def get_simulation(
    simulation_id: str, db: AsyncSession = Depends(get_db)
):
    sim = await db.get(InspectionSimulation, simulation_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return sim
