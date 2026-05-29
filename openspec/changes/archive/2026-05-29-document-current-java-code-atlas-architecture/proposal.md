## Why

项目已经形成了 Python + Java 混合架构，但当前事实来源分散在 README、DESIGN 文档和具体实现里。这个变更把 Java Code Atlas 的当前架构记录到 OpenSpec 中，作为后续重构和功能演进的稳定基线。

## What Changes

- 为现有 Java 静态分析管线补充 OpenSpec 文档。
- 为现有 Atlas JSON 和报告输出契约补充 OpenSpec 文档。
- 为现有本地可视化服务和 watch 工作流补充 OpenSpec 文档。
- 本 proposal 不改变运行时行为、CLI 命令、API 路由或数据格式。
- 不删除现有文档；`DESIGN.md` 和 README 继续作为历史/背景资料保留。

## Capabilities

### New Capabilities
- `static-analysis-pipeline`: 描述 Python 编排层如何构建/调用 Java 分析器，以及 Java 分析器如何提取实体、关系、模块和指标。
- `atlas-output-contract`: 描述生成的 Atlas JSON 文件，以及面向人阅读的 HTML、Markdown、Mermaid 输出。
- `local-visualization-server`: 描述 `atlas serve`、HTTP 路由、WebSocket 行为、reload 行为和文件监听预期。

### Modified Capabilities
- 无。当前 `openspec/specs/` 下还没有既有 OpenSpec capability。

## Impact

- 在 `openspec/changes/document-current-java-code-atlas-architecture/` 下新增 OpenSpec artifacts。
- 为后续变更建立基线规格，例如 schema 规范化、LLM 管线接入、增量 watch 模式、CLI 冒烟测试。
- 不影响 Python 运行时代码、Java 分析器代码、生成报告、Web 路由、配置文件或测试。
