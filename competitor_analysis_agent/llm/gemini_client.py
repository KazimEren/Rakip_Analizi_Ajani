from __future__ import annotations

import time
from typing import Protocol, TypeVar

from pydantic import BaseModel

from competitor_analysis_agent.config import Settings

T = TypeVar("T", bound=BaseModel)

_MAX_RATE_LIMIT_RETRIES = 4
_RATE_LIMIT_BACKOFF_SECONDS = (5, 10, 20, 40)


class LLMClient(Protocol):
    def complete_structured(self, system: str, user: str, output_model: type[T]) -> T: ...


def _is_rate_limit_error(exc: Exception) -> bool:
    return getattr(exc, "code", None) == 429 or "RESOURCE_EXHAUSTED" in str(exc)


class GeminiClient:
    """Wraps the google-genai SDK. Structured output is obtained via
    Gemini's native JSON mode (response_mime_type="application/json" +
    response_schema=<pydantic model>), which keeps the response strictly
    parseable regardless of how much surrounding prose the model wants to add.

    Retries on 429/RESOURCE_EXHAUSTED with backoff: step5 calls this once per
    scraped content item with no pacing between calls, so a successful
    scrape of several items in a row can easily burst past the Gemini free
    tier's per-minute request cap even though the daily quota is nowhere
    near exhausted -- this is a transient condition worth waiting out rather
    than crashing the whole pipeline run over.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._settings.gemini_api_key)
        return self._client

    def complete_structured(self, system: str, user: str, output_model: type[T]) -> T:
        from google.genai import types

        client = self._get_client()
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=output_model,
        )

        for attempt in range(_MAX_RATE_LIMIT_RETRIES):
            try:
                response = client.models.generate_content(
                    model=self._settings.gemini_model, contents=user, config=config
                )
                break
            except Exception as exc:
                if not _is_rate_limit_error(exc) or attempt == _MAX_RATE_LIMIT_RETRIES - 1:
                    raise
                time.sleep(_RATE_LIMIT_BACKOFF_SECONDS[attempt])

        if response.parsed is not None:
            return response.parsed
        return output_model.model_validate_json(response.text)


class MockLLMClient:
    """Dry-run stand-in. Returns canned responses keyed by output model name
    from scraping/fixtures.py, so the pipeline's own logic (prompt assembly,
    parsing, downstream use of the result) is still exercised end-to-end
    without a real API call."""

    def complete_structured(self, system: str, user: str, output_model: type[T]) -> T:
        from competitor_analysis_agent.scraping.fixtures import MOCK_LLM_RESPONSES

        key = output_model.__name__
        if key not in MOCK_LLM_RESPONSES:
            raise KeyError(
                f"No mock response registered for '{key}' in scraping/fixtures.py:MOCK_LLM_RESPONSES"
            )
        return output_model.model_validate(MOCK_LLM_RESPONSES[key])


def get_llm_client(settings: Settings, dry_run: bool) -> LLMClient:
    if dry_run:
        return MockLLMClient()
    return GeminiClient(settings)
