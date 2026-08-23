import type { LucideIcon } from "lucide-react";

export function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
}: {
  label: string;
  value: string | number | null;
  detail: string;
  icon: LucideIcon;
}) {
  return (
    <article className="metric-card">
      <div className="metric-heading"><span>{label}</span><Icon size={17} /></div>
      <strong>{value ?? "N/A"}</strong>
      <p>{detail}</p>
    </article>
  );
}
