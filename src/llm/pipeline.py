"""Batch LLM inference pipeline."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from .backend import LlmBackend
from .prompts import ARCHITECTURE_PROMPT, DESIGN_PATTERN_PROMPT


class LlmPipeline:
    """Run module architecture and class pattern detection in bounded batches."""

    def __init__(self, backend: LlmBackend | None, batch_size: int = 50, enabled: bool = True):
        self.backend = backend
        self.enabled = enabled and backend is not None
        self.batch_size = max(1, batch_size)
        max_concurrency = backend.config.max_concurrency if backend is not None else 1
        self.semaphore = asyncio.Semaphore(max(1, max_concurrency))

    async def detect_architecture(self, modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Detect architecture style for module fingerprints."""

        if not self.enabled:
            return []
        tasks = [self._arch_batch(batch) for batch in self._batches(modules)]
        if not tasks:
            return []
        results = await asyncio.gather(*tasks)
        return [item for batch in results for item in batch]

    async def detect_patterns(self, classes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Detect design patterns for class fingerprints."""

        if not self.enabled:
            return []
        tasks = [self._pattern_batch(batch) for batch in self._batches(classes)]
        if not tasks:
            return []
        results = await asyncio.gather(*tasks)
        return [item for batch in results for item in batch]

    async def _arch_batch(self, modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
        async with self.semaphore:
            prompt = ARCHITECTURE_PROMPT.format(modules=json.dumps(modules, ensure_ascii=False))
            response = await self.backend.chat(
                [
                    {"role": "system", "content": "你是 Java 架构分析器。只基于结构特征判断。"},
                    {"role": "user", "content": prompt},
                ]
            )
            return self._results(response)

    async def _pattern_batch(self, classes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        async with self.semaphore:
            prompt = DESIGN_PATTERN_PROMPT.format(classes=json.dumps(classes, ensure_ascii=False))
            response = await self.backend.chat(
                [
                    {"role": "system", "content": "你是设计模式识别器。只基于结构特征判断。"},
                    {"role": "user", "content": prompt},
                ]
            )
            return self._results(response)

    def _batches(self, items: list[Any]) -> list[list[Any]]:
        return [items[i : i + self.batch_size] for i in range(0, len(items), self.batch_size)]

    @staticmethod
    def _results(response: str) -> list[dict[str, Any]]:
        payload = json.loads(response)
        results = payload.get("results", [])
        if not isinstance(results, list):
            raise ValueError("LLM 响应缺少 results 数组")
        return results
