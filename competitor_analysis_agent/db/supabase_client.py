from __future__ import annotations

from competitor_analysis_agent.config import Settings


def create_supabase_client(settings: Settings):
    """Lazy import so this module only requires the `supabase` package to be
    installed when a live client is actually requested."""
    from supabase import Client, create_client

    if not settings.has_supabase:
        raise RuntimeError(
            "SUPABASE_URL / SUPABASE_KEY are not set; cannot create a live Supabase client."
        )
    client: Client = create_client(settings.supabase_url, settings.supabase_key)
    return client
