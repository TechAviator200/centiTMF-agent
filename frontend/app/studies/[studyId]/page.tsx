export const dynamic = "force-dynamic";

import Link from "next/link";
import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import {
  formatDate,
  readinessScoreColor,
  readinessScoreBarColor,
  readinessZoneColor,
  readinessZoneLabel,
  riskColor,
  deviationScoreColor,
} from "@/lib/utils";
import { StatCard } from "@/app/components/StatCard";
import { RiskBadge } from "@/app/components/RiskBadge";
import { AuditCopilot } from "@/app/components/AuditCopilot";
import { AlertTriangle, Users, FileText, Play, ChevronRight, TrendingUp, ShieldCheck, ShieldAlert } from "lucide-react";

async function getStudyData(studyId: string) {
  try {
    const [study, documents] = await Promise.all([
      api.getStudy(studyId),
      api.getDocuments({ study_id: studyId }),
    ]);
    return { study, documents, error: null };
  } catch (e: any) {
    return { study: null, documents: [], error: e.message };
  }
}

export default async function StudyPage({
  params,
}: {
  params: { studyId: string };
}) {
  const { study, documents, error } = await getStudyData(params.studyId);

  if (!study) {
    if (error?.includes("404")) notFound();
    return (
      <div className="card p-8 text-center text-gray-500">
        <p>Error loading study: {error}</p>
        <p className="text-sm text-gray-400 mt-2">
          The backend may still be starting up — refresh in a moment.
        </p>
      </div>
    );
  }

  const latestSim = study.latest_simulation;
  const readinessScore = latestSim?.risk_score ?? null;

  return (
    <div>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-500 mb-6">
        <Link href="/" className="hover:text-gray-900">Studies</Link>
        <ChevronRight className="w-4 h-4" />
        <span className="font-semibold text-gray-900">{study.name}</span>
      </div>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-3xl font-black text-gray-900">{study.name}</h1>
            {study.phase && (
              <span className="badge text-blue-700 bg-blue-50 border-blue-200">
                {study.phase}
              </span>
            )}
          </div>
          <p className="text-gray-500">
            {study.sponsor || "No sponsor"} · Created {formatDate(study.created_at)}
          </p>
        </div>
        <Link href={`/simulate/${study.id}`} className="btn-primary">
          <Play className="w-4 h-4" />
          Simulate FDA Inspection
        </Link>
      </div>

      {/* ── INSPECTION READINESS — primary metric ─────────────────────── */}
      <div className="card p-6 mb-6">
        <div className="flex items-center gap-2 mb-5">
          {readinessScore !== null && readinessScore >= 60 ? (
            <ShieldCheck className="w-5 h-5 text-green-500" />
          ) : (
            <ShieldAlert className="w-5 h-5 text-red-500" />
          )}
          <h2 className="font-bold text-gray-900">Inspection Readiness Score</h2>
          {latestSim && (
            <span className="text-xs text-gray-400 ml-auto">
              Last simulated {formatDate(latestSim.created_at)}
            </span>
          )}
        </div>

        {readinessScore !== null ? (
          <div className="flex flex-wrap items-center gap-8">
            {/* Score */}
            <div className="flex flex-col items-center">
              <p className={`text-6xl font-black leading-none ${readinessScoreColor(readinessScore)}`}>
                {readinessScore.toFixed(0)}
              </p>
              <p className="text-sm text-gray-400 mt-1">out of 100</p>
            </div>

            {/* Bar */}
            <div className="flex-1 min-w-[200px]">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs text-gray-500">Risk zone</span>
                <span className={`badge text-xs font-bold ${readinessZoneColor(latestSim?.vulnerable_zone)}`}>
                  {readinessZoneLabel(latestSim?.vulnerable_zone)}
                </span>
              </div>
              <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-3 rounded-full transition-all ${readinessScoreBarColor(readinessScore)}`}
                  style={{ width: `${readinessScore}%` }}
                />
              </div>
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>0 Critical</span>
                <span>100 Ready</span>
              </div>
            </div>

            {/* Flag summary */}
            <div className="flex gap-5 text-center">
              {study.flag_counts.CRITICAL > 0 && (
                <div>
                  <p className="text-2xl font-black text-purple-600">{study.flag_counts.CRITICAL}</p>
                  <p className="text-xs text-gray-500">Critical</p>
                </div>
              )}
              <div>
                <p className="text-2xl font-black text-red-600">{study.flag_counts.HIGH}</p>
                <p className="text-xs text-gray-500">High</p>
              </div>
              <div>
                <p className="text-2xl font-black text-amber-500">{study.flag_counts.MEDIUM}</p>
                <p className="text-xs text-gray-500">Medium</p>
              </div>
              <div>
                <p className="text-2xl font-black text-gray-400">{study.flag_counts.TOTAL}</p>
                <p className="text-xs text-gray-500">Total</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-4 py-4">
            <div className="text-center">
              <p className="text-4xl font-black text-gray-300">—</p>
              <p className="text-xs text-gray-400 mt-1">No simulation yet</p>
            </div>
            <div className="flex-1">
              <p className="text-sm text-gray-500 mb-3">
                Run an inspection simulation to generate a readiness score.
                {study.flag_counts.TOTAL > 0 && (
                  <span className="text-red-600 font-medium">
                    {" "}{study.flag_counts.TOTAL} compliance flags detected.
                  </span>
                )}
              </p>
              <Link href={`/simulate/${study.id}`} className="btn-primary inline-flex">
                <Play className="w-4 h-4" /> Run Simulation
              </Link>
            </div>
          </div>
        )}

        {latestSim && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <Link href={`/simulate/${study.id}`} className="btn-secondary text-xs">
              View Full Inspection Report
            </Link>
          </div>
        )}
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Active Sites"
          value={study.sites.filter((s) => s.activated_at).length}
          sub={`of ${study.sites.length} total`}
          icon={<Users className="w-5 h-5" />}
          accent="blue"
        />
        <StatCard
          label="High Risk Flags"
          value={(study.flag_counts.CRITICAL || 0) + (study.flag_counts.HIGH || 0)}
          sub="critical + high severity"
          icon={<AlertTriangle className="w-5 h-5" />}
          accent="red"
        />
        <StatCard
          label="Medium Flags"
          value={study.flag_counts.MEDIUM || 0}
          icon={<AlertTriangle className="w-5 h-5" />}
          accent="amber"
        />
        <StatCard
          label="Documents"
          value={documents.length}
          sub="TMF artifacts on file"
          icon={<FileText className="w-5 h-5" />}
          accent="green"
        />
      </div>

      {/* Site Risk Table */}
      <div className="card mb-6">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h2 className="font-bold text-gray-900">Site Risk Overview</h2>
          <span className="text-sm text-gray-400">{study.sites.length} sites</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                {[
                  "Site",
                  "Status",
                  "Enrolled",
                  "Total Flags",
                  "High/Critical",
                  "Deviation Score",
                  "",
                ].map((h) => (
                  <th
                    key={h}
                    className="text-left py-2.5 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {study.sites
                .sort((a, b) => (b.high_flag_count + b.flag_count) - (a.high_flag_count + a.flag_count))
                .map((site) => (
                <tr
                  key={site.id}
                  className="border-b border-gray-50 hover:bg-gray-50 transition-colors"
                >
                  <td className="py-3 px-4 font-bold text-gray-900">
                    Site {site.site_code}
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`badge text-xs ${
                        site.activated_at
                          ? "text-green-700 bg-green-50 border-green-200"
                          : "text-gray-500 bg-gray-50 border-gray-200"
                      }`}
                    >
                      {site.activated_at ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-medium text-gray-900">
                    {site.enrolled_count}
                  </td>
                  <td className="py-3 px-4">
                    {site.flag_count > 0 ? (
                      <span className="font-semibold text-gray-900">{site.flag_count}</span>
                    ) : (
                      <span className="text-green-600 font-medium">✓ 0</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    {site.high_flag_count > 0 ? (
                      <span className="badge text-red-700 bg-red-50 border-red-200">
                        {site.high_flag_count}
                      </span>
                    ) : (
                      <span className="text-green-600 text-xs font-medium">0</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    {site.deviation_score !== null ? (
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-gray-100 rounded-full h-1.5">
                          <div
                            className={`h-1.5 rounded-full ${
                              (site.deviation_score || 0) >= 60
                                ? "bg-red-500"
                                : (site.deviation_score || 0) >= 35
                                ? "bg-amber-400"
                                : "bg-green-400"
                            }`}
                            style={{ width: `${site.deviation_score}%` }}
                          />
                        </div>
                        <span
                          className={`text-sm font-semibold ${deviationScoreColor(site.deviation_score || 0)}`}
                        >
                          {(site.deviation_score || 0).toFixed(0)}
                        </span>
                      </div>
                    ) : (
                      <span className="text-gray-400 text-xs">—</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <Link
                      href={`/studies/${study.id}/sites/${site.id}`}
                      className="text-blue-600 hover:text-blue-800 text-xs font-medium flex items-center gap-1"
                    >
                      Details <ChevronRight className="w-3 h-3" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Audit Questions */}
      <div className="mb-6">
        <AuditCopilot studyId={study.id} />
      </div>

      {/* Recent Documents */}
      <div className="card">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h2 className="font-bold text-gray-900">TMF Documents</h2>
          <Link href="/upload" className="btn-secondary text-xs">
            Upload Document
          </Link>
        </div>
        {documents.length === 0 ? (
          <div className="p-10 text-center text-gray-400">
            <FileText className="w-8 h-8 mx-auto mb-2" />
            <p className="text-sm">No documents on file</p>
            <Link href="/upload" className="btn-primary mt-4 inline-flex text-sm">
              Upload First Document
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  {["Filename", "Artifact Type", "Site", "Signature", "Uploaded"].map(
                    (h) => (
                      <th
                        key={h}
                        className="text-left py-2.5 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider"
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {documents.slice(0, 12).map((doc) => (
                  <tr key={doc.id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-3 px-4 font-medium text-gray-900 max-w-xs truncate">
                      {doc.filename}
                    </td>
                    <td className="py-3 px-4">
                      <span className="badge text-blue-700 bg-blue-50 border-blue-200 text-xs">
                        {doc.artifact_type.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-500 text-xs">
                      {doc.site_id ? "Site" : "Study"}
                    </td>
                    <td className="py-3 px-4">
                      {doc.has_signature === true ? (
                        <span className="text-green-600 text-xs font-medium">✓ Signed</span>
                      ) : doc.has_signature === false ? (
                        <span className="text-red-500 text-xs font-medium">✗ Unsigned</span>
                      ) : (
                        <span className="text-gray-400 text-xs">—</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-gray-500 text-xs">
                      {formatDate(doc.uploaded_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
