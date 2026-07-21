from competitor_analysis_agent.scraping.apify_client import clean_competitor_name, is_competitor_result


def test_accepts_plausible_product_site():
    assert is_competitor_result("Sudowrite - AI Writing Partner for Fiction", "sudowrite.com") is True
    assert is_competitor_result("NovelAI", "novelai.net") is True


def test_rejects_numbered_listicle_titles():
    assert is_competitor_result("10 Best AI Novel Generators in 2026", "someblog.com") is False
    assert is_competitor_result("7 Free AI Story Writing Tools You Should Try", "example.com") is False
    assert is_competitor_result("Top 5 AI Book Writing Apps", "example.com") is False


def test_rejects_review_and_comparison_titles():
    assert is_competitor_result("Sudowrite vs NovelAI: Which Is Better?", "example.com") is False
    assert is_competitor_result("NovelAI Review: Is It Worth It?", "example.com") is False
    assert is_competitor_result("Best AI Writing Tool Alternatives", "example.com") is False

    assert is_competitor_result("NovelAI Review: Is It Worth It?", "example.com") is False


def test_rejects_known_non_product_domains():
    assert is_competitor_result("aiWriter.ai: Free AI Story Generator", "medium.com") is False
    assert is_competitor_result("aiWriter.ai: Free AI Story Generator", "www.reddit.com") is False
    assert is_competitor_result("aiWriter.ai: Free AI Story Generator", "g2.com") is False


def test_does_not_falsely_reject_product_name_containing_a_number():
    # A product's own name/tagline containing digits shouldn't be confused
    # with a listicle -- only "N Best/Top ..." or "Best/Top N ..." patterns
    # at the start/adjacent to a number should trigger rejection.
    assert is_competitor_result("Plottr 2.0 - Visual Story Planning", "plottr.com") is True


def test_clean_competitor_name_strips_marketing_tagline():
    assert clean_competitor_name("Sudowrite - Best AI Writing Partner for Fiction", "sudowrite.com") == "Sudowrite"
    assert clean_competitor_name("Plottr - Visual Story Planning Software", "plottr.com") == "Plottr"


def test_clean_competitor_name_splits_on_colon_with_no_leading_space():
    assert (
        clean_competitor_name("aiWriter.ai: Free AI Story Generator & Writer", "aiwriter.ai") == "aiWriter.ai"
    )


def test_clean_competitor_name_leaves_plain_name_unchanged():
    assert clean_competitor_name("NovelAI", "novelai.net") == "NovelAI"


def test_clean_competitor_name_does_not_split_compound_hyphenated_word():
    assert clean_competitor_name("E-commerce Story Tool for Authors", "example.com") == "E-commerce Story Tool for Authors"


def test_clean_competitor_name_falls_back_to_domain_when_leading_segment_is_too_short():
    assert clean_competitor_name(": Free AI Story Generator", "aiwriter.ai") == "Aiwriter"
