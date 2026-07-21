"""ADIM 1: Proje girdisinden global arama anahtar kelimeleri ve rakip
kategorileri türetme."""

from __future__ import annotations

from competitor_analysis_agent.llm.gemini_client import LLMClient
from competitor_analysis_agent.llm.prompts import step1_keywords_prompt
from competitor_analysis_agent.models import KeywordsAndCategories


def run_step1(llm: LLMClient, project_description: str) -> KeywordsAndCategories:
    system, user = step1_keywords_prompt(project_description)
    return llm.complete_structured(system, user, KeywordsAndCategories)
