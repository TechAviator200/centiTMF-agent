"""Shared Pydantic v2 schemas used across multiple routers."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class SiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    study_id: str
    site_code: str
    activated_at: Optional[datetime]
    irb_approved_at: Optional[datetime]
    fpi_at: Optional[datetime]
    enrolled_count: int


class ComplianceFlagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    study_id: str
    site_id: Optional[str]
    rule_code: str
    category: Optional[str]
    severity: str
    risk_level: str
    risk_points: int
    title: str
    details: Optional[str]
    created_at: datetime


class DeviationSignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    study_id: str
    site_id: Optional[str]
    score: float
    top_findings_json: Optional[dict[str, Any]]
    created_at: datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    study_id: str
    site_id: Optional[str]
    artifact_type: str
    filename: str
    s3_key: str
    uploaded_at: datetime
    doc_date: Optional[datetime]
    text_excerpt: Optional[str]
    has_signature: Optional[bool]


class SimulationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    study_id: str
    risk_score: float
    vulnerable_zone: Optional[str]
    results_json: Optional[dict[str, Any]]
    narrative: Optional[str]
    created_at: datetime


class ComplianceRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rule_code: str
    name: str
    description: Optional[str]
    category: str
    severity: str
    scope: str
    enabled: bool
    risk_points: int
    message_template: str
    details: Optional[str]
