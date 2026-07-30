"""ADIM 5 devamı: tutan içerik için 3 tier'li (Ayna/Hibrit/Özgün) içerik
iskeleti üretimi -- İçerik Oluşturma Ajanı'nın doğrudan okuyacağı temiz JSON.
"""

from __future__ import annotations

from pydantic import BaseModel

from competitor_analysis_agent.llm.gemini_client import LLMClient
from competitor_analysis_agent.llm.prompts import step6_content_tiering_prompt
from competitor_analysis_agent.models import TIER_LABELS, ContentSkeleton, RawContentItem, ViralContent


class _TierFields(BaseModel):
    hook: str
    intro: str
    body: str
    cta: str


class Step6LLMOutput(BaseModel):
    tier1_ayna: _TierFields
    tier2_hibrit: _TierFields
    tier3_ozgun: _TierFields


def run_step6_tiering(llm: LLMClient, item: RawContentItem, viral: ViralContent) -> list[ContentSkeleton]:
    system, user = step6_content_tiering_prompt(item, viral)
    result = llm.complete_structured(system, user, Step6LLMOutput)

    tiers: list[tuple[int, _TierFields]] = [
        (1, result.tier1_ayna),
        (2, result.tier2_hibrit),
        (3, result.tier3_ozgun),
    ]
    return [
        ContentSkeleton(
            source_viral_content_id=viral.id,
            competitor_name=item.competitor_name,
            platform=item.platform,
            tier_type=tier_type,
            tier_label=TIER_LABELS[tier_type],
            skeleton_data=fields.model_dump(),
        )
        for tier_type, fields in tiers
    ]
