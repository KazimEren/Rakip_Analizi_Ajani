import time
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from competitor_analysis_agent.config import Settings
from competitor_analysis_agent.llm.gemini_client import GeminiClient


class DummyOutput(BaseModel):
    value: str


class FakeRateLimitError(Exception):
    code = 429


def _make_client(monkeypatch) -> tuple[GeminiClient, MagicMock]:
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)
    settings = Settings(gemini_api_key="fake", gemini_model="fake-model")
    client = GeminiClient(settings)
    fake_genai_client = MagicMock()
    client._client = fake_genai_client
    return client, fake_genai_client


def test_retries_on_rate_limit_then_succeeds(monkeypatch):
    client, fake_genai_client = _make_client(monkeypatch)
    success_response = MagicMock(parsed=DummyOutput(value="ok"))
    fake_genai_client.models.generate_content.side_effect = [
        FakeRateLimitError("429 RESOURCE_EXHAUSTED"),
        success_response,
    ]

    result = client.complete_structured("system", "user", DummyOutput)

    assert result.value == "ok"
    assert fake_genai_client.models.generate_content.call_count == 2


def test_raises_after_max_retries_exhausted(monkeypatch):
    client, fake_genai_client = _make_client(monkeypatch)
    fake_genai_client.models.generate_content.side_effect = FakeRateLimitError("429 RESOURCE_EXHAUSTED")

    with pytest.raises(FakeRateLimitError):
        client.complete_structured("system", "user", DummyOutput)

    assert fake_genai_client.models.generate_content.call_count == 4


def test_does_not_retry_non_rate_limit_errors(monkeypatch):
    client, fake_genai_client = _make_client(monkeypatch)
    fake_genai_client.models.generate_content.side_effect = ValueError("some other error")

    with pytest.raises(ValueError):
        client.complete_structured("system", "user", DummyOutput)

    assert fake_genai_client.models.generate_content.call_count == 1
