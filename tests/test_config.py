from __future__ import annotations

from pathlib import Path

import pytest

from src.config import ConfigError, ConfigLoader


def test_load_jstruct_example_sections():
    data = ConfigLoader._load_yaml("config/jstruct.yaml.example")

    for section in ("version", "project", "sources", "java", "llm", "output"):
        assert section in data
    assert data["version"] == 1
    assert data["project"]["name"]


def test_load_model_example_fields():
    data = ConfigLoader._load_yaml("config/model.yaml.example")

    assert data["backend"]
    assert data["endpoint"].endswith("/chat/completions")
    assert data["model"]


def test_load_sources_example_fields():
    data = ConfigLoader._load_yaml("config/sources.yaml.example")

    assert data["type"] == "maven-multi-module"
    assert "root" in data
    assert isinstance(data["modules"], list)


def test_load_defaults_when_jstruct_file_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, config_files: Path):
    monkeypatch.chdir(tmp_path)

    config = ConfigLoader.load("config/missing-jstruct.yaml")

    assert config["project"]["name"] == "jstruct"
    assert config["sources"]["root"] == "/tmp/project"
    assert config["output"]["dir"] == ".jstruct/output"


@pytest.mark.parametrize("template", ["$JSTRUCT_TEST_KEY", "${JSTRUCT_TEST_KEY}"])
def test_env_var_substitution(template: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("JSTRUCT_TEST_KEY", "resolved-key")
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "jstruct.yaml").write_text("sources: {config_file: config/sources.yaml}\nllm: {config_file: config/model.yaml}\n", encoding="utf-8")
    (config_dir / "sources.yaml").write_text("type: maven-multi-module\nroot: /tmp/project\n", encoding="utf-8")
    (config_dir / "model.yaml").write_text(f"endpoint: https://example.test\nmodel: m\napi_key: {template}\n", encoding="utf-8")

    config = ConfigLoader.load("config/jstruct.yaml")

    assert config["llm"]["api_key"] == "resolved-key"


def test_invalid_yaml_raises_config_error(tmp_path: Path):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("project: [unterminated\n", encoding="utf-8")

    with pytest.raises(ConfigError):
        ConfigLoader._load_yaml(bad_yaml)
