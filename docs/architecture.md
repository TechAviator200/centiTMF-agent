# centiTMF — Architecture

## Overview

centiTMF answers one question: **"If regulators inspected this study next month, where would we fail?"**

It combines an eTMF workflow layer (completeness, timeliness, quality monitoring) with AI-native compliance intelligence: rule evaluation, deviation detection, and a 0–100 Inspection Readiness Score with an AI-generated narrative.

---

## System Components

### Local Development (Docker Compose)

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Compose                        │
│                                                          │
│  ┌──────────────┐   HTTP    ┌──────────────────────┐    │
│  │  Next.js 14  │ ────────► │  FastAPI Backend      │    │
│  │  Frontend    │           │  (Python 3.11)        │    │
│  │  :3000       │           │  :8000                │    │
│  └──────────────┘           └──────────┬───────────┘    │
│                                        │                  │
│                             ┌──────────▼───────────┐    │
│                             │  PostgreSQL 16        │    │
│                             │  + pgvector           │    │
│                             └──────────┬───────────┘    │
│                                        │                  │
│                             ┌──────────▼───────────┐    │
│                             │  MinIO (S3-compat.)  │    │
│                             │  Document storage     │    │
│                             └──────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### Production Deployment

```
      Vercel                          Render
┌─────────────────┐          ┌──────────────────────────┐
│  Next.js 14     │  HTTPS   │  FastAPI Backend          │
│  Frontend       │ ───────► │  Docker · Port: $PORT     │
│  (SSR + Client) │          └──────────┬───────────────┘
└─────────────────┘                     │
                                ┌───────┴──────┐
                                │              │
                          ┌─────▼──────┐  ┌───▼──────────────┐
                          │ Supabase   │  │ Cloudflare R2     │
                          │ Postgres   │  │ (S3-compatible)   │
                          │ + pgvector │  │ Document storage  │
                          └────────────┘  └──────────────────┘
```

---

## Data Flow: Inspection Simulation

```
POST /api/simulate/inspection?study_id=...
         │
         ▼
  1. compute_compliance_flags()
         │  ── loads rules from seed_rules.json
         │  ── builds FactDict per site via FactBuilder
         │  ── evaluates each rule against facts
         │  ── writes ComplianceFlag rows
         │
         ▼
  2. compute_deviation_intel()
         │  ── loads site documents (full_text)
         │  ── scores text against deviation patterns
         │  ── writes DeviationSignal rows
         │
         ▼
  3. compute_risk_score(flags, signals)
         │  ── base 100 − flag deductions − penalties
         │  ── returns (score: float, breakdown: dict)
         │
         ▼
  4. generate_inspection_narrative(score, results)
         │  ── GPT-4o if OPENAI_API_KEY is set
         │  ── deterministic template fallback otherwise
         │
         ▼
  5. Persist InspectionSimulation row
         │
         ▼
  6. Return SimulationOut (score, zone, narrative, results_json)
```

---

## Data Flow: Audit Questions

```
POST /api/audit/questions
  { study_id, question }
         │
         ▼
  1. Load study context from DB
         │  ── sites, flags, deviation signals, latest sim
         │
         ▼
  2. Route question by keyword pattern
         │  ── highest_risk | missing | fix_first
         │  ── score_drivers | site_detail | overall
         │
         ▼
  3. Build grounded deterministic answer from real data
         │
         ▼
  4. (Optional) Enhance with GPT-4o
         │
         ▼
  5. Return { question, answer, data_basis }
```

---

## Database Schema

| Table | Purpose |
|-------|---------|
| `studies` | Clinical trial studies |
| `sites` | Study sites with enrollment and IRB data |
| `documents` | Uploaded TMF artifacts (S3 key, artifact_type, detected_artifact_type, classification_overridden, full_text, has_signature) |
| `embeddings` | 1536-dim pgvector embeddings for semantic search |
| `compliance_rules` | Persisted rule definitions (loaded from seed_rules.json) |
| `compliance_flags` | Rule violations per site (category, severity, risk_points, facts_snapshot) |
| `deviation_signals` | Per-site deviation scores and top findings |
| `inspection_simulations` | Historical simulation results (score, zone, narrative, results_json) |

### Document Classification Fields

| Field | Description |
|-------|-------------|
| `artifact_type` | The active (final) classification — may have been user-overridden |
| `detected_artifact_type` | The original AI classification — always preserved for audit trail |
| `classification_overridden` | `true` if the user manually changed the classification |

---

## Compliance Engine

The compliance engine uses a two-component design:

