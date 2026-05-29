from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def sample_atlas_data() -> dict:
    return {
        "atlas": {
            "version": "1.0.0",
            "generated_at": "2026-05-29T00:00:00+00:00",
            "project": "sample-project",
            "totalModules": 2,
            "totalEntities": 3,
            "totalRelationships": 2,
        },
        "modules": [{"name": "app"}, {"name": "core"}],
        "entities": [
            {"fqn": "com.example.app.UserController", "className": "UserController", "module": "app", "roles": ["REST_ENTRY"]},
            {"fqn": "com.example.core.UserService", "className": "UserService", "module": "core", "roles": ["BUSINESS_LOGIC"]},
            {"fqn": "com.example.core.UserRepository", "className": "UserRepository", "module": "core", "roles": ["DATA_ACCESS"]},
        ],
        "relationships": [
            {"source": "com.example.app.UserController", "target": "com.example.core.UserService", "type": "CALLS", "weight": 2},
            {"source": "com.example.core.UserService", "target": "com.example.core.UserRepository", "type": "CALLS", "weight": 1},
        ],
        "metrics": {
            "hotspots": [{"fqn": "com.example.core.UserService", "score": 42}],
            "cycles": [],
            "martin": [{"module": "core", "ca": 1, "ce": 1, "instability": 0.5, "abstractness": 0.25, "distance": 0.25, "zone": "good"}],
        },
    }


@pytest.fixture
def atlas_file(tmp_path: Path, sample_atlas_data: dict) -> Path:
    path = tmp_path / "atlas-raw.json"
    path.write_text(json.dumps(sample_atlas_data), encoding="utf-8")
    return path


@pytest.fixture
def valid_pom_content() -> str:
    return """<project>
  <modelVersion>4.0.0</modelVersion>
  <properties>
    <java.version>17</java.version>
    <maven.compiler.release>17</maven.compiler.release>
  </properties>
</project>
"""


@pytest.fixture
def sample_config(tmp_path: Path) -> dict:
    return {
        "version": 1,
        "project": {"name": "sample-project"},
        "sources": {
            "version": 1,
            "type": "maven-multi-module",
            "root": str(tmp_path / "java-project"),
            "modules": ["app", "core"],
            "exclude": ["**/target/**"],
        },
        "java": {"jdk_version": "17", "maven_home": "", "maven_args": ""},
        "llm": {"enabled": False},
        "output": {"dir": str(tmp_path / "out"), "formats": ["html", "md", "mmd", "json"], "human_first": True},
        "serve": {"host": "127.0.0.1", "port": 8765, "watch": False, "watch_dirs": [], "open_browser": False},
    }


@pytest.fixture
def config_files(tmp_path: Path) -> Path:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "atlas.yaml").write_text(
        """version: 1
project:
  name: fixture-project
sources:
  config_file: config/sources.yaml
java:
  jdk_version: "17"
llm:
  config_file: config/model.yaml
  enabled: true
output:
  dir: .atlas/output
serve:
  host: 127.0.0.1
  port: 8765
""",
        encoding="utf-8",
    )
    (config_dir / "sources.yaml").write_text(
        """version: 1
type: maven-multi-module
root: /tmp/project
modules: [app, core]
exclude:
  - "**/target/**"
""",
        encoding="utf-8",
    )
    (config_dir / "model.yaml").write_text(
        """version: 1
backend: openai_compatible
endpoint: https://example.test/v1/chat/completions
api_key: test-key
model: test-model
headers:
  X-Test: yes
""",
        encoding="utf-8",
    )
    return config_dir
