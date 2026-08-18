# Nexora AI

Nexora AI is a Python 3.12 digital-marketing intelligence platform with source-layer modules for Research, SEO, Backlinks, Outreach, Local SEO, imported Google/Meta Ads analysis, and Analytics.

## Local setup

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Configure only the external-provider variables needed for the workflows you use. `.env` is local-only and must never be committed. The deterministic and import-based modules can run without provider credentials.

## Run the dashboard

```powershell
.\.venv\Scripts\streamlit.exe run dashboard\app.py
```

The application creates its SQLite runtime database at `storage/backlinks.db` through idempotent repository schema initialization. Runtime databases, logs, exports, and caches are intentionally excluded from version control.

## Test and verify

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
.\.venv\Scripts\python.exe -m pip check
```

## Provider boundaries

- Search providers: Tavily, Serper, Brave, Google CSE, and Perplexity.
- AI providers: OpenAI, Gemini, Groq, Claude, and NVIDIA.
- Google Ads and Meta Ads: imported-data intelligence only; no live read or mutation provider.
- Outreach: dry-run/fake delivery only; no live email delivery provider.
- Local SEO: deterministic website/citation-input analysis; no GBP, reviews, or rank-tracking provider.
- Google Search Console: a read-only OAuth refresh-token integration for authorized property discovery and persisted search-performance snapshots. It exposes Google-supplied clicks, impressions, CTR, and average position separately from paid-media metrics; it is not real-time rank tracking.
- Analytics preserves source attribution and currency. It does not perform FX conversion or cross-platform conversion deduplication.

## Google Search Console setup

Nexora uses the Google Search Console API directly over HTTPS and requests only the `https://www.googleapis.com/auth/webmasters.readonly` scope. In Google Cloud, enable the Search Console API, create an OAuth client, and complete a consent flow that produces a refresh token for an account with access to the desired Search Console property. Set these local or hosted-secret environment variables:

```text
GSC_CLIENT_ID=
GSC_CLIENT_SECRET=
GSC_REFRESH_TOKEN=
```

No client secret, refresh token, or access token is stored in SQLite or shown in the dashboard. In the SEO workspace, use **Discover properties**, select an authorized URL-prefix or domain property, choose an explicit period, then use **Refresh data**. Refresh is user-triggered only; it persists idempotent historical snapshots for aggregate, query, page, and date dimensions. Search Console can omit dates without data and can return bounded top rows, so Nexora never fabricates missing rows or dates.

## Controlled beta deployment

Run Nexora as a Streamlit application on Python 3.12 with HTTPS terminated by the selected hosting platform or reverse proxy:

```bash
streamlit run dashboard/app.py --server.headless true
```

Set secrets through the hosting platform's secret manager/environment, never source files or a committed `.env`. `storage/` must be mounted on persistent storage because `storage/backlinks.db` contains runtime and audit data; ephemeral container filesystems are not suitable.

For controlled beta operations, use a private single-tenant deployment or trusted agency pilot. Application authentication and multi-tenancy are not implemented, so this application must not be exposed as a shared public SaaS instance.

Create SQLite backups with the application's `DatabaseManager.backup()` method, which uses SQLite's online backup API. Retain daily backups for 14 days, verify restore integrity regularly, and take a verified backup before schema or deployment changes.
