import {
  ArrowUpRight,
  Bot,
  CheckCircle2,
  FileSearch,
  Link2,
  Search,
  Sparkles,
  Target,
} from "lucide-react";

import { MetricCard } from "@/components/metric-card";
import { getDashboard, getSystemHealth } from "@/lib/api";

const metricIcons = [Target, Link2, Search, Bot] as const;

export default async function OverviewPage() {
  const [health, dashboard] = await Promise.all([
    getSystemHealth().catch(() => null),
    getDashboard().catch(() => null),
  ]);
  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Command center</span>
          <h1>Marketing intelligence, unified.</h1>
          <p>Turn search, visibility, authority, and acquisition signals into focused action.</p>
        </div>
        <button className="primary-button"><Sparkles size={16} /> Run intelligence audit</button>
      </div>

      <section className="metrics-grid" aria-label="Workspace metrics">
        {(dashboard?.metrics ?? [
          { key: "prospects", label: "Tracked prospects", value: null, description: "API unavailable" },
          { key: "backlinks", label: "Backlink records", value: null, description: "API unavailable" },
          { key: "seo", label: "SEO audits", value: null, description: "API unavailable" },
          { key: "visibility", label: "AI observations", value: null, description: "API unavailable" },
        ]).map((metric, index) => (
          <MetricCard
            key={metric.key}
            label={metric.label}
            value={metric.value}
            detail={metric.description}
            icon={metricIcons[index] ?? Target}
          />
        ))}
      </section>

      <section className="overview-grid">
        <article className="panel performance-panel">
          <div className="panel-heading">
            <div><span className="eyebrow">Workspace pulse</span><h2>Intelligence coverage</h2></div>
            <button className="text-button">View analytics <ArrowUpRight size={15} /></button>
          </div>
          <div className="chart-area" aria-label="Illustrative workspace coverage chart">
            <div className="chart-line" />
            <div className="chart-grid-lines"><i /><i /><i /><i /></div>
            <span className="chart-caption">Latest persisted workspace activity</span>
          </div>
        </article>

        <article className="panel attention-panel">
          <div className="panel-heading"><div><span className="eyebrow">Action center</span><h2>Attention</h2></div><CheckCircle2 size={20} /></div>
          <div className="positive-state">
            <span className="positive-icon"><CheckCircle2 size={21} /></span>
            <div><strong>{dashboard?.attention_count ? "Items require review" : "Your workspace is ready"}</strong><p>{dashboard?.attention_count ? `${dashboard.attention_count} persisted items need attention.` : "No critical persisted issues require attention right now."}</p></div>
          </div>
          <div className="system-row"><span><i className={health ? "online" : "offline"} /> API connection</span><strong>{health ? "Connected" : "Unavailable"}</strong></div>
          <button className="secondary-button">Open opportunity explorer</button>
        </article>
      </section>

      <section className="panel activity-panel">
        <div className="panel-heading"><div><span className="eyebrow">Recent activity</span><h2>Intelligence stream</h2></div><button className="text-button">View all</button></div>
        {dashboard?.recent_activity.length ? dashboard.recent_activity.map((item) => (
          <div className="activity-row" key={`${item.category}-${item.observed_at}`}><span className="activity-icon"><FileSearch size={17} /></span><div><strong>{item.title}</strong><p>{item.detail}</p></div><time>{item.observed_at ? new Date(item.observed_at).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "Stored"}</time></div>
        )) : <div className="activity-row"><span className="activity-icon"><FileSearch size={17} /></span><div><strong>No persisted activity yet</strong><p>Run a supported workflow to populate the intelligence stream.</p></div><time>—</time></div>}
      </section>
    </div>
  );
}
