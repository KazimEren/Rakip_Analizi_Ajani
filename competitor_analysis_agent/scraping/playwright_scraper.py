"""Custom Playwright scraper for pages Apify doesn't have a ready actor for:
review sites (Trustpilot) and competitor pricing pages.

playwright is imported lazily so this module (and dry-run mode) works even
before `pip install playwright && playwright install chromium` has run.
"""

from __future__ import annotations

import re

from competitor_analysis_agent.config import Settings
from competitor_analysis_agent.models import Competitor, PricingDataPoint, RawComplaintText

# Common paths competitor sites publish pricing under, tried in order.
# "" (homepage) is the last resort -- marketing homepages sometimes tease a
# starting price even without a dedicated pricing page.
_PRICING_PATH_CANDIDATES = ["/pricing", "/plans", "/price", "/prices", ""]

# Matches both "$12.99" / "€12,99" style (symbol before) and "12.99 USD" /
# "9.99 EUR" style (code/symbol after). Boundary guards on both sides
# (no adjacent digit/separator) stop it from grabbing a fragment of a
# larger thousands-grouped number like "500,000" (users, revenue, etc.)
# or a year like "2026".
_PRICE_PATTERNS = [
    re.compile(r"(?<![\d.,])[$€£]\s?(\d{1,4}(?:[.,]\d{2})?)(?![\d.,])"),
    re.compile(r"(?<![\d.,])(\d{1,4}(?:[.,]\d{2})?)(?![\d.,])\s?(?:USD|EUR|GBP)\b", re.IGNORECASE),
]

# A price is only trusted if a billing-cadence word appears near it --
# this is what actually distinguishes "$12.99/mo" from an unrelated number
# (page view counts, phone numbers, unrelated stats) that happens to be
# formatted like currency.
_PRICING_CONTEXT_KEYWORDS = (
    "/mo", "/month", "per month", "monthly", "/yr", "/year", "per year",
    "annually", "annual", "/user", "per user", "per seat", "billed",
    "subscription", "plan", "tier", "trial", "pricing",
)
_CONTEXT_WINDOW = 40

# Consumer/prosumer SaaS pricing realistically tops out well under this;
# anything above is far more likely a false positive than a real plan price.
_MAX_PLAUSIBLE_PRICE = 2000.0


def _has_pricing_context(text_lower: str, start: int, end: int) -> bool:
    snippet = text_lower[max(0, start - _CONTEXT_WINDOW) : end + _CONTEXT_WINDOW]
    return any(keyword in snippet for keyword in _PRICING_CONTEXT_KEYWORDS)


def _extract_prices(text: str, limit: int) -> list[float]:
    text_lower = text.lower()
    prices: list[float] = []
    for pattern in _PRICE_PATTERNS:
        for match in pattern.finditer(text):
            if not _has_pricing_context(text_lower, match.start(), match.end()):
                continue
            try:
                value = float(match.group(1).replace(",", "."))
            except ValueError:
                continue
            if 0 < value <= _MAX_PLAUSIBLE_PRICE:
                prices.append(value)
            if len(prices) >= limit:
                return prices
    return prices


def _launch_browser(p):
    try:
        return p.chromium.launch()
    except Exception as exc:  # pragma: no cover - depends on local machine state
        raise RuntimeError(
            "Could not launch a Chromium browser. Run `playwright install chromium` first."
        ) from exc


def _get_sync_playwright():
    try:
        from playwright.sync_api import sync_playwright

        return sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "playwright is not installed. Run `pip install playwright && "
            "playwright install chromium` to enable live scraping."
        ) from exc


class PlaywrightScraper:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def scrape_reviews(self, competitor: Competitor, review_url: str | None = None) -> list[RawComplaintText]:
        url = review_url
        if not url and competitor.website:
            # Fallback guess when discovery found nothing -- often wrong
            # (Trustpilot's slug for a company doesn't always match its
            # domain), but better than skipping entirely.
            domain = competitor.website.split("//")[-1].split("/")[0]
            url = f"https://www.trustpilot.com/review/{domain}"
        if not url:
            return []
        max_reviews = self._settings.max_items_per_competitor
        timeout_ms = self._settings.scrape_timeout_seconds * 1000

        sync_playwright = _get_sync_playwright()
        results: list[RawComplaintText] = []
        with sync_playwright() as p:
            browser = _launch_browser(p)
            try:
                page = browser.new_page()
                try:
                    page.goto(url, timeout=timeout_ms)
                except Exception:
                    # No Trustpilot page at this URL / unreachable -- not every
                    # competitor has one, so this is an expected, non-fatal outcome.
                    return []
                # TODO: Trustpilot's review-card selector changes periodically --
                # verify against the live DOM once this runs for real.
                cards = page.locator("[data-service-review-card-paper]").all()[:max_reviews]
                for card in cards:
                    text = card.inner_text().strip()
                    if text:
                        results.append(
                            RawComplaintText(competitor_name=competitor.name, source="Trustpilot", raw_text=text)
                        )
            finally:
                browser.close()
        return results

    def scrape_pricing(self, competitor: Competitor) -> list[PricingDataPoint]:
        if not competitor.website:
            return []
        base_url = competitor.website.rstrip("/")
        max_items = self._settings.max_items_per_competitor
        timeout_ms = self._settings.scrape_timeout_seconds * 1000

        sync_playwright = _get_sync_playwright()
        with sync_playwright() as p:
            browser = _launch_browser(p)
            try:
                page = browser.new_page()
                # Heuristic: try a handful of common pricing-page paths (and
                # finally the homepage) until one yields recognizable price
                # tokens. Not every competitor publishes prices at /pricing,
                # so a single fixed path was too fragile to rely on.
                for path in _PRICING_PATH_CANDIDATES:
                    try:
                        page.goto(base_url + path, timeout=timeout_ms)
                        body_text = page.inner_text("body")
                    except Exception:
                        continue
                    prices = _extract_prices(body_text, max_items)
                    if prices:
                        return [
                            PricingDataPoint(competitor_name=competitor.name, price=price, currency="USD")
                            for price in prices
                        ]
                return []
            finally:
                browser.close()
