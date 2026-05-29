from __future__ import annotations

from pathlib import Path

import pytest

from src.config import ConfigError, ConfigLoader
from src.orchestrator import JavaAnalyzer


def test_empty_sources_list_raises_for_multi_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "jstruct.yaml").write_text("sources: {config_file: config/sources.yaml}\nllm: {enabled: false}\n", encoding="utf-8")
    (config_dir / "sources.yaml").write_text("type: multi-project\nprojects: []\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="multi-project"):
        ConfigLoader.load("config/jstruct.yaml")


def test_jdk_version_detection_from_pom_xml(tmp_path: Path, sample_config: dict, monkeypatch: pytest.MonkeyPatch, valid_pom_content: str):
    project = tmp_path / "java-project"
    project.mkdir()
    (project / "pom.xml").write_text(valid_pom_content, encoding="utf-8")
    sample_config["sources"]["root"] = str(project)
    sample_config["java"]["jdk_version"] = ""
    monkeypatch.setattr("src.orchestrator.shutil.which", lambda name: None)

    assert JavaAnalyzer(sample_config).jdk_version == "17"


def test_multiple_source_directories_in_multi_project(sample_config: dict):
    sample_config["sources"] = {
        "type": "multi-project",
        "projects": [{"path": "/tmp/a"}, {"path": "/tmp/b"}],
        "exclude": [],
    }

    command = JavaAnalyzer(sample_config)._build_command("analyze")

    assert command.count("--root") == 2
    assert "/tmp/a" in command
    assert "/tmp/b" in command


def test_deep_merge_of_config_layers():
    base = {"project": {"name": "base", "owner": "team"}, "output": {"dir": "out", "formats": ["html"]}}
    override = {"project": {"name": "override"}, "output": {"human_first": False}}

    merged = ConfigLoader._merge_dicts(base, override)

    assert merged["project"] == {"name": "override", "owner": "team"}
    assert merged["output"] == {"dir": "out", "formats": ["html"], "human_first": False}
