## ADDED Requirements

### Requirement: Scan 写入 raw、metrics 和 merged JSON artifacts
系统 SHALL 将 scan artifacts 写入已配置的输出目录。

#### Scenario: Scan 成功完成
- **WHEN** 一次配置好的 scan 完成
- **THEN** 系统在 `output.dir` 下写入 `atlas-raw.json`、`atlas-metrics.json` 和 `atlas.json`

#### Scenario: 写入合并后的 Atlas JSON
- **WHEN** raw Atlas data 和 metrics data 可用
- **THEN** 系统写入 `atlas.json`，其内容为 raw Atlas document 加上由 metrics output 派生的顶层 `metrics` 对象

### Requirement: Atlas JSON 包含核心架构数据
合并后的 Atlas JSON SHALL 包含 metadata、module fingerprints、entity fingerprints、relationship records 和 metrics。

#### Scenario: Atlas metadata 存在
- **WHEN** Atlas JSON 被生成
- **THEN** 在这些值可用时，`atlas` 对象包含 schema version、generation timestamp、project name、detected JDK version、total module count、total entity count 和 total relationship count

#### Scenario: Entity 和 relationship 数组存在
- **WHEN** 从已分析 Java 源码生成 Atlas JSON
- **THEN** document 包含 `modules`、`entities` 和 `relationships` 数组，分别表示 module summaries、Java type fingerprints 和 graph edges

#### Scenario: Metrics 被合并
- **WHEN** scan 生成 metrics
- **THEN** 合并后的 document 在 `metrics` 下包含图指标，供报告和 Web UI 使用

### Requirement: 报告生成遵循配置格式
系统 SHALL 根据 `output.formats` 生成人类可读的 report artifacts。

#### Scenario: 启用 HTML 输出
- **WHEN** `output.formats` 包含 `html`
- **THEN** 系统写入 `graph.html`，它是一个外部加载 Atlas 数据的 HTML shell，而不是内联嵌入完整图数据

#### Scenario: 启用 Markdown 输出
- **WHEN** `output.formats` 包含 `md`
- **THEN** 系统使用 Atlas document 中的 module、entity、relationship、hotspot、cycle、Martin metric 和 recommendation 数据写入 `report.md`

#### Scenario: 启用 Mermaid 输出
- **WHEN** `output.formats` 包含 `mmd`
- **THEN** 系统写入 `mermaid.mmd`，其中包含从 Atlas relationships 派生的 module dependency 和 class relationship graph sections

#### Scenario: Scan 总是持久化 JSON 输出
- **WHEN** `scan` 或 server rescan 写入 reports
- **THEN** 无论 `output.formats` 中是否出现 `json`，系统都写入 `atlas.json`

### Requirement: Dump 命令输出面向 agent 的 JSON
`dump` 命令 SHALL 输出一个供下游 agent 消费的紧凑 JSON document。

#### Scenario: Dump 命令以 JSON 格式运行
- **WHEN** 执行 `atlas dump --format json`
- **THEN** 命令向 stdout 写入 JSON，且 `format` 设置为 `atlas-agent-v1`

#### Scenario: Agent dump 汇总依赖
- **WHEN** dump 命令基于 Atlas data 构建输出
- **THEN** 输出包含 project metadata、total counts、cycle 和 pain-module counts、每个 module 的 inbound/outbound dependency lists，以及 recommendations

### Requirement: Renderers 消费 Atlas 数据但不改变分析器输出
Report renderers SHALL 读取 Atlas data 并生成派生视图，不改变 analyzer output 的语义。

#### Scenario: 生成 Markdown recommendations
- **WHEN** cycles、Martin metrics 或 hotspots 存在
- **THEN** Markdown renderer 从这些 metrics 派生 recommendation text，同时保持底层 Atlas data 不变

#### Scenario: 生成 Mermaid graph data
- **WHEN** relationships 引用了带 module 的 entities
- **THEN** Mermaid renderer 从这些 relationships 派生 module dependency edges 和有限的 class relationship edges
