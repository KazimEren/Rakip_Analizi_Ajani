"""ADIM 4: Kullanıcı şikayetleri ve ekstra ürün/değer önerisi (Gap Analysis)."""

from __future__ import annotations

from pydantic import BaseModel

from competitor_analysis_agent.llm.gemini_client import LLMClient
from competitor_analysis_agent.llm.prompts import step4_gap_analysis_no_data_prompt, step4_gap_analysis_prompt
from competitor_analysis_agent.models import Competitor, RawComplaintText, StrategicValueAdd


class Step4LLMOutput(BaseModel):
    strategic_value_adds: list[StrategicValueAdd]


def run_step4(
    llm: LLMClient, complaints: list[RawComplaintText], competitors: list[Competitor]
) -> list[StrategicValueAdd]:
    if not complaints:
        # No scraped complaints (e.g. none of the competitors have a public
        # review-site presence) -- fall back to an LLM estimate grounded in
        # general category knowledge rather than silently returning zero
        # strategic value-adds, mirroring step3's no-scraped-data fallback.
        if not competitors:
            return []
        system, user = step4_gap_analysis_no_data_prompt(competitors)
        result = llm.complete_structured(system, user, Step4LLMOutput)
        return result.strategic_value_adds

    system, user = step4_gap_analysis_prompt(complaints)
    result = llm.complete_structured(system, user, Step4LLMOutput)
    return result.strategic_value_adds
