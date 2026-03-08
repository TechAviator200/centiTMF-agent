# centiTMF — Demo Walkthrough

A guided 5-minute demo of the centiTMF Inspection Readiness platform.

**Live demo:** [centi-tmf-agent.vercel.app](https://centi-tmf-agent.vercel.app/)

To run locally:

```bash
docker compose up --build
# then open http://localhost:3000
```

---

## Step 1 — Homepage

The home screen shows all clinical studies and the primary action controls.

**Hero area:**
- **Run Simulation** button — routes directly to the inspection simulation for the first study. Disabled (grayed out) when no studies exist yet.
- **Upload Documents** button — opens the upload workflow.

The seeded demo includes **ABC-001** (Phase II, Acme Pharma Inc.). Click it to open the study dashboard.

---

## Step 2 — Study Dashboard

The study dashboard is the central compliance hub.

**eTMF Health Dashboard** (top section):
- **Completeness** — expected vs present TMF artifacts with a percentage bar and missing critical count
- **Timeliness** — overdue monitoring reports, stale documents, late filings count
- **Quality** — unsigned document count, QC issue count
- **Risk** — inspection readiness score (from last simulation), highest-risk sites, open HIGH/CRITICAL flags
- **Audit Readiness** — top likely findings and a prioritized recommended action list with quick links

**Inspection Readiness Score card:**
- If no simulation has been run, it shows flag counts and prompts you to run one
- After a simulation, it shows the 0–100 score, colored progress bar, and zone badge (LOW / MEDIUM / HIGH / CRITICAL)

**Stats row:**
- Active Sites, High Risk Flags, Medium Flags, Documents

**Site Risk Overview table:**
- Sites sorted by risk (highest flags first)
- Columns: Site, Status, Enrolled, Total Flags, High/Critical, Deviation Score
- Click **Details** on any site to drill into that site's compliance detail

**Audit Questions panel:**
- Ask natural-language questions grounded in the study's compliance data
- Try: "Which sites are highest risk?", "What artifacts are missing?", "What should be fixed first?"

**TMF Documents table:**
- Shows artifact type, source (study/site), signature status, upload date
- Overridden classifications show a purple "overridden" badge

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

## Step 4 — Document Upload + Classification Override

Navigate to **Upload** (link in navbar or from the study's TMF Documents section).

1. Select a study from the dropdown
2. Optionally select a site (dropdown populates based on study)
3. Drag and drop or click to select a PDF or TXT file
4. Click **Upload & Classify**

The system:
- Extracts full text
- Auto-classifies the artifact type (FDA_1572, Protocol, Delegation_Log, etc.) with a confidence level (High / Medium / Low)
- Detects whether the document is signed
- Generates a 1536-dim embedding and stores the file

**After upload:** The result panel shows:
- **AI Classified: [TYPE]** — what the system detected
- **Confidence** — High / Medium / Low indicator
- **Override classification** — click to reveal a dropdown with all recognized types, then **Confirm Override** to save your choice

The original AI classification is preserved as `detected_artifact_type` for audit trail purposes. Overridden documents show a purple "overridden" badge on the study dashboard.

---

## Step 5 — Inspection Simulation

From the homepage **Run Simulation** button, or from the **Simulate FDA Inspection** button on the study dashboard.

Click **Run New Simulation**.

The simulation:
1. Re-evaluates all compliance rules against the current document state
2. Re-scores protocol deviation intelligence
3. Computes the readiness score (base 100, subtract penalties)
4. Generates an AI narrative (GPT-4o if key set, otherwise deterministic)

Results show:
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
- `GET /api/etmf/studies/{id}/dashboard` — eTMF health dashboard
- `GET /api/studies/{id}` — study detail with site summaries
- `POST /api/documents/upload` — upload and classify a document
- `PATCH /api/documents/{id}/classification` — override AI classification
- `POST /api/simulate/inspection?study_id=...` — run simulation
- `POST /api/audit/questions` — ask an audit question

---

## Demo Scenario Summary

| Site | Story | Risk Level |
|------|-------|-----------|
| Site 004 | Has monitoring report and IRB approval, but delegation log is outdated | MEDIUM |
| Site 012 | Has only a deviation log with blinding breach; missing most required documents | HIGH |
| Site 021 | Outdated FDA 1572 and investigator CV; zero enrollment | MEDIUM |

The demo is designed to show a realistic mix of compliance gaps across three sites, with Site 012 as the clear priority for remediation.
