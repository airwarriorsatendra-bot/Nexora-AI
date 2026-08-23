"use client";

import { FormEvent, useState } from "react";
import { Play, TriangleAlert } from "lucide-react";

import { runSEOAudit } from "@/lib/api";
import type { SEOAudit } from "@/types/api";

export function SEOAuditForm() {
  const [url, setUrl] = useState("");
  const [audit, setAudit] = useState<SEOAudit | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      const result = await runSEOAudit(url);
      if (!result.success || !result.audit) throw new Error(result.message || "Audit failed.");
      setAudit(result.audit);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Audit could not be completed.");
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="panel module-panel">
      <div className="panel-heading"><div><span className="eyebrow">Explicit action</span><h2>Technical audit</h2></div></div>
      <form className="inline-form" onSubmit={submit}>
        <label><span>Website URL</span><input type="url" required maxLength={2048} value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://example.com/page" /></label>
        <button className="primary-button" disabled={pending}><Play size={15} /> {pending ? "Auditing…" : "Run audit"}</button>
      </form>
      {error ? <div className="error-state" role="alert"><TriangleAlert size={17} /><span>{error}</span></div> : null}
      {audit ? <div className="audit-result"><strong>{audit.overall_score.toFixed(0)}</strong><span>Overall score</span><span>{audit.issues.length} findings · {String(audit.metrics.word_count ?? "N/A")} words</span></div> : <p className="section-note">No crawl occurs until you submit this form.</p>}
    </section>
  );
}
