"use client";

import { FormEvent, useState } from "react";
import { Download, Globe2, Play } from "lucide-react";
import { getSiteCrawlDetail, startSiteCrawl } from "@/lib/api";
import type { CrawlComparison, SiteCrawl, SiteCrawlHistory } from "@/types/api";

function csv(name: string, rows: Array<Record<string, unknown>>) {
  if (!rows.length) return;
  const keys = Object.keys(rows[0]);
  const cell = (value: unknown) => {
    const text = String(value ?? "");
    const safe = /^[=+\-@]/.test(text) ? `'${text}` : text;
    return `"${safe.replaceAll('"', '""')}"`;
  };
  const body = [keys.map(cell).join(","), ...rows.map((row) => keys.map((key) => cell(row[key])).join(","))].join("\n");
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([body], { type: "text/csv" }));
  link.download = name;
  link.click();
  URL.revokeObjectURL(link.href);
}

function Data({ title, rows, onExport }: { title: string; rows: Array<Record<string, unknown>>; onExport: () => void }) {
  const display = rows.slice(0, 100);
  const keys = display.length ? Object.keys(display[0]).slice(0, 7) : [];
  return <>
    <div className="panel-heading"><h2>{title}</h2><button className="text-button" disabled={!rows.length} onClick={onExport}><Download size={14} />CSV</button></div>
    {display.length ? <div className="data-table-wrap"><table><caption className="sr-only">{title}</caption><thead><tr>{keys.map((key) => <th key={key}>{key.replaceAll("_", " ")}</th>)}</tr></thead><tbody>{display.map((row, index) => <tr key={index}>{keys.map((key) => <td key={key}>{typeof row[key] === "object" ? JSON.stringify(row[key]) : String(row[key] ?? "N/A")}</td>)}</tr>)}</tbody></table></div> : <div className="empty-state"><Globe2 size={20} /><strong>No {title.toLowerCase()}</strong><p>No matching persisted evidence exists.</p></div>}
  </>;
}

export function SiteCrawlWorkspace({ initial }: { initial: SiteCrawlHistory | null }) {
  const [historyItems, setHistoryItems] = useState<SiteCrawl[]>(initial?.items ?? []);
  const [crawl, setCrawl] = useState<SiteCrawl | null>(initial?.latest ?? null);
  const [comparison, setComparison] = useState<CrawlComparison | null>(null);
  const [tab, setTab] = useState("overview");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function run(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      const completed = await startSiteCrawl({ start_url: String(form.get("url")), max_pages: Number(form.get("pages")), max_depth: Number(form.get("depth")), max_concurrency: Number(form.get("concurrency")) });
      setCrawl(completed);
      setHistoryItems((items) => [completed, ...items.filter((item) => item.crawl_id !== completed.crawl_id)]);
      setComparison(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Crawl failed.");
    } finally {
      setPending(false);
    }
  }

  async function select(id: string) {
    if (!id) return;
    setPending(true);
    setError("");
    try {
      const detail = await getSiteCrawlDetail(id);
      setCrawl(detail.crawl);
      setComparison(detail.comparison);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Crawl could not be loaded.");
    } finally {
      setPending(false);
    }
  }

  const stats = crawl?.summary.statistics;
  const tabs = ["overview", "pages", "issues", "links", "opportunities", "history"];
  const rows = (tab === "pages" ? crawl?.pages ?? [] : tab === "issues" ? crawl?.issues ?? [] : tab === "links" ? crawl?.links ?? [] : tab === "opportunities" ? crawl?.opportunities ?? [] : tab === "history" ? historyItems : []) as unknown as Record<string, unknown>[];
  return <>
    <section className="panel module-panel"><div className="panel-heading"><div><span className="eyebrow">Explicit bounded operation</span><h2>Start crawl</h2></div><Globe2 size={19} /></div><form className="crawl-form" onSubmit={run}><label><span>Start URL</span><input name="url" type="url" required maxLength={2048} /></label><label><span>Max pages</span><input name="pages" type="number" min="1" max="500" defaultValue="100" /></label><label><span>Max depth</span><input name="depth" type="number" min="0" max="10" defaultValue="4" /></label><label><span>Concurrency</span><input name="concurrency" type="number" min="1" max="10" defaultValue="4" /></label><button className="primary-button" disabled={pending}><Play size={15} />{pending ? "Crawling…" : "Run crawl"}</button></form><p className="section-note">No external request occurs until submitted. Progress is not fabricated; the result appears when the bounded operation completes.</p></section>
    {error ? <div className="error-state" role="alert">{error}</div> : null}
    {crawl ? <section className="metrics-grid compact-metrics"><M label="Pages crawled" value={stats?.pages_crawled ?? 0} /><M label="Broken links" value={stats?.broken_links ?? 0} /><M label="Missing meta" value={stats?.missing_meta ?? 0} /><M label="Overall score" value={crawl.summary.overall_score} /></section> : null}
    <div className="module-tabs" role="tablist">{tabs.map((key) => <button key={key} role="tab" aria-selected={tab === key} className={tab === key ? "selected" : ""} onClick={() => setTab(key)}>{key.replaceAll("_", " ")}</button>)}</div>
    <section className="panel module-panel">{tab === "overview" ? <><div className="panel-heading"><h2>Crawl overview</h2></div>{crawl ? <p>{crawl.summary.disclaimer}</p> : <div className="empty-state"><Globe2 size={20} /><strong>No persisted crawl selected</strong><p>Start a bounded crawl or choose one from history.</p></div>}{comparison ? <p className="section-note">Compared with crawl {comparison.previous_crawl_id ?? "N/A"}: {comparison.new_pages.length} new pages, {comparison.resolved_issues.length} resolved issues.</p> : null}</> : tab === "history" ? <><div className="panel-heading"><h2>Crawl history</h2><select aria-label="Select crawl" value={crawl?.crawl_id ?? ""} onChange={(event) => select(event.target.value)}><option value="">Select crawl</option>{historyItems.map((item) => <option key={item.crawl_id} value={item.crawl_id}>{item.request.start_url} · {new Date(item.completed_at).toLocaleString()}</option>)}</select></div><Data title="Crawl history" rows={rows} onExport={() => csv("nexora_crawl_history.csv", rows)} /></> : <Data title={tab} rows={rows} onExport={() => csv(`nexora_crawl_${tab}.csv`, rows)} />}</section>
  </>;
}

function M({ label, value }: { label: string; value: number }) { return <article className="metric-card"><strong>{value}</strong><p>{label}</p></article>; }
