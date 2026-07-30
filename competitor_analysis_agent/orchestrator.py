"""Runs ADIM 1-5 (or a selected subset of them) end to end and persists the
result.

Each ADIM is exposed as its own `run_*_module` function so the GUI can
trigger only the modules the user checked, instead of always paying for the
full 5-step scraping + LLM pipeline. `run_pipeline` is the default
"run everything" composition (used by the CLI and, until the GUI wires up
its own module checkboxes, by the GUI too); `discover_competitors` and the
per-module functions are also called directly by the GUI for scoped re-runs
(e.g. regenerating only content skeletons for an already-analyzed project).
"""

from __future__ import annotations

import logging
import re

from competitor_analysis_agent.config import Settings
from competitor_analysis_agent.db.repository import get_repository
from competitor_analysis_agent.llm.gemini_client import LLMClient, get_llm_client
from competitor_analysis_agent.models import (
    Competitor,
    ContentSkeleton,
    MarketAndGapAnalysis,
    PricingDataPoint,
    PricingMatrix,
    RawComplaintText,
    RawContentItem,
    StrategicValueAdd,
    TopCountry,
    ViralContent,
)
from competitor_analysis_agent.scraping.scraper import ScraperProtocol, get_scraper
from competitor_analysis_agent.steps.step1_keywords import run_step1
from competitor_analysis_agent.steps.step2_geo_filter import run_step2
from competitor_analysis_agent.steps.step3_pricing import run_step3
from competitor_analysis_agent.steps.step4_gap_analysis import run_step4
from competitor_analysis_agent.steps.step5_viral_content import run_step5
from competitor_analysis_agent.steps.step6_content_tiering import run_step6_tiering

SOCIAL_PLATFORMS = ["Instagram", "TikTok", "YouTube", "LinkedIn"]

# Checkbox keys, matching the GUI's 4 module toggles. Used as the default
# when a caller (CLI, existing GUI flow) doesn't pass an explicit selection
# -- i.e. today's "run everything" behavior.
DEFAULT_MODULES: dict[str, bool] = {
    "market_analysis": True,
    "pricing": True,
    "content_skeletons": True,
    "gap_analysis": True,
}

DEFAULT_CONTENT_SKELETON_COUNT = 3

logger = logging.getLogger(__name__)


def discover_competitors(
    llm: LLMClient, scraper: ScraperProtocol, project_description: str
) -> list[Competitor]:
    """ADIM 1 + rakip keşfi. Seçilen modüllerden bağımsız olarak, en az bir
    modül seçiliyse her zaman çalışır: diğer tüm modüllerin girdisi budur."""
    logger.info("ADIM 1: Proje açıklamasından anahtar kelimeler türetiliyor...")
    keywords_and_categories = run_step1(llm, project_description)
    logger.info("ADIM 1 tamamlandı: %d anahtar kelime türetildi.", len(keywords_and_categories.keywords))

    logger.info("Rakip keşfi başlıyor (arama motoru taraması)...")
    competitors = scraper.search_competitors(keywords_and_categories.keywords)
    if not competitors:
        raise ValueError("Türetilen anahtar kelimelerle hiç rakip bulunamadı; akış devam edemiyor.")
    logger.info("%d rakip bulundu: %s", len(competitors), ", ".join(c.name for c in competitors))
    return competitors


def run_market_module(llm: LLMClient, competitors: list[Competitor]) -> tuple[str, list[TopCountry]]:
    """ADIM 2: coğrafi + PPP filtreleme (checkbox 1: Pazar Analizi & Hedef Kitle)."""
    logger.info("ADIM 2: Coğrafi ve PPP filtreleme yapılıyor...")
    recommended_continent, top_3_countries = run_step2(llm, competitors)
    logger.info("ADIM 2 tamamlandı: önerilen kıta=%s", recommended_continent)
    return recommended_continent, top_3_countries


def run_pricing_module(
    llm: LLMClient,
    scraper: ScraperProtocol,
    competitors: list[Competitor],
    top_3_countries: list[TopCountry],
) -> PricingMatrix:
    """ADIM 3: fiyatlandırma benchmark (checkbox 2: Fiyatlandırma Stratejisi).

    top_3_countries may be empty if the market module wasn't selected this
    run -- run_step3 just proceeds without country-specific context."""
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
    return pricing_matrix


def run_gap_module(
    llm: LLMClient, scraper: ScraperProtocol, competitors: list[Competitor]
) -> list[StrategicValueAdd]:
    """ADIM 4: şikayet analizi -> ekstra değer önerileri (checkbox 4)."""
    logger.info("ADIM 4: Kullanıcı şikayetleri/yorumları taranıyor...")
    complaints: list[RawComplaintText] = []
    for competitor in competitors:
        complaints.extend(scraper.scrape_reviews(competitor))
    strategic_value_adds = run_step4(llm, complaints, competitors)
    logger.info("ADIM 4 tamamlandı: %d strateji önerisi üretildi.", len(strategic_value_adds))
    return strategic_value_adds


