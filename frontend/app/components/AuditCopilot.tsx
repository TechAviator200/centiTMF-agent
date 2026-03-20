"use client";

import { useState } from "react";
import { api, AuditAnswer } from "@/lib/api";
import { MessageSquare, Loader2, ChevronRight, Database } from "lucide-react";

const SUGGESTED_QUESTIONS = [
  "Which site is highest risk?",
  "What artifacts are missing?",
  "What should be fixed before an FDA inspection?",
  "What's driving the score down?",
  "Summarize the TMF compliance posture",
];

interface AuditCopilotProps {
  studyId: string;
}

export function AuditCopilot({ studyId }: AuditCopilotProps) {
  const [input, setInput] = useState("");
  const [answer, setAnswer] = useState<AuditAnswer | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ask = async (question: string) => {
    const q = question.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    setAnswer(null);
    try {
      const result = await api.askAuditQuestion(studyId, q);
      setAnswer(result);
    } catch (e: any) {
      setError(e.message || "Failed to get answer");
    } finally {
      setLoading(false);
    }
  };

  const handleChip = (q: string) => {
    setInput(q);
    ask(q);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    ask(input);
    setInput("");
  };

  return (
    <div className="card">
      <div className="flex items-center gap-2 px-5 py-4 border-b border-gray-100">
        <MessageSquare className="w-5 h-5 text-blue-600" />
        <div>
          <h2 className="font-bold text-gray-900">Audit Copilot</h2>
          <p className="text-xs text-gray-400">Ask about TMF status, site risk, or inspection readiness</p>
        </div>
      </div>

      <div className="p-5">
        {/* Suggested question chips */}
        <div className="flex flex-wrap gap-2 mb-4">
          {SUGGESTED_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => handleChip(q)}
              disabled={loading}
              className="text-xs px-3 py-1.5 rounded-full border border-blue-200 text-blue-700 bg-blue-50 hover:bg-blue-100 transition-colors disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>

        {/* Custom question input */}
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="e.g. What artifacts are missing for Site 012?"
            className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="btn-primary px-4"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </button>
        </form>

        {/* Loading */}
        {loading && (
          <div className="mt-4 flex items-center gap-2 text-sm text-gray-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            Analyzing compliance data...
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mt-4 text-sm text-red-600 bg-red-50 rounded-lg p-3 border border-red-100">
            {error}
          </div>
        )}

        {/* Answer */}
        {answer && (
          <div className="mt-4 bg-blue-50 border border-blue-100 rounded-lg p-4">
            <p className="text-xs font-semibold text-blue-600 mb-2">
              Q: {answer.question}
            </p>
            <div className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">
              {answer.answer}
            </div>
            {answer.data_basis.length > 0 && (
              <div className="mt-3 pt-3 border-t border-blue-100 flex items-center gap-1.5">
                <Database className="w-3 h-3 text-blue-400" />
                <p className="text-xs text-blue-500">
                  Based on: {answer.data_basis.join(" · ")}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
