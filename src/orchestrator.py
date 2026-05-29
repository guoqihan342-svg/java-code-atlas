"""Subprocess orchestration for the Java analyzer JAR."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AnalyzerError(RuntimeError):
    """Raised when the Java analyzer cannot complete successfully."""


class JavaAnalyzer:
    """Build and invoke java-code-atlas-analyzer commands."""

    CURRENT_SCHEMA_VERSION = "1.0.0"

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.jar_path = Path("java-analyzer/target/java-code-atlas-analyzer-0.2.0.jar")
        self.jdk_version = str(config.get("java", {}).get("jdk_version") or self._detect_jdk())
        self.maven_home = str(config.get("java", {}).get("maven_home") or "")

    def analyze(self, output_path: Path) -> dict[str, Any]:
        """Run the analyzer's analyze subcommand."""

        self._build_jar()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = self._build_command("analyze")
        cmd.extend(["--output", str(output_path)])
        return self._run(cmd, output_path)

    def metrics(self, input_path: Path, output_path: Path) -> dict[str, Any]:
        """Run the analyzer's metrics subcommand."""

        self._build_jar()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = self._build_command("metrics")
        cmd.extend(["--input", str(input_path), "--output", str(output_path)])
        return self._run(cmd, output_path)

    def scan(self) -> dict[str, Any]:
        """Run analyze + metrics and merge the resulting data for web rendering."""

        output_dir = Path(self.config["output"]["dir"])
        raw_path = output_dir / "atlas-raw.json"
        metrics_path = output_dir / "atlas-metrics.json"
        raw = self.analyze(raw_path)
        metrics = self.metrics(raw_path, metrics_path)
        atlas = dict(raw)
        atlas["metrics"] = metrics.get("metrics", metrics)
        atlas_path = output_dir / "atlas.json"
        atlas_path.write_text(json.dumps(atlas, ensure_ascii=False, indent=2), encoding="utf-8")
        return atlas

    def _build_command(self, subcommand: str) -> list[str]:
        java = "java"
        java_home = os.environ.get(f"JAVA_{self.jdk_version}_HOME", "")
        if java_home:
            java = str(Path(java_home) / "bin" / "java")

        # Build classpath: compiled classes + all dependency jars
        classpath = [str(self.jar_path.parent.parent / "classes")]
        repo = Path.home() / ".m2" / "repository"
        if repo.exists():
            classpath.extend(str(p) for p in repo.rglob("*.jar"))
        cp_sep = ";" if os.name == "nt" else ":"
        cmd = [java, "-cp", cp_sep.join(classpath),
               "io.github.javacodeatlas.AnalyzerCli", subcommand]

        mvn_home = self.maven_home or os.environ.get("M2_HOME", "")
        if mvn_home:
            cmd.extend(["--maven-home", mvn_home])

        sources = self.config["sources"]
        if sources.get("type") == "multi-project":
            for project in sources.get("projects", []):
                cmd.extend(["--root", str(project["path"])])
        else:
            cmd.extend(["--root", str(sources["root"])])
            for module in sources.get("modules", []) or []:
                cmd.extend(["--module", str(module)])

        for pattern in sources.get("exclude", []) or []:
            cmd.extend(["--exclude", str(pattern)])

        return cmd

    def _run(self, cmd: list[str], output_path: Path) -> dict[str, Any]:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=False)
        except FileNotFoundError as exc:
            raise AnalyzerError(f"命令不存在: {cmd[0]}") from exc
        except subprocess.TimeoutExpired as exc:
            raise AnalyzerError("Java 分析器执行超时") from exc

        if result.returncode != 0:
            raise AnalyzerError(f"Java分析器失败:\n{result.stderr.strip() or result.stdout.strip()}")
        if not output_path.exists():
            raise AnalyzerError(f"Java分析器未生成输出文件: {output_path}")

        with output_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        self._validate_schema(data)
        return data

    def _build_jar(self) -> None:
        """Build analyzer JAR with Maven when it is missing."""

        if self.jar_path.exists():
            return
        pom = Path("java-analyzer/pom.xml")
        if not pom.exists():
            raise AnalyzerError("缺少 java-analyzer/pom.xml，无法构建 Java 分析器")

        mvn = str(Path(self.maven_home) / "bin" / "mvn") if self.maven_home else "mvn"
        maven_args = str(self.config.get("java", {}).get("maven_args") or "").split()
        cmd = [mvn, "-f", str(pom), "package", "-DskipTests", *maven_args]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=900, check=False)
        except FileNotFoundError as exc:
            raise AnalyzerError("Maven 不可用，请配置 java.maven_home 或将 mvn 加入 PATH") from exc
        if result.returncode != 0:
            raise AnalyzerError(f"构建 Java 分析器失败:\n{result.stderr.strip() or result.stdout.strip()}")
        if not self.jar_path.exists():
            candidates = sorted(Path("java-analyzer/target").glob("*.jar"))
            shaded = [p for p in candidates if "original-" not in p.name]
            if shaded:
                self.jar_path = shaded[0]
            else:
                raise AnalyzerError(f"构建完成但未找到 JAR: {self.jar_path}")

    def _detect_jdk(self) -> str:
        java = shutil.which("java")
        if not java:
            return ""
        result = subprocess.run([java, "-version"], capture_output=True, text=True, check=False)
        text = result.stderr or result.stdout
        if '"' in text:
            version = text.split('"')[1]
            return version.split(".")[0] if not version.startswith("1.") else version.split(".")[1]
        return ""

    def _validate_schema(self, data: dict[str, Any]) -> None:
        version = data.get("atlas", {}).get("version")
        if version != self.CURRENT_SCHEMA_VERSION:
            raise ValueError(f"数据版本不匹配: 期望 {self.CURRENT_SCHEMA_VERSION}, 收到 {version}; 请重建 JAR")


def fallback_empty_atlas(config: dict[str, Any], error: str | None = None) -> dict[str, Any]:
    """Create a valid empty Atlas document for recoverable UI states."""

    now = datetime.now(timezone.utc).isoformat()
    atlas = {
        "atlas": {
            "version": JavaAnalyzer.CURRENT_SCHEMA_VERSION,
            "generated_at": now,
            "generatedAt": now,
            "project": config.get("project", {}).get("name", "java-code-atlas"),
            "totalModules": 0,
            "totalEntities": 0,
            "totalRelationships": 0,
        },
        "modules": [],
        "entities": [],
        "relationships": [],
        "metrics": {"hotspots": [], "cycles": [], "martin": []},
    }
    if error:
        atlas["error"] = error
    return atlas
