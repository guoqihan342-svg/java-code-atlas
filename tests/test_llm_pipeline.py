from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from src.llm.pipeline import LlmPipeline


class FakeBackend:
    def __init__(self):
        self.config = SimpleNamespace(max_concurrency=2)
        self.messages = []

    async def chat(self, messages):
        self.messages.append(messages)
        return json.dumps({"results": [{"ok": True, "batch": len(self.messages)}]})


def test_batch_splitting_logic():
    pipeline = LlmPipeline(FakeBackend(), batch_size=2)

    assert pipeline._batches([1, 2, 3, 4, 5]) == [[1, 2], [3, 4], [5]]


def test_prompt_template_rendering():
    backend = FakeBackend()
    pipeline = LlmPipeline(backend, batch_size=1)

    results = asyncio.run(pipeline.detect_architecture([{"module": "app", "roles": ["controller"]}]))

    assert results == [{"ok": True, "batch": 1}]
    user_prompt = backend.messages[0][1]["content"]
    assert '"module": "app"' in user_prompt
    assert "返回严格 JSON" in user_prompt


def test_disabled_llm_returns_empty_results():
    pipeline = LlmPipeline(None, enabled=False)

    assert asyncio.run(pipeline.detect_architecture([{"module": "app"}])) == []
    assert asyncio.run(pipeline.detect_patterns([{"fqn": "Example"}])) == []
