"""
centiTMF Seed Script
====================

Seeds demo data for study ABC-001 with 3 sites and representative TMF documents.

This script is:
  - Idempotent: safe to run on every deploy
  - Restorative: repairs partial production state (upserts study/sites/docs)
  - Complete: always recomputes flags, deviation signals, and ensures a simulation exists

Seed document content is embedded directly as Python strings so this script
works in any environment (Render, Docker, local) without filesystem path dependencies.

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
import hashlib
import logging
import math
import sys
import time
import uuid
from collections import Counter
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
    InspectionSimulation,
    Site,
    Study,
)
from app.rules.rule_engine import FactBuilder, evaluate_rule, load_rules
from app.services.artifact_classifier import classify_artifact
from app.services.deviation_intelligence import _score_text
from app.services.inspection_simulation import compute_risk_score, _classify_zone
from app.services.llm import _deterministic_narrative
from app.services.s3 import ensure_bucket, upload_bytes

setup_logging()
logger = logging.getLogger("centitmf.seed")

# ---------------------------------------------------------------------------
# Embedded seed document content
# Inlined so the script is self-contained in any Docker/cloud environment.
# ---------------------------------------------------------------------------

_PROTOCOL = """\
CLINICAL TRIAL PROTOCOL
Study Title: A Phase II, Randomized, Double-Blind Study of XYZ-101 in Adult Patients
Protocol Number: ABC-001
Version: 2.1
Date: 2023-11-15
Sponsor: Acme Pharma Inc.

1. PROTOCOL SYNOPSIS
This study protocol describes a randomized, double-blind, placebo-controlled study
evaluating the efficacy and safety of XYZ-101 in adult patients aged 18-75.

2. STUDY OBJECTIVES
Primary: Assess reduction in primary endpoint at 12 weeks.
Secondary: Assess safety, tolerability, and pharmacokinetics.

3. STUDY DESIGN
Phase II, multicenter, randomized, double-blind, parallel-group study.
Target enrollment: 120 patients across 3 sites.

4. ELIGIBILITY CRITERIA
Inclusion:
- Age 18-75 years
- Confirmed diagnosis per protocol section 5.2
- Signed informed consent

Exclusion:
- Pregnant or breastfeeding
- Prior treatment with XYZ-101
- Significant renal impairment (eGFR < 30)

5. DOSING REGIMEN
XYZ-101: 50 mg oral, twice daily for 12 weeks
Placebo: matching tablet, twice daily for 12 weeks

CRITICAL: Dosing window defined as +/-2 hours from scheduled time.
Doses missed beyond this window constitute a protocol deviation.

6. PROTOCOL AMENDMENT HISTORY
Version 1.0: Initial protocol
Version 2.0: Amended eligibility criteria (section 4)
Version 2.1: Clarified dosing window; updated SAE reporting timelines

7. SITES
Site 004 - General Hospital (Activated 2023-12-01, First Patient In: 2024-01-10)
Site 012 - Research Center (Activated 2024-01-15, First Patient In: 2024-02-01)
Site 021 - University Clinic (Activated 2024-01-20, Pending first enrollment)

8. MONITORING
Per protocol monitoring plan. Minimum 2 monitoring visits per site per year.
Initial monitoring visit within 30 days of first patient enrollment.
"""

_MONITORING_REPORT_004 = """\
MONITORING VISIT REPORT
Study: ABC-001
Site: 004 - General Hospital
Visit Type: Routine Monitoring Visit
Visit Date: 2024-03-15
Monitor: J. Smith, CRA

SITE PERSONNEL PRESENT
Principal Investigator: Dr. A. Johnson
Study Coordinator: M. Lee

VISIT SUMMARY
This was the second routine monitoring visit for Site 004. Site has enrolled 18 patients
as of visit date. All source data verification (SDV) completed for 15 patients.

FINDINGS

1. Protocol Deviations
   - 2 patients with documented dosing window exceedance (>2 hours)
   - 1 patient: visit window exceeded by 4 days for Week 8 assessment
   These constitute minor protocol deviations and have been logged.

