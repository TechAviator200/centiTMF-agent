import { ComplianceFlag } from "@/lib/api";
import { RiskBadge } from "./RiskBadge";
import { formatDate } from "@/lib/utils";
import { AlertTriangle } from "lucide-react";

interface FlagTableProps {
  flags: ComplianceFlag[];
  showSite?: boolean;
}

export function FlagTable({ flags, showSite = false }: FlagTableProps) {
  if (flags.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-gray-400">
        <AlertTriangle className="w-8 h-8 mb-2" />
        <p className="text-sm">No compliance flags detected</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100">
            <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Risk
            </th>
            <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Rule
            </th>
            <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Finding
            </th>
            {showSite && (
              <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Site
              </th>
            )}
            <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Date
            </th>
          </tr>
        </thead>
        <tbody>
          {flags.map((flag) => (
            <tr key={flag.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
              <td className="py-3 px-4">
                <RiskBadge level={flag.risk_level} />
              </td>
              <td className="py-3 px-4 font-mono text-xs text-gray-500">
                {flag.rule_code}
              </td>
              <td className="py-3 px-4">
                <p className="font-medium text-gray-900">{flag.title}</p>
                {flag.details && (
                  <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{flag.details}</p>
                )}
              </td>
              {showSite && (
                <td className="py-3 px-4 text-gray-500 text-xs">
                  {flag.site_id ? flag.site_id.slice(0, 8) + "..." : "Study"}
                </td>
              )}
              <td className="py-3 px-4 text-gray-500 text-xs whitespace-nowrap">
                {formatDate(flag.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
