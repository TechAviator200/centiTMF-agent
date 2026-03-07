"""
centiTMF Seed Script
====================

Seeds demo data for study ABC-001 with 3 sites and representative TMF documents.
Runs the rule engine (compliance flags) and deviation intelligence automatically.

Demo story:
  Site 004 — Medium risk. Has monitoring report and IRB approval, but delegation
             log is outdated and several key docs are missing.
  Site 012 — High risk. Only has a deviation log showing major violations including
             a blinding breach. Most required documents are missing.
  Site 021 — Medium risk. Has an outdated FDA 1572 and outdated investigator CV.
             Zero enrollment so some enrollment-dependent rules don't apply.

Usage:
  python scripts/seed.py   (from /app inside Docker, or backend/ locally)
"""
import asyncio
import hashlib
import logging
import math
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Allow running from /app in Docker
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.models import (
    Base,
    ComplianceFlag,
    ComplianceRule,
    DeviationSignal,
    Document,
    DocumentEmbedding,
    Site,
    Study,
)
from app.rules.rule_engine import FactBuilder, evaluate_rule, load_rules
from app.services.artifact_classifier import classify_artifact
from app.services.deviation_intelligence import _DEVIATION_RULES, _score_text
from app.services.s3 import ensure_bucket, upload_bytes

setup_logging()
logger = logging.getLogger("centitmf.seed")

SEED_DOCS_DIR = Path(__file__).parent.parent.parent / "seed_docs"

# Documents to seed and which site they belong to (None = study-level)
SEED_FILES: list[tuple[str, str | None]] = [
    ("protocol_abc001.txt",              None),        # study-level
    ("monitoring_report_site004.txt",    "004"),
    ("irb_approval_site004.txt",         "004"),
    ("delegation_log_site004_outdated.txt", "004"),
    ("deviation_log_site012.txt",        "012"),
    ("fda_1572_site021_outdated.txt",    "021"),
    ("investigator_cv_site021.txt",      "021"),
]


# ── Schema migration ──────────────────────────────────────────────────────────

def migrate_schema(engine) -> None:
    """
    Safely add new columns to existing tables if they don't exist.
    This handles the case where Docker volumes persist an older schema.
    """
    migrations = [
        # Documents: full_text + has_signature
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS full_text TEXT",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS has_signature BOOLEAN",
        # ComplianceFlags: new fields
        "ALTER TABLE compliance_flags ADD COLUMN IF NOT EXISTS category VARCHAR",
        "ALTER TABLE compliance_flags ADD COLUMN IF NOT EXISTS severity VARCHAR",
        "ALTER TABLE compliance_flags ADD COLUMN IF NOT EXISTS risk_points INTEGER DEFAULT 5",
        "ALTER TABLE compliance_flags ADD COLUMN IF NOT EXISTS facts_snapshot JSONB",
        # Backfill severity from risk_level if null
        "UPDATE compliance_flags SET severity = risk_level WHERE severity IS NULL",
    ]
    with engine.connect() as conn:
        for stmt in migrations:
            try:
                conn.execute(text(stmt))
            except Exception as e:
                logger.debug(f"Migration skipped (likely already applied): {e}")
        conn.commit()
    logger.info("Schema migration complete.")


# ── Utilities ─────────────────────────────────────────────────────────────────

