"""System/user prompt builders for each of the 5 pipeline steps.

Every function returns a (system, user) tuple. The caller passes the user
prompt, together with the relevant pydantic output model, to
LLMClient.complete_structured().

Language policy: every analysis output this agent produces is read by a
Turkish-speaking user, so all free-text content (rationale, explanations,
summaries, feature descriptions) must be written entirely in Turkish -- see
_BASE_SYSTEM. The only two exceptions, called out explicitly in their own
prompts below, are step1's `keywords` (must stay English -- they're fed
directly into real search-engine/social-media queries, where English yields
far better competitor coverage regardless of the target market) and step2's
`country` field on each candidate (must stay English -- it's matched against
data/ppp_tiers.py's English-keyed income table; data/country_names_tr.py
translates it to Turkish for display *after* that deterministic match, so
the match itself is never at the mercy of translation drift/synonyms).
"""

from __future__ import annotations

import json

from competitor_analysis_agent.models import (
    Competitor,
    PricingDataPoint,
    RawComplaintText,
    RawContentItem,
    ViralContent,
)

_BASE_SYSTEM = (
    "You are an autonomous market and competitor analysis strategist. "
    "You reason carefully about global markets, pricing, and audience psychology. "
    "Always respond only through the provided tool call -- never in free text. "
    "Unless a field's own instructions explicitly say otherwise, write every "
    "free-text value you produce (rationale, explanations, summaries, feature "
    "descriptions, category labels) entirely in Turkish -- no English words or "
    "sentences -- regardless of what language the source material (project "
    "description, scraped reviews, social content) is written in."
)


def step1_keywords_prompt(project_description: str) -> tuple[str, str]:
    system = (
        _BASE_SYSTEM
        + " Task: given a project description, derive the global search keywords "
        "and competitor categories that should be used to find this project's "
        "real-world competitors across search engines and social media."
    )
    user = (
        f"Project description:\n{project_description}\n\n"
        "Produce 8-15 concise, high-signal global search keywords -- EXCEPTION to "
        "the Turkish-output rule: keywords must be in English, since most "
        "competitor research happens in English regardless of the target market, "
        "and they are used directly as real search-engine queries -- and 3-6 "
        "competitor_categories (types of products/services that compete with "
        "this project), written in Turkish."
    )
    return system, user


_STEP2_PPP_CRITERIA = (
    " A deterministic filter is then applied in code that keeps only countries "
    "classified upper-middle-income or high-income (World Bank income group "
    "definitions) -- bias your candidates toward countries you're confident "
    "meet that bar, even if they're smaller or less obvious markets than the "
    "biggest population centers in the region. A large, well-known "
    "lower-middle- or low-income country will be discarded regardless of how "
    "attractive its market otherwise looks, so proposing one doesn't help."
)

_STEP2_LANGUAGE_NOTE = (
    " EXCEPTION to the Turkish-output rule: write `recommended_continent` in "
    "Turkish (one of: Afrika, Asya, Avrupa, Kuzey Amerika, Güney Amerika, "
    "Okyanusya) and each candidate's `country` in English (its standard "
    "English name, e.g. \"South Africa\", not \"Güney Afrika\") -- country is "
    "matched against an English-keyed reference table in code and would "
    "silently fail that match if translated. Write every candidate's "
    "`rationale` in Turkish."
)


def step2_geo_filter_prompt(
    competitors: list[Competitor],
    locked_continent: str | None = None,
    exclude_countries: list[str] | None = None,
) -> tuple[str, str]:
    payload = [c.model_dump() for c in competitors]

    if locked_continent:
        # Retry path: the first pass didn't yield enough income-tier-qualifying
        # countries. Keep the continent fixed and ask for more, different
        # candidates instead of re-rolling the continent choice too.
        system = (
            _BASE_SYSTEM
            + " Task: too few of your previously proposed candidate countries "
            "passed the income-tier filter described below. Propose additional, "
            "distinct candidate countries within the SAME continent as before."
            + _STEP2_PPP_CRITERIA
            + _STEP2_LANGUAGE_NOTE
        )
        exclusion = ", ".join(exclude_countries or []) or "none yet"
        user = (
            f"Continent (fixed, do not change): {locked_continent}\n"
            f"Countries already proposed -- do not repeat these: {exclusion}\n\n"
            "Competitors found so far (name, continent, country, category):\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
            f"Propose at least 5 more candidate countries within {locked_continent} "
            "not already listed above. Set recommended_continent to the same "
            f"fixed value: {locked_continent!r}."
        )
        return system, user

    system = (
        _BASE_SYSTEM
        + " Task: given a list of competitors mapped to continents/countries, "
        "identify the continent with high potential and low saturation (avoid "
        "continents where competition is already dense), then propose candidate "
        "countries within that continent as expansion targets, each with a short "
        "rationale."
        + _STEP2_PPP_CRITERIA
        + " Propose at least 8 candidate countries so the downstream filter has "
        "enough to work with."
        + _STEP2_LANGUAGE_NOTE
    )
    user = (
        "Competitors found so far (name, continent, country, category):\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
        "Which continent is least saturated relative to its potential, and which "
        "countries within it should we consider entering first?"
    )
    return system, user


