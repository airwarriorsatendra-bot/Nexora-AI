# Nexora AI Beta 17 web migration

## Architecture

```text
Browser -> Next.js (`web/`) -> FastAPI (`api/`)
                              -> existing compositions and services
                              -> existing repositories -> SQLite
                              -> existing providers (explicit actions only)
```

Next.js owns presentation and browser interaction. FastAPI is a thin typed HTTP adapter. Existing Python services remain the source of truth. The Streamlit dashboard remains the fallback and parity reference.

Authentication is deferred to the SaaS foundation. Beta 17 remains a single-user development deployment; it does not present a fake login or claim production multi-user authorization.

## Local development

From the repository root, run the API in one terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Run the web application in another terminal:

```powershell
cd web
npm.cmd install
npm.cmd run dev
```

The API defaults to port `8000`; Next.js defaults to `3000`. `run_api.bat` and `run_web.bat` provide equivalent Windows entry points. Existing Streamlit launch instructions and files remain intact.

## Configuration

- `NEXORA_ALLOWED_ORIGINS`: comma-separated explicit browser origins for FastAPI CORS.
- `NEXORA_API_BASE_URL`: server-only Next.js connection to FastAPI.
- `NEXORA_API_HOST` and `NEXORA_API_PORT`: launch-script/deployment settings.

No provider secret is exposed through a `NEXT_PUBLIC_*` variable. Settings endpoints return configuration presence only.

## Safety and freshness

Read routes load persisted SQLite evidence and do not refresh Google, Moz, Gmail, SERP, GBP, or AI providers. Technical audits remain explicit POST actions. Next.js server reads use `no-store`; provider operations are not cached.