2. Informed Consent
   - All patients have current version 2.1 ICF on file.
   - No consent issues identified.

3. Documentation
   - Source documents complete and legible for verified patients.
   - Query open: Patient 004-007 Week 4 assessment vitals not transcribed.

4. Drug Accountability
   - Reconciliation complete. No discrepancies.

5. Regulatory Documents
   - FDA Form 1572 on file - NOTE: Current PI signature dated 2022-04-01.
     Form 1572 requires update to reflect protocol amendment v2.1.
   - Delegation log: OUTDATED - does not include sub-investigator added in Jan 2024.
     Corrective action required.

RISK ASSESSMENT
Overall site risk: MEDIUM
Deviation rate: 2/18 enrolled = 11%

FOLLOW-UP ACTIONS
1. Site to update FDA Form 1572 for protocol amendment v2.1 (deadline: 30 days)
2. Site to update delegation log to include new sub-investigator (deadline: 14 days)
3. Site to resolve open query for Patient 004-007 (deadline: 7 days)

Next monitoring visit scheduled: 2024-06-15
"""

_IRB_APPROVAL_004 = """\
INSTITUTIONAL REVIEW BOARD APPROVAL LETTER

IRB Name: General Hospital Institutional Review Board
IRB Registration: FWA00012345
IRB Protocol Number: GH-IRB-2023-ABC001

Date of Approval: 2023-11-20
Site: 004 - General Hospital

STUDY INFORMATION
Study Title: A Phase II, Randomized, Double-Blind Study of XYZ-101 in Adult Patients
Protocol Number: ABC-001
Version: 2.0
Sponsor: Acme Pharma Inc.
Principal Investigator: Dr. A. Johnson, MD

APPROVAL STATEMENT
The General Hospital Institutional Review Board has reviewed and approved
the above referenced research study. This approval is granted for the
protocol version referenced above.

This approval is valid for one year from the date of this letter.
Continuing review is required to maintain approval.

NOTE: Protocol Version 2.1 was issued November 2023.
This IRB approval references Version 2.0.
Updated IRB approval for protocol version 2.1 has been requested
but has not yet been received as of the date of this document.

EXPIRATION: This approval expires 2024-11-20.

REQUIRED ACTIONS:
- Obtain IRB approval for Protocol Version 2.1
- Submit annual continuing review 90 days prior to expiration

Signed: IRB Chair Dr. Patricia Nguyen
Date of Signature: 2023-11-20
/s/ Dr. Patricia Nguyen, IRB Chair
"""

_DELEGATION_LOG_004 = """\
DELEGATION OF AUTHORITY LOG
Study: ABC-001
Site: 004 - General Hospital
Principal Investigator: Dr. A. Johnson, MD
Date Prepared: 2023-12-01

PURPOSE
This Delegation of Authority Log documents which study personnel have been
authorized by the Principal Investigator to perform specific study-related
tasks at Site 004.

DELEGATED PERSONNEL

Name: M. Lee, RN
Role: Study Coordinator
Delegated Tasks:
  - Patient scheduling and visit coordination
  - Source document collection
  - AE/SAE data entry
  - Query resolution
Signature: /s/ M. Lee
Date: 2023-12-01

Name: Dr. B. Chen, MD
Role: Sub-Investigator
Delegated Tasks:
  - Patient informed consent process
  - Study drug administration oversight
  - Safety assessments
Signature: /s/ Dr. B. Chen
Date: 2023-12-01

INVESTIGATOR SIGNATURE
I authorize the above individuals to perform the specified study tasks.
/s/ Dr. A. Johnson, MD
Date: 2023-12-01

--- IMPORTANT NOTE ---
This delegation log was prepared at site initiation in December 2023.
Sub-Investigator Dr. C. Williams joined the study team in January 2024.
Dr. C. Williams is NOT listed on this delegation log.
The delegation log requires update to include Dr. C. Williams.

