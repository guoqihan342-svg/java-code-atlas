"""Click command-line interface for JavaStruct."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import click
import yaml
from rich.console import Console

from .config import ConfigLoader
from .orchestrator import JavaAnalyzer
from .render.html import HtmlRenderer
from .render.markdown import MarkdownRenderer
from .render.mermaid import MermaidRenderer
from .web.server import JavaStructServer

console = Console()


@click.group()
def cli() -> None:
    """JavaStruct."""


@cli.command()
@click.option("--host", default=None, help="HTTP host override.")
@click.option("--port", default=None, type=int, help="HTTP port override.")
@click.option("--no-browser", is_flag=True, help="Do not open browser automatically.")
@click.option("--no-watch", is_flag=True, help="Disable watchdog file watching.")
def serve(host: str | None, port: int | None, no_browser: bool, no_watch: bool) -> None:
    """Load config, scan Java code, start aiohttp, browser, and watchdog."""

    config = ConfigLoader.load()
    if host:
        config["serve"]["host"] = host
    if port:
        config["serve"]["port"] = port
    if no_browser:
        config["serve"]["open_browser"] = False
    if no_watch:
        config["serve"]["watch"] = False
    asyncio.run(JavaStructServer(config).start())


@cli.command()
@click.option("-o", "--output-dir", default=None, type=click.Path(path_type=Path), help="Output directory override.")
def scan(output_dir: Path | None) -> None:
    """Run one scan, write reports, and exit."""

    config = ConfigLoader.load()
    if output_dir:
        config["output"]["dir"] = str(output_dir)
    java_struct = JavaAnalyzer(config).scan()
    _write_reports(config, java_struct)
    console.print(f"[green]扫描完成[/green]: {config['output']['dir']}")


@cli.command()
@click.option("--format", "fmt", default="json", type=click.Choice(["json"]), help="Dump format.")
def dump(fmt: str) -> None:
    """Output pure data JSON for downstream agents."""

    config = ConfigLoader.load()
    java_struct = JavaAnalyzer(config).scan()
    click.echo(json.dumps(_agent_dump(java_struct), ensure_ascii=False, indent=2))


@cli.group(name="config")
def config_group() -> None:
    """Configuration management."""


@config_group.command("init")
@click.option("--force", is_flag=True, help="Overwrite existing config files.")
def config_init(force: bool) -> None:
    """Create config/java_struct.yaml, sources.yaml, and model.yaml from examples."""

    created = ConfigLoader.init_examples(force=force)
    if created:
        for path in created:
            console.print(f"[green]写入[/green] {path}")
    else:
        console.print("[yellow]配置已存在；使用 --force 覆盖[/yellow]")


@config_group.command("validate")
def config_validate() -> None:
    """Validate current configuration."""

    ConfigLoader.load()
    console.print("[green]配置有效[/green]")


@config_group.command("show")
def config_show() -> None:
    """Show merged configuration."""

    config = ConfigLoader.load()
    click.echo(yaml.safe_dump(config, allow_unicode=True, sort_keys=False))


def _write_reports(config: dict[str, Any], java_struct: dict[str, Any]) -> None:
    output_dir = Path(config["output"]["dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    formats = set(config.get("output", {}).get("formats", []))
    (output_dir / "java_struct.json").write_text(json.dumps(java_struct, ensure_ascii=False, indent=2), encoding="utf-8")
    if "html" in formats:
        HtmlRenderer().write(output_dir / "graph.html", config)
    if "md" in formats:
        MarkdownRenderer().write(java_struct, output_dir / "report.md")
    if "mmd" in formats:
        MermaidRenderer().write(java_struct, output_dir / "mermaid.mmd")


def _agent_dump(java_struct: dict[str, Any]) -> dict[str, Any]:
    meta = java_struct.get("java_struct", {})
    metrics = java_struct.get("metrics", {})
    modules = java_struct.get("modules", [])
    relationships = java_struct.get("relationships", [])
    entities = java_struct.get("entities", [])
    entity_module = {e.get("fqn"): e.get("module") for e in entities}
    deps_in: dict[str, set[str]] = {m.get("id") or m.get("module") or m.get("name"): set() for m in modules}
    deps_out: dict[str, set[str]] = {m.get("id") or m.get("module") or m.get("name"): set() for m in modules}
    for rel in relationships:
        src = entity_module.get(rel.get("source"))
        dst = entity_module.get(rel.get("target"))
        if src and dst and src != dst:
            deps_out.setdefault(src, set()).add(dst)
            deps_in.setdefault(dst, set()).add(src)

    return {
        "format": "java_struct-agent-v1",
        "java_struct_version": meta.get("version", "1.0.0"),
        "timestamp": meta.get("generated_at") or meta.get("generatedAt"),
        "project": meta.get("project"),
        "summary": {
            "total_modules": meta.get("totalModules", len(modules)),
            "total_classes": meta.get("totalEntities", len(entities)),
            "total_relationships": meta.get("totalRelationships", len(relationships)),
            "cycles": len(metrics.get("cycles", [])),
            "pain_modules": len([m for m in metrics.get("martin", []) if m.get("zone") == "pain"]),
        },
        "modules": [
            {
                "id": mid,
                "deps_in": sorted(deps_in.get(mid, set())),
                "deps_out": sorted(deps_out.get(mid, set())),
            }
            for mid in sorted(set(deps_in) | set(deps_out))
            if mid
        ],
        "recommendations": MarkdownRenderer._recommendations(
            metrics.get("cycles", []), metrics.get("martin", []), metrics.get("hotspots", [])
        ),
    }
