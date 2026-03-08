"use client";

import { useState, useRef, useEffect } from "react";
import { api, Study, Site, UploadResult } from "@/lib/api";
import { Upload, FileText, CheckCircle, XCircle, Loader2, Edit2, ChevronRight } from "lucide-react";

type Status = "idle" | "uploading" | "success" | "error";
type OverrideStatus = "idle" | "saving" | "saved" | "error";

const ARTIFACT_TYPES = [
  "FDA_1572",
  "Delegation_Log",
  "IRB_Approval",
  "Monitoring_Visit_Report",
  "SAE_Follow_Up",
  "Investigator_CV",
  "Protocol",
  "Deviation_Log",
  "Informed_Consent",
  "Site_Activation",
  "Other",
];

const CONFIDENCE_LABELS: Record<string, { label: string; color: string }> = {
  high:   { label: "High confidence",   color: "text-green-700 bg-green-50 border-green-200" },
  medium: { label: "Medium confidence", color: "text-amber-700 bg-amber-50 border-amber-200" },
  low:    { label: "Low confidence",    color: "text-red-700 bg-red-50 border-red-200" },
};

export default function UploadPage() {
  const [studies, setStudies] = useState<Study[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [studyId, setStudyId] = useState("");
  const [siteId, setSiteId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Classification override state
  const [showOverride, setShowOverride] = useState(false);
  const [selectedType, setSelectedType] = useState("");
  const [overrideStatus, setOverrideStatus] = useState<OverrideStatus>("idle");

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
    setUploadResult(null);
    setError(null);
    setShowOverride(false);
    setOverrideStatus("idle");
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
    setUploadResult(null);
    setShowOverride(false);
    setOverrideStatus("idle");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("study_id", studyId);
    if (siteId) formData.append("site_id", siteId);

    try {
      const res = await api.uploadDocument(formData);
      setUploadResult(res);
      setSelectedType(res.artifact_type);
      setStatus("success");
    } catch (err: any) {
      setError(err.message || "Upload failed");
      setStatus("error");
    }
  };

  const handleConfirmOverride = async () => {
    if (!uploadResult?.document?.id || selectedType === uploadResult.artifact_type) {
      setShowOverride(false);
      return;
    }
    setOverrideStatus("saving");
    try {
      await api.updateClassification(uploadResult.document.id, selectedType);
      setUploadResult((prev) =>
        prev ? { ...prev, artifact_type: selectedType } : prev
      );
      setOverrideStatus("saved");
      setShowOverride(false);
    } catch {
      setOverrideStatus("error");
    }
  };

  const confidenceMeta = uploadResult
    ? CONFIDENCE_LABELS[uploadResult.confidence] ?? CONFIDENCE_LABELS.low
    : null;

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-black text-gray-900 mb-2">Upload Document</h1>
        <p className="text-gray-500 text-sm">
          Upload PDF or TXT TMF artifacts. The system auto-classifies the artifact type
          using AI. You can review and override the classification before finalizing.
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
              Classifying &amp; processing...
            </>
          ) : (
            <>
              <Upload className="w-4 h-4" />
              Upload &amp; Classify
            </>
          )}
        </button>

        {/* ── Success + Classification Review ─────────────────────────────── */}
        {status === "success" && uploadResult && (
          <div className="card border-green-200 bg-green-50 overflow-hidden">
            {/* Upload success header */}
            <div className="flex items-start gap-3 p-5 border-b border-green-100">
              <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-green-800">Upload successful</p>
                <p className="text-sm text-green-700 mt-0.5">{uploadResult.message}</p>
              </div>
            </div>

            {/* AI Classification panel */}
            <div className="p-5 bg-white">
              <h3 className="text-sm font-bold text-gray-700 mb-3">AI Classification</h3>
              <div className="flex flex-wrap items-center gap-3 mb-3">
                <div>
                  <p className="text-xs text-gray-500 mb-1">Detected artifact type</p>
                  <span className="badge text-blue-700 bg-blue-50 border-blue-200">
                    {uploadResult.artifact_type.replace(/_/g, " ")}
                  </span>
                </div>
                {confidenceMeta && (
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Confidence</p>
                    <span className={`badge text-xs ${confidenceMeta.color}`}>
                      {confidenceMeta.label}
                    </span>
                  </div>
                )}
                {uploadResult.has_signature !== null && (
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Signature</p>
                    <span className={`text-xs font-medium ${uploadResult.has_signature ? "text-green-600" : "text-red-500"}`}>
                      {uploadResult.has_signature ? "✓ Detected" : "✗ Not detected"}
                    </span>
                  </div>
                )}
              </div>

              {/* Override section */}
              {overrideStatus === "saved" ? (
                <div className="flex items-center gap-2 text-sm text-purple-700 bg-purple-50 border border-purple-200 rounded-lg px-3 py-2">
                  <CheckCircle className="w-4 h-4" />
                  Classification updated to <strong>{selectedType.replace(/_/g, " ")}</strong>
                </div>
              ) : showOverride ? (
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-semibold text-gray-600 mb-1.5">
                      Override classification
                    </label>
                    <select
                      value={selectedType}
                      onChange={(e) => setSelectedType(e.target.value)}
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {ARTIFACT_TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t.replace(/_/g, " ")}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={handleConfirmOverride}
                      disabled={overrideStatus === "saving"}
                      className="btn-primary text-sm py-1.5"
                    >
                      {overrideStatus === "saving" ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <CheckCircle className="w-3.5 h-3.5" />
                      )}
                      Confirm Override
                    </button>
                    <button
                      type="button"
                      onClick={() => { setShowOverride(false); setSelectedType(uploadResult.artifact_type); }}
                      className="btn-secondary text-sm py-1.5"
                    >
                      Cancel
                    </button>
                  </div>
                  {overrideStatus === "error" && (
                    <p className="text-xs text-red-600">Failed to save override — please try again.</p>
                  )}
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => setShowOverride(true)}
                  className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-blue-600 transition-colors"
                >
                  <Edit2 className="w-3.5 h-3.5" />
                  Override classification
                </button>
              )}
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