Per monitoring visit report dated 2024-03-15:
"Delegation log: OUTDATED - does not include sub-investigator added in Jan 2024.
Corrective action required."

STATUS: OUTDATED - requires update
MONITORING FINDING: YES (see MVR 2024-03-15)
"""

_DEVIATION_LOG_012 = """\
PROTOCOL DEVIATION LOG
Study: ABC-001
Site: 012 - Research Center
Report Period: January 2024 - March 2024

SITE INFORMATION
PI: Dr. K. Patel
Study Coordinator: T. Brown

DEVIATION SUMMARY
Total Deviations: 8
Major Deviations: 3
Minor Deviations: 5

DEVIATION ENTRIES

DEV-012-001
Date: 2024-01-22
Category: Major Deviation
Description: Eligibility criteria not met - Patient 012-002 enrolled despite eGFR reading
             of 28 (protocol requires eGFR >= 30). Patient enrolled in error.
Action: Patient withdrawn from study. SAE assessment completed - no harm identified.
Protocol Section: 4 (Exclusion Criteria)
Status: Closed

DEV-012-002
Date: 2024-02-05
Category: Major Deviation
Description: Protocol violation - Dosing window exceeded for 3 consecutive doses.
             Patient 012-005 administered drug outside +/-2 hour window.
Action: Documented, causality assessed. No safety impact.
Protocol Section: 5 (Dosing Regimen)
Status: Closed - CAPA submitted

DEV-012-003
Date: 2024-02-18
Category: Minor Deviation
Description: Missed assessment - Week 4 PK sample not collected for Patient 012-003.
Action: Missing data noted in database. No safety impact.
Protocol Section: 7 (Assessments)
Status: Closed

DEV-012-004
Date: 2024-02-28
Category: Major Deviation - CRITICAL
Description: Blinding breach - Study drug assignment inadvertently revealed to site
             staff during drug reconciliation. Patient 012-007 affected.
Action: Sponsor notified within 24 hours. Regulatory reporting assessment in progress.
Protocol Section: 8 (Blinding)
Status: OPEN - Under regulatory review

DEV-012-005
Date: 2024-03-08
Category: Minor Deviation
Description: Incorrect dosing documented for Patient 012-009. Dose administered at
             incorrect time on Day 14.
Action: Documentation corrected in source data.
Protocol Section: 5 (Dosing Regimen)
Status: Closed

DEV-012-006
Date: 2024-03-12
Category: Minor Deviation
Description: Documentation error - Visit window exceeded by 2 days for Patient 012-011.
Action: Deviation logged. No clinical impact.
Status: Closed

DEV-012-007
Date: 2024-03-15
Category: Minor Deviation
Description: Reminder sent to site regarding GDP failure - source data correction without
             proper documentation trail.
Action: Site staff re-trained on GCP/GDP requirements.
Status: Closed

DEV-012-008
Date: 2024-03-20
Category: Minor Deviation
Description: Late filing - Adverse event form submitted 10 days past required deadline.
Action: Corrective action implemented. Sponsor notified.
Status: Closed

TREND ANALYSIS
Site 012 deviation risk increasing. Deviation rate: 8 deviations in 3 months for 22 enrolled.
Major deviation rate (3/22 = 13.6%) exceeds acceptable threshold.
Blinding breach (DEV-012-004) represents critical protocol violation requiring FDA reporting.

SITE RISK RATING: HIGH
Recommend immediate for-cause monitoring visit.
"""

_FDA_1572_021 = """\
STATEMENT OF INVESTIGATOR
(FORM FDA 1572)
[OUTDATED VERSION - NOT CURRENT]

Form FDA 1572 (Rev. 07/2012)
OMB No. 0910-0014

STUDY NUMBER: ABC-001
DATE: 2022-04-01  [NOTE: This document predates protocol version 2.1 - REQUIRES UPDATE]

1. NAME AND ADDRESS OF INVESTIGATOR
Dr. R. Williams, MD, PhD
University Clinic, 500 Research Blvd, Suite 300

