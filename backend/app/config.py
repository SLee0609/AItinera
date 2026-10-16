from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend settings, read from environment variables (and `backend/.env` locally)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    # "minimal", "low", "medium" or "high"; empty to use the model's default.
    gemini_thinking_level: str = "low"
    # Server-side key, restricted to Places API (New) and Routes API.
    google_maps_server_key: str = ""
    # Supabase project URL (https://<ref>.supabase.co) and its secret key, which bypasses row level security.
    supabase_url: str = ""
    supabase_secret_key: str = ""

    # Comma-separated origins allowed to call the API from a browser (local development).
    allowed_origins: str = "http://localhost:5173"

    attractions_per_day: int = 4
    candidates_per_day: int = 6
    max_stops_per_day: int = 8
    balance_tolerance: float = 1.25
    city_padding_km: float = 10.0
    route_polylines: bool = True
    pipeline_timeout_s: float = 55.0

    @property
    def storage_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_secret_key)

    @property
    def supabase_base_url(self) -> str:
        return self.supabase_url.rstrip("/")

    @property
    def allowed_origin_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
