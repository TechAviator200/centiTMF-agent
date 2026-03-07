# API Overview

Interactive Swagger docs: `http://localhost:8000/docs`

All endpoints are prefixed with `/api`. The API is a standard REST JSON API served by FastAPI.

---

## Studies

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/studies` | List all studies |
| `GET` | `/api/studies/{study_id}` | Study detail with site risk summaries and latest simulation |
| `GET` | `/api/studies/{study_id}/sites` | List sites for a study |
| `GET` | `/api/studies/{study_id}/sites/{site_id}` | Site detail with compliance flags and deviation findings |
| `GET` | `/api/studies/rules/all` | List all compliance rules loaded in the system |

### Study Detail Response

```json
{
  "id": "...",
  "name": "ABC-001",
  "phase": "Phase II",
  "sponsor": "Acme Pharma Inc.",
  "created_at": "...",
  "sites": [
    {
      "id": "...",
      "site_code": "012",
      "activated_at": "...",
      "enrolled_count": 22,
      "flag_count": 9,
      "high_flag_count": 5,
      "deviation_score": 70.0
    }
  ],
  "flag_counts": { "CRITICAL": 0, "HIGH": 13, "MEDIUM": 11, "LOW": 0, "TOTAL": 24 },
  "latest_simulation": {
    "id": "...",
    "risk_score": 47.0,
    "vulnerable_zone": "HIGH",
    "created_at": "..."
  }
}
```

---

## Documents

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/documents` | List documents (optional filters: `study_id`, `site_id`, `artifact_type`) |
| `POST` | `/api/documents/upload` | Upload and classify a TMF document (multipart form) |

### Upload Request

```
POST /api/documents/upload
Content-Type: multipart/form-data

file=<binary>
study_id=<uuid>
site_id=<uuid>   (optional — omit for study-level document)
```

### Upload Response

```json
{
  "id": "...",
  "artifact_type": "Delegation_Log",
  "filename": "delegation_log_v2.pdf",
  "has_signature": true,
  "message": "Document uploaded and classified successfully"
}
```

### Recognized Artifact Types

`FDA_1572` | `Delegation_Log` | `IRB_Approval` | `Monitoring_Visit_Report` | `SAE_Follow_Up` | `Investigator_CV` | `Protocol` | `Deviation_Log` | `Informed_Consent` | `Site_Activation` | `Other`

---

## Compute

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/compute/missing-docs?study_id=...` | Re-run compliance engine and refresh flags for a study |
| `POST` | `/api/compute/deviation-intel?study_id=...` | Re-run deviation intelligence and refresh signals |

These endpoints are called automatically by the simulation endpoint, but can also be triggered independently.

---

## Simulate

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/simulate/inspection?study_id=...` | Run a full inspection simulation |
| `GET` | `/api/simulate/simulations` | List simulations (optional filter: `study_id`) |
| `GET` | `/api/simulate/simulations/{simulation_id}` | Get a specific simulation by ID |

### Simulation Response

```json
{
  "id": "...",
  "study_id": "...",
  "risk_score": 53.0,
  "vulnerable_zone": "HIGH",
  "narrative": "Based on the current state of the TMF...",
  "results_json": {
    "total_flags": 9,
    "critical_flags": 0,
    "high_flags": 5,
    "medium_flags": 4,
    "low_flags": 0,
    "scoring_breakdown": {
      "base_score": 100,
      "flag_deduction": 37,
      "cluster_penalty": 10,
      "multi_site_deviation_penalty": 0,
      "per_site_deviation_penalty": 5,
      "total_deduction": 52
    },
    "top_flags": [
      {
        "rule_code": "TMF-001",
        "severity": "HIGH",
        "risk_points": 10,
        "category": "Regulatory Documents",
        "title": "FDA Form 1572 missing for Site 012",
        "site_id": "...",
        "site_code": "012"
      }
    ],
    "missing_artifacts": ["FDA Form 1572 missing for Site 012", "..."],
    "high_deviation_sites": ["012"],
    "site_deviation_scores": [
      {
        "site_id": "...",
        "site_code": "012",
        "score": 70.0,
        "findings": ["Blinding breach documented", "Protocol deviation noted"]
      }
    ]
  },
  "created_at": "..."
}
```

---

## Audit Questions

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/audit/questions` | Ask a bounded audit readiness question |

### Request

```json
{
  "study_id": "<uuid>",
  "question": "Which sites are highest risk?"
}
```

### Response

```json
{
  "question": "Which sites are highest risk?",
  "answer": "Sites ranked by risk:\n\n1. Site 012 — 5 high/critical flags, 9 total flags, deviation score 70\n...",
  "data_basis": ["Site 012: 9 flags (5 high/critical)", "Site 004: 9 flags (5 high/critical)"]
}
```

### Supported Question Types

The endpoint routes questions by keyword pattern. Effective question templates:

| Question | Routes To |
|----------|-----------|
| "Which sites are highest risk?" | Site risk ranking |
| "What artifacts are missing?" | Missing artifact list |
| "What should be fixed first?" | Prioritized remediation |
| "What's driving the score down?" | Scoring breakdown |
| "Tell me about Site 012" | Site-specific detail |
| "Give me an overall readiness assessment" | Summary |

The endpoint accepts free-text questions — the routing is keyword-based, not LLM-based, ensuring grounded answers even without an OpenAI key.

---

## System

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/` | Service info |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc UI |