**FactBuilder** (`app/rules/rule_engine.py`) — normalizes site + document state into a flat fact dict:
```python
{
  "site_activated": True,
  "has_enrolled_patients": True,
  "site_has_fda_1572": False,
  "study_has_protocol": True,
  "site_has_unsigned_document": False,
  "deviation_score": 65.0,
  ...
}
```

**RuleEvaluator** — evaluates a JSON condition tree against the fact dict. Rules are defined in `app/rules/seed_rules.json` and loaded at runtime. See [rule-engine.md](rule-engine.md) for details.

---

## Scoring Model

The Inspection Readiness Score starts at **100** and deducts penalties:

| Event | Deduction |
|-------|-----------|
| CRITICAL compliance flag | −20 each |
| HIGH compliance flag | −10 each |
| MEDIUM compliance flag | −5 each |
| LOW compliance flag | −2 each |
| Site cluster (3+ flags at one site) | −10 per site (max 2 sites) |
| Multiple high-deviation sites (≥2) | −10 |
| Per high-deviation site (score ≥ 60) | −5 each |

Zone classification:
- **LOW RISK**: 80–100
- **MEDIUM RISK**: 60–79
- **HIGH RISK**: 40–59
- **CRITICAL RISK**: 0–39

---

## Frontend Architecture

Next.js 14 App Router with Server Components for data-fetching pages and Client Components for interactive features.

| Page | Rendering | Purpose |
|------|-----------|---------|
| `/` | Server | Study list |
| `/studies/[studyId]` | Server + Client (AuditCopilot) | Study dashboard |
| `/studies/[studyId]/sites/[siteId]` | Server | Site detail |
| `/simulate/[studyId]` | Client | Inspection simulation |
| `/upload` | Client | Document upload |

Server-side fetches use `INTERNAL_API_URL=http://backend:8000` (within Docker). Browser fetches use `NEXT_PUBLIC_API_URL=http://localhost:8000`.

---

## Key Source Files

| File | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI app, CORS, router registration |
| `backend/app/db/models.py` | SQLAlchemy ORM models |
| `backend/app/rules/rule_engine.py` | FactBuilder + RuleEvaluator |
| `backend/app/rules/seed_rules.json` | Data-driven compliance rule definitions |
| `backend/app/services/compliance_engine.py` | Runs rule evaluation per study |
| `backend/app/services/deviation_intelligence.py` | Text pattern scoring |
| `backend/app/services/inspection_simulation.py` | Score computation + simulation |
| `backend/app/services/audit_copilot.py` | Bounded Q&A with LLM enhancement |
| `backend/app/services/document_ingestion.py` | Upload pipeline |
| `backend/scripts/seed.py` | Demo data seeding with schema migration |
| `frontend/lib/api.ts` | API client (all fetch calls) |
| `frontend/lib/utils.ts` | Shared color/label helpers |

---

## Production Deployment Notes

### URL Normalization

The backend automatically normalizes database URLs at startup:
- `postgres://...` → `postgresql+asyncpg://...` (async engine)
- `postgres://...` → `postgresql://...` (sync engine)
- `postgresql://...` → `postgresql+asyncpg://...` (async engine)

Supabase, Render, and most PaaS providers emit `postgres://` URLs — this normalization ensures SQLAlchemy compatibility without manual URL editing.

### Port Binding (Render)

Render assigns a dynamic port via the `$PORT` environment variable. The backend CMD reads it:
```
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
```
Local Docker Compose overrides this CMD with its own command (port 8000 + reload).

### Supabase Connection Strings

Supabase provides two connection URLs:
- **Pooled (Session Mode, port 6543)** — use for `DATABASE_URL` (FastAPI async engine)
- **Direct (port 5432)** — use for `SYNC_DATABASE_URL` (seed script)

If only `DATABASE_URL` is set, `SYNC_DATABASE_URL` is derived from it automatically.

### Cloudflare R2 Storage

R2 is S3-compatible. Required configuration:
- `S3_ENDPOINT_URL`: `https://<account-id>.r2.cloudflarestorage.com`
- `AWS_REGION`: `auto`
- Buckets must be pre-created in the Cloudflare dashboard (auto-creation is not available).

## Security Notes

- All secrets are injected via environment variables — nothing is committed
- CORS is `allow_origins=["*"]` for local development; restrict to your domain in production
- Default credentials are for local Docker use only — rotate before any public deployment
- File uploads are type-checked at the FastAPI layer
- `materials/` (private research) is gitignored and must never be committed
