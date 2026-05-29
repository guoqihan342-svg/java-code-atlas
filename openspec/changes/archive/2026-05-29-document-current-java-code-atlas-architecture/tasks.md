## 1. 基线审查

- [x] 1.1 对照 `static-analysis-pipeline` 和 `atlas-output-contract` specs，审查 `src/cli.py`、`src/config.py` 和 `src/orchestrator.py`
- [x] 1.2 对照实体提取、关系提取和指标计算 requirements，审查 `java-analyzer/src/main/java/io/github/javacodeatlas/`
- [x] 1.3 对照 `local-visualization-server` spec，审查 `src/web/server.py`、`src/web/watcher.py` 和 `src/web/websocket.py`
- [x] 1.4 对照报告生成 requirements，审查 `src/render/` 和 `templates/`

## 2. Spec 一致性

- [x] 2.1 确认 proposal 中的 capability 名称与 spec 文件夹名称完全一致
- [x] 2.2 确认每个 spec requirement 至少包含一个带 WHEN/THEN 断言的 `#### Scenario`
- [x] 2.3 确认 specs 只记录当前已实现行为，不包含 LLM scan 集成或真正增量 watch 更新等未来行为
- [x] 2.4 确认 design 明确把运行时代码修改列为 non-goals

## 3. 验证

- [x] 3.1 运行 `openspec status --change "document-current-java-code-atlas-architecture"`，确认所有 artifacts 完成
- [x] 3.2 检查 `git status --short`，确认本 change 只包含 OpenSpec proposal artifacts
- [x] 3.3 记录后续 change 候选项：schema 规范化、LLM scan 集成、增量 watch 行为、CLI 冒烟测试
