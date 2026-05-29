## Context

Java Code Atlas 是一个已有代码库，由两个运行时协作完成核心功能：

- Python 负责面向用户的 CLI、配置加载、Java 分析器编排、报告渲染和本地 Web 服务。
- Java 负责静态分析可执行入口、Maven 模块发现、基于 JavaParser 的指纹提取、关系提取和图指标计算。

仓库里已经有高层设计文档，但其中混合了当前已实现行为和计划中的目标行为。这个变更创建 OpenSpec artifacts，用来描述当前已经实现的架构，方便后续变更明确区分“现状基线”和“计划改进”。

主要实现参考：

- `src/cli.py`：`serve`、`scan`、`dump` 和 config 命令。
- `src/config.py`：配置加载、环境变量展开和校验。
- `src/orchestrator.py`：Java 分析器构建/调用和 scan 数据合成。
- `src/web/server.py`、`src/web/watcher.py`、`src/web/websocket.py`：本地服务、reload 和 WebSocket 行为。
- `src/render/*` 和 `templates/*`：报告输出。
- `java-analyzer/src/main/java/io/github/javacodeatlas/*`：Java 静态分析和指标计算。

## Goals / Non-Goals

**Goals:**

- 把当前已实现架构沉淀为可审查的 OpenSpec requirements。
- 将当前行为和未来规划项分开。
- 提供稳定的 capability 名称，供后续变更修改。
- 记录 CLI、配置、分析器、输出文件、Web 路由和 reload 行为之间的系统边界。
- 保持这个 change 为纯文档变更。

**Non-Goals:**

- 不修改 Python 或 Java 源码。
- 不改变生成的 JSON schema、API 路由名称、CLI 行为、报告模板或 watch 行为。
- 不在本 change 中新增测试覆盖。
- 不处理现有 README/DESIGN 输出中的编码显示问题。
- 不把 LLM pipeline 接入 `JavaAnalyzer.scan()`。
- 不实现真正的 watch 增量图更新。

## Decisions

### 将运行时行为拆成三个 capability 记录

基线拆分为 `static-analysis-pipeline`、`atlas-output-contract` 和 `local-visualization-server`。

原因：这三个 capability 对应项目的主要运行边界：生成图数据、持久化/渲染图数据、交互式服务图数据。更小的 spec 能让后续 delta 更容易审查。

考虑过的替代方案：只创建一个 `java-code-atlas-architecture` spec。这样初始更简单，但后续不相关的改造都会修改同一个大型 capability。

### 所有基线 spec 都使用 ADDED requirements

当前 `openspec/specs/` 下没有已提交的既有 OpenSpec specs，因此每个基线 capability 都是新增能力。

原因：OpenSpec archive 可以把这些新增能力合并为长期规格，不需要 MODIFIED delta。

考虑过的替代方案：在 `specs/` 之外创建普通文档。那样后续变更就没有稳定的 OpenSpec 契约可修改。

### 明确记录当前 full-reload watch 行为

设计文档提到增量更新，但当前服务端实现是在文件变化后通过 `JavaAnalyzer.scan()` 重新扫描，并广播 `full-reload` 事件。

原因：spec 必须描述已经实现的行为，而不是愿景行为。后续可以用 `improve-watch-mode-incremental-rescan` 之类的 change 修改这个 requirement。

考虑过的替代方案：按计划中的增量模型写 spec。那会制造错误基线，让验证结果失真。

### 将 LLM 集成排除在基线之外

仓库包含 `src/llm/`，但主 scan 路径没有调用 `LlmPipeline`。

原因：如果把它记录成当前激活管线的一部分，会夸大现有行为。后续 change 可以单独新增或正式化 LLM 模式识别。

考虑过的替代方案：把 LLM 写成可选激活行为。但这不符合当前 `JavaAnalyzer.scan()` 路径。

## Risks / Trade-offs

- 风险：如果未来代码变更绕过 OpenSpec，文档可能再次滞后。缓解：要求后续架构变更通过 OpenSpec delta 修改归档后的 specs。
- 风险：部分现有文档描述的是尚未实现的目标特性。缓解：基线 specs 优先记录从代码观察到的行为，并把未来改进标为 out of scope。
- 风险：spec 可能遗漏 JavaParser 提取或 Maven 解析的边界情况。缓解：requirements 保持在行为契约层面，算法细化留给后续定向 change。
- 风险：本 change 不新增测试。缓解：tasks 包含 artifacts 和 OpenSpec status 的人工验证；后续实现型变更应补自动化测试。

## Migration Plan

这是纯文档变更。不需要部署、数据迁移、回滚策略或运行时兼容处理。

如果需要回退，在 archive 之前删除 `openspec/changes/document-current-java-code-atlas-architecture/`；如果已经 archive，则回退归档后的 spec 变更。

## Open Questions

- 后续归档 specs 是否应该包含直接源码文件引用，还是保持纯行为描述？
- specs 归档后，是否应该把 `DESIGN.md` 标记为历史设计文档？
- 下一个 change 是否应该优先规范化 Atlas metadata 命名？
