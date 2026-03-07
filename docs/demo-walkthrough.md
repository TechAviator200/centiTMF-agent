# centiTMF — Demo Walkthrough

A guided 3-minute demo of the centiTMF Inspection Readiness platform.

## Prerequisites

```bash
docker compose up --build
```

Open http://localhost:3000.

---

## Step 1 — Study List

The home screen shows all clinical studies. The seeded demo includes **ABC-001** (Phase II, Acme Pharma Inc.).

- Click **ABC-001** to open the study dashboard.

---

## Step 2 — Study Dashboard

The study dashboard is the central compliance hub for a single study.

**Inspection Readiness Score card** (top of page):
- If no simulation has been run, it shows flag counts and prompts you to run one
- After a simulation, it shows the 0–100 score, colored progress bar, and zone badge

**Stats row:**
- Active Sites — how many sites are activated vs total
- High Risk Flags — combined CRITICAL + HIGH severity
- Medium Flags — MEDIUM severity
- Documents — total TMF artifacts on file

**Site Risk Overview table:**
- Sites sorted by risk (highest flags first)
- Columns: Site, Status, Enrolled, Total Flags, High/Critical, Deviation Score
- Click **Details** on any site to drill into that site's compliance detail

**Audit Questions panel:**
- Ask natural-language questions grounded in the study's compliance data
- Try the suggested chips: "Which sites are highest risk?", "What artifacts are missing?", etc.
- Type a custom question and press Enter

---

## Step 3 — Site Detail

Click **Details** on Site 012 (the highest-risk site in the demo).

The site page shows:
- Enrolled patient count, activation date, IRB date, FPI date
- Critical/High flag count, Medium flag count, Documents on file
- **Deviation Intelligence** card — deviation risk score (0–100) with top findings
- **Compliance Flags table** — all flags for this site with severity badges and rule codes
- **Documents on file** — artifact type, signature status, upload date

---

## Step 4 — Document Upload

Navigate to **Upload** (link in navbar or from the study's TMF Documents section).

1. Select a study from the dropdown
2. Optionally select a site (dropdown populates based on study)
3. Drag and drop or click to select a PDF or TXT file
4. Click **Upload & Classify**

The system:
- Extracts full text
- Auto-classifies the artifact type (FDA_1572, Protocol, Delegation_Log, etc.)
- Detects whether the document is signed
- Generates a 1536-dim embedding
- Stores the file in MinIO

The response shows the classified artifact type.

---

## Step 5 — Inspection Simulation

Navigate to **Simulate** (button in the study header or top nav).

Click **Run New Simulation**.

The simulation:
1. Re-evaluates all compliance rules against the current document state
2. Re-scores protocol deviation intelligence
3. Computes the readiness score (base 100, subtract penalties)
4. Generates an AI narrative (GPT-4o if key set, otherwise deterministic)

The results page shows:
- **Readiness Score gauge** — 0–100 with zone badge
- **Score breakdown** — flag deductions, cluster penalties, deviation penalties
- **Regulatory Assessment Narrative** — structured assessment by risk zone
- **Missing Artifacts** — list of documents not yet on file
- **Site Deviation Risk** — mini bar charts with findings per site
- **Top Compliance Flags table** — sorted by risk_points with site codes
- **Simulation History** — prior runs for trend tracking

---

## Step 6 — API Explorer

Navigate to http://localhost:8000/docs for the full Swagger interface.

Key endpoints to explore:
- `GET /api/studies` — list studies
- `GET /api/studies/{id}` — study detail with site summaries
- `GET /api/studies/{id}/sites/{sid}` — site detail with flags
- `POST /api/simulate/inspection?study_id=...` — run simulation
- `POST /api/audit/questions` — ask an audit question
- `POST /api/documents/upload` — upload a document

---

## Demo Scenario Summary

| Site | Story | Risk Level |
|------|-------|-----------|
| Site 004 | Has monitoring report and IRB approval, but delegation log is outdated | MEDIUM |
| Site 012 | Has only a deviation log with blinding breach; missing most required documents | HIGH |
| Site 021 | Outdated FDA 1572 and investigator CV; zero enrollment | MEDIUM |

The demo is designed to show a realistic mix of compliance gaps across three sites, with Site 012 as the clear priority for remediation.
