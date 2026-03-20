"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { api, ETMFDashboard as ETMFDashboardData, SiteRiskSummary } from "@/lib/api";
import {
  CheckCircle,
  AlertTriangle,
  Clock,
  Shield,
  FileCheck,
  ChevronRight,
  Loader2,
  XCircle,
  TrendingUp,
  Play,
  MessageSquare,
} from "lucide-react";

interface Props {
  studyId: string;
  sites?: SiteRiskSummary[];
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
      className={`inline-block w-2 h-2 rounded-full flex-shrink-0 mt-1.5 ${
        colors[severity] ?? "bg-gray-400"
      }`}
    />
  );
}

function siteRiskLevel(site: SiteRiskSummary): "HIGH" | "MEDIUM" | "LOW" {
  if (site.high_flag_count > 0) return "HIGH";
  if (site.flag_count > 0) return "MEDIUM";
  return "LOW";
}

function SiteRiskBadge({ level }: { level: "HIGH" | "MEDIUM" | "LOW" }) {
  const styles = {
    HIGH: "text-red-700 bg-red-50 border-red-200",
    MEDIUM: "text-amber-700 bg-amber-50 border-amber-200",
    LOW: "text-green-700 bg-green-50 border-green-200",
  };
  return <span className={`badge text-xs ${styles[level]}`}>{level}</span>;
}

