from competitor_analysis_agent.models import Competitor, RawComplaintText
from competitor_analysis_agent.steps.step4_gap_analysis import Step4LLMOutput, run_step4

_COMPETITORS = [
    Competitor(name="X", website="https://x.com", category="fintech app"),
    Competitor(name="Y", website="https://y.com", category="fintech app"),
]


class _FakeLLM:
    def __init__(self, response):
        self._response = response
        self.calls: list[tuple[str, str]] = []

    def complete_structured(self, system, user, output_model):
        self.calls.append((system, user))
        return self._response


def test_run_step4_falls_back_to_general_knowledge_when_no_complaints_scraped():
    fallback = Step4LLMOutput(
        strategic_value_adds=[
            {
                "competitor_weakness": "Inferred: onboarding friction common in this category.",
                "recommended_feature": "One-tap guided onboarding.",
            }
        ]
    )
    llm = _FakeLLM(fallback)

    result = run_step4(llm, complaints=[], competitors=_COMPETITORS)

    assert len(result) == 1
    assert result[0].recommended_feature == "One-tap guided onboarding."
    assert len(llm.calls) == 1
    user_prompt = llm.calls[0][1]
    assert "X" in user_prompt and "Y" in user_prompt


def test_run_step4_returns_empty_when_no_complaints_and_no_competitors():
    llm = _FakeLLM(Step4LLMOutput(strategic_value_adds=[]))

    result = run_step4(llm, complaints=[], competitors=[])

    assert result == []
    assert len(llm.calls) == 0


def test_run_step4_uses_scraped_complaints_path_when_available():
    scraped_result = Step4LLMOutput(
        strategic_value_adds=[
            {"competitor_weakness": "Crashes on bank linking.", "recommended_feature": "Resumable linking flow."}
        ]
    )
    llm = _FakeLLM(scraped_result)
    complaints = [RawComplaintText(competitor_name="X", source="Trustpilot", raw_text="It keeps crashing.")]

    result = run_step4(llm, complaints=complaints, competitors=_COMPETITORS)

    assert len(result) == 1
    assert result[0].competitor_weakness == "Crashes on bank linking."
