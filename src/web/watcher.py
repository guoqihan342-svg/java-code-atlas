"""Watch Java source file changes with debounce."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


ChangeCallback = Callable[[str], Awaitable[None]]


class FileWatcher:
    """Watch configured source roots and invoke callback for .java changes."""

    def __init__(self, config: dict[str, Any], callback: ChangeCallback):
        self.config = config
        self.callback = callback
        self.observer = Observer()
        self._last_scan_by_path: dict[str, float] = {}
        self._debounce = 2.0
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.get_event_loop()

    async def start(self) -> None:
        """Start watchdog observer and keep it alive until cancelled."""

        handler = _Handler(self._on_event)
        for root in self._watch_roots():
            if root.exists():
                self.observer.schedule(handler, str(root), recursive=True)
        self.observer.start()
        try:
            while self.observer.is_alive():
                await asyncio.sleep(1)
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop watchdog observer."""

        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join(timeout=5)

    def _watch_roots(self) -> list[Path]:
        serve_roots = self.config.get("serve", {}).get("watch_dirs") or []
        if serve_roots:
            return [Path(root) for root in serve_roots]
        sources = self.config["sources"]
        if sources.get("type") == "multi-project":
            return [Path(project["path"]) for project in sources.get("projects", [])]
        return [Path(sources["root"])]

    def _on_event(self, path: str) -> None:
        if not path.endswith(".java"):
            return
        now = time.time()
        last = self._last_scan_by_path.get(path, 0.0)
        if now - last < self._debounce:
            return
        self._last_scan_by_path[path] = now
        self._loop.call_soon_threadsafe(lambda: asyncio.create_task(self.callback(path)))


class _Handler(FileSystemEventHandler):
    def __init__(self, callback: Callable[[str], None]):
        self.callback = callback

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self.callback(str(event.src_path))

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self.callback(str(event.src_path))
