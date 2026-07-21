import pytest

from competitor_analysis_agent.models import CandidateCountry, Competitor
from competitor_analysis_agent.steps.step2_geo_filter import Step2LLMOutput, run_step2

_COMPETITORS = [Competitor(name="X", website="https://x.com", category="fintech app")]


class _FakeLLM:
    def __init__(self, responses):
        self._responses = iter(responses)
        self.calls: list[tuple[str, str]] = []

    def complete_structured(self, system, user, output_model):
        self.calls.append((system, user))
        return next(self._responses)


def test_run_step2_retries_when_first_pass_yields_too_few_qualifying_countries():
    first = Step2LLMOutput(
        recommended_continent="Africa",
        candidate_countries=[
            CandidateCountry(country="Nigeria", rationale="largest population"),
            CandidateCountry(country="Kenya", rationale="fast fintech growth"),
            CandidateCountry(country="South Africa", rationale="mature market"),
        ],
    )
    second = Step2LLMOutput(
        recommended_continent="Africa",
        candidate_countries=[
            CandidateCountry(country="Botswana", rationale="stable upper-middle-income economy"),
            CandidateCountry(country="Namibia", rationale="growing digital adoption"),
        ],
    )
    llm = _FakeLLM([first, second])

    continent, top_3 = run_step2(llm, _COMPETITORS)

    assert continent == "Africa"
    countries = [c.country for c in top_3]
    assert len(top_3) == 3
    # PPP match happens on the LLM's English country name; the result is
    # translated to Turkish for display (see data/country_names_tr.py).
    assert countries == ["Güney Afrika", "Botsvana", "Namibya"]
    assert [c.rank for c in top_3] == [1, 2, 3]
    assert len(llm.calls) == 2


def test_run_step2_does_not_repropose_already_rejected_countries_in_retry_prompt():
    first = Step2LLMOutput(
        recommended_continent="Africa",
        candidate_countries=[CandidateCountry(country="Nigeria", rationale="largest population")],
    )
    second = Step2LLMOutput(
        recommended_continent="Africa",
        candidate_countries=[
            CandidateCountry(country="South Africa", rationale="mature market"),
            CandidateCountry(country="Botswana", rationale="stable economy"),
            CandidateCountry(country="Namibia", rationale="growing adoption"),
        ],
    )
    llm = _FakeLLM([first, second])

    run_step2(llm, _COMPETITORS)

    retry_user_prompt = llm.calls[1][1]
    assert "Nigeria" in retry_user_prompt
    assert "Africa" in retry_user_prompt


def test_run_step2_raises_after_max_attempts_if_still_insufficient():
    stuck = Step2LLMOutput(
        recommended_continent="Africa",
        candidate_countries=[CandidateCountry(country="Nigeria", rationale="largest population")],
    )
    llm = _FakeLLM([stuck, stuck, stuck])

    with pytest.raises(ValueError):
        run_step2(llm, _COMPETITORS)

    assert len(llm.calls) == 3
