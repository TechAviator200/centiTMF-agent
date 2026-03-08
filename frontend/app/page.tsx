export const dynamic = "force-dynamic";

import Link from "next/link";
import { api, Study } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { FileText, ChevronRight, Activity, Shield, Play } from "lucide-react";

async function getStudies(): Promise<Study[]> {
  try {
    return await api.getStudies();
  } catch {
    return [];
  }
}

export default async function HomePage() {
  const studies = await getStudies();

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-3">
          <div className="flex items-center justify-center w-10 h-10 bg-blue-600 rounded-xl">
            <Shield className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-black text-gray-900">
              <span className="text-gray-900">centi</span>
              <span className="text-blue-600">TMF</span>
            </h1>
            <p className="text-sm text-gray-500">Inspection Readiness AI Agent</p>
          </div>
        </div>
        <p className="text-gray-600 max-w-2xl">
          AI-powered Trial Master File analysis. Predict regulatory inspection risk,
          detect missing artifacts, and identify protocol deviation trends across sites.
        </p>
        {/* Hero CTA */}
        <div className="mt-4 flex flex-wrap gap-3">
          {studies[0] ? (
            <Link href={`/simulate/${studies[0].id}`} className="btn-primary">
              <Play className="w-4 h-4" />
              Run Simulation
            </Link>
          ) : (
            <span className="btn-primary opacity-40 cursor-not-allowed pointer-events-none">
              <Play className="w-4 h-4" />
              Run Simulation
            </span>
          )}
          <Link href="/upload" className="btn-secondary">
            <FileText className="w-4 h-4" />
            Upload Documents
          </Link>
        </div>
      </div>

      {/* Studies List */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold text-gray-900">Clinical Studies</h2>
        <span className="text-sm text-gray-500">{studies.length} {studies.length !== 1 ? "studies" : "study"}</span>
      </div>

      {studies.length === 0 ? (
        <div className="card p-12 text-center">
          <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-500 mb-2">No studies yet</h3>
          <p className="text-sm text-gray-400 mb-6">
            The backend may still be starting up. Refresh in a moment.
          </p>
          <Link href="/upload" className="btn-primary">
            Upload a Document
          </Link>
        </div>
      ) : (
        <div className="grid gap-4">
          {studies.map((study) => (
            <Link
              key={study.id}
              href={`/studies/${study.id}`}
              className="card p-5 hover:shadow-md hover:border-blue-200 transition-all group"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="flex items-center justify-center w-10 h-10 bg-blue-50 rounded-lg">
                    <Activity className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-bold text-gray-900 group-hover:text-blue-700 transition-colors">
                        {study.name}
                      </h3>
                      {study.phase && (
                        <span className="badge text-blue-700 bg-blue-50 border-blue-200">
                          {study.phase}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-500">
                      {study.sponsor || "No sponsor"} · Added {formatDate(study.created_at)}
                    </p>
                  </div>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-blue-600 transition-colors" />
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Quick Links */}
      <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Link href="/upload" className="card p-5 hover:shadow-md hover:border-blue-200 transition-all group">
          <div className="flex items-center gap-4">
            <FileText className="w-8 h-8 text-blue-600 flex-shrink-0" />
            <div>
              <p className="font-semibold text-gray-800 group-hover:text-blue-700">Upload Documents</p>
              <p className="text-xs text-gray-500 mt-0.5">Add TMF artifacts · auto-classify · override type</p>
            </div>
          </div>
        </Link>
        <a
          href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/docs`}
          target="_blank"
          rel="noopener noreferrer"
          className="card p-5 hover:shadow-md hover:border-blue-200 transition-all group"
        >
          <div className="flex items-center gap-4">
            <Activity className="w-8 h-8 text-blue-600 flex-shrink-0" />
            <div>
              <p className="font-semibold text-gray-800 group-hover:text-blue-700">API Explorer</p>
              <p className="text-xs text-gray-500 mt-0.5">Interactive OpenAPI documentation</p>
            </div>
          </div>
        </a>
      </div>
    </div>
  );
}
