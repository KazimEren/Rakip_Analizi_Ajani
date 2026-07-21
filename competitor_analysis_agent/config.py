from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str = ""
    supabase_key: str = ""
    supabase_db_url: str = ""

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-lite"

    apify_api_token: str = ""

    # Hard limits for scraping (Apify actors + Playwright), to bound API
    # usage/cost and wall-clock time per pipeline run.
    max_competitors_per_search: int = 10
    max_items_per_competitor: int = 15
    scrape_timeout_seconds: int = 45

    output_dir: str = "output"

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def has_apify(self) -> bool:
        return bool(self.apify_api_token)

    def resolve_dry_run(self, requested: bool | None) -> bool:
        """CLI flag wins when given; otherwise dry-run unless every real
        credential is present."""
        if requested is not None:
            return requested
        return not (self.has_supabase and self.has_gemini and self.has_apify)


def get_settings() -> Settings:
    return Settings()
