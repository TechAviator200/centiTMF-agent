from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, Site
from app.db.session import get_db
from app.schemas.common import DocumentOut
from app.services.artifact_classifier import ARTIFACT_TYPES, classify_artifact_with_confidence
from app.services.document_ingestion import ingest_document
from app.services.s3 import generate_presigned_url

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


class UploadResponse(BaseModel):
    document: DocumentOut
    artifact_type: str
    detected_artifact_type: str
    confidence: str
    has_signature: Optional[bool]
    message: str


class ClassificationUpdateBody(BaseModel):
    artifact_type: str
    override_reason: Optional[str] = None


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    study_id: str = Form(...),
    site_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 50 MB)")

    # Validate site_id belongs to the study
    if site_id:
        site = await db.get(Site, site_id)
        if not site or site.study_id != study_id:
            raise HTTPException(status_code=400, detail="Invalid site_id for this study")

    doc = await ingest_document(
        db=db,
        study_id=study_id,
        site_id=site_id,
        filename=file.filename,
        content=content,
        content_type=file.content_type or "application/octet-stream",
    )

    # Recompute confidence from the stored detected type for response metadata
    _, confidence = classify_artifact_with_confidence(file.filename, doc.text_excerpt or "")

    sig_label = (
        "Signature detected"
        if doc.has_signature is True
        else "No signature detected"
        if doc.has_signature is False
        else "Signature status inconclusive"
    )

    return UploadResponse(
        document=DocumentOut.model_validate(doc),
        artifact_type=doc.artifact_type,
        detected_artifact_type=doc.detected_artifact_type or doc.artifact_type,
        confidence=confidence,
        has_signature=doc.has_signature,
        message=f"Classified as {doc.artifact_type.replace('_', ' ')}. {sig_label}.",
    )


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    study_id: Optional[str] = None,
    site_id: Optional[str] = None,
    artifact_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Document).order_by(Document.uploaded_at.desc())
    if study_id:
        query = query.where(Document.study_id == study_id)
    if site_id:
        query = query.where(Document.site_id == site_id)
    if artifact_type:
        query = query.where(Document.artifact_type == artifact_type)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.patch("/{document_id}/classification", response_model=DocumentOut)
async def update_classification(
    document_id: str,
    body: ClassificationUpdateBody,
    db: AsyncSession = Depends(get_db),
):
    """
    Manually override the AI-classified artifact type.

    Preserves `detected_artifact_type` (original AI pick) and sets
    `classification_overridden = True` for audit trail purposes.
    """
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if body.artifact_type not in ARTIFACT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid artifact_type. Valid types: {', '.join(ARTIFACT_TYPES)}",
        )

    # Store the AI-detected type before first override
    if not doc.classification_overridden and doc.detected_artifact_type is None:
        doc.detected_artifact_type = doc.artifact_type

    doc.artifact_type = body.artifact_type
    doc.classification_overridden = True
    await db.commit()
    await db.refresh(doc)
    return DocumentOut.model_validate(doc)


@router.get("/artifact-types/list")
async def list_artifact_types():
    """Return the list of recognized TMF artifact types."""
    return {"artifact_types": ARTIFACT_TYPES}


@router.get("/{document_id}/download-url")
async def get_download_url(document_id: str, db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        url = generate_presigned_url(doc.s3_key)
    except Exception:
        url = None
    return {"url": url, "s3_key": doc.s3_key, "expires_in": 3600}
