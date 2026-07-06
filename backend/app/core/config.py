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
