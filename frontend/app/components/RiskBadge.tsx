import { cn, riskColor } from "@/lib/utils";

interface RiskBadgeProps {
  level: string;
  className?: string;
}

export function RiskBadge({ level, className }: RiskBadgeProps) {
  return (
    <span className={cn("badge", riskColor(level), className)}>
      {level}
    </span>
  );
}
