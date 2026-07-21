"""ADIM 3: Fiyatlandırma benchmark analizi.

min/avg/max is pure arithmetic and must never be delegated to the LLM; the
LLM's job is limited to recommending + explaining the market-entry price
given the already-computed matrix and target countries.
"""

from __future__ import annotations

from statistics import mean

from pydantic import BaseModel

from competitor_analysis_agent.llm.gemini_client import LLMClient
from competitor_analysis_agent.llm.prompts import step3_pricing_no_data_prompt, step3_pricing_prompt
from competitor_analysis_agent.models import Competitor, PricingDataPoint, PricingMatrix, TopCountry


class Step3LLMOutput(BaseModel):
    recommended_entry_price: float
    rationale: str


def compute_min_avg_max(prices: list[PricingDataPoint]) -> tuple[float, float, float]:
    if not prices:
        raise ValueError("No pricing data points to compute a matrix from.")
    values = [p.price for p in prices]
    return min(values), round(mean(values), 2), max(values)


def run_step3(
    llm: LLMClient,
    prices: list[PricingDataPoint],
    top_3_countries: list[TopCountry],
    competitors: list[Competitor],
) -> PricingMatrix:
    if not prices:
        # Scraping found nothing usable (e.g. a freemium-heavy niche, or no
        # extractable pricing page). pricing_matrix is a required field on
        # the output record, so fall back to an LLM estimate rather than
        # crashing the whole pipeline over one missing data source -- but
        # keep min/avg/max at 0 and say so plainly, instead of fabricating
        # numbers that look like real scraped data.
        system, user = step3_pricing_no_data_prompt(competitors, [c.country for c in top_3_countries])
        result = llm.complete_structured(system, user, Step3LLMOutput)
        return PricingMatrix(
            min_price=0.0,
            avg_price=0.0,
            max_price=0.0,
            recommended_entry_price=round(result.recommended_entry_price, 2),
            rationale="Bu pazar için hiçbir rakip fiyat verisi kazınamadı. " + result.rationale,
        )

    min_price, avg_price, max_price = compute_min_avg_max(prices)
    system, user = step3_pricing_prompt(
        prices, min_price, avg_price, max_price, [c.country for c in top_3_countries]
    )
    result = llm.complete_structured(system, user, Step3LLMOutput)

    # Sanity guard: keep the LLM's recommendation within a plausible band
    # around the observed range instead of trusting it unconditionally.
    lower_bound, upper_bound = min_price * 0.5, max_price * 1.5
    entry_price = min(max(result.recommended_entry_price, lower_bound), upper_bound)

    return PricingMatrix(
        min_price=min_price,
        avg_price=avg_price,
        max_price=max_price,
        recommended_entry_price=round(entry_price, 2),
        rationale=result.rationale,
    )
