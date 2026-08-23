import { LockKeyhole, Settings, ShieldCheck } from "lucide-react";

import { getProviderStatus } from "@/lib/api";

export default async function SettingsPage() {
  const data = await getProviderStatus().catch(() => null);
  return (
    <div className="page module-page">
      <div className="page-heading"><div><span className="eyebrow">System</span><h1>Workspace settings</h1><p>Configuration presence is visible; credentials and token material never cross the API boundary.</p></div></div>
      <section className="panel module-panel">
        <div className="panel-heading"><div><span className="eyebrow">Provider health</span><h2>Backend integrations</h2></div><ShieldCheck size={20} /></div>
        <div className="provider-grid">
          {data?.providers.map((item) => <article className="provider-card" key={item.provider}><span className={`provider-dot ${item.status.toLowerCase()}`} /><div><strong>{item.provider}</strong><p>{item.detail}</p></div><span className="provider-state">{item.status.replaceAll("_", " ")}</span></article>) ?? <div className="error-state"><Settings size={17} />Provider status API is unavailable.</div>}
        </div>
      </section>
      <section className="panel module-panel security-note"><LockKeyhole size={20} /><div><strong>Authentication boundary</strong><p>{data?.authentication.replaceAll("_", " ") ?? "Status unavailable"}. Beta 17 does not implement insecure placeholder authentication.</p></div></section>
    </div>
  );
}
