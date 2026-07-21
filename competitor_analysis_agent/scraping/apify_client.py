"""Real, Apify-backed competitor search and social-content collection.

apify_client is imported lazily so this module (and dry-run mode) works
without the package installed / without a real APIFY_API_TOKEN.
"""

from __future__ import annotations

import re

from competitor_analysis_agent.config import Settings
from competitor_analysis_agent.models import Competitor, RawContentItem

# TODO: verify these actor IDs (and their output field names, used below)
# against the live Apify Store once a real APIFY_API_TOKEN is available --
# actor slugs and output shapes can change over time.
GOOGLE_SEARCH_ACTOR_ID = "apify/google-search-scraper"
INSTAGRAM_ACTOR_ID = "apify/instagram-scraper"
TIKTOK_ACTOR_ID = "clockworks/tiktok-scraper"
YOUTUBE_ACTOR_ID = "streamers/youtube-scraper"

_SOCIAL_ACTOR_BY_PLATFORM = {
    "Instagram": INSTAGRAM_ACTOR_ID,
    "TikTok": TIKTOK_ACTOR_ID,
    "YouTube": YOUTUBE_ACTOR_ID,
}

# competitor.website is the company's own domain (from Google search
# results), which is generally NOT a profile URL on these platforms -- the
# actors reject anything that isn't. Validate before calling so a mismatch
# is a graceful skip instead of an API error that kills the whole run. Also
# used to recognize a genuine profile URL among discover_social_profile_url's
# search results (as opposed to e.g. a news article that merely links one).
_PLATFORM_URL_PATTERNS = {
    "Instagram": re.compile(r"^(https://)?(www\.)?instagram\.com/[A-Za-z0-9._-]+(/.*)?$", re.IGNORECASE),
    "TikTok": re.compile(r"^(https://)?(www\.)?tiktok\.com/@[A-Za-z0-9._-]+(/.*)?$", re.IGNORECASE),
    "YouTube": re.compile(
        r"^(https://)?(www\.)?youtube\.com/(@|channel/|c/|user/)[A-Za-z0-9._-]+(/.*)?$", re.IGNORECASE
    ),
}

_SOCIAL_SITE_SEARCH_FILTERS = {
    "Instagram": "site:instagram.com",
    "TikTok": "site:tiktok.com",
    "YouTube": "site:youtube.com",
}


def build_social_scrape_input(platform: str, profile_url: str, max_items: int) -> dict:
    """Each Apify social actor has its own input field names -- verified
    against each actor's published input schema on the Apify Store
    (apify/instagram-scraper, clockworks/tiktok-scraper,
    streamers/youtube-scraper). Getting these wrong doesn't error loudly:
    the actor just silently ignores the URL/limit and the run comes back
    with zero items (this is exactly what happened before this was fixed --
    YouTube's "directUrls"/"resultsLimit" aren't real fields on that actor,
    so every video limit stayed at its default of 0)."""
    if platform == "Instagram":
        return {"directUrls": [profile_url], "resultsLimit": max_items, "resultsType": "posts"}
    if platform == "TikTok":
        return {"profiles": [profile_url], "resultsPerPage": max_items}
    if platform == "YouTube":
        return {
            "startUrls": [{"url": profile_url}],
            "maxResults": max_items,
            "maxResultsShorts": max_items,
            "maxResultStreams": 0,
        }
    raise ValueError(f"No known Apify input shape for platform={platform!r}")

# Coarse ccTLD -> country hints for tagging a competitor's likely home
# market from its domain. Approximate by nature; a .com competitor yields
# no hint and is left for the step-2 LLM reasoning to place geographically.
_COUNTRY_TLD_HINTS = {
    "de": "Germany", "fr": "France", "co.uk": "United Kingdom", "uk": "United Kingdom",
    "mx": "Mexico", "br": "Brazil", "tr": "Turkey", "in": "India", "ca": "Canada",
    "au": "Australia", "jp": "Japan", "kr": "South Korea", "nl": "Netherlands",
    "es": "Spain", "it": "Italy", "pl": "Poland", "se": "Sweden", "za": "South Africa",
}

