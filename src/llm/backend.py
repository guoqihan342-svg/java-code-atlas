"""OpenAI-compatible LLM backend."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class LlmConfig:
    """Runtime settings for an OpenAI-compatible chat completion endpoint."""

    endpoint: str
    api_key: str
    model: str
    temperature: float = 0.0
    max_tokens: int = 4096
    headers: dict[str, str] = field(default_factory=dict)
    max_concurrency: int = 2
    retry: int = 3

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LlmConfig":
        return cls(
            endpoint=str(data.get("endpoint", "")),
            api_key=str(data.get("api_key", "")),
            model=str(data.get("model", "")),
            temperature=float(data.get("temperature", 0.0)),
            max_tokens=int(data.get("max_tokens", 4096)),
            headers=dict(data.get("headers") or {}),
            max_concurrency=int(data.get("max_concurrency", 2)),
            retry=int(data.get("retry", 3)),
        )


class LlmBackend:
    """OpenAI-compatible API abstraction for DeepSeek, OpenAI, and self-hosted models."""

    def __init__(self, config: LlmConfig):
        if not config.endpoint:
            raise ValueError("LLM endpoint 不能为空")
        if not config.model:
            raise ValueError("LLM model 不能为空")
        self.config = config
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0),
            headers=self._build_headers(),
        )

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        headers.update(self.config.headers)
        return headers

    async def chat(self, messages: list[dict[str, str]]) -> str:
        """Call the chat completion endpoint with exponential backoff."""

        last_error: Exception | None = None
        for attempt in range(self.config.retry + 1):
            try:
                response = await self.client.post(
                    self.config.endpoint,
                    json={
                        "model": self.config.model,
                        "messages": messages,
                        "temperature": self.config.temperature,
                        "max_tokens": self.config.max_tokens,
                        "response_format": {"type": "json_object"},
                    },
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                if not isinstance(content, str):
                    raise KeyError("choices[0].message.content")
                return content
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                last_error = exc
                if attempt >= self.config.retry:
                    break
                await asyncio.sleep(2**attempt)
        raise RuntimeError(f"LLM 调用失败: {last_error}") from last_error

    async def close(self) -> None:
        """Close underlying HTTP resources."""

        await self.client.aclose()
