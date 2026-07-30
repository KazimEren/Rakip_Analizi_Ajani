"""CLI entrypoint.

Usage:
    python -m competitor_analysis_agent.main --project-description "..." --dry-run
    python -m competitor_analysis_agent.main --project-description "..." --live
"""

from __future__ import annotations

import argparse
import sys

from competitor_analysis_agent.config import get_settings
from competitor_analysis_agent.orchestrator import run_pipeline


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rakip ve Pazar Analizi Ajanı")
    parser.add_argument("--project-description", required=True, help="Proje fikri açıklaması")
    parser.add_argument(
        "--project-name", default=None, help="Proje adı (verilmezse açıklamadan türetilir)"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Mock veriyle çalıştır, Supabase'e yazmaz")
    mode.add_argument("--live", action="store_true", help="Gerçek API'lerle çalıştır, Supabase'e yazar")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    settings = get_settings()

    requested_dry_run = True if args.dry_run else (False if args.live else None)
    dry_run = settings.resolve_dry_run(requested_dry_run)

    project_name = args.project_name or args.project_description[:60]

    if dry_run:
        print("Dry-run modunda çalışıyor (mock LLM + mock scraping). Supabase'e gerçek yazım yapılmayacak.\n")
    else:
        print(f"Live modda çalışıyor. Model: {settings.gemini_model}\n")

    market_analysis, viral_contents, content_skeletons = run_pipeline(
        project_description=args.project_description,
        project_name=project_name,
        settings=settings,
        dry_run=dry_run,
    )

    if market_analysis.recommended_continent:
        print(f"Önerilen kıta: {market_analysis.recommended_continent}")
        print("İlk 3 ülke:")
        for country in market_analysis.top_3_countries or []:
            print(f"  {country.rank}. {country.country} ({country.ppp_status}) - {country.rationale}")

    if market_analysis.pricing_matrix:
        pm = market_analysis.pricing_matrix
        print(
            f"\nFiyat matrisi: min={pm.min_price} avg={pm.avg_price} max={pm.max_price} "
            f"onerilen_giris={pm.recommended_entry_price}"
        )

    if market_analysis.strategic_value_adds is not None:
        print(f"\n{len(market_analysis.strategic_value_adds)} strateji önerisi:")
        for va in market_analysis.strategic_value_adds:
            print(f"  - {va.competitor_weakness} -> {va.recommended_feature}")

    print(f"\n{len(viral_contents)} viral içerik analizi üretildi, {len(content_skeletons)} tier iskeleti üretildi.")

    if dry_run:
        print(f"\nÇıktı yazıldı: {settings.output_dir}/projects/{market_analysis.id}.json")
    else:
        print("\nSupabase tablolarına yazıldı: market_and_gap_analysis, viral_contents, content_skeletons")

    return 0


if __name__ == "__main__":
    sys.exit(main())
