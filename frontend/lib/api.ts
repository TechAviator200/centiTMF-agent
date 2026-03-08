// Server-side fetches (Next.js RSC) go directly to the backend container.
// Client-side fetches use NEXT_PUBLIC_API_URL (public env var, resolves to localhost in browser).
const API_BASE =
  typeof window === "undefined"
    ? process.env.INTERNAL_API_URL || "http://backend:8000"
    : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Study {
  id: string;
  name: string;
  phase: string | null;
  sponsor: string | null;
  created_at: string;
}

export interface SiteRiskSummary {
  id: string;
  study_id: string;
  site_code: string;
  activated_at: string | null;
  irb_approved_at: string | null;
  fpi_at: string | null;
  enrolled_count: number;
  flag_count: number;
  high_flag_count: number;
  deviation_score: number | null;
}

export interface Site {
  id: string;
  study_id: string;
  site_code: string;
  activated_at: string | null;
  irb_approved_at: string | null;
  fpi_at: string | null;
  enrolled_count: number;
}

export interface StudyDetail extends Study {
  sites: SiteRiskSummary[];
  flag_counts: {
    CRITICAL: number;
    HIGH: number;
    MEDIUM: number;
    LOW: number;
    TOTAL: number;
  };
  latest_simulation: {
    id: string;
    risk_score: number;
    vulnerable_zone: string | null;
    created_at: string;
  } | null;
}

export interface ComplianceFlag {
  id: string;
  study_id: string;
  site_id: string | null;
  rule_code: string;
  category: string | null;
  severity: string;
  risk_level: string;
  risk_points: number;
  title: string;
  details: string | null;
  created_at: string;
}

export interface SiteDetail extends Site {
  compliance_flags: ComplianceFlag[];
  deviation_score: number | null;
  deviation_findings: string[];
}

export interface Document {
  id: string;
  study_id: string;
  site_id: string | null;
  artifact_type: string;
  detected_artifact_type: string | null;
  classification_overridden: boolean;
  filename: string;
  s3_key: string;
  uploaded_at: string;
  doc_date: string | null;
  text_excerpt: string | null;
  has_signature: boolean | null;
}

export interface UploadResult {
  document: Document;
  artifact_type: string;
  detected_artifact_type: string;
  confidence: string;
  has_signature: boolean | null;
  message: string;
}

export interface ETMFDashboard {
  study_id: string;
  as_of: string;
  completeness: {
    expected_artifacts: number;
    present_artifacts: number;
    completeness_pct: number;
    missing_critical_count: number;
  };
  timeliness: {
    overdue_monitoring_reports: number;
    stale_documents: number;
    late_filings_count: number;
  };
  quality: {
    unsigned_documents: number;
    qc_issue_count: number;
  };
  risk: {
    readiness_score: number | null;
    highest_risk_sites: string[];
    open_critical_flags: number;
    open_high_flags: number;
  };
  audit_readiness: {
    top_findings: Array<{
      rule_code: string;
      title: string;
      severity: string;
      site_code: string | null;
      risk_points: number;
    }>;
    recommended_actions: string[];
  };
}

export interface AuditAnswer {
  question: string;
  answer: string;
  data_basis: string[];
}

export interface SimulationResult {
  id: string;
  study_id: string;
  risk_score: number;
  vulnerable_zone: string | null;
  results_json: {
    risk_score: number;
    total_flags: number;
    critical_flags: number;
    high_flags: number;
    medium_flags: number;
    low_flags: number;
    scoring_breakdown: {
      base_score: number;
      flag_deduction: number;
      cluster_penalty: number;
      multi_site_deviation_penalty: number;
      per_site_deviation_penalty: number;
      total_deduction: number;
    };
    top_flags: Array<{
      rule_code: string;
      severity: string;
      risk_level: string;
      risk_points: number;
      category: string | null;
      title: string;
      site_id: string | null;
      site_code: string;
    }>;
    missing_artifacts: string[];
    high_deviation_sites: string[];
    site_deviation_scores: Array<{
      site_id: string;
      site_code: string;
      score: number;
      findings: string[];
    }>;
  } | null;
  narrative: string | null;
  created_at: string;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status} — ${path}: ${body.slice(0, 200)}`);
  }
  return res.json();
}

export const api = {
  // Studies
  getStudies: () => apiFetch<Study[]>("/api/studies"),
  getStudy: (studyId: string) => apiFetch<StudyDetail>(`/api/studies/${studyId}`),
  getSites: (studyId: string) => apiFetch<Site[]>(`/api/studies/${studyId}/sites`),
  getSite: (studyId: string, siteId: string) =>
    apiFetch<SiteDetail>(`/api/studies/${studyId}/sites/${siteId}`),

  // Documents
  getDocuments: (params?: {
    study_id?: string;
    site_id?: string;
    artifact_type?: string;
  }) => {
    const qs = params
      ? "?" +
        new URLSearchParams(
          Object.fromEntries(
            Object.entries(params).filter(([, v]) => v != null) as [string, string][]
          )
        ).toString()
      : "";
    return apiFetch<Document[]>(`/api/documents${qs}`);
  },
  uploadDocument: (formData: FormData) =>
    fetch(`${API_BASE}/api/documents/upload`, {
      method: "POST",
      body: formData,
    }).then((r) => {
      if (!r.ok) return r.text().then((t) => { throw new Error(t); });
      return r.json() as Promise<UploadResult>;
    }),

  updateClassification: (
    documentId: string,
    artifactType: string,
    overrideReason?: string
  ) =>
    apiFetch<Document>(`/api/documents/${documentId}/classification`, {
      method: "PATCH",
      body: JSON.stringify({ artifact_type: artifactType, override_reason: overrideReason }),
    }),

  getArtifactTypes: () =>
    apiFetch<{ artifact_types: string[] }>("/api/documents/artifact-types/list"),

  // Compute
  computeMissingDocs: (studyId: string) =>
    apiFetch(`/api/compute/missing-docs?study_id=${studyId}`, { method: "POST" }),
  computeDeviationIntel: (studyId: string) =>
    apiFetch(`/api/compute/deviation-intel?study_id=${studyId}`, { method: "POST" }),

  // Simulate
  simulateInspection: (studyId: string) =>
    apiFetch<SimulationResult>(`/api/simulate/inspection?study_id=${studyId}`, {
      method: "POST",
    }),
  getSimulations: (studyId?: string) => {
    const qs = studyId ? `?study_id=${studyId}` : "";
    return apiFetch<SimulationResult[]>(`/api/simulate/simulations${qs}`);
  },

  // eTMF Dashboard
  getETMFDashboard: (studyId: string) =>
    apiFetch<ETMFDashboard>(`/api/etmf/studies/${studyId}/dashboard`),

  // Audit Questions
  askAuditQuestion: (studyId: string, question: string) =>
    apiFetch<AuditAnswer>("/api/audit/questions", {
      method: "POST",
      body: JSON.stringify({ study_id: studyId, question }),
    }),
};
