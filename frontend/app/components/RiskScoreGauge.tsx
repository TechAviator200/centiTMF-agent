"use client";

import { readinessScoreColor } from "@/lib/utils";

interface RiskScoreGaugeProps {
  score: number;
  zone?: string | null;
  size?: "sm" | "lg";
}

export function RiskScoreGauge({ score, zone, size = "lg" }: RiskScoreGaugeProps) {
  const clampedScore = Math.max(0, Math.min(100, score));
  const circumference = 2 * Math.PI * 40;
  const strokeDashoffset = circumference * (1 - clampedScore / 100);

  const colorClass = readinessScoreColor(score);
  // Higher readiness score = greener
  const strokeColor =
    score >= 80 ? "#22c55e" : score >= 60 ? "#f59e0b" : score >= 40 ? "#f97316" : "#ef4444";

  if (size === "sm") {
    return (
      <div className="flex items-center gap-2">
        <div className="relative w-12 h-12">
          <svg className="w-12 h-12 -rotate-90" viewBox="0 0 96 96">
            <circle cx="48" cy="48" r="40" fill="none" stroke="#e5e7eb" strokeWidth="8" />
            <circle
              cx="48"
              cy="48"
              r="40"
              fill="none"
              stroke={strokeColor}
              strokeWidth="8"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
            />
          </svg>
          <span className={`absolute inset-0 flex items-center justify-center text-xs font-bold ${colorClass}`}>
            {Math.round(clampedScore)}
          </span>
        </div>
        {zone && (
          <span className={`text-sm font-semibold ${colorClass}`}>{zone}</span>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative w-36 h-36">
        <svg className="w-36 h-36 -rotate-90" viewBox="0 0 96 96">
          <circle cx="48" cy="48" r="40" fill="none" stroke="#e5e7eb" strokeWidth="8" />
          <circle
            cx="48"
            cy="48"
            r="40"
            fill="none"
            stroke={strokeColor}
            strokeWidth="8"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-4xl font-black ${colorClass}`}>
            {Math.round(clampedScore)}
          </span>
          <span className="text-xs text-gray-500 mt-0.5">/ 100</span>
        </div>
      </div>
      {zone && (
        <div className={`text-sm font-bold px-3 py-1 rounded-full border ${
          score >= 80 ? "text-green-700 bg-green-50 border-green-200" :
          score >= 60 ? "text-amber-700 bg-amber-50 border-amber-200" :
          score >= 40 ? "text-orange-700 bg-orange-50 border-orange-200" :
          "text-red-700 bg-red-50 border-red-200"
        }`}>
          {zone} RISK
        </div>
      )}
    </div>
  );
}
