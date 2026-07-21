import pytest

from competitor_analysis_agent.models import PricingDataPoint
from competitor_analysis_agent.steps.step3_pricing import compute_min_avg_max


def test_compute_min_avg_max():
    prices = [
        PricingDataPoint(competitor_name="A", price=10.0),
        PricingDataPoint(competitor_name="B", price=20.0),
        PricingDataPoint(competitor_name="C", price=30.0),
    ]
    min_p, avg_p, max_p = compute_min_avg_max(prices)
    assert min_p == 10.0
    assert avg_p == 20.0
    assert max_p == 30.0


def test_compute_min_avg_max_empty_raises():
    with pytest.raises(ValueError):
        compute_min_avg_max([])