2. EDUCATION, TRAINING AND EXPERIENCE
See attached Curriculum Vitae

3. NAME AND ADDRESS OF ANY MEDICAL SCHOOL, HOSPITAL OR OTHER
RESEARCH FACILITY WHERE THE CLINICAL INVESTIGATION WILL BE
CONDUCTED:
University Clinic - Site 021

4. NAME AND ADDRESS OF ANY CLINICAL LABORATORY FACILITIES TO BE USED:
University Clinical Lab
Central Reference Lab (contract)

5. NAME AND ADDRESS OF THE INSTITUTIONAL REVIEW BOARD (IRB)
University IRB Committee
Ethics approval reference: UNI-IRB-2022-441

6. NAMES OF THE SUBINVESTIGATORS
[BLANK - Subinvestigators added in 2024 not reflected]

7. NAME AND CODE NUMBER OF THE PROTOCOL(S)
Protocol: ABC-001, Version 1.0
[NOTE: Protocol has been amended to v2.1 - this form has NOT been updated]

8. COMMITMENTS
I agree to conduct the study in accordance with the relevant, current protocol(s)
and will only make changes in a protocol after notifying the sponsor...

[Signature block - Signed April 1, 2022]
Dr. R. Williams

FILING STATUS: OUTDATED
This FDA 1572 does not reflect:
- Protocol amendment v2.1 (updated Nov 2023)
- New subinvestigators added January 2024
- Updated IRB approval reference

ACTION REQUIRED: Updated FDA 1572 must be obtained and filed.
RISK LEVEL: HIGH
"""

_INVESTIGATOR_CV_021 = """\
CURRICULUM VITAE - INVESTIGATOR

NAME: Dr. Robert Williams, MD, PhD
TITLE: Professor of Clinical Medicine
INSTITUTION: University Clinic
ADDRESS: 500 Research Blvd, Suite 300

STUDY: ABC-001
SITE: 021 - University Clinic
ROLE: Principal Investigator

DATE OF PREPARATION: 2021-03-15

NOTE: This CV was prepared in March 2021.
Per protocol requirements, Investigator CVs must be current within 2 years.
This CV is OUTDATED as of March 2023.
An updated CV has been requested but not yet received.

EDUCATION
MD: University Medical School, 1995
PhD (Clinical Pharmacology): State University, 2000

BOARD CERTIFICATIONS
Internal Medicine (certified 2000, recertified 2020)
Clinical Pharmacology (certified 2002)

CLINICAL TRIAL EXPERIENCE
Principal Investigator: 12 completed Phase II/III trials
Current active trials: 4
GCP Training: Completed 2020 (renewal required)

PUBLICATIONS
Williams R et al. (2019) NEJM 380:2344-2355
Williams R et al. (2021) Lancet 397:1824-1835

SIGNATURE
/s/ Dr. Robert Williams
Date: 2021-03-15

