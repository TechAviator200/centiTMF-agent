import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  accent?: "red" | "amber" | "green" | "blue" | "gray";
  icon?: React.ReactNode;
}

const accentMap = {
  red: "text-red-600 bg-red-50",
  amber: "text-amber-600 bg-amber-50",
  green: "text-green-600 bg-green-50",
  blue: "text-blue-600 bg-blue-50",
  gray: "text-gray-600 bg-gray-50",
};

export function StatCard({ label, value, sub, accent = "blue", icon }: StatCardProps) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
            {label}
          </p>
          <p className={cn("text-3xl font-black", accentMap[accent].split(" ")[0])}>
            {value}
          </p>
          {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
        </div>
        {icon && (
          <div className={cn("p-2.5 rounded-lg", accentMap[accent])}>
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}
