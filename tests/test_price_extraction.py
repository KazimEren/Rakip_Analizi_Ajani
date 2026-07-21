from competitor_analysis_agent.scraping.playwright_scraper import _extract_prices


def test_extracts_price_with_billing_cadence_context():
    text = "Pro plan: $12.99/mo billed monthly. Annual plan: $99.00/year."
    prices = _extract_prices(text, limit=10)
    assert 12.99 in prices
    assert 99.00 in prices


def test_ignores_number_without_pricing_context():
    text = "Random trivia: the answer to life is $42 according to an old book."
    prices = _extract_prices(text, limit=10)
    assert prices == []


def test_ignores_thousands_grouped_number_not_a_price():
    text = "Trusted by $500,000 in funding and pricing plans starting soon."
    prices = _extract_prices(text, limit=10)
    assert 500.0 not in prices
    assert 500000.0 not in prices


def test_ignores_implausibly_large_value():
    text = "Enterprise contract: $250000 per year, billed annually."
    prices = _extract_prices(text, limit=10)
    assert prices == []


def test_respects_limit():
    text = "Plans: $1/mo, $2/mo, $3/mo, $4/mo billed monthly for each tier."
    prices = _extract_prices(text, limit=2)
    assert len(prices) == 2