def step3_pricing_prompt(
    pricing_points: list[PricingDataPoint],
    min_price: float,
    avg_price: float,
    max_price: float,
    top_3_countries: list[str],
) -> tuple[str, str]:
    system = (
        _BASE_SYSTEM
        + " Task: given competitor pricing data and an already-computed "
        "min/avg/max price matrix, recommend a market-entry price and explain "
        "why, taking into account the socio-economic profile of the target "
        "countries. The recommended price should usually fall within or near "
        "the observed min/max range unless there is a clear reason to undercut "
        "or premium-position beyond it. Write the rationale entirely in Turkish."
    )
    payload = [p.model_dump() for p in pricing_points]
    user = (
        f"Observed competitor prices:\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
        f"Computed matrix: min={min_price}, avg={avg_price}, max={max_price}\n"
        f"Target entry countries: {', '.join(top_3_countries)}\n\n"
        "Recommend a market-entry price (same currency as the observed prices) and, "
        "in Turkish, a rationale."
    )
    return system, user


def step3_pricing_no_data_prompt(
    competitors: list[Competitor],
    top_3_countries: list[str],
) -> tuple[str, str]:
    """Used when scraping found zero usable prices (e.g. a freemium-heavy
    niche, or pricing pages that didn't yield extractable data). The LLM
    still has to propose a market-entry price -- grounded in general
    knowledge of the competitor category instead of scraped numbers -- since
    pricing_matrix is a required field on the output record."""
    system = (
        _BASE_SYSTEM
        + " Task: no competitor pricing could be scraped for this market. Using your "
        "general knowledge of this competitor category, estimate a reasonable "
        "market-entry price and explain your reasoning. Be explicit in the rationale "
        "(in Turkish) that this is an estimate, not derived from scraped data."
    )
    names = [c.name for c in competitors]
    categories = sorted({c.category for c in competitors if c.category})
    user = (
        f"Competitors found (no scrapeable pricing): {', '.join(names)}\n"
        f"Competitor categories: {', '.join(categories) if categories else 'unknown'}\n"
        f"Target entry countries: {', '.join(top_3_countries)}\n\n"
        "Propose a market-entry price (state the currency, typically USD) and, in "
        "Turkish, a rationale."
    )
    return system, user


def step4_gap_analysis_prompt(complaints: list[RawComplaintText]) -> tuple[str, str]:
    system = (
        _BASE_SYSTEM
        + " Task: given user complaints/negative reviews about competitors, "
        "identify the top recurring pain points and turn each into an "
        "actionable extra product/feature recommendation that would let our "
        "project stand out. Write both competitor_weakness and "
        "recommended_feature entirely in Turkish, even though the source "
        "complaints below may be in other languages."
    )
    payload = [c.model_dump() for c in complaints]
    user = (
        f"Complaints gathered about competitors:\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
        "Identify the 3 most important recurring weaknesses and, for each, propose "
        "one concrete recommended_feature that directly addresses it. Answer in Turkish."
    )
    return system, user


