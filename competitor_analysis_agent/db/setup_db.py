"""Applies db/schema.sql to the Supabase Postgres database.

supabase-py talks to Supabase through PostgREST, which cannot execute
arbitrary DDL. So this script takes one of two paths:

  1. If SUPABASE_DB_URL (a direct Postgres connection string) is set, it
     connects with psycopg2 and runs schema.sql directly.
  2. Otherwise, it prints schema.sql and instructs the user to paste it into
     the Supabase Dashboard's SQL Editor.

Run with: python -m competitor_analysis_agent.db.setup_db
"""

from __future__ import annotations

import sys
from pathlib import Path

from competitor_analysis_agent.config import get_settings

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _print_manual_instructions(schema_sql: str) -> None:
    print(
        "SUPABASE_DB_URL is not set, so the schema can't be applied automatically.\n"
        "Copy the SQL below into the Supabase Dashboard > SQL Editor and run it:\n"
    )
    print("-" * 70)
    print(schema_sql)
    print("-" * 70)


def main() -> int:
    settings = get_settings()
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    if not settings.supabase_db_url:
        _print_manual_instructions(schema_sql)
        return 0

    import psycopg2

    print("Connecting to Supabase Postgres via SUPABASE_DB_URL...")
    conn = psycopg2.connect(settings.supabase_db_url)
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        print("Schema applied: market_and_gap_analysis, viral_contents (+ indexes).")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
