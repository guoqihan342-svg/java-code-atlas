from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from src.render.html import HtmlRenderer


REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYZER_DIR = REPO_ROOT / "java-analyzer"
PETCLINIC_DIR = Path("/tmp/spring-petclinic")
ATLAS_JSON = Path("/tmp/spring-petclinic-atlas.json")
METRICS_JSON = Path("/tmp/spring-petclinic-metrics.json")
SCHEMA_VERSION = "1.0.0"

pytestmark = [
    pytest.mark.skipif(shutil.which("git") is None, reason="git is required to clone spring-petclinic"),
    pytest.mark.skipif(shutil.which("java") is None, reason="java is required to run the analyzer"),
    pytest.mark.skipif(shutil.which("javac") is None, reason="javac is required to compile the analyzer"),
]


@pytest.fixture
def output_files():
    for path in (ATLAS_JSON, METRICS_JSON):
        path.unlink(missing_ok=True)
    yield ATLAS_JSON, METRICS_JSON
    for path in (ATLAS_JSON, METRICS_JSON):
        path.unlink(missing_ok=True)


def _run(args: list[str], *, cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def _ensure_petclinic() -> Path:
    if not PETCLINIC_DIR.exists():
        result = _run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "https://github.com/spring-projects/spring-petclinic.git",
                str(PETCLINIC_DIR),
            ],
            cwd=Path("/tmp"),
            timeout=120,
        )
        if result.returncode != 0:
            pytest.skip(f"could not clone spring-petclinic: {result.stderr.strip()}")

    if not (PETCLINIC_DIR / "pom.xml").exists():
        pytest.skip(f"{PETCLINIC_DIR} is not a usable spring-petclinic checkout")
    return PETCLINIC_DIR


def _m2_classpath() -> str:
    jars = sorted(Path.home().joinpath(".m2").rglob("*.jar"))
    if not jars:
        pytest.skip("no Maven dependencies found in ~/.m2 for javac analyzer classpath")
    return os.pathsep.join(str(jar) for jar in jars)


def _compile_analyzer() -> str:
    classes_dir = ANALYZER_DIR / "target" / "classes"
    classes_dir.mkdir(parents=True, exist_ok=True)

    sources = sorted(ANALYZER_DIR.joinpath("src/main/java").rglob("*.java"))
    assert sources, "java analyzer sources are missing"

    deps = _m2_classpath()
    result = _run(
        ["javac", "-cp", deps, "-d", str(classes_dir), *map(str, sources)],
        cwd=ANALYZER_DIR,
        timeout=120,
    )
    if result.returncode != 0:
        pytest.fail(f"failed to compile analyzer with javac\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")

    analyzer_cli = classes_dir / "io/github/javacodeatlas/AnalyzerCli.class"
    assert analyzer_cli.exists(), "AnalyzerCli.class was not produced by javac"
    return os.pathsep.join([str(classes_dir), deps])


def _warm_petclinic_dependencies() -> None:
    if shutil.which("mvn") is None:
        return

    try:
        _run(["mvn", "-o", "dependency:go-offline"], cwd=PETCLINIC_DIR, timeout=30)
    except subprocess.TimeoutExpired:
        # The analyzer runs from the compiled analyzer classpath, so this warmup is optional.
        return


def _load_json(path: Path) -> dict:
    assert path.exists(), f"{path} does not exist"
    assert path.stat().st_size > 1024, f"{path} is unexpectedly small"
    return json.loads(path.read_text(encoding="utf-8"))


def _entity_id(entity: dict) -> str | None:
    return entity.get("id") or entity.get("fqn")


def _entity_name(entity: dict) -> str | None:
    return entity.get("name") or entity.get("className")


def _metric_list(metrics: dict, *names: str) -> list:
    for name in names:
        value = metrics.get(name)
        if isinstance(value, list):
            return value
    return []