def step4_gap_analysis_no_data_prompt(competitors: list[Competitor]) -> tuple[str, str]:
    """Used when scraping found zero complaints (e.g. none of the competitors
    have a public review-site presence). strategic_value_adds is a required,
    non-empty-in-spirit field on the output record, so fall back to an LLM
    estimate grounded in general knowledge of the competitor category instead
    of silently shipping an empty list -- mirrors step3_pricing_no_data_prompt's
    fallback for the same kind of "scraping came back empty" situation."""
    system = (
        _BASE_SYSTEM
        + " Task: no scraped complaints or negative reviews could be found for "
        "these competitors. Using your general knowledge of this competitor "
        "category, infer the 3 most common/likely user pain points for products "
        "like these, and for each propose one concrete recommended_feature that "
        "directly addresses it. Be explicit in each competitor_weakness (in "
        "Turkish) that this is inferred from general category knowledge, not "
        "scraped reviews. Write both competitor_weakness and recommended_feature "
        "entirely in Turkish."
    )
    names = [c.name for c in competitors]
    categories = sorted({c.category for c in competitors if c.category})
    user = (
        f"Competitors (no scraped complaints available): {', '.join(names)}\n"
        f"Competitor categories: {', '.join(categories) if categories else 'unknown'}\n\n"
        "Identify the 3 most likely recurring weaknesses for this category and, for "
        "each, propose one concrete recommended_feature that directly addresses it. "
        "Answer in Turkish."
    )
    return system, user


def step5_viral_content_prompt(item: RawContentItem) -> tuple[str, str]:
    system = (
        _BASE_SYSTEM
        + " Task: break down a single piece of competitor social content into its "
        "4-stage retention anatomy, then summarize why it works. Be specific and "
        "concrete -- reference actual wording/visuals from the content where possible, "
        "not generic platitudes. Write all five output fields entirely in Turkish, "
        "even though the raw content below may be in another language -- you may "
        "quote a short original-language phrase from it, but the analysis itself "
        "(your own sentences) must be Turkish."
    )
    user = (
        f"Platform: {item.platform}\nCompetitor: {item.competitor_name}\n"
        f"Content URL: {item.content_url or 'n/a'}\n"
        f"Engagement note: {item.engagement_note or 'n/a'}\n\n"
        f"Raw text/transcript:\n{item.raw_text_or_transcript}\n\n"
        "Analyze, writing every field in Turkish:\n"
        "- hook_analysis (0-3s): the attention-grabbing hook, visual/text style\n"
        "- intro_and_problem (3-7s): how the problem or curiosity gap is introduced\n"
        "- body_and_value (7-25s): the solution/value delivery and narrative flow\n"
        "- call_to_action (25-30s): the closing CTA mechanism\n"
        "- overall_summary: why this content retains attention, algorithmically and psychologically"
    )
    return system, user


def step6_content_tiering_prompt(item: RawContentItem, viral: ViralContent) -> tuple[str, str]:
    system = (
        _BASE_SYSTEM
        + " Task: this piece of competitor content has already been confirmed as a top "
        "performer and broken down into its hook/intro/body/CTA anatomy. Now produce 3 "
        "distinct content-skeleton variations our own project can use, each with its own "
        "hook/intro/body/cta fields, ready for a downstream content-generation agent:\n"
        "- tier1_ayna (Mirror/re-skin): the core message, hook and logic stay 100% the "
        "same as the original; only the visual concept and wording are lightly refreshed "
        "for our brand.\n"
        "- tier2_hibrit (Hybrid): the core meaning stays the same, but layer in our own "
        "value propositions and extra touches on top of it.\n"
        "- tier3_ozgun (Re-imagined): keep the same core message and emotion, but write it "
        "entirely from scratch in our own original voice and structure -- it should not "
        "read like a paraphrase of the original.\n"
        "Also produce concept_summary: a 1-2 sentence summary of what this source content's "
        "core topic/purpose is -- this single summary represents the whole group of 3 tiers "
        "derived from it, not any one tier individually.\n"
        "Write every field entirely in Turkish, even though the source content below may be "
        "in another language."
    )
    user = (
        f"Platform: {item.platform}\nCompetitor: {item.competitor_name}\n"
        f"Original raw text/transcript:\n{item.raw_text_or_transcript}\n\n"
        "Confirmed retention anatomy of the original:\n"
        f"- Hook (0-3s): {viral.hook_analysis}\n"
        f"- Intro/Problem (3-7s): {viral.intro_and_problem}\n"
        f"- Body/Value (7-25s): {viral.body_and_value}\n"
        f"- CTA (25-30s): {viral.call_to_action}\n"
        f"- Why it works: {viral.overall_summary}\n\n"
        "Produce tier1_ayna, tier2_hibrit, tier3_ozgun (each with hook/intro/body/cta fields) "
        "and concept_summary, all in Turkish."
    )
    return system, user
