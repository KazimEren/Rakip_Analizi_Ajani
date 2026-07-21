"""Runs ADIM 1-5 end to end and persists the result."""

from __future__ import annotations

import logging

from competitor_analysis_agent.config import Settings
from competitor_analysis_agent.db.repository import get_repository
from competitor_analysis_agent.llm.gemini_client import get_llm_client
from competitor_analysis_agent.models import (
    MarketAndGapAnalysis,
    PricingDataPoint,
    RawComplaintText,
    RawContentItem,
    ViralContent,
)
from competitor_analysis_agent.scraping.scraper import get_scraper
from competitor_analysis_agent.steps.step1_keywords import run_step1
from competitor_analysis_agent.steps.step2_geo_filter import run_step2
from competitor_analysis_agent.steps.step3_pricing import run_step3
from competitor_analysis_agent.steps.step4_gap_analysis import run_step4
from competitor_analysis_agent.steps.step5_viral_content import run_step5

SOCIAL_PLATFORMS = ["Instagram", "TikTok", "YouTube", "LinkedIn"]

logger = logging.getLogger(__name__)


def run_pipeline(
    project_description: str,
    project_name: str,
    settings: Settings,
    dry_run: bool,
) -> tuple[MarketAndGapAnalysis, list[ViralContent]]:
    llm = get_llm_client(settings, dry_run)
    scraper = get_scraper(settings, dry_run)

    # ADIM 1: anahtar kelime + rakip kategorisi türetme
    logger.info("ADIM 1: Proje açıklamasından anahtar kelimeler türetiliyor...")
    keywords_and_categories = run_step1(llm, project_description)
    logger.info("ADIM 1 tamamlandı: %d anahtar kelime türetildi.", len(keywords_and_categories.keywords))

    # Rakip keşfi (ADIM 2'yi besler)
    logger.info("Rakip keşfi başlıyor (arama motoru taraması)...")
    competitors = scraper.search_competitors(keywords_and_categories.keywords)
    if not competitors:
        raise ValueError("Türetilen anahtar kelimelerle hiç rakip bulunamadı; akış devam edemiyor.")
    logger.info("%d rakip bulundu: %s", len(competitors), ", ".join(c.name for c in competitors))

    # ADIM 2: coğrafi + PPP filtreleme
    logger.info("ADIM 2: Coğrafi ve PPP filtreleme yapılıyor...")
    recommended_continent, top_3_countries = run_step2(llm, competitors)
    logger.info("ADIM 2 tamamlandı: önerilen kıta=%s", recommended_continent)

    # ADIM 3: fiyatlandırma benchmark
    logger.info("ADIM 3: Rakip fiyatlandırmaları taranıyor...")
    pricing_points: list[PricingDataPoint] = []
    for competitor in competitors:
        pricing_points.extend(scraper.scrape_pricing(competitor))
    pricing_matrix = run_step3(llm, pricing_points, top_3_countries, competitors)
    logger.info(
        "ADIM 3 tamamlandı: min=%s avg=%s max=%s önerilen_giriş=%s",
        pricing_matrix.min_price,
        pricing_matrix.avg_price,
        pricing_matrix.max_price,
        pricing_matrix.recommended_entry_price,
    )

    # ADIM 4: şikayet analizi -> ekstra değer önerileri
    logger.info("ADIM 4: Kullanıcı şikayetleri/yorumları taranıyor...")
    complaints: list[RawComplaintText] = []
    for competitor in competitors:
        complaints.extend(scraper.scrape_reviews(competitor))
    strategic_value_adds = run_step4(llm, complaints, competitors)
    logger.info("ADIM 4 tamamlandı: %d strateji önerisi üretildi.", len(strategic_value_adds))

    # ADIM 5: tutan içerik anatomi analizi
    logger.info("ADIM 5: Rakiplerin sosyal medya içerikleri taranıyor (Instagram/TikTok/YouTube/LinkedIn)...")
    content_items: list[RawContentItem] = []
    for competitor in competitors:
        content_items.extend(scraper.scrape_social_content(competitor, SOCIAL_PLATFORMS))
    viral_contents = run_step5(llm, content_items)
    logger.info("ADIM 5 tamamlandı: %d viral içerik analiz edildi.", len(viral_contents))

    market_analysis = MarketAndGapAnalysis(
        project_name=project_name,
        recommended_continent=recommended_continent,
        top_3_countries=top_3_countries,
        pricing_matrix=pricing_matrix,
        strategic_value_adds=strategic_value_adds,
    )

    logger.info("Sonuçlar kaydediliyor...")
    repository = get_repository(settings, dry_run)
    repository.save_market_analysis(market_analysis)
    repository.save_viral_contents(viral_contents)
    logger.info("Kayıt tamamlandı.")

    return market_analysis, viral_contents
