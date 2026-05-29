from __future__ import annotations

from src.render.mermaid import MermaidRenderer


def test_mermaid_graph_generation(sample_jstruct_data: dict):
    output = MermaidRenderer().render(sample_jstruct_data)

    assert "flowchart LR" in output
    assert "classDiagram" in output
    assert "UserController --> UserService" in output


def test_module_dependency_diagram(sample_jstruct_data: dict):
    edges = MermaidRenderer.module_dependency_graph(sample_jstruct_data)

    assert edges == [{"source": "app", "target": "core", "weight": 2}]


def test_output_starts_with_graph_or_flowchart_after_comment(sample_jstruct_data: dict):
    output = MermaidRenderer().render(sample_jstruct_data)
    body = "\n".join(line for line in output.splitlines() if not line.startswith("%%")).strip()

    assert body.startswith(("graph", "flowchart"))
