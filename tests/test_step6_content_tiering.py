from competitor_analysis_agent.models import TIER_LABELS, RawContentItem, ViralContent
from competitor_analysis_agent.steps.step6_content_tiering import Step6LLMOutput, run_step6_tiering


class _FakeLLM:
    def __init__(self, response):
        self._response = response
        self.calls: list[tuple[str, str]] = []

    def complete_structured(self, system, user, output_model):
        self.calls.append((system, user))
        return self._response


def _tier_fields(prefix: str) -> dict:
    return {"hook": f"{prefix}-hook", "intro": f"{prefix}-intro", "body": f"{prefix}-body", "cta": f"{prefix}-cta"}


def _make_item_and_viral() -> tuple[RawContentItem, ViralContent]:
    item = RawContentItem(
        competitor_name="BudgetWise",
        platform="TikTok",
        content_url="https://tiktok.com/@budgetwise/video/1",
        raw_text_or_transcript="3 signs you're about to overspend this month.",
        engagement_note="engagement=1200000",
    )
    viral = ViralContent(
        competitor_name="BudgetWise",
        platform="TikTok",
        hook_analysis="hook",
        intro_and_problem="intro",
        body_and_value="body",
        call_to_action="cta",
        overall_summary="summary",
    )
    return item, viral


_CONCEPT_SUMMARY = "Maaş günü kaygısını bütçe farkındalığına dönüştüren kısa bir uyarı formatı."


def test_run_step6_tiering_produces_three_labeled_tiers():
    response = Step6LLMOutput(
        tier1_ayna=_tier_fields("ayna"),
        tier2_hibrit=_tier_fields("hibrit"),
        tier3_ozgun=_tier_fields("ozgun"),
        concept_summary=_CONCEPT_SUMMARY,
    )
    llm = _FakeLLM(response)
    item, viral = _make_item_and_viral()

    skeletons = run_step6_tiering(llm, item, viral)

    assert len(skeletons) == 3
    assert [s.tier_type for s in skeletons] == [1, 2, 3]
    assert [s.tier_label for s in skeletons] == [TIER_LABELS[1], TIER_LABELS[2], TIER_LABELS[3]]
    assert all(s.source_viral_content_id == viral.id for s in skeletons)
    assert all(s.competitor_name == "BudgetWise" and s.platform == "TikTok" for s in skeletons)
    assert all(s.status == "PENDING" for s in skeletons)
    assert skeletons[0].skeleton_data == _tier_fields("ayna")
    assert skeletons[1].skeleton_data == _tier_fields("hibrit")
    assert skeletons[2].skeleton_data == _tier_fields("ozgun")
    assert len(llm.calls) == 1

    # De-dup field: every tier carries the source post's URL.
    assert all(s.source_post_url == item.content_url for s in skeletons)
    # Concept grouping: all 3 tiers share one group id and summary.
    assert len({s.concept_group_id for s in skeletons}) == 1
    assert all(s.concept_summary == _CONCEPT_SUMMARY for s in skeletons)


def test_run_step6_tiering_prompt_grounds_on_confirmed_anatomy():
    response = Step6LLMOutput(
        tier1_ayna=_tier_fields("ayna"),
        tier2_hibrit=_tier_fields("hibrit"),
        tier3_ozgun=_tier_fields("ozgun"),
        concept_summary=_CONCEPT_SUMMARY,
    )
    llm = _FakeLLM(response)
    item, viral = _make_item_and_viral()

    run_step6_tiering(llm, item, viral)

    user_prompt = llm.calls[0][1]
    assert viral.hook_analysis in user_prompt
    assert viral.overall_summary in user_prompt
    assert item.raw_text_or_transcript in user_prompt


def test_run_step6_tiering_assigns_distinct_group_ids_per_call():
    response = Step6LLMOutput(
        tier1_ayna=_tier_fields("ayna"),
        tier2_hibrit=_tier_fields("hibrit"),
        tier3_ozgun=_tier_fields("ozgun"),
        concept_summary=_CONCEPT_SUMMARY,
    )
    llm = _FakeLLM(response)
    item, viral = _make_item_and_viral()

    first_call = run_step6_tiering(llm, item, viral)
    second_call = run_step6_tiering(llm, item, viral)

    assert first_call[0].concept_group_id != second_call[0].concept_group_id
