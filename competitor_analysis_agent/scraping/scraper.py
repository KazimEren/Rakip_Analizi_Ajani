from __future__ import annotations

from typing import Protocol

from competitor_analysis_agent.config import Settings
from competitor_analysis_agent.models import Competitor, PricingDataPoint, RawComplaintText, RawContentItem


class ScraperProtocol(Protocol):
    def search_competitors(self, keywords: list[str]) -> list[Competitor]: ...

    def scrape_reviews(self, competitor: Competitor) -> list[RawComplaintText]: ...

    def scrape_pricing(self, competitor: Competitor) -> list[PricingDataPoint]: ...

    def scrape_social_content(self, competitor: Competitor, platforms: list[str]) -> list[RawContentItem]: ...


class RealScraper:
    """Composes ApifyScraper (search + social content) and PlaywrightScraper
    (review sites + pricing pages) behind one interface."""

    def __init__(self, settings: Settings) -> None:
        from competitor_analysis_agent.scraping.apify_client import ApifyScraper
        from competitor_analysis_agent.scraping.playwright_scraper import PlaywrightScraper

        self._apify = ApifyScraper(settings)
        self._playwright = PlaywrightScraper(settings)

    def search_competitors(self, keywords: list[str]) -> list[Competitor]:
        return self._apify.search_competitors(keywords)

    def scrape_reviews(self, competitor: Competitor) -> list[RawComplaintText]:
        review_url = self._apify.discover_review_page_url(competitor)
        return self._playwright.scrape_reviews(competitor, review_url)

    def scrape_pricing(self, competitor: Competitor) -> list[PricingDataPoint]:
        return self._playwright.scrape_pricing(competitor)

    def scrape_social_content(self, competitor: Competitor, platforms: list[str]) -> list[RawContentItem]:
        items: list[RawContentItem] = []
        for platform in platforms:
            items.extend(self._apify.scrape_social_content(competitor, platform))
        return items


class MockScraper:
    """Dry-run stand-in backed by scraping/fixtures.py canned data."""

    def search_competitors(self, keywords: list[str]) -> list[Competitor]:
        from competitor_analysis_agent.scraping.fixtures import MOCK_COMPETITORS

        return list(MOCK_COMPETITORS)

    def scrape_reviews(self, competitor: Competitor) -> list[RawComplaintText]:
        from competitor_analysis_agent.scraping.fixtures import MOCK_COMPLAINTS

        return [c for c in MOCK_COMPLAINTS if c.competitor_name == competitor.name]

    def scrape_pricing(self, competitor: Competitor) -> list[PricingDataPoint]:
        from competitor_analysis_agent.scraping.fixtures import MOCK_PRICING

        return [p for p in MOCK_PRICING if p.competitor_name == competitor.name]

    def scrape_social_content(self, competitor: Competitor, platforms: list[str]) -> list[RawContentItem]:
        from competitor_analysis_agent.scraping.fixtures import MOCK_CONTENT

        return [c for c in MOCK_CONTENT if c.competitor_name == competitor.name and c.platform in platforms]


def get_scraper(settings: Settings, dry_run: bool) -> ScraperProtocol:
    if dry_run:
        return MockScraper()
    return RealScraper(settings)
