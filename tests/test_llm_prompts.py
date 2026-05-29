from __future__ import annotations

import json

from src.llm.prompts import ARCHITECTURE_PROMPT, DESIGN_PATTERN_PROMPT


def test_module_description_prompt_template():
    rendered = ARCHITECTURE_PROMPT.format(modules=json.dumps([{"module": "app"}]))

    assert "Java 代码结构分析器" in rendered
    assert '"module": "app"' in rendered
    assert '"style": "layered"' in rendered


def test_architecture_pattern_identification_template():
    rendered = DESIGN_PATTERN_PROMPT.format(classes=json.dumps([{"fqn": "com.example.Foo"}]))

    assert "设计模式识别器" in rendered
    assert "Singleton" in rendered
    assert '"patterns": ["Singleton"]' in rendered


def test_prompt_output_format_specs_are_json_serializable():
    architecture_spec = {"results": [{"module": "...", "style": "layered", "confidence": 0.9}]}
    pattern_spec = {"results": [{"fqn": "...", "patterns": ["Singleton"], "confidence": 0.9}]}

    assert json.loads(json.dumps(architecture_spec)) == architecture_spec
    assert json.loads(json.dumps(pattern_spec)) == pattern_spec