export function ETMFDashboard({ studyId, sites }: Props) {
  const [data, setData] = useState<ETMFDashboardData | null>(null);
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
      <div className="card p-6 flex items-center gap-3 text-gray-500 mb-6">
        <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
        <span className="text-sm">Loading eTMF dashboard...</span>
      </div>
    );
  }

  if (error || !data) {
    return null;
  }

  const { completeness, timeliness, quality, risk, audit_readiness } = data;
  const pct = completeness.completeness_pct;

  // Rank sites by risk priority
  const rankedSites = sites
    ? [...sites].sort(
        (a, b) =>
          b.high_flag_count * 3 + b.flag_count -
          (a.high_flag_count * 3 + a.flag_count)
      )
    : [];

  // Missing-artifact findings derived from audit readiness
  const missingFindings = audit_readiness.top_findings
    .filter((f) => f.title.toLowerCase().includes("missing"))
    .slice(0, 3);

  return (
    <div className="mb-6">
      {/* Section header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-bold text-gray-900 flex items-center gap-2">
          <FileCheck className="w-4 h-4 text-blue-600" />
          eTMF Health Dashboard
        </h2>
        <span className="text-xs text-gray-400">
          Live · {new Date(data.as_of).toLocaleString()}
        </span>
      </div>

      {/* KPI Strip — 4 compact cards */}
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
          <p className="text-xs text-gray-500 mt-2">overdue filings</p>
          {timeliness.overdue_monitoring_reports > 0 && (
            <p className="text-xs text-amber-600 mt-1">
              {timeliness.overdue_monitoring_reports} monitoring report(s)
            </p>
          )}
          {timeliness.late_filings_count === 0 && (
            <p className="text-xs text-green-600 font-medium mt-1">All filings current</p>
          )}
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
          {quality.unsigned_documents > 0 && (
            <p className="text-xs text-red-600 mt-1">
              {quality.unsigned_documents} unsigned doc(s)
            </p>
          )}
          {quality.qc_issue_count === 0 && (
            <p className="text-xs text-green-600 font-medium mt-1">No quality issues</p>
          )}
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
                risk.readiness_score >= 80
                  ? "text-green-600"
                  : risk.readiness_score >= 60
                  ? "text-amber-500"
                  : "text-red-600"
              }`}
            >
              {risk.readiness_score.toFixed(0)}
            </p>
          ) : (
            <p className="text-3xl font-black leading-none text-gray-300">—</p>
          )}
          <p className="text-xs text-gray-500 mt-2">readiness score</p>
          {risk.open_high_flags + risk.open_critical_flags > 0 && (
            <p className="text-xs text-red-600 mt-1">
              {risk.open_critical_flags + risk.open_high_flags} high/critical flag(s)
            </p>
          )}
          {risk.highest_risk_sites.length > 0 && (
            <p className="text-xs text-gray-500 mt-0.5">
              Top risk: Site {risk.highest_risk_sites[0]}
            </p>
          )}
        </div>
      </div>

      {/* Main 2-column grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* ── LEFT COLUMN ─────────────────────────────────────────────── */}
        <div className="space-y-4">
          {/* A. Completeness Breakdown */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-blue-600" />
              Completeness Breakdown
            </h3>
            <div className="mb-3">
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>
                  {completeness.present_artifacts} of {completeness.expected_artifacts} artifacts
                  present
                </span>
                <span className={`font-bold ${pctColor(pct)}`}>{pct.toFixed(0)}%</span>
              </div>
              <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-2 rounded-full ${pctBarColor(pct)}`}
                  style={{ width: `${Math.min(pct, 100)}%` }}
                />
              </div>
            </div>
            {completeness.missing_critical_count > 0 ? (
              <div className="space-y-1.5 mb-3">
                <p className="text-xs font-semibold text-red-600">
                  {completeness.missing_critical_count} critical artifact(s) missing:
                </p>
                {missingFindings.length > 0 ? (
                  missingFindings.map((f, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs text-gray-700">
                      <span className="inline-block w-1.5 h-1.5 rounded-full bg-red-500 flex-shrink-0 mt-1.5" />
                      <span>
                        {f.title}
                        {f.site_code && (
                          <span className="text-gray-400"> · Site {f.site_code}</span>
                        )}
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="flex items-start gap-2 text-xs text-gray-700">
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-red-500 flex-shrink-0 mt-1.5" />
                    Critical artifacts require attention
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-green-600 font-medium mb-3">
                No missing artifacts detected
              </p>
            )}
            <Link
              href={`/simulate/${studyId}`}
              className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
            >
              View inspection report <ChevronRight className="w-3 h-3" />
            </Link>
          </div>

          {/* B. Timeliness */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <Clock className="w-4 h-4 text-amber-500" />
              Timeliness
            </h3>
            {timeliness.late_filings_count === 0 ? (
              <p className="text-xs text-green-600 font-medium">All documents up to date</p>
            ) : (
              <div className="space-y-2">
                {timeliness.overdue_monitoring_reports > 0 && (
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-700">Overdue monitoring reports</span>
                    <span className="badge text-amber-700 bg-amber-50 border-amber-200">
                      {timeliness.overdue_monitoring_reports} overdue
                    </span>
                  </div>
                )}
                {timeliness.stale_documents > 0 && (
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-700">Stale documents (&gt;2 years)</span>
                    <span className="badge text-amber-700 bg-amber-50 border-amber-200">
                      {timeliness.stale_documents} stale
                    </span>
                  </div>
                )}
                {timeliness.late_filings_count >
                  timeliness.overdue_monitoring_reports + timeliness.stale_documents && (
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-700">Other late filings</span>
                    <span className="badge text-red-700 bg-red-50 border-red-200">
                      {timeliness.late_filings_count -
                        timeliness.overdue_monitoring_reports -
                        timeliness.stale_documents}{" "}
                      late
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* C. Quality Issues */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <XCircle className="w-4 h-4 text-red-500" />
              Quality Issues
            </h3>
            {quality.qc_issue_count === 0 && quality.unsigned_documents === 0 ? (
              <p className="text-xs text-green-600 font-medium">No quality issues detected</p>
            ) : (
              <div className="space-y-2">
                {quality.unsigned_documents > 0 && (
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-700">Missing signatures</span>
                    <span className="badge text-red-700 bg-red-50 border-red-200">
                      {quality.unsigned_documents} unsigned
                    </span>
                  </div>
                )}
                {quality.qc_issue_count > 0 && (
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-700">QC issues flagged</span>
                    <span className="badge text-red-700 bg-red-50 border-red-200">
                      {quality.qc_issue_count} issues
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── RIGHT COLUMN ────────────────────────────────────────────── */}
        <div className="space-y-4">
          {/* D. Risk Overview */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-blue-600" />
              Risk Overview
            </h3>
            {rankedSites.length > 0 ? (
              <div className="space-y-3">
                {rankedSites.map((site, idx) => {
                  const level = siteRiskLevel(site);
                  return (
                    <div key={site.id} className="flex items-center gap-3 text-sm">
                      <span className="text-gray-400 text-xs w-5 text-right flex-shrink-0">
                        {idx + 1}.
                      </span>
                      <span className="font-semibold text-gray-900 flex-1">
                        Site {site.site_code}
                      </span>
                      <SiteRiskBadge level={level} />
                      <span className="text-xs text-gray-500">
                        {site.flag_count} flag{site.flag_count !== 1 ? "s" : ""}
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : risk.highest_risk_sites.length > 0 ? (
              <div className="space-y-3">
                {risk.highest_risk_sites.slice(0, 3).map((siteCode, idx) => (
                  <div key={siteCode} className="flex items-center gap-3 text-sm">
                    <span className="text-gray-400 text-xs w-5 text-right flex-shrink-0">
                      {idx + 1}.
                    </span>
                    <span className="font-semibold text-gray-900 flex-1">
                      Site {siteCode}
                    </span>
                    <SiteRiskBadge
                      level={idx === 0 ? "HIGH" : idx === 1 ? "MEDIUM" : "LOW"}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-green-600 font-medium">No high-risk sites detected</p>
            )}
          </div>

          {/* E. Audit Readiness */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              Audit Readiness
            </h3>

            {/* Top Findings */}
            <div className="mb-4">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                Top Likely Findings
              </p>
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
            <div className="mb-4">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                Recommended Actions
              </p>
              {audit_readiness.recommended_actions.length === 0 ? (
                <p className="text-xs text-green-600 font-medium">No urgent actions required</p>
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
            </div>

            {/* CTA Buttons */}
            <div className="flex flex-wrap gap-2 pt-3 border-t border-gray-100">
              <Link href={`/simulate/${studyId}`} className="btn-primary text-xs py-1.5 px-3">
                <Play className="w-3.5 h-3.5" />
                Run Simulation
              </Link>
              <a href="#audit-copilot" className="btn-secondary text-xs py-1.5 px-3">
                <MessageSquare className="w-3.5 h-3.5" />
                Ask Audit Copilot
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
