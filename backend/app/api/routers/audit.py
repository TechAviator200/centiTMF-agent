from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.audit_copilot import answer_audit_question

router = APIRouter(prefix="/api/audit", tags=["audit"])


class AuditQuestionRequest(BaseModel):
    study_id: str
    question: str


class AuditQuestionResponse(BaseModel):
    question: str
    answer: str
    data_basis: list[str]


@router.post("/questions", response_model=AuditQuestionResponse)
async def ask_audit_question(
    request: AuditQuestionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Answer a bounded audit readiness question grounded in study data.

    Supported question types:
    - Which sites are highest risk?
    - What artifacts are missing?
    - What should be fixed first?
    - What is driving the score down?
    - Tell me about Site 012
    - Give me an overall readiness assessment
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    return await answer_audit_question(db, request.study_id, request.question.strip())
