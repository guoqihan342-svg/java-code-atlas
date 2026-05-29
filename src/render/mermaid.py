"""Mermaid graph generation."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader


class MermaidRenderer:
    """Generate module dependency and class relationship Mermaid diagrams."""

    def __init__(self, template_dir: str | Path = "templates"):
        self.env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=False)

    def render(self, java_struct: dict[str, Any]) -> str:
        template = self.env.get_template("mermaid.mmd.j2")
        return template.render(
            project=java_struct.get("java_struct", {}).get("project", "JavaStruct"),
            module_graph=self.module_dependency_graph(java_struct),
            class_graph=self.class_relationship_graph(java_struct),
        )

    def write(self, java_struct: dict[str, Any], output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(java_struct), encoding="utf-8")
        return path

    @staticmethod
    def module_dependency_graph(java_struct: dict[str, Any]) -> list[dict[str, Any]]:
        entity_module = {entity.get("fqn"): entity.get("module", "unknown") for entity in java_struct.get("entities", [])}
        weights: dict[tuple[str, str], int] = defaultdict(int)
        for rel in java_struct.get("relationships", []):
            src = entity_module.get(rel.get("source"))
            dst = entity_module.get(rel.get("target"))
            if not src or not dst or src == dst:
                continue
            weights[(src, dst)] += int(rel.get("weight", 1) or 1)
        return [{"source": s, "target": t, "weight": w} for (s, t), w in sorted(weights.items())]

    @staticmethod
    def class_relationship_graph(java_struct: dict[str, Any], limit: int = 200) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for rel in java_struct.get("relationships", [])[:limit]:
            rows.append(
                {
                    "source": MermaidRenderer._short(rel.get("source", "")),
                    "target": MermaidRenderer._short(rel.get("target", "")),
                    "type": rel.get("type", "depends"),
                }
            )
        return rows

    @staticmethod
    def _short(fqn: str) -> str:
        return fqn.rsplit(".", 1)[-1].replace("$", "_").replace("-", "_")
