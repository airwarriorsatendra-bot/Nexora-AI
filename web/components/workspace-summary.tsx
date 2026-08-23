import { Activity, Database, ShieldCheck, Sparkles } from "lucide-react";

import { getWorkspaceSummary } from "@/lib/api";

const icons = [Activity, Database, Sparkles, ShieldCheck] as const;

export async function WorkspaceSummaryView({ workspace, eyebrow, title, description }: { workspace: string; eyebrow: string; title: string; description: string }) {
  const data = await getWorkspaceSummary(workspace).catch(() => null);
  return <div className="page module-page">
    <div className="page-heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div></div>
    <section className="metrics-grid compact-metrics">{(data?.metrics ?? []).map((metric,index) => { const Icon=icons[index%icons.length]; return <article className="metric-card" key={metric.key}><div className="metric-heading"><span>{metric.label}</span><Icon size={17}/></div><strong>{metric.value ?? "N/A"}</strong><p>{metric.description}</p></article>; })}</section>
    <section className="panel module-panel"><div className="empty-state"><Database size={22}/><strong>{data ? "Persisted workspace connected" : "Workspace API unavailable"}</strong><p>{data?.note ?? "No data is fabricated while the API is unavailable."}</p></div></section>
  </div>;
}