WARNING: CV older than 2 years. Update required for study compliance.
"""

# (filename, site_code or None, embedded_content)
SEED_FILES: list[tuple[str, str | None, str]] = [
    ("protocol_abc001.txt",                 None,  _PROTOCOL),
    ("monitoring_report_site004.txt",       "004", _MONITORING_REPORT_004),
    ("irb_approval_site004.txt",            "004", _IRB_APPROVAL_004),
    ("delegation_log_site004_outdated.txt", "004", _DELEGATION_LOG_004),
    ("deviation_log_site012.txt",           "012", _DEVIATION_LOG_012),
    ("fda_1572_site021_outdated.txt",       "021", _FDA_1572_021),
    ("investigator_cv_site021.txt",         "021", _INVESTIGATOR_CV_021),
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
    """
    Restorative seed: upserts the full ABC-001 demo state on every run.

    Safe to run on every deploy. If production is in a partial state
    (study exists but missing flags/signals/simulation), this repairs it.
    """
    engine = create_engine(settings.sync_database_url, echo=False)
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
        # ── Study: get or create ───────────────────────────────────────────
        study = session.query(Study).filter_by(name="ABC-001").first()
        if study:
            study_id = study.id
            logger.info(f"Study ABC-001 found ({study_id}) — restoring full demo state.")
        else:
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

        # ── Sites: get by site_code or create ─────────────────────────────
        now = datetime.now(timezone.utc)
        existing_sites = {
            s.site_code: s
            for s in session.query(Site).filter_by(study_id=study_id).all()
        }

        SITE_DEFS: dict[str, dict] = {
            "004": dict(
                activated_at=now - timedelta(days=90),
                irb_approved_at=now - timedelta(days=95),
                fpi_at=now - timedelta(days=60),
                enrolled_count=18,
            ),
            "012": dict(
                activated_at=now - timedelta(days=75),
                irb_approved_at=now - timedelta(days=80),
                fpi_at=now - timedelta(days=45),
                enrolled_count=22,
            ),
            "021": dict(
                activated_at=now - timedelta(days=70),
                irb_approved_at=now - timedelta(days=72),
                fpi_at=None,
                enrolled_count=0,
            ),
        }

        site_objs: dict[str, Site] = {}
        for code, attrs in SITE_DEFS.items():
            if code in existing_sites:
                site_objs[code] = existing_sites[code]
                logger.info(f"Site {code} found — reusing.")
            else:
                s = Site(id=str(uuid.uuid4()), study_id=study_id, site_code=code, **attrs)
                session.add(s)
                site_objs[code] = s
                logger.info(f"Site {code} created.")

        session.flush()

        # ── Compliance rules: upsert by rule_code ─────────────────────────
        rules = load_rules()
        existing_rule_codes = {
            r.rule_code
            for r in session.query(ComplianceRule.rule_code).all()
        }
        added_rules = 0
        for rule in rules:
            if rule["rule_code"] not in existing_rule_codes:
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
                added_rules += 1
        session.flush()
        logger.info(f"Compliance rules ready ({len(rules)} total, {added_rules} newly added).")

        # ── Documents: insert only if filename not already present ─────────
        existing_filenames = {
            d.filename
            for d in session.query(Document).filter(Document.study_id == study_id).all()
        }

        for filename, site_code, content in SEED_FILES:
            if filename in existing_filenames:
                logger.info(f"Document already seeded: {filename} — skipping.")
                continue

            full_text = content.strip()
            text_excerpt = full_text[:1000]
            artifact_type = classify_artifact(filename, full_text)
            has_signature = detect_signature_simple(full_text.lower())

            site_obj = site_objs.get(site_code) if site_code else None
            site_id = site_obj.id if site_obj else None

            doc_id = str(uuid.uuid4())
            s3_key = f"documents/{study_id}/{doc_id}/{filename}"
            try:
                upload_bytes(s3_key, full_text.encode("utf-8"), "text/plain")
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
            logger.info(f"Seeded: {filename} -> {artifact_type} (sig={has_signature})")

        session.flush()

        # Load all study docs for flag/deviation recomputation
        all_docs = session.query(Document).filter(Document.study_id == study_id).all()
        study_level_docs = [d for d in all_docs if d.site_id is None]
        site_docs_map: dict[str, list[Document]] = {}
        for d in all_docs:
            if d.site_id:
                site_docs_map.setdefault(d.site_id, []).append(d)

        # ── Compliance flags: always clear + recompute ─────────────────────
        session.query(ComplianceFlag).filter(
            ComplianceFlag.study_id == study_id
        ).delete(synchronize_session=False)
        session.flush()

        new_flags: list[ComplianceFlag] = []
        for site in site_objs.values():
            site_docs = site_docs_map.get(site.id, [])
            facts = FactBuilder.build(
                site=site,
                site_docs=site_docs,
                study_docs=study_level_docs,
                deviation_score=None,
            )
            for rule in rules:
                if evaluate_rule(rule, facts):
                    flag = ComplianceFlag(
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
                    )
                    session.add(flag)
                    new_flags.append(flag)

        session.flush()
        logger.info(f"Compliance flags recomputed: {len(new_flags)} flags.")

        # ── Deviation signals: always clear + recompute ────────────────────
        session.query(DeviationSignal).filter(
            DeviationSignal.study_id == study_id
        ).delete(synchronize_session=False)
        session.flush()

        new_signals: list[DeviationSignal] = []
        study_text = " ".join(
            (d.full_text or d.text_excerpt or "") for d in study_level_docs
        )
        for site in site_objs.values():
            site_specific_docs = site_docs_map.get(site.id, [])
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

            signal = DeviationSignal(
                id=str(uuid.uuid4()),
                study_id=study_id,
                site_id=site.id,
                score=round(score, 1),
                top_findings_json={"findings": findings[:6]},
                created_at=datetime.now(timezone.utc),
            )
            session.add(signal)
            new_signals.append(signal)
            logger.info(f"Deviation score Site {site.site_code}: {score:.1f}")

        session.flush()
        logger.info(f"Deviation signals recomputed: {len(new_signals)} signals.")

        # ── Inspection simulation: create if none exists ───────────────────
        sim_count = session.query(InspectionSimulation).filter(
            InspectionSimulation.study_id == study_id
        ).count()

        if sim_count == 0:
            risk_score, breakdown = compute_risk_score(new_flags, new_signals)

            # Build results payload matching the shape expected by the frontend
            id_to_code = {s.id: s.site_code for s in site_objs.values()}
            _DEDUCTIONS = {"CRITICAL": 20, "HIGH": 10, "MEDIUM": 5, "LOW": 2}
            by_severity = Counter(f.severity for f in new_flags)

            top_flags_data = [
                {
                    "rule_code": f.rule_code,
                    "severity": f.severity,
                    "risk_level": f.risk_level,
                    "risk_points": f.risk_points,
                    "category": f.category,
                    "title": f.title,
                    "site_id": f.site_id,
                    "site_code": id_to_code.get(f.site_id, "Study") if f.site_id else "Study",
                }
                for f in sorted(
                    new_flags,
                    key=lambda x: _DEDUCTIONS.get(x.severity, 0),
                    reverse=True,
                )[:12]
            ]

            high_dev_signals = [s for s in new_signals if s.score >= 40]
            site_deviation_scores = [
                {
                    "site_id": s.site_id,
                    "site_code": id_to_code.get(s.site_id, "?") if s.site_id else "?",
                    "score": s.score,
                    "findings": (s.top_findings_json or {}).get("findings", []),
                }
                for s in sorted(new_signals, key=lambda x: x.score, reverse=True)
            ]

            results = {
                "risk_score": risk_score,
                "total_flags": len(new_flags),
                "critical_flags": by_severity.get("CRITICAL", 0),
                "high_flags": by_severity.get("HIGH", 0),
                "medium_flags": by_severity.get("MEDIUM", 0),
                "low_flags": by_severity.get("LOW", 0),
                "scoring_breakdown": breakdown,
                "top_flags": top_flags_data,
                "missing_artifacts": list({f.title for f in new_flags})[:12],
                "high_deviation_sites": [
                    id_to_code.get(s.site_id, s.site_id)
                    for s in high_dev_signals[:5]
                    if s.site_id
                ],
                "site_deviation_scores": site_deviation_scores,
            }

            narrative = _deterministic_narrative(risk_score, results)

            sim = InspectionSimulation(
                id=str(uuid.uuid4()),
                study_id=study_id,
                risk_score=risk_score,
                vulnerable_zone=_classify_zone(risk_score),
                results_json=results,
                narrative=narrative,
                created_at=datetime.now(timezone.utc),
            )
            session.add(sim)
            session.flush()
            logger.info(
                f"Inspection simulation created: score={risk_score:.1f}, "
                f"zone={sim.vulnerable_zone}, flags={len(new_flags)}, signals={len(new_signals)}"
            )
        else:
            logger.info(f"Simulation already exists ({sim_count} record(s)) — skipping.")

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