# --- Filtering out non-competitor search results ---------------------------
# Product-discovery keywords (e.g. "AI novel generator") are dominated in
# Google results by blog listicles ("10 Best AI Novel Generators..."),
# review aggregators, and social/forum threads -- none of which are an
# actual competitor's own site. Without this filter, search_competitors
# happily treats a listicle's title as a "competitor name" and its
# publisher's domain as the "website", which then poisons every downstream
# step (pricing, reviews, social discovery all search for a nonsense name).

_LISTICLE_TITLE_RE = re.compile(
    r"(^\s*\d+\s+(best|top|free)\b)"      # "10 Best ...", "7 Free ..."
    r"|(\b(best|top)\s+\d+\b)"            # "Best 10 ..."
    r"|(\bvs\.?\b)"                       # "X vs Y"
    r"|(\b(review|reviews|alternatives?|comparison|roundup)\b)",
    re.IGNORECASE,
)

# Content aggregators, review sites, social platforms, and forum/Q&A sites
# that routinely rank for product-discovery keywords but are never
# themselves the product being searched for.
_NON_PRODUCT_DOMAINS = {
    "medium.com", "reddit.com", "quora.com", "youtube.com", "wikipedia.org",
    "forbes.com", "techcrunch.com", "businessinsider.com", "g2.com",
    "capterra.com", "producthunt.com", "trustpilot.com", "pcmag.com",
    "zapier.com", "makeuseof.com", "toptenreviews.com", "softwareadvice.com",
    "getapp.com", "wikihow.com", "linkedin.com", "facebook.com", "twitter.com",
    "x.com", "instagram.com", "tiktok.com", "pinterest.com", "slant.co",
    "alternativeto.net", "sourceforge.net", "github.com", "blog.google",
}


def is_competitor_result(title: str, domain: str) -> bool:
    """True if a Google organic result plausibly IS a product/company's own
    site, as opposed to a blog post, listicle, review aggregator, or social
    platform that merely mentions one."""
    bare_domain = domain[4:] if domain.startswith("www.") else domain
    if any(bare_domain == d or bare_domain.endswith("." + d) for d in _NON_PRODUCT_DOMAINS):
        return False
    if _LISTICLE_TITLE_RE.search(title):
        return False
    return True


# Splits a page <title> down to its leading brand-name segment, e.g.
# "Sudowrite - Best AI Writing Partner for Fiction" -> "Sudowrite" and
# "aiWriter.ai: Free AI Story Generator & Writer" -> "aiWriter.ai". A bare
# "-" only counts as a separator when surrounded by spaces, so compound
# hyphenated names ("E-commerce Tool") aren't chopped in half.
_TITLE_SEPARATOR_RE = re.compile(r"\s-\s|\s*[:|–—]\s+")


def clean_competitor_name(title: str, domain: str) -> str:
    """Extracts a plausible brand name from a full search-result title,
    since the raw title (used as Competitor.name) is page-title marketing
    copy, not a company name -- e.g. it shouldn't end up stored as
    "Sudowrite - Best AI Writing Partner for Fiction" in the DB."""
    candidate = _TITLE_SEPARATOR_RE.split(title.strip(), maxsplit=1)[0].strip()
    if len(candidate) >= 2:
        return candidate
    # Leading segment was empty/too short (e.g. title started with the
    # separator) -- fall back to the domain's label as a best guess.
    bare_domain = domain[4:] if domain.startswith("www.") else domain
    label = bare_domain.split(".")[0]
    return label.capitalize() if label else title.strip()


