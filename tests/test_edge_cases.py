import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _build_classpath():
    """Build classpath string for java -cp: target/classes + all M2 jars."""
    m2_jars = list((REPO_ROOT / "java-analyzer").glob("target/test-lib/*.jar"))
    m2_jars += sorted((Path.home() / ".m2" / "repository").rglob("*.jar"))
    jars = [str(p) for p in m2_jars]
    classes = str(REPO_ROOT / "java-analyzer" / "target" / "classes")
    return classes + ":" + ":".join(jars)


def _is_runnable_analyzer():
    """Verify the analyzer can be invoked via java -cp."""
    main_class = str(REPO_ROOT / "java-analyzer" / "target" / "classes" / "io" / "github" / "javacodeatlas" / "AnalyzerCli.class")
    if not Path(main_class).exists():
        return False
    # Quick smoke test: --help should work
    result = subprocess.run(
        ["java", "-cp", _build_classpath(), "io.github.javacodeatlas.AnalyzerCli", "analyze", "--help"],
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    return result.returncode == 0


@pytest.fixture(scope="session")
def atlas_jar():
    """Returns the classpath string (not a JAR path — we use java -cp, not java -jar)."""
    if shutil.which("java") is None:
        pytest.skip("java is not available")
    if shutil.which("javac") is None:
        pytest.skip("javac is not available")
    if not _is_runnable_analyzer():
        pytest.skip("analyzer classes not found or not runnable; compile with: javac -cp ... -d target/classes $(find src/main/java -name '*.java')")
    return _build_classpath()


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def pom(artifact_id, packaging="jar", modules=None, extra_properties=""):
    module_block = ""
    if modules:
        module_lines = "\n".join(f"    <module>{module}</module>" for module in modules)
        module_block = f"\n  <modules>\n{module_lines}\n  </modules>"
    return f"""
    <project>
      <modelVersion>4.0.0</modelVersion>
      <groupId>test</groupId>
      <artifactId>{artifact_id}</artifactId>
      <version>1.0.0</version>
      <packaging>{packaging}</packaging>
      {extra_properties}
      {module_block}
    </project>
    """


def run_analyze(atlas_jar, project_root, output=None, timeout=30):
    """atlas_jar is the classpath string (java -cp, not java -jar)."""
    output = output or project_root / "atlas.json"
    start = time.monotonic()
    result = subprocess.run(
        [
            "java",
            "-cp",
            atlas_jar,
            "io.github.javacodeatlas.AnalyzerCli",
            "analyze",
            "--root",
            str(project_root),
            "--output",
            str(output),
        ],
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    runtime = time.monotonic() - start
    assert result.returncode == 0, result.stderr or result.stdout
    assert "OutOfMemoryError" not in result.stderr
    assert output.exists()
    return json.loads(output.read_text(encoding="utf-8")), output, runtime, result


def run_metrics(atlas_jar, atlas_json, output=None, timeout=30):
    """atlas_jar is the classpath string."""
    output = output or atlas_json.with_name("atlas-metrics.json")
    result = subprocess.run(
        [
            "java",
            "-cp",
            atlas_jar,
            "io.github.javacodeatlas.AnalyzerCli",
            "metrics",
            "--input",
            str(atlas_json),
            "--output",
            str(output),
        ],
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(output.read_text(encoding="utf-8"))


def module_names(doc):
    return {module["module"] for module in doc["modules"]}


def entity_by_class(doc, class_name):
    return next(entity for entity in doc["entities"] if entity["className"] == class_name)


def build_empty(base):
    project = base / "tests" / "test_projects" / "empty"
    project.mkdir(parents=True)
    return project


def build_single_class(base):
    project = base / "tests" / "test_projects" / "single_class"
    write_file(
        project / "src/main/java/Hello.java",
        """
        public class Hello {
        }
        """,
    )
    return project


def build_circular(base):
    project = base / "tests" / "test_projects" / "circular"
    write_file(
        project / "src/main/java/circular/A.java",
        """
        package circular;

        import circular.B;

        public class A {
            public A(B b) {
            }
        }
        """,
    )
    write_file(
        project / "src/main/java/circular/B.java",
        """
        package circular;

        import circular.A;

        public class B {
            public B(A a) {
            }
        }
        """,
    )
    return project


def build_nested_maven(base):
    project = base / "tests" / "test_projects" / "nested_maven"
    write_file(project / "pom.xml", pom("nested-root", packaging="pom", modules=["parent"]))
    write_file(project / "parent/pom.xml", pom("parent", packaging="pom", modules=["core", "api"]))
    write_file(project / "parent/core/pom.xml", pom("core"))
    write_file(project / "parent/api/pom.xml", pom("api"))
    write_file(
        project / "parent/core/src/main/java/core/CoreService.java",
        """
        package core;

        public class CoreService {
        }
        """,
    )
    write_file(
        project / "parent/api/src/main/java/api/ApiController.java",
        """
        package api;

        import core.CoreService;

        public class ApiController {
            public ApiController(CoreService coreService) {
            }
        }
        """,
    )
    return project


def build_annotations(base):
    project = base / "tests" / "test_projects" / "annotations"
    annotations = {
        "RestEndpoint": "@RestController",
        "BusinessService": "@Service",
        "DataRepository": "@Repository",
        "GenericComponent": "@Component",
        "AppConfig": "@Configuration",
        "RemoteClient": '@FeignClient(name = "remote")',
        "BootApp": "@SpringBootApplication",
    }
    for class_name, annotation in annotations.items():
        write_file(
            project / f"src/main/java/ann/{class_name}.java",
            f"""
            package ann;

            {annotation}
            public class {class_name} {{
            }}
            """,
        )
    return project


def build_large(base):
    project = base / "tests" / "test_projects" / "large"
    methods = "\n".join(f"    public int method{i}() {{ return {i}; }}" for i in range(225))
    write_file(
        project / "src/main/java/stress/LargeClass.java",
        f"""
        package stress;

        public class LargeClass {{
        {methods}
        }}
        """,
    )
    return project


def build_jdk_versions(base):
    project = base / "tests" / "test_projects" / "jdk_versions"
    write_file(
        project / "pom.xml",
        pom(
            "jdk-versions",
            extra_properties="""
            <properties>
              <maven.compiler.release>21</maven.compiler.release>
            </properties>
            """,
        ),
    )
    write_file(project / ".java-version", "11")
    write_file(project / "build.gradle", 'sourceCompatibility = "1.8"')
    write_file(
        project / "src/main/java/jdk/JdkVersionMarker.java",
        """
        package jdk;

        public class JdkVersionMarker {
        }
        """,
    )
    return project


def build_regression(base):
    project = base / "tests" / "test_projects" / "regression"
    write_file(project / "pom.xml", pom("regression-root", packaging="pom", modules=["parent", "plain"]))
    write_file(project / "parent/pom.xml", pom("parent", packaging="pom", modules=["core", "api"]))
    write_file(project / "parent/core/pom.xml", pom("core", packaging="jar"))
    write_file(project / "parent/api/pom.xml", pom("api", packaging="jar"))
    write_file(project / "plain/pom.xml", pom("plain", packaging="jar"))
    write_file(
        project / "parent/core/src/main/java/reg/Core.java",
        """
        package reg;

        public class Core {
        }
        """,
    )
    write_file(
        project / "parent/api/src/main/java/reg/Api.java",
        """
        package reg;

        public class Api {
            public Api(Core core) {
            }
        }
        """,
    )
    write_file(
        project / "plain/src/main/java/reg/Plain.java",
        """
        package reg;

        public class Plain {
        }
        """,
    )
    return project


CASES = [
    ("empty", build_empty),
    ("single_class", build_single_class),
    ("circular", build_circular),
    ("nested_maven", build_nested_maven),
    ("annotations", build_annotations),
    ("large", build_large),
    ("jdk_versions", build_jdk_versions),
    ("regression", build_regression),
]


@pytest.mark.parametrize("case_name,builder", CASES)
def test_edge_case_projects(atlas_jar, tmp_path, case_name, builder):
    project = builder(tmp_path)
    doc, atlas_json, runtime, _ = run_analyze(atlas_jar, project)

    # Normalize: analyzer omits empty arrays, ensure keys always exist
    doc.setdefault("modules", [])
    doc.setdefault("entities", [])
    doc.setdefault("relationships", [])

    assert isinstance(doc["modules"], list)
    assert isinstance(doc["entities"], list)
    assert isinstance(doc["relationships"], list)

    if case_name == "empty":
        assert doc.get("modules", []) == []
        assert doc.get("entities", []) == []
        assert doc.get("relationships", []) == []
        assert doc["atlas"]["totalModules"] == 0
        assert doc["atlas"]["totalEntities"] == 0
        assert doc["atlas"]["totalRelationships"] == 0

    elif case_name == "single_class":
        assert len(doc["entities"]) == 1
        assert len(doc["relationships"]) == 0
        assert len(doc["modules"]) == 1
        assert doc["modules"][0]["classes"] == 1

    elif case_name == "circular":
        assert len(doc["entities"]) == 2
        assert len(doc["relationships"]) == 2
        metrics = run_metrics(atlas_jar, atlas_json)
        assert len(metrics["classCycles"]) == 1
        assert metrics["classCycles"][0]

    elif case_name == "nested_maven":
        assert len(doc["modules"]) == 2
        assert module_names(doc) == {"core", "api"}
        assert "parent" not in module_names(doc)
        assert len(doc["entities"]) == 2

    elif case_name == "annotations":
        expected_roles = {
            "RestEndpoint": {"REST_ENTRY"},
            "BusinessService": {"BUSINESS_LOGIC", "SPRING_BEAN"},
            "DataRepository": {"DATA_ACCESS", "SPRING_BEAN"},
            "GenericComponent": {"BUSINESS_LOGIC", "SPRING_BEAN"},
            "AppConfig": {"CONFIG", "SPRING_BEAN"},
            "RemoteClient": {"RPC_CLIENT"},
            "BootApp": {"CONFIG", "SPRING_BEAN"},
        }
        for class_name, roles in expected_roles.items():
            assert roles <= set(entity_by_class(doc, class_name)["roles"])

    elif case_name == "large":
        assert runtime < 30
        entity = entity_by_class(doc, "LargeClass")
        assert entity["methods"] >= 200

    elif case_name == "jdk_versions":
        assert doc["atlas"]["jdkVersion"] == "21"

    elif case_name == "regression":
        assert module_names(doc) == {"core", "api", "plain"}
        assert {module["type"] for module in doc["modules"]} == {"jar"}
        assert "ar" not in {module["type"] for module in doc["modules"]}


def test_mall_stress_regression(atlas_jar, tmp_path):
    mall = Path("/tmp/mall")
    if not mall.exists():
        pytest.skip("/tmp/mall is not available")

    doc, atlas_json, runtime, result = run_analyze(
        atlas_jar,
        mall,
        output=tmp_path / "mall-atlas.json",
        timeout=30,
    )

    assert doc["atlas"]["totalEntities"] == 519
    assert atlas_json.stat().st_size < 1_000_000
    assert runtime < 30
    assert "OutOfMemoryError" not in result.stderr


@pytest.mark.slow
def test_yudao_cloud_full_stress(atlas_jar, tmp_path):
    yudao = Path("/tmp/yudao-cloud")
    if not yudao.exists():
        pytest.skip("/tmp/yudao-cloud is not available")

    doc, atlas_json, _, result = run_analyze(
        atlas_jar,
        yudao,
        output=tmp_path / "yudao-cloud-atlas.json",
        timeout=180,
    )

    assert doc["atlas"]["totalEntities"] >= 4_700
    assert atlas_json.stat().st_size < 10_000_000
    assert "OutOfMemoryError" not in result.stderr
