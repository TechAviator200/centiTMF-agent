"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { api, ETMFDashboard } from "@/lib/api";
import {
  CheckCircle,
  AlertTriangle,
  Clock,
  Shield,
  FileCheck,
  ChevronRight,
  Loader2,
  XCircle,
} from "lucide-react";

interface Props {
  studyId: string;
}

function pctColor(pct: number): string {
  if (pct >= 85) return "text-green-600";
  if (pct >= 60) return "text-amber-500";
  return "text-red-600";
}

function pctBarColor(pct: number): string {
  if (pct >= 85) return "bg-green-500";
  if (pct >= 60) return "bg-amber-400";
  return "bg-red-500";
}

function severityDot(severity: string) {
  const colors: Record<string, string> = {
    CRITICAL: "bg-purple-500",
    HIGH: "bg-red-500",
    MEDIUM: "bg-amber-400",
    LOW: "bg-gray-400",
  };
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full flex-shrink-0 mt-1.5 ${colors[severity] ?? "bg-gray-400"}`}
    />
  );
}

export function ETMFDashboard({ studyId }: Props) {
  const [data, setData] = useState<ETMFDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getETMFDashboard(studyId)
      .then(setData)
      .catch((e) => setError(e.message || "Failed to load eTMF dashboard"))
      .finally(() => setLoading(false));
  }, [studyId]);

  if (loading) {
    return (
      <div className="card p-6 flex items-center gap-3 text-gray-500">
        <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
        <span className="text-sm">Loading eTMF dashboard...</span>
      </div>
    );
  }

  if (error || !data) {
    return null; // silent fail — dashboard is additive, not critical
  }

  const { completeness, timeliness, quality, risk, audit_readiness } = data;
  const pct = completeness.completeness_pct;

  return (
    <div className="mb-6">
      {/* Section header */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-bold text-gray-900 flex items-center gap-2">
          <FileCheck className="w-4 h-4 text-blue-600" />
          eTMF Health Dashboard
        </h2>
        <span className="text-xs text-gray-400">
          Live · {new Date(data.as_of).toLocaleString()}
        </span>
      </div>

      {/* 4-column metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        {/* Completeness */}
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="w-4 h-4 text-blue-600" />
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Completeness
            </span>
          </div>
          <p className={`text-3xl font-black leading-none ${pctColor(pct)}`}>
            {pct.toFixed(0)}%
          </p>
          <div className="w-full h-1.5 bg-gray-100 rounded-full mt-2 overflow-hidden">
            <div
              className={`h-1.5 rounded-full ${pctBarColor(pct)}`}
              style={{ width: `${Math.min(pct, 100)}%` }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-1.5">
            {completeness.present_artifacts}/{completeness.expected_artifacts} artifacts
          </p>
          {completeness.missing_critical_count > 0 && (
            <p className="text-xs text-red-600 font-medium mt-0.5">
              {completeness.missing_critical_count} critical missing
            </p>
          )}
        </div>

        {/* Timeliness */}
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-amber-500" />
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Timeliness
            </span>
          </div>
          <p
            className={`text-3xl font-black leading-none ${
              timeliness.late_filings_count > 0 ? "text-amber-500" : "text-green-600"
            }`}
          >
            {timeliness.late_filings_count}
          </p>
          <p className="text-xs text-gray-500 mt-2">late / overdue filings</p>
          <div className="mt-1.5 space-y-0.5">
            {timeliness.overdue_monitoring_reports > 0 && (
              <p className="text-xs text-amber-600">
                {timeliness.overdue_monitoring_reports} overdue monitoring report(s)
              </p>
            )}
            {timeliness.stale_documents > 0 && (
              <p className="text-xs text-amber-600">
                {timeliness.stale_documents} stale document(s)
              </p>
            )}
            {timeliness.late_filings_count === 0 && (
              <p className="text-xs text-green-600 font-medium">All filings current</p>
            )}
          </div>
        </div>

        {/* Quality */}
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-2">
            <XCircle className="w-4 h-4 text-red-500" />
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Quality
            </span>
          </div>
          <p
            className={`text-3xl font-black leading-none ${
              quality.qc_issue_count > 0 ? "text-red-600" : "text-green-600"
            }`}
          >
            {quality.qc_issue_count}
          </p>
          <p className="text-xs text-gray-500 mt-2">QC issues</p>
          <div className="mt-1.5 space-y-0.5">
            {quality.unsigned_documents > 0 && (
              <p className="text-xs text-red-600">
                {quality.unsigned_documents} unsigned document(s)
              </p>
            )}
            {quality.qc_issue_count === 0 && (
              <p className="text-xs text-green-600 font-medium">No quality issues</p>
            )}
          </div>
        </div>

        {/* Risk */}
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-2">
            <Shield className="w-4 h-4 text-blue-600" />
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Risk
            </span>
          </div>
          {risk.readiness_score !== null ? (
            <p
              className={`text-3xl font-black leading-none ${
                risk.readiness_score >= 60 ? "text-green-600" : "text-red-600"
              }`}
            >
              {risk.readiness_score.toFixed(0)}
            </p>
          ) : (
            <p className="text-3xl font-black leading-none text-gray-300">—</p>
          )}
          <p className="text-xs text-gray-500 mt-2">readiness score</p>
          <div className="mt-1.5 space-y-0.5">
            {risk.open_high_flags + risk.open_critical_flags > 0 && (
              <p className="text-xs text-red-600">
                {risk.open_critical_flags + risk.open_high_flags} high/critical flag(s)
              </p>
            )}
            {risk.highest_risk_sites.length > 0 && (
              <p className="text-xs text-gray-500">
                Top risk: Site {risk.highest_risk_sites[0]}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Audit Readiness panel */}
      <div className="card p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Top Findings */}
          <div>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
              Top Likely Findings
            </h3>
            {audit_readiness.top_findings.length === 0 ? (
              <p className="text-xs text-green-600 font-medium">No critical findings</p>
            ) : (
              <ul className="space-y-1.5">
                {audit_readiness.top_findings.slice(0, 4).map((f, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-gray-700">
                    {severityDot(f.severity)}
                    <span>
                      {f.title}
                      {f.site_code && (
                        <span className="text-gray-400"> · Site {f.site_code}</span>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Recommended Actions */}
          <div>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <ChevronRight className="w-3.5 h-3.5 text-blue-600" />
              Recommended Actions
            </h3>
            {audit_readiness.recommended_actions.length === 0 ? (
              <p className="text-xs text-green-600 font-medium">
                No urgent actions required
              </p>
            ) : (
              <ul className="space-y-1.5">
                {audit_readiness.recommended_actions.slice(0, 4).map((action, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-gray-700">
                    <span className="text-blue-600 font-bold flex-shrink-0">{i + 1}.</span>
                    {action}
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-3 flex gap-2">
              <Link
                href={`/simulate/${studyId}`}
                className="text-xs text-blue-600 font-medium hover:underline flex items-center gap-1"
              >
                Run Simulation <ChevronRight className="w-3 h-3" />
              </Link>
              <Link
                href="/upload"
                className="text-xs text-gray-500 hover:underline flex items-center gap-1"
              >
                Upload Documents <ChevronRight className="w-3 h-3" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
