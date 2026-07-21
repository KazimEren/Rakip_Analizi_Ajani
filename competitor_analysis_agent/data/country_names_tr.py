"""English -> Turkish display names for the countries covered by
data/ppp_tiers.py.

The PPP/income-tier lookup in data/ppp_tiers.py is keyed on English country
names, and the LLM is instructed (see llm/prompts.py) to keep each candidate
country's `country` field in English specifically so that lookup stays a
reliable, deterministic dictionary match -- translation drift/synonyms would
otherwise make countries fail the filter for the wrong reason. This module
converts the already-filtered result to Turkish for display/persistence only,
after the PPP match has already happened against the English name.

Unknown countries fall back to their original (English) name rather than
raising, since the filter step already guarantees only entries present in
PPP_TIERS -- and by extension in this table -- ever reach here in practice.
"""

from __future__ import annotations

COUNTRY_NAMES_TR: dict[str, str] = {
    # --- High income ---
    "United States": "Amerika Birleşik Devletleri",
    "Canada": "Kanada",
    "United Kingdom": "Birleşik Krallık",
    "Germany": "Almanya",
    "France": "Fransa",
    "Netherlands": "Hollanda",
    "Sweden": "İsveç",
    "Norway": "Norveç",
    "Denmark": "Danimarka",
    "Switzerland": "İsviçre",
    "Ireland": "İrlanda",
    "Australia": "Avustralya",
    "New Zealand": "Yeni Zelanda",
    "Japan": "Japonya",
    "South Korea": "Güney Kore",
    "Singapore": "Singapur",
    "United Arab Emirates": "Birleşik Arap Emirlikleri",
    "Saudi Arabia": "Suudi Arabistan",
    "Israel": "İsrail",
    "Qatar": "Katar",
    "Poland": "Polonya",
    "Spain": "İspanya",
    "Italy": "İtalya",
    "Portugal": "Portekiz",
    "Chile": "Şili",
    "Panama": "Panama",
    "Uruguay": "Uruguay",
    "Mauritius": "Mauritius",
    # --- Upper middle income ---
    "Mexico": "Meksika",
    "Brazil": "Brezilya",
    "Argentina": "Arjantin",
    "Colombia": "Kolombiya",
    "Peru": "Peru",
    "Turkey": "Türkiye",
    "South Africa": "Güney Afrika",
    "Malaysia": "Malezya",
    "Thailand": "Tayland",
    "China": "Çin",
    "Romania": "Romanya",
    "Bulgaria": "Bulgaristan",
    "Serbia": "Sırbistan",
    "Kazakhstan": "Kazakistan",
    "Costa Rica": "Kosta Rika",
    "Indonesia": "Endonezya",
    "Botswana": "Botsvana",
    "Namibia": "Namibya",
    "Gabon": "Gabon",
    "Equatorial Guinea": "Ekvator Ginesi",
    "Libya": "Libya",
    # --- Lower middle income ---
    "India": "Hindistan",
    "Vietnam": "Vietnam",
    "Philippines": "Filipinler",
    "Egypt": "Mısır",
    "Morocco": "Fas",
    "Nigeria": "Nijerya",
    "Kenya": "Kenya",
    "Ghana": "Gana",
    "Bangladesh": "Bangladeş",
    "Pakistan": "Pakistan",
    "Tunisia": "Tunus",
    "Algeria": "Cezayir",
    "Ukraine": "Ukrayna",
    # --- Low income ---
    "Ethiopia": "Etiyopya",
    "Uganda": "Uganda",
    "Mozambique": "Mozambik",
    "Democratic Republic of the Congo": "Kongo Demokratik Cumhuriyeti",
    "Afghanistan": "Afganistan",
    "Yemen": "Yemen",
    "Madagascar": "Madagaskar",
}

PPP_STATUS_TR: dict[str, str] = {
    "low": "düşük gelir",
    "lower_middle": "alt-orta gelir",
    "upper_middle": "üst-orta gelir",
    "high": "yüksek gelir",
}


def to_turkish_country_name(english_name: str) -> str:
    return COUNTRY_NAMES_TR.get(english_name, english_name)


def to_turkish_ppp_status(tier: str | None) -> str:
    if tier is None:
        return "bilinmiyor"
    return PPP_STATUS_TR.get(tier, "bilinmiyor")
