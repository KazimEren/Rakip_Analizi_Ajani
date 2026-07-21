"""ADIM 5: Tutan içerik anatomi analizi (Viral Content Breakdown)."""

from __future__ import annotations

from pydantic import BaseModel

from competitor_analysis_agent.llm.gemini_client import LLMClient
from competitor_analysis_agent.llm.prompts import step5_viral_content_prompt
from competitor_analysis_agent.models import RawContentItem, ViralContent


class Step5LLMOutput(BaseModel):
    hook_analysis: str
    intro_and_problem: str
    body_and_value: str
    call_to_action: str
    overall_summary: str


def run_step5(llm: LLMClient, items: list[RawContentItem]) -> list[ViralContent]:
    results: list[ViralContent] = []
    for item in items:
        system, user = step5_viral_content_prompt(item)
        analysis = llm.complete_structured(system, user, Step5LLMOutput)
        results.append(
            ViralContent(
                competitor_name=item.competitor_name,
                content_url=item.content_url,
                platform=item.platform,
                hook_analysis=analysis.hook_analysis,
                intro_and_problem=analysis.intro_and_problem,
                body_and_value=analysis.body_and_value,
                call_to_action=analysis.call_to_action,
                overall_summary=analysis.overall_summary,
            )
        )
    return results