def test_full_pipeline_on_spring_petclinic(output_files):
    atlas_path, metrics_path = output_files
    project = _ensure_petclinic()
    classpath = _compile_analyzer()
    _warm_petclinic_dependencies()

    analyze_start = time.perf_counter()
    analyze = _run(
        [
            "java",
            "-cp",
            classpath,
            "io.github.javacodeatlas.AnalyzerCli",
            "analyze",
            "--root",
            str(project),
            "--output",
            str(atlas_path),
        ],
        cwd=ANALYZER_DIR,
        timeout=120,
    )
    analyze_seconds = time.perf_counter() - analyze_start
    print(f"spring-petclinic analyze took {analyze_seconds:.2f}s")
    assert analyze.returncode == 0, f"analyze failed\nSTDOUT:\n{analyze.stdout}\nSTDERR:\n{analyze.stderr}"

    atlas = _load_json(atlas_path)
    assert atlas.get("atlas", {}).get("version") == SCHEMA_VERSION
    assert len(atlas.get("modules") or []) >= 1

    entities = atlas.get("entities") or []
    relationships = atlas.get("relationships") or []
    assert entities, "atlas must contain entity fingerprints"
    assert relationships, "atlas must contain dependencies"

    allowed_kinds = {"CLASS", "INTERFACE", "ENUM", "class", "interface", "enum", "abstract", "record", "annotation"}
    for entity in entities:
        assert _entity_id(entity), f"entity is missing id/fqn: {entity}"
        assert _entity_name(entity), f"entity is missing name/className: {entity}"
        assert entity.get("kind") in allowed_kinds
        assert "javaPackage" in entity
        assert isinstance(entity.get("roles", []), list)

    spring_roles = {
        "SERVICE",
        "CONTROLLER",
        "REST_ENTRY",
        "MVC_ENTRY",
        "BUSINESS_LOGIC",
        "SPRING_BEAN",
        "CONFIG",
        "DATA_ACCESS",
        "PERSISTENCE_MODEL",
    }
    assert any(spring_roles.intersection(entity.get("roles", [])) for entity in entities)

    metrics = _run(
        [
            "java",
            "-cp",
            classpath,
            "io.github.javacodeatlas.AnalyzerCli",
            "metrics",
            "--input",
            str(atlas_path),
            "--output",
            str(metrics_path),
        ],
        cwd=ANALYZER_DIR,
        timeout=120,
    )
    assert metrics.returncode == 0, f"metrics failed\nSTDOUT:\n{metrics.stdout}\nSTDERR:\n{metrics.stderr}"

    metrics_doc = _load_json(metrics_path)
    hotspots = _metric_list(metrics_doc, "hotSpots", "hotspots")
    assert hotspots, "metrics must contain hotSpots/hotspots"
    hotspot_scores = [hotspot["score"] for hotspot in hotspots]
    assert hotspot_scores == sorted(hotspot_scores, reverse=True)

    module_metrics = _metric_list(metrics_doc, "moduleMetrics", "martin")
    assert module_metrics, "metrics must contain moduleMetrics/martin"
    for metric in module_metrics:
        assert "abstractness" in metric
        assert "instability" in metric
        assert 0 <= metric["abstractness"] <= 1
        assert 0 <= metric["instability"] <= 1

    cycle_count = metrics_doc.get("cycleCount")
    if cycle_count is None:
        cycle_count = len(metrics_doc.get("moduleCycles") or [])
    assert cycle_count == 0

    graph_stats = metrics_doc.get("graphStats")
    if graph_stats is None:
        graph_stats = {
            "nodeCount": len(metrics_doc.get("classDegrees") or {}),
            "edgeCount": len(relationships),
        }
    assert graph_stats["nodeCount"] >= len(entities)
    assert graph_stats["edgeCount"] >= len(relationships)

    html = HtmlRenderer(template_dir=REPO_ROOT / "templates").render()
    assert "cytoscape" in html.lower()
