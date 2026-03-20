"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { api, SimulationResult, StudyDetail } from "@/lib/api";
import {
  formatDate,
  readinessScoreColor,
  readinessZoneColor,
  readinessZoneLabel,
  deviationScoreColor,
  riskColor,
} from "@/lib/utils";
import { RiskScoreGauge } from "@/app/components/RiskScoreGauge";
import { ChevronRight, Play, LayoutDashboard, Loader2, AlertTriangle, TrendingUp, FileText, ShieldCheck, ShieldAlert } from "lucide-react";

export default function SimulatePage({ params }: { params: { studyId: string } }) {
  const [study, setStudy] = useState<StudyDetail | null>(null);
  const [simulations, setSimulations] = useState<SimulationResult[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getStudy(params.studyId)
      .then(setStudy)
      .catch(() => {});
    api.getSimulations(params.studyId)
      .then(setSimulations)
      .catch(() => {});
  }, [params.studyId]);

  const handleSimulate = async () => {
    setRunning(true);
    setError(null);
    try {
      const sim = await api.simulateInspection(params.studyId);
      setSimulations((prev) => [sim, ...prev]);
    } catch (e: any) {
      setError(e.message || "Simulation failed");
    } finally {
      setRunning(false);
    }
  };

  const latest = simulations[0] || null;
  const score = latest?.risk_score ?? null;

  return (
    <div>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-500 mb-6 flex-wrap">
        <Link href="/" className="hover:text-gray-900">Studies</Link>
        <ChevronRight className="w-4 h-4" />
        {study && (
          <>
            <Link href={`/studies/${params.studyId}`} className="hover:text-gray-900">{study.name}</Link>
            <ChevronRight className="w-4 h-4" />
          </>
        )}
        <span className="font-semibold text-gray-900">Inspection Simulation</span>
      </div>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-3xl font-black text-gray-900">
              {study ? study.name : "Study"} — Inspection Readiness
            </h1>
            {study?.phase && (
              <span className="badge text-blue-700 bg-blue-50 border-blue-200">
                {study.phase}
              </span>
            )}
          </div>
          {study?.sponsor && (
            <p className="text-sm text-gray-500 mb-1">{study.sponsor}</p>
          )}
          <p className="text-gray-500 text-sm">
            Evaluates Trial Master File completeness, deviation patterns, and site-level
            compliance signals to assess FDA inspection readiness.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link href={`/studies/${params.studyId}`} className="btn-secondary">
            <LayoutDashboard className="w-4 h-4" />
            View TMF Dashboard
          </Link>
          <button
            onClick={handleSimulate}
            disabled={running}
            className="btn-primary"
          >
            {running ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Simulating...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Run New Simulation
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="card p-4 border-red-200 bg-red-50 mb-6">
          <p className="text-sm text-red-700 font-semibold">{error}</p>
        </div>
      )}

      {latest ? (
        <div className="space-y-6">
          {/* ── Score = 0 critical banner ───────────────────────────────────── */}
          {score !== null && score === 0 && (
            <div className="rounded-xl border border-red-300 bg-red-50 p-4 flex items-start gap-3">
              <ShieldAlert className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-red-700 text-sm tracking-wide">
                  FAILED — INSPECTION READINESS
                </p>
                <p className="text-xs text-red-600 mt-0.5">
                  Critical deficiencies detected across the Trial Master File. Immediate
                  remediation required before any regulatory inspection.
                </p>
              </div>
            </div>
          )}

          {/* ── Readiness Score — hero card ────────────────────────────────── */}
          <div className={`card p-8 ${score !== null && score < 40 ? "border-red-200" : ""}`}>
            <div className="flex items-center gap-2 mb-6">
              {score !== null && score >= 60 ? (
                <ShieldCheck className="w-5 h-5 text-green-500" />
              ) : (
                <ShieldAlert className="w-5 h-5 text-red-500" />
              )}
              <div>
                <h2 className="font-bold text-gray-900">Trial Master File — Inspection Readiness</h2>
                <p className="text-xs text-gray-400">
                  Based on TMF completeness, deviation patterns, and inspection readiness logic
                </p>
              </div>
              <span className="text-xs text-gray-400 ml-auto">
                Simulated {formatDate(latest.created_at)}
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-10">
              <RiskScoreGauge score={latest.risk_score} zone={latest.vulnerable_zone} size="lg" />

              <div className="flex-1 min-w-0">
                {/* Flag counts */}
                <div className="flex gap-6 mb-6">
                  {latest.results_json && (
                    <>
                      {(latest.results_json.critical_flags ?? 0) > 0 && (
                        <div className="text-center">
                          <p className="text-2xl font-black text-purple-600">{latest.results_json.critical_flags}</p>
                          <p className="text-xs text-gray-500">Critical</p>
                        </div>
                      )}
                      <div className="text-center">
                        <p className="text-2xl font-black text-red-600">{latest.results_json.high_flags}</p>
                        <p className="text-xs text-gray-500">High</p>
                      </div>
                      <div className="text-center">
                        <p className="text-2xl font-black text-amber-500">{latest.results_json.medium_flags}</p>
                        <p className="text-xs text-gray-500">Medium</p>
                      </div>
                      <div className="text-center">
                        <p className="text-2xl font-black text-gray-500">{latest.results_json.total_flags}</p>
                        <p className="text-xs text-gray-500">Total</p>
                      </div>
                    </>
                  )}
                </div>

                {/* Scoring breakdown */}
                {latest.results_json?.scoring_breakdown && (
                  <div className="bg-gray-50 rounded-lg p-4 border border-gray-100">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                      Score Breakdown
                    </p>
                    <div className="space-y-1.5 text-xs text-gray-600">
                      <div className="flex justify-between">
                        <span>Base score</span>
                        <span className="font-semibold text-gray-800">
                          {latest.results_json.scoring_breakdown.base_score}
                        </span>
                      </div>
                      <div className="flex justify-between text-red-600">
                        <span>Flag deductions</span>
                        <span className="font-semibold">
                          −{latest.results_json.scoring_breakdown.flag_deduction}
                        </span>
                      </div>
                      {latest.results_json.scoring_breakdown.cluster_penalty > 0 && (
                        <div className="flex justify-between text-orange-600">
                          <span>Cluster penalty</span>
                          <span className="font-semibold">
                            −{latest.results_json.scoring_breakdown.cluster_penalty}
                          </span>
                        </div>
                      )}
                      {(latest.results_json.scoring_breakdown.multi_site_deviation_penalty +
                        latest.results_json.scoring_breakdown.per_site_deviation_penalty) > 0 && (
                        <div className="flex justify-between text-amber-600">
                          <span>Deviation penalties</span>
                          <span className="font-semibold">
                            −{latest.results_json.scoring_breakdown.multi_site_deviation_penalty +
                              latest.results_json.scoring_breakdown.per_site_deviation_penalty}
                          </span>
                        </div>
                      )}
                      <div className="flex justify-between border-t border-gray-200 pt-1.5 mt-1.5">
                        <span className="font-semibold text-gray-700">Final score</span>
                        <span className={`font-black ${readinessScoreColor(latest.risk_score)}`}>
                          {latest.risk_score.toFixed(0)} / 100
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Narrative */}
          {latest.narrative && (
            <div className="card p-6">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp className="w-5 h-5 text-blue-600" />
                <h2 className="font-bold text-gray-900">Regulatory Assessment Narrative</h2>
              </div>
              <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans leading-relaxed bg-gray-50 rounded-lg p-4 border border-gray-100">
                {latest.narrative}
              </pre>
            </div>
          )}

          {/* Missing TMF Artifacts */}
          {latest.results_json?.missing_artifacts && latest.results_json.missing_artifacts.length > 0 && (
            <div className="card p-6">
              <div className="flex items-center gap-2 mb-1">
                <FileText className="w-5 h-5 text-red-500" />
                <h2 className="font-bold text-gray-900">Missing TMF Artifacts</h2>
                <span className="badge text-red-700 bg-red-50 border-red-200 ml-auto">
                  {latest.results_json.missing_artifacts.length} items
                </span>
              </div>
              <p className="text-xs text-gray-400 mb-4">
                Required documents absent from the Trial Master File at time of simulation.
              </p>
              <ul className="space-y-2">
                {latest.results_json.missing_artifacts.map((item, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                    <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Site Deviation Scores */}
          {latest.results_json?.site_deviation_scores && latest.results_json.site_deviation_scores.length > 0 && (
            <div className="card p-6">
              <div className="flex items-center gap-2 mb-1">
                <TrendingUp className="w-5 h-5 text-amber-500" />
                <h2 className="font-bold text-gray-900">Site Deviation Risk</h2>
              </div>
              <p className="text-xs text-gray-400 mb-4">Protocol deviation exposure by site, scored 0–100.</p>
              <div className="space-y-4">
                {latest.results_json.site_deviation_scores.map((s) => (
                  <div key={s.site_id}>
                    <div className="flex items-center gap-4 mb-1.5">
                      <div className="w-20 text-xs font-semibold text-gray-700">
                        Site {s.site_code}
                      </div>
                      <div className="flex-1 bg-gray-100 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full transition-all ${
                            s.score >= 60 ? "bg-red-500" :
                            s.score >= 35 ? "bg-amber-400" :
                            "bg-green-400"
                          }`}
                          style={{ width: `${s.score}%` }}
                        />
                      </div>
                      <span className={`text-sm font-bold w-10 text-right ${deviationScoreColor(s.score)}`}>
                        {s.score.toFixed(0)}
                      </span>
                    </div>
                    {s.findings && s.findings.length > 0 && (
                      <div className="ml-20 space-y-0.5">
                        {s.findings.slice(0, 2).map((f, fi) => (
                          <p key={fi} className="text-xs text-gray-500 truncate">· {f}</p>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top Compliance Flags */}
          {latest.results_json?.top_flags && latest.results_json.top_flags.length > 0 && (
            <div className="card">
              <div className="flex items-center gap-2 p-5 border-b border-gray-100">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                <h2 className="font-bold text-gray-900">Top Compliance Flags</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 bg-gray-50">
                      {["Severity", "Rule", "Finding", "Site", "Points"].map((h) => (
                        <th key={h} className="text-left py-2.5 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {latest.results_json.top_flags.map((f, i) => (
                      <tr key={i} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                        <td className="py-3 px-4">
                          <span className={`badge text-xs ${riskColor(f.severity || f.risk_level)}`}>
                            {f.severity || f.risk_level}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-xs text-gray-500">{f.rule_code}</td>
                        <td className="py-3 px-4">
                          <p className="font-medium text-gray-900">{f.title}</p>
                          {f.category && (
                            <p className="text-xs text-gray-400 mt-0.5">{f.category}</p>
                          )}
                        </td>
                        <td className="py-3 px-4 text-xs text-gray-500">
                          {f.site_code ? `Site ${f.site_code}` : "Study"}
                        </td>
                        <td className="py-3 px-4 text-xs font-semibold text-red-600">
                          −{f.risk_points}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Simulation History */}
          {simulations.length > 1 && (
            <div className="card">
              <div className="p-5 border-b border-gray-100">
                <h2 className="font-bold text-gray-900">Simulation History</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100">
                      {["Date", "Readiness Score", "Zone", "Total Flags"].map((h) => (
                        <th key={h} className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {simulations.map((sim) => (
                      <tr key={sim.id} className="border-b border-gray-50">
                        <td className="py-3 px-4 text-gray-600 text-xs">{formatDate(sim.created_at)}</td>
                        <td className="py-3 px-4">
                          <span className={`font-bold ${readinessScoreColor(sim.risk_score)}`}>
                            {sim.risk_score.toFixed(1)}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`badge text-xs ${readinessZoneColor(sim.vulnerable_zone)}`}>
                            {readinessZoneLabel(sim.vulnerable_zone)}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-gray-600">
                          {sim.results_json?.total_flags ?? "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="card p-16 text-center">
          <ShieldCheck className="w-16 h-16 text-gray-200 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-gray-500 mb-2">No inspection simulation run yet</h3>
          <p className="text-sm text-gray-400 mb-1">
            Run a simulation to score this study's Trial Master File against inspection readiness criteria.
          </p>
          <p className="text-xs text-gray-400 mb-6">
            Analyzes TMF completeness, deviation patterns, site compliance flags, and clustering risk.
          </p>
          <button onClick={handleSimulate} disabled={running} className="btn-primary mx-auto">
            {running ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Running...</>
            ) : (
              <><Play className="w-4 h-4" /> Simulate FDA Inspection</>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
