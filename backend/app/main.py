from datetime import datetime, timezone
from importlib import import_module

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers.chart import router as chart_router

app = FastAPI(
    title="AskJunoPath API",
    version="1.0.0"
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


def _ephemeris_check() -> dict[str, str]:
    module_names = (
        "backend.engines.ephemeris_engine",
        "app.engines.ephemeris_engine",
        "backend.app.engines.ephemeris_engine",
    )

    last_error: Exception | None = None
    for module_name in module_names:
        try:
            module = import_module(module_name)
            ephemeris_files_ok = getattr(module, "ephemeris_files_ok")
            if ephemeris_files_ok():
                return {
                    "status": "ok",
                    "detail": f"{module_name}.ephemeris_files_ok passed",
                }
            return {
                "status": "degraded",
                "detail": f"{module_name}.ephemeris_files_ok returned false",
            }
        except Exception as exc:
            last_error = exc

    return {
        "status": "degraded",
        "detail": f"ephemeris check unavailable: {last_error}",
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
        "version": "1.0.0",
        "app_env": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "service": "askjunopath-api",
        "checks": checks,
    }
