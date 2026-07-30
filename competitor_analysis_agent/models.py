from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator

KNOWN_PLATFORMS = {"Instagram", "LinkedIn", "YouTube", "TikTok"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- Intermediate (non-persisted) models -----------------------------------


class KeywordsAndCategories(BaseModel):
    keywords: list[str]
    competitor_categories: list[str]


class Competitor(BaseModel):
    name: str
    website: str | None = None
    continent: str | None = None
    country: str | None = None
    category: str | None = None


class PricingDataPoint(BaseModel):
    competitor_name: str
    price: float
    currency: str = "USD"
    plan_name: str | None = None


class RawComplaintText(BaseModel):
    """A raw scraped review/complaint snippet, before the LLM extracts pain
    points and strategic value-adds from it in step 4."""

    competitor_name: str
    source: str  # e.g. "Trustpilot", "Reddit", "Google Reviews", "App Store"
    raw_text: str


class CandidateCountry(BaseModel):
    """LLM's raw proposal for step 2, before the deterministic PPP-tier
    filter in data/ppp_tiers.py is applied."""

    country: str
    rationale: str


class RawContentItem(BaseModel):
    """A single piece of scraped social content before anatomy analysis."""

    competitor_name: str
    platform: str
    content_url: str | None = None
    raw_text_or_transcript: str = ""
    engagement_note: str = ""


# --- Persisted models (mirror the two Supabase tables) ---------------------


class TopCountry(BaseModel):
    rank: int
    country: str
    rationale: str
    ppp_status: str


class PricingMatrix(BaseModel):
    min_price: float
    avg_price: float
    max_price: float
    recommended_entry_price: float
    rationale: str


class StrategicValueAdd(BaseModel):
    competitor_weakness: str
    recommended_feature: str


class MarketAndGapAnalysis(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_name: str
    project_description: str = ""
    modules_run: dict[str, bool] = Field(default_factory=dict)
    recommended_continent: str | None = None
    top_3_countries: list[TopCountry] | None = None
    pricing_matrix: PricingMatrix | None = None
    strategic_value_adds: list[StrategicValueAdd] | None = None
    created_at: datetime = Field(default_factory=_utcnow)

    def to_supabase_row(self) -> dict:
        return {
            "id": str(self.id),
            "project_name": self.project_name,
            "project_description": self.project_description,
            "modules_run": self.modules_run,
            "recommended_continent": self.recommended_continent,
            "top_3_countries": [c.model_dump() for c in self.top_3_countries] if self.top_3_countries else None,
            "pricing_matrix": self.pricing_matrix.model_dump() if self.pricing_matrix else None,
            "strategic_value_adds": (
                [v.model_dump() for v in self.strategic_value_adds] if self.strategic_value_adds else None
            ),
            "created_at": self.created_at.isoformat(),
        }


class ViralContent(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_id: uuid.UUID | None = None
    competitor_name: str
    content_url: str | None = None
    platform: str
    hook_analysis: str
    intro_and_problem: str
    body_and_value: str
    call_to_action: str
    overall_summary: str
    created_at: datetime = Field(default_factory=_utcnow)

    @field_validator("platform")
    @classmethod
    def _normalize_platform(cls, v: str) -> str:
        for known in KNOWN_PLATFORMS:
            if v.strip().lower() == known.lower():
                return known
        # Unknown platform values are kept as-is rather than rejected: a
        # scraper/LLM surprise here shouldn't crash the whole pipeline run.
        return v.strip()

    def to_supabase_row(self) -> dict:
        return {
            "id": str(self.id),
            "project_id": str(self.project_id) if self.project_id else None,
            "competitor_name": self.competitor_name,
            "content_url": self.content_url,
            "platform": self.platform,
            "hook_analysis": self.hook_analysis,
            "intro_and_problem": self.intro_and_problem,
            "body_and_value": self.body_and_value,
            "call_to_action": self.call_to_action,
            "overall_summary": self.overall_summary,
            "created_at": self.created_at.isoformat(),
        }


# Tier 1 = Ayna (re-skin): mesaj/kanca/mantık aynı, görsel+kelimeler hafif
# güncellenmiş. Tier 2 = Hibrit: ana anlam aynı + bizim değer önerilerimiz
# eklenmiş. Tier 3 = Özgün: aynı çekirdek mesaj, baştan yazılmış.
TIER_LABELS: dict[int, str] = {1: "Ayna", 2: "Hibrit", 3: "Özgün"}


class ContentSkeleton(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_id: uuid.UUID | None = None
    source_viral_content_id: uuid.UUID | None = None
    competitor_name: str
    platform: str
    tier_type: int
    tier_label: str
    skeleton_data: dict
    status: str = "PENDING"
    created_at: datetime = Field(default_factory=_utcnow)

    @field_validator("tier_type")
    @classmethod
    def _validate_tier_type(cls, v: int) -> int:
        if v not in TIER_LABELS:
            raise ValueError(f"tier_type must be one of {sorted(TIER_LABELS)}, got {v}")
        return v

    def to_supabase_row(self) -> dict:
        return {
            "id": str(self.id),
            "project_id": str(self.project_id) if self.project_id else None,
            "source_viral_content_id": str(self.source_viral_content_id) if self.source_viral_content_id else None,
            "competitor_name": self.competitor_name,
            "platform": self.platform,
            "tier_type": self.tier_type,
            "tier_label": self.tier_label,
            "skeleton_data": self.skeleton_data,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }
