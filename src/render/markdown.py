"""Markdown report generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader


class MarkdownRenderer:
    """Render architecture overview, hotspot Top10, and refactoring suggestions."""

    def __init__(self, template_dir: str | Path = "templates"):
        self.env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=False)

    def render(self, java_struct: dict[str, Any]) -> str:
        metrics = java_struct.get("metrics", {})
        hotspots = list(metrics.get("hotspots", []))[:10]
        cycles = metrics.get("cycles", [])
        martin = metrics.get("martin", [])
        recommendations = self._recommendations(cycles, martin, hotspots)
        template = self.env.get_template("report.md.j2")
        return template.render(
            meta=java_struct.get("java_struct", {}),
            modules=java_struct.get("modules", []),
            entities=java_struct.get("entities", []),
            relationships=java_struct.get("relationships", []),
            hotspots=hotspots,
            cycles=cycles,
            martin=martin,
            recommendations=recommendations,
        )

    def write(self, java_struct: dict[str, Any], output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(java_struct), encoding="utf-8")
        return path

    @staticmethod
    def _recommendations(cycles: list[Any], martin: list[dict[str, Any]], hotspots: list[dict[str, Any]]) -> list[str]:
        suggestions: list[str] = []
        if cycles:
            suggestions.append(f"发现 {len(cycles)} 处环依赖，优先拆分跨模块调用或提取接口。")
        pain = [m for m in martin if m.get("zone") == "pain"]
        if pain:
            names = ", ".join(str(m.get("module")) for m in pain[:5])
            suggestions.append(f"痛苦区模块需要降低具体依赖或提高抽象度: {names}。")
        if hotspots:
            top = hotspots[0].get("fqn") or hotspots[0].get("class") or "未知类"
            suggestions.append(f"最高热点 {top} 建议优先做职责拆分和复杂度治理。")
        return suggestions or ["未发现明确的高优先级重构项。"]
