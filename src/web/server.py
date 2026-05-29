"""aiohttp web server for Java Code Atlas."""

from __future__ import annotations

import asyncio
import json
import webbrowser
from pathlib import Path
from typing import Any

from aiohttp import WSMsgType, web

from src.orchestrator import JavaAnalyzer
from src.render.html import HtmlRenderer
from src.render.markdown import MarkdownRenderer
from src.render.mermaid import MermaidRenderer
from src.web.websocket import WebSocketManager


class AtlasServer:
    """Serve the interactive Atlas UI and JSON APIs."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.app = web.Application()
        self.atlas_data: dict[str, Any] | None = None
        self.status = "idle"
        self.error: str | None = None
        self._scan_lock = asyncio.Lock()
        self.ws = WebSocketManager()
        self._watcher = None
        self._setup_routes()

    def _setup_routes(self) -> None:
        self.app.router.add_get("/", self._index)
        self.app.router.add_get("/api/atlas.json", self._atlas_json)
        self.app.router.add_get("/api/status", self._status)
        self.app.router.add_post("/api/reload", self._reload)
        self.app.router.add_get("/ws", self._websocket)

    async def _index(self, request: web.Request) -> web.Response:
        html = HtmlRenderer().render(self.config)
        return web.Response(text=html, content_type="text/html")

    async def _atlas_json(self, request: web.Request) -> web.Response:
        if not self.atlas_data:
            raise web.HTTPNotFound(text="图谱尚未生成")
        return web.json_response(self.atlas_data)

    async def _status(self, request: web.Request) -> web.Response:
        return web.json_response({"status": self.status, "error": self.error})

    async def _reload(self, request: web.Request) -> web.Response:
        asyncio.create_task(self._rescan(broadcast=True))
        return web.json_response({"status": "scanning"})

    async def _websocket(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)
        self.ws.add(ws)
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT and msg.data == "reload":
                    asyncio.create_task(self._rescan(broadcast=True))
                elif msg.type == WSMsgType.ERROR:
                    break
        finally:
            self.ws.discard(ws)
        return ws

    async def start(self) -> None:
        """Run initial scan, start HTTP server, optionally open browser and watch files."""

        host = self.config["serve"]["host"]
        port = int(self.config["serve"]["port"])
        await self._rescan(broadcast=False)

        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()

        url = f"http://{host}:{port}"
        print(f"\nJava Code Atlas -> {url}")
        print(f"监控目录: {self._watch_description()}")
        print(f"Watch 模式: {'启用' if self.config['serve'].get('watch') else '关闭'}\n")

        if self.config["serve"].get("open_browser", True):
            webbrowser.open(url)

        if self.config["serve"].get("watch", True):
            from .watcher import FileWatcher

            self._watcher = FileWatcher(self.config, self._on_file_changed)
            asyncio.create_task(self._watcher.start())

        await asyncio.Event().wait()

    async def _on_file_changed(self, path: str) -> None:
        await self.ws.broadcast({"type": "status", "status": "scanning", "path": path})
        await self._rescan(broadcast=True, changed_path=path)

    async def _rescan(self, broadcast: bool = False, changed_path: str | None = None) -> None:
        async with self._scan_lock:
            self.status = "scanning"
            self.error = None
            if broadcast:
                await self.ws.broadcast({"type": "status", "status": "scanning"})
            try:
                analyzer = JavaAnalyzer(self.config)
                atlas = await asyncio.to_thread(analyzer.scan)
                self.atlas_data = atlas
                self._write_reports(atlas)
                self.status = "done"
                if broadcast:
                    await self.ws.broadcast(
                        {
                            "type": "full-reload",
                            "changed_path": changed_path,
                            "atlas": atlas.get("atlas", {}),
                        }
                    )
            except Exception as exc:
                self.status = "error"
                self.error = str(exc)
                if broadcast:
                    await self.ws.broadcast({"type": "error", "error": self.error})
                if self.atlas_data is None:
                    raise

    def _write_reports(self, atlas: dict[str, Any]) -> None:
        output_dir = Path(self.config["output"]["dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        formats = set(self.config.get("output", {}).get("formats", []))
        (output_dir / "atlas.json").write_text(json.dumps(atlas, ensure_ascii=False, indent=2), encoding="utf-8")
        if "html" in formats:
            HtmlRenderer().write(output_dir / "graph.html", self.config)
        if "md" in formats:
            MarkdownRenderer().write(atlas, output_dir / "report.md")
        if "mmd" in formats:
            MermaidRenderer().write(atlas, output_dir / "mermaid.mmd")

    def _watch_description(self) -> str:
        if self.config["serve"].get("watch_dirs"):
            return ", ".join(map(str, self.config["serve"]["watch_dirs"]))
        sources = self.config["sources"]
        if sources.get("type") == "multi-project":
            return ", ".join(project["path"] for project in sources.get("projects", []))
        return str(sources.get("root", ""))
