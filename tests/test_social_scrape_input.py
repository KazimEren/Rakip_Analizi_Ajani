import pytest

from competitor_analysis_agent.scraping.apify_client import build_social_scrape_input


def test_instagram_input_shape():
    result = build_social_scrape_input("Instagram", "https://instagram.com/sudowrite", 10)
    assert result == {
        "directUrls": ["https://instagram.com/sudowrite"],
        "resultsLimit": 10,
        "resultsType": "posts",
    }


def test_tiktok_input_shape():
    result = build_social_scrape_input("TikTok", "https://tiktok.com/@sudowrite", 10)
    assert result == {
        "profiles": ["https://tiktok.com/@sudowrite"],
        "resultsPerPage": 10,
    }


def test_youtube_input_shape():
    result = build_social_scrape_input("YouTube", "https://youtube.com/@sudowrite", 10)
    assert result == {
        "startUrls": [{"url": "https://youtube.com/@sudowrite"}],
        "maxResults": 10,
        "maxResultsShorts": 10,
        "maxResultStreams": 0,
    }


def test_unknown_platform_raises():
    with pytest.raises(ValueError):
        build_social_scrape_input("LinkedIn", "https://linkedin.com/company/sudowrite", 10)
