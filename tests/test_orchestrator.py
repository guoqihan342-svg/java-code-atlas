from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from src.orchestrator import AnalyzerError, JavaAnalyzer


def test_jdk_detection_logic(monkeypatch: pytest.MonkeyPatch, sample_config: dict):
    sample_config["java"]["jdk_version"] = ""
    monkeypatch.setattr("src.orchestrator.shutil.which", lambda name: "/usr/bin/java")

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr='openjdk version "21.0.2" 2024-01-16')

    monkeypatch.setattr("src.orchestrator.subprocess.run", fake_run)

    assert JavaAnalyzer(sample_config).jdk_version == "21"


def test_jar_path_construction_from_config(sample_config: dict):
    analyzer = JavaAnalyzer(sample_config)

    assert analyzer.jar_path == Path("java-analyzer/target/java-code-atlas-analyzer-0.2.0.jar")
    command = analyzer._build_command("analyze")
    assert "io.github.javacodeatlas.AnalyzerCli" in command
    assert "--root" in command
    assert sample_config["sources"]["root"] in command


def test_analyze_subprocess_call_constructed_correctly(monkeypatch: pytest.MonkeyPatch, sample_config: dict, sample_atlas_data: dict, tmp_path: Path):
    calls: list[list[str]] = []
    monkeypatch.setattr(JavaAnalyzer, "_build_jar", lambda self: None)

    def fake_run(cmd, capture_output, text, timeout, check):
        calls.append(cmd)
        output_path = Path(cmd[cmd.index("--output") + 1])
        output_path.write_text(json.dumps(sample_atlas_data), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("src.orchestrator.subprocess.run", fake_run)
    output_path = tmp_path / "atlas-raw.json"

    result = JavaAnalyzer(sample_config).analyze(output_path)

    assert result["atlas"]["version"] == JavaAnalyzer.CURRENT_SCHEMA_VERSION
    assert calls
    cmd = calls[0]
    assert cmd[-2:] == ["--output", str(output_path)]
    assert cmd[0] == "java"
    assert "analyze" in cmd


def test_error_handling_when_analyzer_process_fails(monkeypatch: pytest.MonkeyPatch, sample_config: dict, tmp_path: Path):
    monkeypatch.setattr(JavaAnalyzer, "_build_jar", lambda self: None)

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="bad config")

    monkeypatch.setattr("src.orchestrator.subprocess.run", fake_run)

    with pytest.raises(AnalyzerError, match="bad config"):
        JavaAnalyzer(sample_config).analyze(tmp_path / "atlas-raw.json")
