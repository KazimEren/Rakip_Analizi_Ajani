from competitor_analysis_agent.models import CandidateCountry
from competitor_analysis_agent.steps.step2_geo_filter import filter_by_ppp_tier


def test_filter_excludes_low_and_lower_middle_tier_countries():
    candidates = [
        CandidateCountry(country="Germany", rationale="high income"),
        CandidateCountry(country="India", rationale="lower middle income"),
        CandidateCountry(country="Ethiopia", rationale="low income"),
        CandidateCountry(country="Mexico", rationale="upper middle income"),
    ]
    result = filter_by_ppp_tier(candidates)
    countries = [c.country for c in result]
    assert "Hindistan" not in countries
    assert "Etiyopya" not in countries
    assert "Almanya" in countries
    assert "Meksika" in countries


def test_filter_ranks_in_proposal_order_and_limits_to_3():
    candidates = [
        CandidateCountry(country="Germany", rationale="r1"),
        CandidateCountry(country="Mexico", rationale="r2"),
        CandidateCountry(country="Brazil", rationale="r3"),
        CandidateCountry(country="Turkey", rationale="r4"),
    ]
    result = filter_by_ppp_tier(candidates)
    assert len(result) == 3
    assert [c.rank for c in result] == [1, 2, 3]
    # Country match happens on the LLM's English name; the result is
    # translated to Turkish for display (see data/country_names_tr.py).
    assert result[0].country == "Almanya"
    assert result[0].ppp_status == "yüksek gelir"


def test_filter_unknown_country_is_excluded_not_assumed_passing():
    candidates = [CandidateCountry(country="Narnia", rationale="fictional")]
    result = filter_by_ppp_tier(candidates)
    assert result == []
