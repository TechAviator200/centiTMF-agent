# centiTMF

AI-native compliance intelligence for clinical trials.

centiTMF helps clinical teams maintain inspection readiness, monitor document completeness, detect TMF compliance gaps, and prepare for audits and regulatory review.

---

## Why centiTMF

Clinical trials depend on a complete and inspection-ready Trial Master File (TMF), but maintaining readiness is often manual, reactive, and difficult to monitor across sites.

centiTMF adds a compliance intelligence layer that continuously answers:

> "If auditors or regulators reviewed this study next month, where would we be exposed?"

The platform analyzes TMF artifacts and site-level activity to surface risk before it becomes a real inspection problem.

---

## Core Capabilities

- **Inspection Readiness Monitoring** — 0–100 readiness score with zone classification (LOW / MEDIUM / HIGH / CRITICAL)
- **Document Completeness Analysis** — automated detection of missing TMF artifacts per site
- **Missing Artifact Detection** — data-driven compliance rules evaluated against a normalized fact model
- **Protocol Deviation Intelligence** — cross-document analysis detecting deviation trends and risk signals per site
- **Site-Level Risk Visibility** — per-site flag counts, deviation scores, and enrollment-gated compliance checks
- **Inspection Simulation** — composite readiness score with penalty breakdown and AI-generated narrative
- **Audit Questions** — ask bounded natural-language questions grounded in study compliance data

---

## Screenshots

### Study List
![Study list showing ABC-001 with Phase II badge](docs/images/screenshot-home.png)
*The home screen shows all clinical studies with one-click access to each study's compliance dashboard.*

### Study Dashboard — Inspection Readiness
![Study dashboard with readiness score, compliance flags, and site risk table](docs/images/screenshot-dashboard.png)
*The study dashboard surfaces inspection readiness at a glance: flag counts, site-level risk rankings, and deviation signals.*

### Inspection Simulation
![Inspection simulation page with readiness score gauge and scoring breakdown](docs/images/screenshot-simulation.png)
*Simulation generates a 0–100 readiness score with a full penalty breakdown, AI narrative, and site deviation risk chart.*

> **To add screenshots:** save PNG files to `docs/images/` matching the filenames above. See [docs/images/README.md](docs/images/README.md).

---

## Architecture Overview

```
Document Upload  ──►  Artifact Classifier  ──►  S3 / PostgreSQL
                                                       │
                                              Compliance Engine
                                              (Fact Model + Rules)
                                                       │
                                              Deviation Intelligence
                                              (Text Pattern Scoring)
                                                       │
                                              Inspection Simulation
                                              (Base-100 Scoring + LLM)
                                                       │
                                         Audit Questions ──►  Report
```

1. **Document Ingestion** — PDF/TXT upload, rule-based artifact classification, full-text extraction, signature detection, vector embedding
2. **Fact Model Generation** — `FactBuilder` normalizes each site's state into a deterministic fact dict
3. **Rule-Based Compliance Detection** — 10 data-driven JSON rules evaluated against the fact model; violations become compliance flags
4. **Deviation Intelligence** — keyword pattern scoring across site documents detects protocol deviation signals
5. **Scoring and Simulation** — base-100 subtract model with CRITICAL/HIGH/MEDIUM/LOW deductions and cluster/deviation penalties
6. **Audit Questions** — bounded Q&A grounded in flags, deviation signals, and simulation outputs; enhanced by GPT-4o when configured

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Python 3.11, SQLAlchemy 2.0 (async), Pydantic v2 |
| Database | PostgreSQL 16 + pgvector |
| Storage | MinIO (S3-compatible) |
| Frontend | Next.js 14, TypeScript, TailwindCSS (App Router) |
| Embeddings | OpenAI text-embedding-3-small (deterministic hash fallback) |
| LLM | GPT-4o (deterministic template fallback) |
| Infrastructure | Docker Compose |

---

## Local Setup

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/centiTMF.git
cd centiTMF

# 2. (Optional) Configure OpenAI for AI-enhanced narratives and audit answers
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...

# 3. Start all services
docker compose up --build
```

Services:

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| MinIO Console | http://localhost:9001 |

On first start, the backend automatically seeds demo study **ABC-001** with three sites and representative TMF documents.

---

## Demo

See [docs/demo-walkthrough.md](docs/demo-walkthrough.md) for a guided 3-minute walkthrough.

---

## Running Tests

```bash
# Inside Docker
docker compose exec backend pytest

# Or locally (Python 3.11 + dev dependencies)
cd backend && pip install -e ".[dev]" && pytest
```

Tests cover the rule engine evaluator, artifact classifier, and risk scoring model. All tests are pure unit tests — no database required.

---

## Make Commands

```bash
make up            # Build and start all services
make down          # Stop all services
make logs          # Stream all service logs
make logs-backend  # Stream backend logs only
make shell-backend # Open a shell in the backend container
make shell-db      # Open psql in the postgres container
make seed          # Re-run the seed script
make reset         # Wipe volumes and rebuild from scratch
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/PRD.md](docs/PRD.md) | Product requirements and roadmap |
| [docs/architecture.md](docs/architecture.md) | System design and data flow |
| [docs/rule-engine.md](docs/rule-engine.md) | Fact model and compliance rule evaluation |
| [docs/demo-walkthrough.md](docs/demo-walkthrough.md) | Step-by-step demo guide |
| [docs/api-overview.md](docs/api-overview.md) | REST API reference |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *(empty)* | Optional — enables AI narratives and enhanced Audit Questions |
| `DATABASE_URL` | `postgresql+asyncpg://centitmf:centitmf@postgres:5432/centitmf` | Async Postgres connection |
| `SYNC_DATABASE_URL` | `postgresql://centitmf:centitmf@postgres:5432/centitmf` | Sync connection (seed script) |
| `S3_ENDPOINT_URL` | `http://minio:9000` | MinIO / S3 endpoint |
| `S3_BUCKET` | `centitmf-docs` | Document storage bucket |

---

## License

MIT
