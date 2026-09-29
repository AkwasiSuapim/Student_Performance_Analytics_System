import type { RiskLevel } from "../api/types";

const CONFIG: Record<RiskLevel, { icon: string; label: string }> = {
  high: { icon: "▲", label: "High priority" },
  moderate: { icon: "◆", label: "Moderate priority" },
  low: { icon: "●", label: "Low priority" },
};

export function RiskBadge({ level }: { level: RiskLevel }) {
  const { icon, label } = CONFIG[level];
  return (
    <span className={`badge badge-${level}`}>
      <span aria-hidden="true">{icon}</span>
      {label}
    </span>
  );
}
