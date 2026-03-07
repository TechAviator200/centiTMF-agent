"""
Document Ingestion Pipeline
============================

Steps:
1. Extract full text from PDF/TXT
2. Classify artifact type from filename + text
3. Detect likely signature presence (heuristic)
4. Upload raw file to S3/MinIO
5. Persist document metadata (including full_text and has_signature)
6. Generate and store vector embedding
"""
import io
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, DocumentEmbedding
from app.services.artifact_classifier import classify_artifact
from app.services.embeddings import embed_text
from app.services.s3 import upload_bytes

logger = logging.getLogger("centitmf.ingestion")

# Heuristic patterns indicating a signature is present in the document
_SIGNATURE_PATTERNS = [
    r"/s/\s+\w+",           # "/s/ John Smith" (electronic sig)
    r"signature\s*:",       # "Signature:"
    r"signed\s+by\s*:",     # "Signed by:"
    r"electronically\s+signed",
    r"\bsigned\b.{0,30}\bdate\b",
    r"__+\s*\n.*signature",  # underline followed by "signature"
    r"x\s*_{3,}",           # X _____ (blank sig line - absent)
]

_UNSIGNED_INDICATORS = [
    r"signature\s+required",
    r"not\s+yet\s+signed",
    r"awaiting\s+signature",
    r"unsigned",
    r"\[\s*signature\s*\]",
    r"x\s*_{5,}",           # long blank line = empty sig field
]


def extract_text(filename: str, content: bytes) -> str:
    """Extract plain text from PDF or TXT bytes."""
    if filename.lower().endswith(".pdf"):
        try:
            import pypdf

            reader = pypdf.PdfReader(io.BytesIO(content))
            pages = []
            for page in reader.pages[:30]:
                extracted = page.extract_text()
                if extracted:
                    pages.append(extracted)
            return "\n".join(pages)
        except Exception as e:
            logger.warning(f"PDF extraction failed for '{filename}': {e}")
            return content.decode("utf-8", errors="replace")
    else:
        return content.decode("utf-8", errors="replace")


def detect_signature(text: str) -> Optional[bool]:
    """
    Heuristic signature detection.
    Returns:
        True  — signature indicators found
        False — explicit unsigned indicators found
        None  — inconclusive
    """
    text_lower = text.lower()

    for pattern in _UNSIGNED_INDICATORS:
        if re.search(pattern, text_lower):
            return False

    for pattern in _SIGNATURE_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True

    return None


async def ingest_document(
    db: AsyncSession,
    study_id: str,
    site_id: Optional[str],
    filename: str,
    content: bytes,
    content_type: str = "application/octet-stream",
) -> Document:
    """Full ingestion pipeline. Returns persisted Document."""

    # 1. Extract full text
    full_text = extract_text(filename, content)
    text_excerpt = full_text[:1000]

    # 2. Classify artifact
    artifact_type = classify_artifact(filename, full_text)
    logger.info(f"Classified '{filename}' as {artifact_type}")

    # 3. Signature detection
    has_signature = detect_signature(full_text)

    # 4. Upload to S3
    doc_id = str(uuid.uuid4())
    s3_key = f"documents/{study_id}/{doc_id}/{filename}"
    try:
        upload_bytes(s3_key, content, content_type)
        logger.info(f"Uploaded to S3: {s3_key}")
    except Exception as e:
        logger.warning(f"S3 upload failed (non-fatal): {e}")
        s3_key = f"local/{study_id}/{doc_id}/{filename}"

    # 5. Persist document record
    doc = Document(
        id=doc_id,
        study_id=study_id,
        site_id=site_id,
        artifact_type=artifact_type,
        filename=filename,
        s3_key=s3_key,
        uploaded_at=datetime.now(timezone.utc),
        text_excerpt=text_excerpt,
        full_text=full_text,
        has_signature=has_signature,
    )
    db.add(doc)
    await db.flush()

    # 6. Generate and store embedding
    embedding_text = full_text[:6000] if full_text else filename
    embedding_vector = await embed_text(embedding_text)
    emb = DocumentEmbedding(
        document_id=doc_id,
        embedding=embedding_vector,
    )
    db.add(emb)
    await db.flush()

    logger.info(
        f"Ingested document {doc_id}: type={artifact_type}, "
        f"signed={has_signature}, chars={len(full_text)}"
    )
    return doc
