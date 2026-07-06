import os

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    supabase_url: str
    supabase_service_role_key: str
    # Anon/public key used to verify user JWTs (app.core.auth). Required with
    # no default: every authenticated endpoint depends on it, so a missing key
    # must fail loudly at startup instead of silently 500-ing every request.
    supabase_key: str
    # Optional: when absent, prediction synthesis runs in deterministic
    # fallback mode and a WARNING is logged at startup (app.main).
    gemini_api_key: str | None = None
    chart_engine_version: str = "1.4.0"
    environment: str = "development"

    # Support reading from .env file when running locally
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()

# Environments explicitly recognised as NON-production. Anything else —
# including typos, "staging" and empty strings — is treated as production, so
# every production-only guard fails closed (audit finding #12).
NON_PRODUCTION_ENVIRONMENTS = frozenset({"development", "dev", "local", "test"})


def is_production(environment: str | None = None) -> bool:
    """Fail-closed production check: True unless the environment is explicitly
    on the non-production allow-list. Defaults to ``settings.environment``."""
    env = settings.environment if environment is None else environment
    return env.strip().lower() not in NON_PRODUCTION_ENVIRONMENTS


# Shared Swiss Ephemeris path resolution (audit finding #16). Every engine
# reads SE_EPHE_PATH through this helper so the unset-variable fallback cannot
# diverge between engines again. None means the pyswisseph library default;
# real deployments (Dockerfile) set SE_EPHE_PATH explicitly.
SE_EPHE_PATH_ENV_VAR = "SE_EPHE_PATH"
DEFAULT_SE_EPHE_PATH: str | None = None


def get_se_ephe_path() -> str | None:
    """SE_EPHE_PATH from the environment, read at call time, else the shared
    default. Call-time reads keep test conftests and probes effective."""
    return os.environ.get(SE_EPHE_PATH_ENV_VAR) or DEFAULT_SE_EPHE_PATH
