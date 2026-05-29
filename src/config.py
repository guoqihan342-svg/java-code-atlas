"""Configuration loading and validation for JStruct."""

from __future__ import annotations

import os
import re
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml
from yaml import YAMLError


class ConfigError(ValueError):
    """Raised when JStruct configuration is missing or invalid."""


class ConfigLoader:
    """Load jstruct.yaml and merge referenced source/model configuration."""

    CONFIG_DIR = Path("config")

    DEFAULTS: dict[str, Any] = {
        "version": 1,
        "project": {"name": "jstruct"},
        "sources": {"config_file": "config/sources.yaml"},
        "java": {"jdk_version": "", "maven_home": "", "maven_args": ""},
        "llm": {"config_file": "config/model.yaml", "enabled": True},
        "output": {
            "dir": ".jstruct/output",
            "formats": ["html", "md", "mmd", "json"],
            "human_first": True,
        },
        "serve": {
            "host": "127.0.0.1",
            "port": 8765,
            "watch": True,
            "watch_dirs": [],
            "open_browser": True,
        },
        "cache": {"dir": ".jstruct/cache", "ttl_hours": 24},
        "logging": {"level": "info", "file": ".jstruct/jstruct.log"},
    }

    @classmethod
    def load(cls, config_file: str | Path = "config/jstruct.yaml") -> dict[str, Any]:
        """Load, merge, resolve environment variables, and validate config."""

        jstruct_path = Path(config_file)
        jstruct_overrides = cls._load_yaml(jstruct_path) if jstruct_path.exists() else {}
        jstruct = cls._merge_dicts(deepcopy(cls.DEFAULTS), jstruct_overrides)

        sources_ref = jstruct.get("sources", {}).get("config_file", "config/sources.yaml")
        model_ref = jstruct.get("llm", {}).get("config_file", "config/model.yaml")

        sources = cls._load_yaml(cls._resolve_path(sources_ref))
        llm_inline = jstruct.get("llm", {})
        model = cls._load_yaml(cls._resolve_path(model_ref)) if cls._resolve_path(model_ref).exists() else {}
        model = cls._merge_dicts(model, {k: v for k, v in llm_inline.items() if k != "config_file"})

        jstruct["sources"] = sources
        jstruct["llm"] = model
        jstruct = cls._resolve_env_vars(jstruct)
        cls._validate(jstruct)
        return jstruct

    @classmethod
    def init_examples(cls, force: bool = False) -> list[Path]:
        """Create editable config files from bundled .example files."""

        cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        created: list[Path] = []
        for name in ("jstruct.yaml", "sources.yaml", "model.yaml"):
            target = cls.CONFIG_DIR / name
            source = cls.CONFIG_DIR / f"{name}.example"
            if target.exists() and not force:
                continue
            if source.exists():
                shutil.copyfile(source, target)
            else:
                target.write_text(yaml.safe_dump(cls.DEFAULTS if name == "jstruct.yaml" else {}, sort_keys=False), encoding="utf-8")
            created.append(target)
        return created

    @classmethod
    def _load_yaml(cls, path: str | Path) -> dict[str, Any]:
        """Read a YAML file and return a dictionary."""

        yaml_path = Path(path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {yaml_path}")
        try:
            with yaml_path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
        except YAMLError as exc:
            raise ConfigError(f"配置文件 YAML 解析失败: {yaml_path}") from exc
        if not isinstance(data, dict):
            raise ConfigError(f"配置文件必须是 YAML object: {yaml_path}")
        return data

    @classmethod
    def _resolve_path(cls, filename: str | Path) -> Path:
        path = Path(filename)
        if path.is_absolute():
            return path
        if path.parts and path.parts[0] == cls.CONFIG_DIR.name:
            return path
        return cls.CONFIG_DIR / path

    @classmethod
    def _resolve_env_vars(cls, config: Any) -> Any:
        """Recursively replace ${VAR_NAME} placeholders with environment values."""

        pattern = re.compile(r"\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)")

        def resolve(value: Any) -> Any:
            if isinstance(value, str):
                return pattern.sub(lambda m: os.environ.get(m.group(1) or m.group(2), m.group(0)), value)
            if isinstance(value, dict):
                return {k: resolve(v) for k, v in value.items()}
            if isinstance(value, list):
                return [resolve(v) for v in value]
            return value

        return resolve(config)

    @classmethod
    def _validate(cls, config: dict[str, Any]) -> None:
        required = ["project", "sources", "java", "output", "serve"]
        for key in required:
            if key not in config:
                raise ConfigError(f"jstruct.yaml 缺少必填项: {key}")

        sources = config["sources"]
        source_type = sources.get("type", "maven-multi-module")
        if source_type == "multi-project":
            projects = sources.get("projects")
            if not isinstance(projects, list) or not projects:
                raise ConfigError("sources.yaml multi-project 模式缺少 projects")
            for project in projects:
                if not project.get("path"):
                    raise ConfigError("sources.yaml projects 条目缺少 path")
        elif "root" not in sources:
            raise ConfigError("sources.yaml 缺少 root")

        serve = config["serve"]
        if not isinstance(serve.get("port"), int) or not (1 <= serve["port"] <= 65535):
            raise ConfigError("serve.port 必须是 1-65535 的整数")

        output = config["output"]
        if not output.get("dir"):
            raise ConfigError("output.dir 不能为空")

        llm = config.get("llm", {})
        if llm.get("enabled", True) and llm.get("endpoint") and not llm.get("model"):
            raise ConfigError("llm.model 不能为空")

    @staticmethod
    def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        merged = deepcopy(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = ConfigLoader._merge_dicts(merged[key], value)
            else:
                merged[key] = value
        return merged