_ENGAGEMENT_RE = re.compile(r"engagement=(\d+)")


def _engagement_score(item: RawContentItem) -> int:
    match = _ENGAGEMENT_RE.search(item.engagement_note or "")
    return int(match.group(1)) if match else 0


def select_top_performing_content(items: list[RawContentItem], count: int) -> list[RawContentItem]:
    """Deterministically ranks scraped content by parsed engagement and keeps
    only the top `count` -- tier üretimi rastgele/her içerik için değil,
    sadece tuttuğu kesinleşen içerikler için LLM çağrısı yapmalı."""
    return sorted(items, key=_engagement_score, reverse=True)[:count]


def run_content_module(
    llm: LLMClient,
    scraper: ScraperProtocol,
    competitors: list[Competitor],
    count: int = DEFAULT_CONTENT_SKELETON_COUNT,
) -> tuple[list[ViralContent], list[ContentSkeleton]]:
    """ADIM 5 + Tier üretimi (checkbox 3: Tutan İçerik İskeletleri).

    Scrape edilen tüm içerikler arasından en yüksek etkileşimli `count`
    tanesi seçilir; yalnızca onlar için anatomi analizi (ADIM 5) ve ardından
    3 tier'li (Ayna/Hibrit/Özgün) içerik iskeleti üretilir."""
    logger.info("ADIM 5: Rakiplerin sosyal medya içerikleri taranıyor (Instagram/TikTok/YouTube/LinkedIn)...")
    content_items: list[RawContentItem] = []
    for competitor in competitors:
        content_items.extend(scraper.scrape_social_content(competitor, SOCIAL_PLATFORMS))

    top_items = select_top_performing_content(content_items, count)
    logger.info(
        "ADIM 5: %d taranan içerikten en yüksek etkileşimli %d tanesi seçildi.",
        len(content_items),
        len(top_items),
    )
    if not top_items:
        return [], []

    viral_contents = run_step5(llm, top_items)

    content_skeletons: list[ContentSkeleton] = []
    for item, viral in zip(top_items, viral_contents):
        content_skeletons.extend(run_step6_tiering(llm, item, viral))

    logger.info(
        "ADIM 5 tamamlandı: %d içerik analiz edildi, %d tier iskeleti üretildi.",
        len(viral_contents),
        len(content_skeletons),
    )
    return viral_contents, content_skeletons


def run_pipeline(
    project_description: str,
    project_name: str,
    settings: Settings,
    dry_run: bool,
    modules: dict[str, bool] | None = None,
    content_skeleton_count: int = DEFAULT_CONTENT_SKELETON_COUNT,
) -> tuple[MarketAndGapAnalysis, list[ViralContent], list[ContentSkeleton]]:
    resolved_modules = {**DEFAULT_MODULES, **(modules or {})}
    if not any(resolved_modules.values()):
        raise ValueError("En az bir modül seçilmeden analiz çalıştırılamaz.")

    llm = get_llm_client(settings, dry_run)
    scraper = get_scraper(settings, dry_run)

    competitors = discover_competitors(llm, scraper, project_description)

    recommended_continent: str | None = None
    top_3_countries: list[TopCountry] | None = None
    if resolved_modules["market_analysis"]:
        recommended_continent, top_3_countries = run_market_module(llm, competitors)

    pricing_matrix: PricingMatrix | None = None
    if resolved_modules["pricing"]:
        pricing_matrix = run_pricing_module(llm, scraper, competitors, top_3_countries or [])

    strategic_value_adds: list[StrategicValueAdd] | None = None
    if resolved_modules["gap_analysis"]:
        strategic_value_adds = run_gap_module(llm, scraper, competitors)

    viral_contents: list[ViralContent] = []
    content_skeletons: list[ContentSkeleton] = []
    if resolved_modules["content_skeletons"]:
        viral_contents, content_skeletons = run_content_module(
            llm, scraper, competitors, content_skeleton_count
        )

    market_analysis = MarketAndGapAnalysis(
        project_name=project_name,
        project_description=project_description,
        modules_run=resolved_modules,
        recommended_continent=recommended_continent,
        top_3_countries=top_3_countries,
        pricing_matrix=pricing_matrix,
        strategic_value_adds=strategic_value_adds,
    )
    for vc in viral_contents:
        vc.project_id = market_analysis.id
    for cs in content_skeletons:
        cs.project_id = market_analysis.id

    logger.info("Sonuçlar kaydediliyor...")
    repository = get_repository(settings, dry_run)
    repository.save_market_analysis(market_analysis)
    repository.save_viral_contents(viral_contents)
    repository.save_content_skeletons(content_skeletons)
    logger.info("Kayıt tamamlandı.")

    return market_analysis, viral_contents, content_skeletons
