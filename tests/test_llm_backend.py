from __future__ import annotations

import asyncio

import pytest

from src.llm.backend import LlmBackend, LlmConfig


def test_backend_creation_from_config_dict():
    config = LlmConfig.from_dict(
        {
            "endpoint": "https://example.test/v1/chat/completions",
            "api_key": "sk-test",
            "model": "model-a",
            "temperature": 0.2,
            "headers": {"X-Provider-Key": "sk-custom"},
        }
    )
    backend = LlmBackend(config)

    assert backend.config.model == "model-a"
    assert backend.config.temperature == 0.2
    asyncio.run(backend.close())


def test_api_url_construction_from_endpoint_and_model(monkeypatch: pytest.MonkeyPatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": '{"results":[]}'}}]}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def post(self, url, json):
            captured["url"] = url
            captured["json"] = json
            return FakeResponse()

        async def aclose(self):
            pass

    monkeypatch.setattr("src.llm.backend.httpx.AsyncClient", FakeAsyncClient)
    backend = LlmBackend(LlmConfig(endpoint="https://example.test/chat", api_key="sk-test", model="model-b"))

    assert asyncio.run(backend.chat([{"role": "user", "content": "hi"}])) == '{"results":[]}'
    assert captured["url"] == "https://example.test/chat"
    assert captured["json"]["model"] == "model-b"


def test_header_construction_with_custom_sk_header():
    backend = LlmBackend(
        LlmConfig(
            endpoint="https://example.test/chat",
            api_key="sk-main",
            model="model-a",
            headers={"X-API-Key": "sk-custom"},
        )
    )

    headers = backend._build_headers()

    assert headers["Authorization"] == "Bearer sk-main"
    assert headers["X-API-Key"] == "sk-custom"
    asyncio.run(backend.close())


@pytest.mark.parametrize("field,value,error", [("endpoint", "", "endpoint"), ("model", "", "model")])
def test_missing_required_fields_raise_errors(field: str, value: str, error: str):
    kwargs = {"endpoint": "https://example.test/chat", "api_key": "sk-test", "model": "model-a"}
    kwargs[field] = value

    with pytest.raises(ValueError, match=error):
        LlmBackend(LlmConfig(**kwargs))
