from datetime import datetime, timezone
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers.chart import router as chart_router
from app.routers.internal import router as internal_router

app = FastAPI(
    title="AskJunoPath API",
    version=settings.chart_engine_version,
)

# Configure CORS (Allow all for Day 1 MVP)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include chart calculations router
app.include_router(chart_router)

# Internal/dev-only career prediction wrapper (D029). Self-gates to non-production
# environments at request time; invisible (404) in production. Not a public API.
app.include_router(internal_router)


def _ephemeris_check() -> dict[str, str]:
    ephe_path = os.environ.get("SE_EPHE_PATH")
    se1_file_count = 0
    if ephe_path:
        path = Path(ephe_path)
        if path.is_dir():
            se1_file_count = len(list(path.glob("*.se1")))

    try:
        from app.engines.ephemeris_engine import ephemeris_files_ok

        if ephemeris_files_ok():
            return {
                "status": "ok",
                "detail": (
                    "app.engines.ephemeris_engine.ephemeris_files_ok passed; "
                    f"{se1_file_count} .se1 file(s) at {ephe_path}"
                ),
            }

        return {
            "status": "degraded",
            "detail": (
                "app.engines.ephemeris_engine.ephemeris_files_ok returned false; "
                f"SE_EPHE_PATH={ephe_path!r}; .se1 file count={se1_file_count}"
            ),
        }
    except Exception as exc:
        return {
            "status": "degraded",
            "detail": f"ephemeris check failed: {exc}",
        }


def _database_check() -> dict[str, str]:
    try:
        from app.core import db

        client = getattr(db, "supabase", None)
        if client is None:
            return {
                "status": "skipped",
                "detail": "Supabase client is not initialized",
            }

        getattr(client, "table")
        return {
            "status": "ok",
            "detail": "Supabase client initialized",
        }
    except Exception as exc:
        return {
            "status": "degraded",
            "detail": f"database check failed: {exc}",
        }


@app.get("/health")
def health_check():
    """
    Health check endpoint for Azure Container Apps probes and local validation.
    """
    checks = {
        "ephemeris": _ephemeris_check(),
        "database": _database_check(),
    }
    overall_status = (
        "ok"
        if all(check["status"] == "ok" for check in checks.values())
        else "degraded"
    )

    return {
        "status": overall_status,
        "version": settings.chart_engine_version,
        "app_env": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "service": "askjunopath-api",
        "checks": checks,
    }
