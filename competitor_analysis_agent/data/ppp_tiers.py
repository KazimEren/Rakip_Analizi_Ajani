"""Static, simplified World-Bank-style income group reference table.

Used by ADIM 2 (geo filtering) to deterministically enforce the CLAUDE.md
rule: "Orta segmentin altındaki veya alım gücü yetersiz ülkeleri kesinlikle
ele" (exclude countries below the mid-income tier). This is intentionally a
small, hand-maintained snapshot for orientation purposes, not a live PPP/GNI
feed -- refresh periodically from an authoritative source (e.g. the World
Bank's country income classifications) before relying on it for a real
market-entry decision.

Tiers, from lowest to highest purchasing power: "low", "lower_middle",
"upper_middle", "high".
"""

from __future__ import annotations

PPP_TIERS: dict[str, str] = {
    # --- High income ---
    "United States": "high",
    "Canada": "high",
    "United Kingdom": "high",
    "Germany": "high",
    "France": "high",
    "Netherlands": "high",
    "Sweden": "high",
    "Norway": "high",
    "Denmark": "high",
    "Switzerland": "high",
    "Ireland": "high",
    "Australia": "high",
    "New Zealand": "high",
    "Japan": "high",
    "South Korea": "high",
    "Singapore": "high",
    "United Arab Emirates": "high",
    "Saudi Arabia": "high",
    "Israel": "high",
    "Qatar": "high",
    "Poland": "high",
    "Spain": "high",
    "Italy": "high",
    "Portugal": "high",
    "Chile": "high",
    "Panama": "high",
    "Uruguay": "high",
    "Mauritius": "high",
    # --- Upper middle income ---
    "Mexico": "upper_middle",
    "Brazil": "upper_middle",
    "Argentina": "upper_middle",
    "Colombia": "upper_middle",
    "Peru": "upper_middle",
    "Turkey": "upper_middle",
    "South Africa": "upper_middle",
    "Malaysia": "upper_middle",
    "Thailand": "upper_middle",
    "China": "upper_middle",
    "Romania": "upper_middle",
    "Bulgaria": "upper_middle",
    "Serbia": "upper_middle",
    "Kazakhstan": "upper_middle",
    "Costa Rica": "upper_middle",
    "Indonesia": "upper_middle",
    "Botswana": "upper_middle",
    "Namibia": "upper_middle",
    "Gabon": "upper_middle",
    "Equatorial Guinea": "upper_middle",
    "Libya": "upper_middle",
    # --- Lower middle income (excluded by the mid-tier cutoff) ---
    "India": "lower_middle",
    "Vietnam": "lower_middle",
    "Philippines": "lower_middle",
    "Egypt": "lower_middle",
    "Morocco": "lower_middle",
    "Nigeria": "lower_middle",
    "Kenya": "lower_middle",
    "Ghana": "lower_middle",
    "Bangladesh": "lower_middle",
    "Pakistan": "lower_middle",
    "Tunisia": "lower_middle",
    "Algeria": "lower_middle",
    "Ukraine": "lower_middle",
    # --- Low income (excluded by the mid-tier cutoff) ---
    "Ethiopia": "low",
    "Uganda": "low",
    "Mozambique": "low",
    "Democratic Republic of the Congo": "low",
    "Afghanistan": "low",
    "Yemen": "low",
    "Madagascar": "low",
}

_TIER_RANK = {"low": 0, "lower_middle": 1, "upper_middle": 2, "high": 3}
UPPER_MIDDLE_CUTOFF = _TIER_RANK["upper_middle"]


def get_tier(country: str) -> str | None:
    """Returns the income tier for a country, or None if unknown (unknown
    countries are treated conservatively -- not assumed to pass the filter)."""
    return PPP_TIERS.get(country)


def is_at_least_upper_middle(country: str) -> bool:
    tier = get_tier(country)
    if tier is None:
        return False
    return _TIER_RANK[tier] >= UPPER_MIDDLE_CUTOFF
