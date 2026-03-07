"use client";

import { useState, useRef } from "react";
import { api, Study, Site } from "@/lib/api";
import { useEffect } from "react";
import { Upload, FileText, CheckCircle, XCircle, Loader2 } from "lucide-react";

type Status = "idle" | "uploading" | "success" | "error";

export default function UploadPage() {
  const [studies, setStudies] = useState<Study[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [studyId, setStudyId] = useState("");
  const [siteId, setSiteId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<{ artifact_type: string; message: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.getStudies().then(setStudies).catch(() => {});
  }, []);

  useEffect(() => {
    if (!studyId) {
      setSites([]);
      setSiteId("");
      return;
    }
    api.getSites(studyId)
      .then(setSites)
      .catch(() => setSites([]));
    setSiteId("");
  }, [studyId]);

  const handleFile = (f: File) => {
    setFile(f);
    setStatus("idle");
    setResult(null);
    setError(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !studyId) return;

    setStatus("uploading");
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("study_id", studyId);
    if (siteId) formData.append("site_id", siteId);

    try {
      const res = await api.uploadDocument(formData);
      setResult({ artifact_type: res.artifact_type, message: res.message });
      setStatus("success");
    } catch (err: any) {
      setError(err.message || "Upload failed");
      setStatus("error");
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-black text-gray-900 mb-2">Upload Document</h1>
        <p className="text-gray-500 text-sm">
          Upload PDF or TXT TMF artifacts. The system will auto-classify the artifact type,
          store it in S3, and generate embeddings.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Study Select */}
        <div className="card p-5">
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Study <span className="text-red-500">*</span>
          </label>
          <select
            value={studyId}
            onChange={(e) => setStudyId(e.target.value)}
            required
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select a study...</option>
            {studies.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} {s.phase ? `(${s.phase})` : ""}
              </option>
            ))}
          </select>
        </div>

        {/* Site Select (optional) */}
        <div className="card p-5">
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Site <span className="text-gray-400 font-normal">(optional — leave blank for study-level document)</span>
          </label>
          <select
            value={siteId}
            onChange={(e) => setSiteId(e.target.value)}
            disabled={!studyId || sites.length === 0}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
          >
            <option value="">Study-level document (no site)</option>
            {sites.map((s) => (
              <option key={s.id} value={s.id}>
                Site {s.site_code}
                {s.activated_at ? "" : " (inactive)"}
              </option>
            ))}
          </select>
          {studyId && sites.length === 0 && (
            <p className="text-xs text-gray-400 mt-1.5">No sites found for this study.</p>
          )}
        </div>

        {/* File Drop Zone */}
        <div
          className={`card p-8 text-center cursor-pointer transition-all border-2 border-dashed ${
            dragging
              ? "border-blue-400 bg-blue-50"
              : file
              ? "border-green-300 bg-green-50"
              : "border-gray-200 hover:border-blue-300 hover:bg-blue-50"
          }`}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.docx"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
          {file ? (
            <div className="flex flex-col items-center gap-2">
              <FileText className="w-10 h-10 text-green-500" />
              <p className="font-semibold text-gray-900">{file.name}</p>
              <p className="text-xs text-gray-500">{(file.size / 1024).toFixed(1)} KB</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 text-gray-400">
              <Upload className="w-10 h-10" />
              <p className="font-semibold text-gray-600">Drop a file here or click to browse</p>
              <p className="text-xs">PDF, TXT, DOCX — max 50MB</p>
            </div>
          )}
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={!file || !studyId || status === "uploading"}
          className="btn-primary w-full justify-center py-3"
        >
          {status === "uploading" ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <Upload className="w-4 h-4" />
              Upload & Classify
            </>
          )}
        </button>

        {/* Result */}
        {status === "success" && result && (
          <div className="card p-5 border-green-200 bg-green-50">
            <div className="flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-green-800">Upload successful</p>
                <p className="text-sm text-green-700 mt-1">{result.message}</p>
                <div className="mt-2">
                  <span className="badge text-blue-700 bg-blue-100 border-blue-200">
                    Classified: {result.artifact_type.replace(/_/g, " ")}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {status === "error" && error && (
          <div className="card p-5 border-red-200 bg-red-50">
            <div className="flex items-start gap-3">
              <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-red-800">Upload failed</p>
                <p className="text-sm text-red-700 mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}
      </form>

      {/* Artifact Type Reference */}
      <div className="card p-5 mt-6">
        <h3 className="text-sm font-bold text-gray-700 mb-3">Recognized Artifact Types</h3>
        <div className="flex flex-wrap gap-2">
          {[
            "FDA 1572", "Delegation Log", "IRB Approval", "Monitoring Visit Report",
            "SAE Follow Up", "Investigator CV", "Protocol", "Deviation Log",
            "Informed Consent", "Site Activation"
          ].map((t) => (
            <span key={t} className="badge text-gray-600 bg-gray-50 border-gray-200 text-xs">
              {t}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
