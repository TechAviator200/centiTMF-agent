export const dynamic = "force-dynamic";

import Link from "next/link";
import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { formatDate, deviationScoreColor } from "@/lib/utils";
import { FlagTable } from "@/app/components/FlagTable";
import { StatCard } from "@/app/components/StatCard";
import { AlertTriangle, Users, FileText, ChevronRight, TrendingUp } from "lucide-react";

async function getSiteData(studyId: string, siteId: string) {
  try {
    const [site, documents] = await Promise.all([
      api.getSite(studyId, siteId),
      api.getDocuments({ study_id: studyId, site_id: siteId }),
    ]);
    return { site, documents, error: null };
  } catch (e: any) {
    return { site: null, documents: [], error: e.message };
  }
}

export default async function SitePage({
  params,
}: {
  params: { studyId: string; siteId: string };
}) {
  const { site, documents, error } = await getSiteData(params.studyId, params.siteId);

  if (!site) {
    if (error?.includes("404")) notFound();
    return (
      <div className="card p-8 text-center text-gray-500">
        <p>Error loading site: {error}</p>
      </div>
    );
  }

  const criticalHighFlags = site.compliance_flags.filter(
    (f) => f.severity === "CRITICAL" || f.severity === "HIGH" ||
           f.risk_level === "CRITICAL" || f.risk_level === "HIGH"
  );
  const medFlags = site.compliance_flags.filter(
    (f) => f.severity === "MEDIUM" || f.risk_level === "MEDIUM"
  );

  return (
    <div>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-500 mb-6 flex-wrap">
        <Link href="/" className="hover:text-gray-900">Studies</Link>
        <ChevronRight className="w-4 h-4" />
        <Link href={`/studies/${params.studyId}`} className="hover:text-gray-900">
          Study
        </Link>
        <ChevronRight className="w-4 h-4" />
        <span className="font-semibold text-gray-900">Site {site.site_code}</span>
      </div>

      {/* Site Header */}
      <div className="flex flex-wrap items-start justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-3xl font-black text-gray-900">Site {site.site_code}</h1>
            <span className={`badge ${site.activated_at ? "text-green-700 bg-green-50 border-green-200" : "text-gray-500 bg-gray-50 border-gray-200"}`}>
              {site.activated_at ? "Active" : "Inactive"}
            </span>
          </div>
          <div className="flex gap-4 text-sm text-gray-500">
            <span>Activated: {formatDate(site.activated_at)}</span>
            <span>IRB: {formatDate(site.irb_approved_at)}</span>
            <span>FPI: {formatDate(site.fpi_at)}</span>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Enrolled"
          value={site.enrolled_count}
          sub="subjects"
          icon={<Users className="w-5 h-5" />}
          accent="blue"
        />
        <StatCard
          label="Critical / High"
          value={criticalHighFlags.length}
          sub="severity flags"
          icon={<AlertTriangle className="w-5 h-5" />}
          accent="red"
        />
        <StatCard
          label="Medium Flags"
          value={medFlags.length}
          icon={<AlertTriangle className="w-5 h-5" />}
          accent="amber"
        />
        <StatCard
          label="Documents"
          value={documents.length}
          sub="on file"
          icon={<FileText className="w-5 h-5" />}
          accent="green"
        />
      </div>

      {/* Deviation Score */}
      {site.deviation_score !== null && (
        <div className="card p-6 mb-8">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-blue-600" />
            <h2 className="font-bold text-gray-900">Deviation Intelligence</h2>
          </div>
          <div className="flex items-center gap-8">
            <div>
              <p className="text-xs text-gray-500 mb-1">Deviation Risk Score</p>
              <p className={`text-5xl font-black ${deviationScoreColor(site.deviation_score)}`}>
                {site.deviation_score.toFixed(1)}
                <span className="text-lg text-gray-400">/100</span>
              </p>
              <p className="text-xs text-gray-400 mt-1">Higher = more deviation risk</p>
            </div>
            {site.deviation_findings.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                  Top Findings
                </p>
                <ul className="space-y-1.5">
                  {site.deviation_findings.map((f, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                      <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Compliance Flags */}
      <div className="card mb-8">
        <div className="flex items-center justify-between p-5 border-b border-gray-100">
          <h2 className="font-bold text-gray-900">Compliance Flags</h2>
          <div className="flex gap-2">
            <span className="badge text-red-700 bg-red-50 border-red-200">{criticalHighFlags.length} HIGH+</span>
            <span className="badge text-amber-700 bg-amber-50 border-amber-200">{medFlags.length} MEDIUM</span>
          </div>
        </div>
        <FlagTable flags={site.compliance_flags} />
      </div>

      {/* Documents on file */}
      <div className="card">
        <div className="flex items-center justify-between p-5 border-b border-gray-100">
          <h2 className="font-bold text-gray-900">Documents on File</h2>
          <span className="text-sm text-gray-400">{documents.length} files</span>
        </div>
        {documents.length === 0 ? (
          <div className="p-8 text-center text-gray-400">
            <FileText className="w-8 h-8 mx-auto mb-2" />
            <p className="text-sm">No documents on file for this site</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  {["Filename", "Artifact Type", "Signature", "Uploaded"].map((h) => (
                    <th key={h} className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-3 px-4 font-medium text-gray-900">{doc.filename}</td>
                    <td className="py-3 px-4">
                      <span className="badge text-blue-700 bg-blue-50 border-blue-200">
                        {doc.artifact_type.replace(/_/g, " ")}
                      </span>
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
                    <td className="py-3 px-4 text-gray-500 text-xs">{formatDate(doc.uploaded_at)}</td>
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