class ApifyScraper:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = None

    def _get_client(self):
        if self._client is None:
            from apify_client import ApifyClient

            self._client = ApifyClient(self._settings.apify_api_token)
        return self._client

    def _run_actor(self, actor_id: str, run_input: dict) -> list[dict]:
        client = self._get_client()
        run = client.actor(actor_id).call(
            run_input=run_input, timeout_secs=self._settings.scrape_timeout_seconds
        )
        return list(client.dataset(run["defaultDatasetId"]).iterate_items())

    def search_competitors(self, keywords: list[str]) -> list[Competitor]:
        max_competitors = self._settings.max_competitors_per_search
        competitors: dict[str, Competitor] = {}
        for keyword in keywords:
            if len(competitors) >= max_competitors:
                break
            items = self._run_actor(
                GOOGLE_SEARCH_ACTOR_ID,
                {"queries": keyword, "resultsPerPage": max_competitors, "maxPagesPerQuery": 1},
            )
            for item in items:
                for result in item.get("organicResults", []):
                    if len(competitors) >= max_competitors:
                        break
                    url = result.get("url", "")
                    title = result.get("title", "")
                    if not url or not title:
                        continue
                    domain = url.split("//")[-1].split("/")[0].lower()
                    if domain in competitors:
                        continue
                    if not is_competitor_result(title, domain):
                        continue
                    country = next(
                        (name for tld, name in _COUNTRY_TLD_HINTS.items() if domain.endswith("." + tld)),
                        None,
                    )
                    competitors[domain] = Competitor(
                        name=clean_competitor_name(title, domain),
                        website=url,
                        continent=None,
                        country=country,
                        category=keyword,
                    )
        # Hard cap: never return more than max_competitors_per_search, even if
        # the last processed keyword's page pushed slightly past it.
        return list(competitors.values())[:max_competitors]

    def _search_organic_results(self, query: str, max_results: int) -> list[dict]:
        items = self._run_actor(
            GOOGLE_SEARCH_ACTOR_ID,
            {"queries": query, "resultsPerPage": max_results, "maxPagesPerQuery": 1},
        )
        results: list[dict] = []
        for item in items:
            results.extend(item.get("organicResults", []))
        return results[:max_results]

    def discover_social_profile_url(self, competitor: Competitor, platform: str) -> str | None:
        """Finds the competitor's actual profile URL on `platform` via a
        targeted site-scoped search, since competitor.website (their own
        domain) essentially never is one."""
        site_filter = _SOCIAL_SITE_SEARCH_FILTERS.get(platform)
        pattern = _PLATFORM_URL_PATTERNS.get(platform)
        if site_filter is None or pattern is None:
            return None
        query = f'"{competitor.name}" {site_filter}'
        for result in self._search_organic_results(query, max_results=3):
            url = result.get("url", "")
            if pattern.match(url):
                return url
        return None

    def discover_review_page_url(self, competitor: Competitor) -> str | None:
        """Finds the competitor's actual Trustpilot review page via search,
        instead of guessing `trustpilot.com/review/{domain}` (wrong whenever
        Trustpilot's slug for a company doesn't match its domain)."""
        query = f'"{competitor.name}" trustpilot reviews'
        for result in self._search_organic_results(query, max_results=3):
            url = result.get("url", "")
            if "trustpilot.com/review/" in url.lower():
                return url
        return None

    def scrape_social_content(self, competitor: Competitor, platform: str) -> list[RawContentItem]:
        actor_id = _SOCIAL_ACTOR_BY_PLATFORM.get(platform)
        if actor_id is None:
            return []

        pattern = _PLATFORM_URL_PATTERNS.get(platform)
        profile_url = competitor.website if competitor.website and pattern and pattern.match(competitor.website) else None
        if profile_url is None:
            profile_url = self.discover_social_profile_url(competitor, platform)
        if profile_url is None:
            return []

        max_items = self._settings.max_items_per_competitor
        items = self._run_actor(actor_id, build_social_scrape_input(platform, profile_url, max_items))

        results: list[RawContentItem] = []
        for item in items[:max_items]:
            # Field names below follow common conventions across Apify's
            # social scraper actors, but aren't guaranteed for every one --
            # confirm against real output once this runs live.
            text = item.get("caption") or item.get("text") or item.get("title") or ""
            url = item.get("url") or item.get("webVideoUrl") or item.get("postUrl")
            engagement = item.get("likesCount") or item.get("viewCount") or item.get("diggCount")
            results.append(
                RawContentItem(
                    competitor_name=competitor.name,
                    platform=platform,
                    content_url=url,
                    raw_text_or_transcript=text,
                    engagement_note=f"engagement={engagement}" if engagement is not None else "",
                )
            )
        return results