def wait_for_db(engine, retries: int = 25, delay: int = 3) -> None:
    for i in range(retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database ready.")
            return
        except Exception as e:
            logger.warning(f"DB not ready ({i + 1}/{retries}): {e}")
            time.sleep(delay)
    raise RuntimeError("Could not connect to database.")


def make_embedding(text_content: str) -> list[float]:
    """Deterministic 1536-dim unit-vector embedding for seeding."""
    seed = hashlib.sha256(text_content.encode("utf-8")).digest()
    values: list[float] = []
    i = 0
    while len(values) < 1536:
        chunk = hashlib.sha256(seed + i.to_bytes(4, "big")).digest()
        values.extend((b / 127.5) - 1.0 for b in chunk)
        i += 1
    values = values[:1536]
    mag = math.sqrt(sum(v * v for v in values))
    return [v / mag for v in values] if mag > 0 else values


def detect_signature_simple(text_lower: str) -> bool | None:
    import re
    unsigned = [r"x\s*_{5,}", r"awaiting\s+signature", r"not\s+yet\s+signed", r"unsigned"]
    signed = [r"/s/\s+\w+", r"electronically\s+signed", r"date of signature", r"/s/ "]
    for p in unsigned:
        if re.search(p, text_lower):
            return False
    for p in signed:
        if re.search(p, text_lower):
            return True
    return None


# ── Core seed function ────────────────────────────────────────────────────────

def seed() -> None:
    engine = create_engine(settings.SYNC_DATABASE_URL, echo=False)
    wait_for_db(engine)

    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    Base.metadata.create_all(engine)
    migrate_schema(engine)
    logger.info("Tables ready.")

    try:
        ensure_bucket()
        logger.info("S3 bucket ready.")
    except Exception as e:
        logger.warning(f"S3 not available (non-fatal): {e}")

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Idempotency guard
        if session.query(Study).filter_by(name="ABC-001").first():
            logger.info("Seed data already present — skipping.")
            return

        # ── Study ──────────────────────────────────────────────────────────
        study_id = str(uuid.uuid4())
        study = Study(
            id=study_id,
            name="ABC-001",
            phase="Phase II",
            sponsor="Acme Pharma Inc.",
            created_at=datetime.now(timezone.utc),
        )
        session.add(study)
        session.flush()
        logger.info(f"Study ABC-001 created ({study_id})")

        # ── Sites ──────────────────────────────────────────────────────────
        now = datetime.now(timezone.utc)
        site_004 = Site(
            id=str(uuid.uuid4()), study_id=study_id, site_code="004",
            activated_at=now - timedelta(days=90),
            irb_approved_at=now - timedelta(days=95),
            fpi_at=now - timedelta(days=60),
            enrolled_count=18,
        )
        site_012 = Site(
            id=str(uuid.uuid4()), study_id=study_id, site_code="012",
            activated_at=now - timedelta(days=75),
            irb_approved_at=now - timedelta(days=80),
            fpi_at=now - timedelta(days=45),
            enrolled_count=22,
        )
        site_021 = Site(
            id=str(uuid.uuid4()), study_id=study_id, site_code="021",
            activated_at=now - timedelta(days=70),
            irb_approved_at=now - timedelta(days=72),
            fpi_at=None,      # not yet enrolled
            enrolled_count=0,
        )
        session.add_all([site_004, site_012, site_021])
        session.flush()
        site_code_to_obj = {"004": site_004, "012": site_012, "021": site_021}
        logger.info("Sites 004, 012, 021 created.")

        # ── Load compliance rules into DB ──────────────────────────────────
        rules = load_rules()
        existing_codes = {
            r.rule_code
            for r in session.query(ComplianceRule.rule_code).all()
        }
        for rule in rules:
            if rule["rule_code"] not in existing_codes:
                session.add(ComplianceRule(
                    id=str(uuid.uuid4()),
                    rule_code=rule["rule_code"],
                    name=rule["name"],
                    description=rule.get("description"),
                    category=rule["category"],
                    severity=rule["severity"],
                    scope=rule.get("scope", "site"),
                    enabled=rule.get("enabled", True),
                    risk_points=rule.get("risk_points", 5),
                    message_template=rule["message_template"],
                    details=rule.get("details"),
                    condition_json=rule.get("condition"),
                    created_at=datetime.now(timezone.utc),
                ))
        session.flush()
        logger.info(f"Loaded {len(rules)} compliance rules.")

        # ── Ingest seed documents ──────────────────────────────────────────
        # site_id=None means study-level doc
        ingested_docs: list[Document] = []
        for filename, site_code in SEED_FILES:
            filepath = SEED_DOCS_DIR / filename
            if not filepath.exists():
                logger.warning(f"Seed doc not found: {filepath} — skipping")
                continue

            raw = filepath.read_bytes()
            full_text = raw.decode("utf-8", errors="replace")
            text_excerpt = full_text[:1000]
            artifact_type = classify_artifact(filename, full_text)
            has_signature = detect_signature_simple(full_text.lower())

            site_obj = site_code_to_obj.get(site_code) if site_code else None
            site_id = site_obj.id if site_obj else None

            doc_id = str(uuid.uuid4())
            s3_key = f"documents/{study_id}/{doc_id}/{filename}"
            try:
                upload_bytes(s3_key, raw, "text/plain")
            except Exception as e:
                logger.warning(f"S3 upload failed for {filename}: {e}")
                s3_key = f"seed/{study_id}/{filename}"

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
            session.add(doc)
            session.flush()

            emb = DocumentEmbedding(
                document_id=doc_id,
                embedding=make_embedding(full_text[:4000]),
            )
            session.add(emb)
            ingested_docs.append(doc)
            logger.info(f"Seeded: {filename} → {artifact_type} (sig={has_signature})")

        session.flush()

        # ── Compliance flags via rule engine ───────────────────────────────
        study_level_docs = [d for d in ingested_docs if d.site_id is None]
        site_docs_map: dict[str, list[Document]] = {}
        for d in ingested_docs:
            if d.site_id:
                site_docs_map.setdefault(d.site_id, []).append(d)

        for site in [site_004, site_012, site_021]:
            site_docs = site_docs_map.get(site.id, [])
            facts = FactBuilder.build(
                site=site,
                site_docs=site_docs,
                study_docs=study_level_docs,
                deviation_score=None,  # computed after
            )

            for rule in rules:
                if evaluate_rule(rule, facts):
                    session.add(ComplianceFlag(
                        id=str(uuid.uuid4()),
                        study_id=study_id,
                        site_id=site.id,
                        rule_code=rule["rule_code"],
                        category=rule.get("category"),
                        severity=rule["severity"],
                        risk_level=rule["severity"],
                        risk_points=rule.get("risk_points", 5),
                        title=rule["message_template"].format(site_code=site.site_code),
                        details=rule.get("details"),
                        facts_snapshot=facts,
                        created_at=datetime.now(timezone.utc),
                    ))

        session.flush()
        logger.info("Compliance flags generated via rule engine.")

        # ── Deviation signals ─────────────────────────────────────────────
        import re as _re
        all_docs = ingested_docs
        site_texts: dict[str, str] = {}
        study_text = " ".join(
            (d.full_text or d.text_excerpt or "")
            for d in all_docs if d.site_id is None
        )

        for site in [site_004, site_012, site_021]:
            site_specific_docs = [d for d in all_docs if d.site_id == site.id]
            site_text = " ".join(
                (d.full_text or d.text_excerpt or "") for d in site_specific_docs
            )
            combined = (site_text + "\n" + study_text).lower()
            score, findings = _score_text(combined)

            if site.enrolled_count > 0:
                has_mvr = any(
                    d.artifact_type == "Monitoring_Visit_Report"
                    for d in site_specific_docs
                )
                if not has_mvr:
                    score = min(score + 20.0, 100.0)
                    findings.insert(0, "No monitoring visit report on file for enrolled site")

            session.add(DeviationSignal(
                id=str(uuid.uuid4()),
                study_id=study_id,
                site_id=site.id,
                score=round(score, 1),
                top_findings_json={"findings": findings[:6]},
                created_at=datetime.now(timezone.utc),
            ))

        session.flush()
        logger.info("Deviation signals generated.")

        session.commit()
        logger.info("Seed complete. ABC-001 ready for demo.")

    except Exception as e:
        session.rollback()
        logger.error(f"Seed failed: {e}", exc_info=True)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed()
