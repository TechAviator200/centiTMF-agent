from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


class Study(Base):
    __tablename__ = "studies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    phase: Mapped[Optional[str]] = mapped_column(String)
    sponsor: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sites: Mapped[list[Site]] = relationship(
        "Site", back_populates="study", cascade="all, delete-orphan"
    )
    documents: Mapped[list[Document]] = relationship(
        "Document", back_populates="study", cascade="all, delete-orphan"
    )
    compliance_flags: Mapped[list[ComplianceFlag]] = relationship(
        "ComplianceFlag", back_populates="study", cascade="all, delete-orphan"
    )
    deviation_signals: Mapped[list[DeviationSignal]] = relationship(
        "DeviationSignal", back_populates="study", cascade="all, delete-orphan"
    )
    inspection_simulations: Mapped[list[InspectionSimulation]] = relationship(
        "InspectionSimulation", back_populates="study", cascade="all, delete-orphan"
    )


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    study_id: Mapped[str] = mapped_column(
        String, ForeignKey("studies.id", ondelete="CASCADE"), nullable=False
    )
    site_code: Mapped[str] = mapped_column(String, nullable=False)
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    irb_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    fpi_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    enrolled_count: Mapped[int] = mapped_column(Integer, default=0)

    study: Mapped[Study] = relationship("Study", back_populates="sites")
    documents: Mapped[list[Document]] = relationship("Document", back_populates="site")
    compliance_flags: Mapped[list[ComplianceFlag]] = relationship(
        "ComplianceFlag", back_populates="site"
    )
    deviation_signals: Mapped[list[DeviationSignal]] = relationship(
        "DeviationSignal", back_populates="site"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    study_id: Mapped[str] = mapped_column(
        String, ForeignKey("studies.id", ondelete="CASCADE"), nullable=False
    )
    site_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("sites.id", ondelete="SET NULL")
    )
    artifact_type: Mapped[str] = mapped_column(String, nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    s3_key: Mapped[str] = mapped_column(String, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    doc_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # Short excerpt for quick display
    text_excerpt: Mapped[Optional[str]] = mapped_column(Text)
    # Full extracted text — used by rule engine and deviation analysis
    full_text: Mapped[Optional[str]] = mapped_column(Text)
    # Heuristic signature detection result
    has_signature: Mapped[Optional[bool]] = mapped_column(Boolean)
    # Classification: AI-detected type (preserved even after manual override)
    detected_artifact_type: Mapped[Optional[str]] = mapped_column(String)
    # Set to True when a user manually overrides the AI classification
    classification_overridden: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    study: Mapped[Study] = relationship("Study", back_populates="documents")
    site: Mapped[Optional[Site]] = relationship("Site", back_populates="documents")
    embedding: Mapped[Optional[DocumentEmbedding]] = relationship(
        "DocumentEmbedding",
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan",
    )


class DocumentEmbedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(1536))

    document: Mapped[Document] = relationship("Document", back_populates="embedding")


class ComplianceRule(Base):
    """
    Persisted rule definitions loaded from app/rules/seed_rules.json.
    Stored in DB so they are queryable via API and auditable.
    """
    __tablename__ = "compliance_rules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    rule_code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String, nullable=False)
    # CRITICAL | HIGH | MEDIUM | LOW
    severity: Mapped[str] = mapped_column(String, nullable=False)
    # site | study
    scope: Mapped[str] = mapped_column(String, nullable=False, default="site")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # Risk points deducted from 100-point readiness score when rule fires
    risk_points: Mapped[int] = mapped_column(Integer, default=5)
    message_template: Mapped[str] = mapped_column(String, nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text)
    # JSON condition tree evaluated against site fact dict
    condition_json: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ComplianceFlag(Base):
    __tablename__ = "compliance_flags"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    study_id: Mapped[str] = mapped_column(
        String, ForeignKey("studies.id", ondelete="CASCADE"), nullable=False
    )
    site_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("sites.id", ondelete="CASCADE")
    )
    rule_code: Mapped[str] = mapped_column(String, nullable=False)
    # Denormalized from rule for zero-join display
    category: Mapped[Optional[str]] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    # risk_level kept as alias for backward compatibility with frontend
    risk_level: Mapped[str] = mapped_column(String, nullable=False)
    risk_points: Mapped[int] = mapped_column(Integer, default=5)
    title: Mapped[str] = mapped_column(String, nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text)
    # Snapshot of the fact dict that caused this rule to fire (explainability)
    facts_snapshot: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    study: Mapped[Study] = relationship("Study", back_populates="compliance_flags")
    site: Mapped[Optional[Site]] = relationship("Site", back_populates="compliance_flags")


class DeviationSignal(Base):
    __tablename__ = "deviation_signals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    study_id: Mapped[str] = mapped_column(
        String, ForeignKey("studies.id", ondelete="CASCADE"), nullable=False
    )
    site_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("sites.id", ondelete="CASCADE")
    )
    score: Mapped[float] = mapped_column(Float, default=0.0)
    top_findings_json: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    study: Mapped[Study] = relationship("Study", back_populates="deviation_signals")
    site: Mapped[Optional[Site]] = relationship("Site", back_populates="deviation_signals")


class InspectionSimulation(Base):
    __tablename__ = "inspection_simulations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    study_id: Mapped[str] = mapped_column(
        String, ForeignKey("studies.id", ondelete="CASCADE"), nullable=False
    )
    # 0 = critical failure, 100 = fully inspection ready
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    vulnerable_zone: Mapped[Optional[str]] = mapped_column(String)
    results_json: Mapped[Optional[dict]] = mapped_column(JSON)
    narrative: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    study: Mapped[Study] = relationship("Study", back_populates="inspection_simulations")
