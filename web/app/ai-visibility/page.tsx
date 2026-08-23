import { AIVisibilityWorkspace } from "@/components/ai-visibility-workspace";
import { getAIVisibility } from "@/lib/api";
export default async function Page() { const initial = await getAIVisibility().catch(() => ({ providers: [], prompts: [], history: [] })); return <div className="page module-page"><div className="page-heading"><div><span className="eyebrow">Grounded intelligence</span><h1>AI visibility</h1><p>Monitor provider-specific mentions and structured citation evidence with explicit, bounded execution.</p></div></div><AIVisibilityWorkspace initial={initial}/></div>; }
