from __future__ import annotations

from src.render.html import HtmlRenderer


def test_html_generation_with_minimal_atlas_data():
    html = HtmlRenderer().render({"project": {"name": "sample-project"}})

    assert "<!DOCTYPE html>" in html
    assert "Java Code Atlas" in html


def test_output_contains_cytoscape_cdn_link():
    html = HtmlRenderer().render()

    assert "https://cdn.jsdelivr.net/npm/cytoscape" in html


def test_json_data_is_fetched_not_inlined():
    html = HtmlRenderer().render()

    assert "fetch('/api/atlas.json')" in html
    assert "const atlas =" not in html


def test_four_view_tabs_exist():
    html = HtmlRenderer().render()

    for view_id in ("btn-topo", "btn-matrix", "btn-layers", "btn-hot"):
        assert f'id="{view_id}"' in html
    assert html.count("<button id=\"btn-") == 4
