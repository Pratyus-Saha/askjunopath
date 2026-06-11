# Health Endpoint Specification

**File:** `backend/app/main.py`
**Route:** `GET /health`
**Status:** Day 1 contract

## Response Shape

`/health` must always return HTTP 200 for local health checks unless the FastAPI process itself is unavailable.

Required top-level fields:

- `status`: `"ok"` when all checks pass, otherwise `"degraded"`
- `version`: application or engine version string
- `app_env`: current app environment
- `timestamp`: UTC ISO 8601 timestamp
- `checks`: object containing sub-checks

Required checks:

- `checks.ephemeris`
- `checks.database`

Each check returns:

- `status`: `"ok"`, `"degraded"`, or `"skipped"`
- `detail`: short human-readable summary

## Ephemeris Check

The ephemeris check safely attempts to import:

`backend.engines.ephemeris_engine.ephemeris_files_ok`

If that import path is unavailable in the current repo layout, it may fall back to:

`app.engines.ephemeris_engine.ephemeris_files_ok`

If no engine module exists yet, or if the check raises, `/health` returns `status: "degraded"` for the ephemeris check and still returns HTTP 200.

No real `.se1` files are required for unit tests. Missing or invalid `SE_EPHE_PATH` must degrade safely, never return HTTP 500.

## Database Check

The database check uses the app's existing database pattern when available. In the current app, that means checking whether the existing Supabase client has initialized.

If no database client exists, credentials are absent, or a probe raises, `/health` returns `status: "skipped"` or `status: "degraded"` for the database check and still returns HTTP 200.

Do not add new Supabase logic outside the approved health file. No real Supabase credentials are required for unit tests.
