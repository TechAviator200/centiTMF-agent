# centiTMF — Product Requirements Document

## Product

**centiTMF** is an AI-native compliance intelligence platform for clinical trial Trial Master Files (TMFs). It continuously monitors TMF completeness, detects compliance gaps, and helps teams maintain inspection readiness and audit preparedness.

---

## Problem

Clinical trials are subject to regulatory inspection at any time. Sponsors and CROs are responsible for maintaining a complete, accurate, and inspection-ready Trial Master File — but in practice:

- TMF completeness is monitored manually, inconsistently, and reactively
- Missing artifacts are discovered during inspections rather than before them
- Protocol deviation trends are buried in individual site documents
- Compliance gaps at one site are invisible to the sponsor until a monitor visit
- There is no continuous, automated view of "inspection readiness" across a study

The result: teams are always catching up rather than staying ahead of regulatory risk.

---

## Users

| Role | Primary Need |
|------|-------------|
| Clinical Operations Lead | Portfolio-level visibility into TMF completeness across studies |
| Clinical Trial Manager | Site-level compliance status and remediation priorities |
| Quality Assurance | Evidence of inspection readiness before audit or filing |
| Regulatory Affairs | Artifact completeness and document quality verification |

---

## Product Concept

centiTMF sits on top of the TMF and answers one core question:

> "If regulators inspected this study next month, where would we fail?"

It does this by:
1. Ingesting TMF documents and classifying artifact types
2. Evaluating data-driven compliance rules against a normalized fact model
3. Detecting deviation patterns from document text
4. Producing a 0–100 Inspection Readiness Score with a full penalty breakdown
5. Enabling natural-language Audit Questions grounded in study data

---

## Key Features

### Inspection Readiness Score
A composite 0–100 score reflecting TMF completeness, protocol deviation risk, and site-level compliance. Higher is better. Zone classification: LOW (80+), MEDIUM (60–79), HIGH (40–59), CRITICAL (0–39).

### Document Completeness Analysis
Automated detection of missing TMF artifacts per site. Rules evaluate whether each active site has the required documents on file: FDA Form 1572, Delegation Log, IRB Approval, Investigator CV, Monitoring Visit Report, and more.

### Artifact Auto-Classification
Uploaded documents are automatically classified into 10 TMF artifact types using filename and text heuristics. No manual tagging required.

### Protocol Deviation Intelligence
Document text is scored against a pattern library to detect deviation signals: blinding breaches, protocol violations, consent issues, dosing errors, and more. Per-site deviation scores contribute to the readiness score.

### Site-Level Risk Visibility
Each site is independently evaluated and ranked by risk. Flag counts, deviation scores, and enrollment-gated compliance checks are shown per site.

### Inspection Simulation
A full simulation run re-evaluates all rules and deviation signals, computes a fresh readiness score with breakdown, and generates a regulatory narrative (AI-enhanced when OpenAI is configured, deterministic fallback otherwise).

### Audit Questions
Bounded natural-language Q&A grounded in study data. Users can ask: "Which sites are highest risk?", "What artifacts are missing?", "What should be fixed first?", etc. Answers are always grounded in real compliance data — not hallucinated.

---

## MVP Scope

The initial version of centiTMF includes:

- [x] Document upload (PDF, TXT) with artifact auto-classification
- [x] Full-text extraction and signature detection
- [x] Data-driven compliance rule evaluation (10 rules, JSON-defined)
- [x] Fact model normalization (`FactBuilder`)
- [x] Protocol deviation intelligence (keyword pattern scoring)
- [x] Inspection Readiness Score (base-100 subtract model)
- [x] Per-site risk summaries and rankings
- [x] Inspection simulation with AI narrative
- [x] Audit Questions (bounded Q&A, LLM-enhanced)
- [x] Vector embeddings for document search (pgvector)
- [x] Fully Dockerized local deployment

---

## Future Roadmap

### Near-term
- **Rule editor** — add or modify compliance rules via UI without code changes
- **Document versioning** — track document revisions and flag outdated artifacts
- **Signature workflow** — track required signatures and send reminders
- **Email alerts** — notify stakeholders when readiness score drops below threshold

### Medium-term
- **Multi-study portfolio view** — aggregate readiness across all studies
- **Semantic document search** — find relevant TMF sections using vector similarity
- **Audit trail** — full history of compliance flags and remediation actions
- **CSV/PDF export** — inspection-ready readiness report export

### Long-term
- **Regulatory change detection** — monitor FDA/EMA guidance updates and flag impacted rules
- **Predictive risk modeling** — forecast readiness trajectory based on historical patterns
- **Integration connectors** — connect to document management systems via API
- **Role-based access control** — sponsor, CRO, and site-level access tiers

---

## Non-Goals (MVP)

- Electronic signature workflows
- CTMS or EDC integration
- eTMF taxonomy enforcement (21 CFR Part 11)
- Multi-tenant SaaS infrastructure
- Real-time collaboration

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Readiness score accuracy | Validated against known inspection findings |
| Artifact classification accuracy | > 90% on test document set |
| Time to first simulation | < 5 minutes from fresh install |
| Audit Questions answer relevance | Grounded in real study data, zero hallucination |
