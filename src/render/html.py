"""HTML shell renderer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


class HtmlRenderer:
    """Render the graph HTML shell; data is loaded by the browser via fetch."""

    def __init__(self, template_dir: str | Path = "templates"):
        self.template_dir = Path(template_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(("html", "xml")),
        )

    def render(self, config: dict[str, Any] | None = None) -> str:
        template = self.env.get_template("graph.html.j2")
        return template.render(config=config or {})

    def write(self, output_path: str | Path, config: dict[str, Any] | None = None) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(config), encoding="utf-8")
        return path
