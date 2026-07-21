"""ADIM 2: Küresel coğrafi ve sosyo-ekonomik filtreleme.

The LLM proposes a continent + candidate countries; the mid-tier-income
exclusion rule itself is enforced deterministically in Python
(filter_by_ppp_tier), not trusted to the LLM's guessed economic knowledge.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from competitor_analysis_agent.data.country_names_tr import to_turkish_country_name, to_turkish_ppp_status
from competitor_analysis_agent.data.ppp_tiers import get_tier, is_at_least_upper_middle
from competitor_analysis_agent.llm.gemini_client import LLMClient
from competitor_analysis_agent.llm.prompts import step2_geo_filter_prompt
from competitor_analysis_agent.models import CandidateCountry, Competitor, TopCountry

logger = logging.getLogger(__name__)

# CLAUDE.md requires exactly the first 3 target countries. A single LLM pass
# can propose mostly countries that don't pass the income-tier filter (e.g.
# it defaults to the region's biggest/best-known markets, which are often
# lower-middle income) -- rather than silently shipping fewer than 3
# countries, ask for more distinct candidates in the same continent, merging
# across attempts, before giving up.
_MIN_QUALIFYING_COUNTRIES = 3
_MAX_STEP2_ATTEMPTS = 3


class Step2LLMOutput(BaseModel):
    recommended_continent: str
    candidate_countries: list[CandidateCountry]


def _dedupe_candidates(candidates: list[CandidateCountry]) -> list[CandidateCountry]:
    """Keeps the first occurrence of each country (case-insensitive), in
    order -- retry attempts may re-propose an already-seen country."""
    seen: set[str] = set()
    deduped: list[CandidateCountry] = []
    for c in candidates:
        key = c.country.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)
    return deduped


def filter_by_ppp_tier(candidates: list[CandidateCountry], limit: int = 3) -> list[TopCountry]:
    """Pure function, no network/LLM: excludes any candidate below the
    upper-middle income tier, then ranks the survivors in proposal order.

    The PPP match itself is done against the LLM's English country name
    (data/ppp_tiers.py's keys); the country name and income-tier label are
    only translated to Turkish afterwards, for display/persistence, so the
    match can't be broken by translation drift/synonyms."""
    survivors = [c for c in candidates if is_at_least_upper_middle(c.country)]
    top = survivors[:limit]
    return [
        TopCountry(
            rank=i + 1,
            country=to_turkish_country_name(c.country),
            rationale=c.rationale,
            ppp_status=to_turkish_ppp_status(get_tier(c.country)),
        )
        for i, c in enumerate(top)
    ]


def run_step2(llm: LLMClient, competitors: list[Competitor]) -> tuple[str, list[TopCountry]]:
    system, user = step2_geo_filter_prompt(competitors)
    result = llm.complete_structured(system, user, Step2LLMOutput)
    recommended_continent = result.recommended_continent

    all_candidates = list(result.candidate_countries)
    top = filter_by_ppp_tier(_dedupe_candidates(all_candidates), limit=_MIN_QUALIFYING_COUNTRIES)

    attempt = 1
    while len(top) < _MIN_QUALIFYING_COUNTRIES and attempt < _MAX_STEP2_ATTEMPTS:
        attempt += 1
        logger.info(
            "ADIM 2: yalnızca %d ülke PPP filtresini geçti, %d. denemede daha fazla aday isteniyor...",
            len(top),
            attempt,
        )
        already_proposed = [c.country for c in _dedupe_candidates(all_candidates)]
        system, user = step2_geo_filter_prompt(
            competitors, locked_continent=recommended_continent, exclude_countries=already_proposed
        )
        retry_result = llm.complete_structured(system, user, Step2LLMOutput)
        all_candidates.extend(retry_result.candidate_countries)
        top = filter_by_ppp_tier(_dedupe_candidates(all_candidates), limit=_MIN_QUALIFYING_COUNTRIES)

    if len(top) < _MIN_QUALIFYING_COUNTRIES:
        raise ValueError(
            f"Only {len(top)} candidate countries in {recommended_continent!r} passed the "
            f"upper-middle-income-or-above PPP filter after {attempt} attempt(s) (need "
            f"{_MIN_QUALIFYING_COUNTRIES}). Widen the LLM's candidate list or extend "
            "data/ppp_tiers.py coverage."
        )
    return recommended_continent, top
