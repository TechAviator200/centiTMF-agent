import { type ClassValue, clsx } from "clsx";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/** Badge color for severity/risk_level values */
export function riskColor(level: string): string {
  switch (level?.toUpperCase()) {
    case "CRITICAL":
      return "text-purple-700 bg-purple-50 border-purple-200";
    case "HIGH":
      return "text-red-700 bg-red-50 border-red-200";
    case "MEDIUM":
      return "text-amber-700 bg-amber-50 border-amber-200";
    case "LOW":
      return "text-green-700 bg-green-50 border-green-200";
    default:
      return "text-gray-600 bg-gray-50 border-gray-200";
  }
}

/**
 * Color class for a readiness score (0 = critical, 100 = perfect).
 * Lower score = worse = redder.
 */
export function readinessScoreColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-amber-500";
  if (score >= 40) return "text-orange-500";
  return "text-red-600";
}

export function readinessScoreBarColor(score: number): string {
  if (score >= 80) return "bg-green-500";
  if (score >= 60) return "bg-amber-400";
  if (score >= 40) return "bg-orange-400";
  return "bg-red-500";
}

export function readinessZoneLabel(zone: string | null | undefined): string {
  switch ((zone || "").toUpperCase()) {
    case "LOW":      return "LOW RISK";
    case "MEDIUM":   return "MEDIUM RISK";
    case "HIGH":     return "HIGH RISK";
    case "CRITICAL": return "CRITICAL RISK";
    default:         return "UNKNOWN";
  }
}

export function readinessZoneColor(zone: string | null | undefined): string {
  switch ((zone || "").toUpperCase()) {
    case "LOW":      return "text-green-700 bg-green-50 border-green-200";
    case "MEDIUM":   return "text-amber-700 bg-amber-50 border-amber-200";
    case "HIGH":     return "text-orange-700 bg-orange-50 border-orange-200";
    case "CRITICAL": return "text-red-700 bg-red-50 border-red-200";
    default:         return "text-gray-600 bg-gray-50 border-gray-200";
  }
}

export function artifactTypeLabel(type: string): string {
  return type.replace(/_/g, " ");
}

/** Returns a human-readable relative time string (e.g. "12m ago", "2h ago", "3d ago") */
export function formatRelativeTime(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  const diffMs = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

/** Deviation score color — higher deviation = worse */
export function deviationScoreColor(score: number): string {
  if (score >= 60) return "text-red-600";
  if (score >= 35) return "text-amber-500";
  if (score > 0)   return "text-yellow-600";
  return "text-green-600";
}
