from __future__ import annotations

from src.render.markdown import MarkdownRenderer


def test_markdown_report_generation(sample_atlas_data: dict):
    report = MarkdownRenderer().render(sample_atlas_data)

    assert "# sample-project 架构报告" in report
    assert "## 架构概览" in report
    assert "## 重构建议" in report


def test_headers_and_tables_are_correctly_formatted(sample_atlas_data: dict):
    report = MarkdownRenderer().render(sample_atlas_data)

    assert "| 排名 | 类 | 分数 |" in report
    assert "|---:|---|---:|" in report
    assert "| 模块 | Ca | Ce | I | A | D | Zone |" in report
    assert "| core | 1 | 1 | 0.50 | 0.25 | 0.25 | good |" in report
