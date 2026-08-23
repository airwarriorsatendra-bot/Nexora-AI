# Beta 17 parity and release matrix

`PARITY_VERIFIED` means the supported Beta 17 workflow has a FastAPI surface, a usable Next.js route, persisted or explicitly refreshed data semantics, and automated regression coverage. It does not claim capabilities outside the product's current domain model.

| Workflow | FastAPI surface | Next.js route | Certification |
|---|---|---|---|
| Executive dashboard | `/api/v1/dashboard` | `/` | PARITY_VERIFIED |
| SEO audits and intelligence | `/api/v1/seo/*` | `/seo` | PARITY_VERIFIED |
| Rank tracking | `/api/v1/rank-tracking/*` | `/seo/rank-tracking` | PARITY_VERIFIED |
| Site crawl | `/api/v1/site-crawl/*` | `/seo/site-crawl` | PARITY_VERIFIED |
| Competitor gaps | `/api/v1/competitor-gaps/*` | `/seo/competitor-gaps` | PARITY_VERIFIED |
| Current content intelligence | `/api/v1/content/*` | `/seo/content` | PARITY_VERIFIED |
| AEO/GEO | `/api/v1/aeo/*` | `/seo/aeo-geo` | PARITY_VERIFIED |
| AI Visibility | `/api/v1/workspaces/ai-visibility` | `/ai-visibility` | PARITY_VERIFIED |
| Backlinks | `/api/v1/backlinks/*` | `/backlinks` | PARITY_VERIFIED |
| Outreach | `/api/v1/outreach/*` | `/outreach` | PARITY_VERIFIED |
| Local SEO | `/api/v1/local-seo/*` | `/local-seo` | PARITY_VERIFIED |
| Analytics (GSC and GA4) | `/api/v1/analytics/*` | `/analytics` | PARITY_VERIFIED |
| Google Ads | `/api/v1/workspaces/google-ads` | `/google-ads` | PARITY_VERIFIED |
| Meta Ads | `/api/v1/workspaces/meta-ads` | `/meta-ads` | PARITY_VERIFIED |
| Provider settings | `/api/v1/settings/providers` | `/settings` | PARITY_VERIFIED |

## Analytics closure evidence

- Default reads are persisted-only and never contact Google providers.
- GSC and GA4 refreshes are explicit POST actions and require a resource plus date window.
- Query, page, date, and GA4 dimension evidence support bounded filtering, sorting, and pagination.
- CSV exports apply the active value and date filters.
- Compatible equal-window snapshot comparisons are exposed by source.
- Cross-source page matching validates hosts and preserves GSC/GA4 source separation; attribution is explicitly `NOT_INFERRED`.
- Missing data remains missing rather than being replaced with fabricated values.

## Intentional domain boundaries

These are documented product boundaries, not hidden parity failures:

- Content briefs do not yet have a persisted version-history model.
- AEO/GEO does not yet persist source-level answer citations or historical runs.
- Competitor page-gap observations remain independent snapshots rather than a longitudinal series.
- Paid-media workspaces are read-oriented; live campaign mutation is deferred.
- Provider settings report configuration/offline readiness and do not ping third parties during page render.
- User authentication and authorization are deferred to the deployment boundary.

## Release decision

All 15 supported Beta 17 workflows are `PARITY_VERIFIED` (15/15, 100%). Automated browser navigation generates no non-localhost provider calls. Streamlit remains available as a rollback surface; retiring it is a product-owner deployment decision rather than a parity blocker.
