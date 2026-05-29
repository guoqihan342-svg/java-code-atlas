## ADDED Requirements

### Requirement: Python 编排器调用 Java 分析器扫描序列
系统 SHALL 按配置执行扫描：在需要时构建 Java 分析器 JAR，调用 Java `analyze` 子命令生成原始 Atlas 数据，再基于原始数据调用 Java `metrics` 子命令，并把返回的指标合并进内存中的 Atlas document。

#### Scenario: 完整扫描生成合并后的 Atlas 数据
- **WHEN** 使用有效配置且 Java/Maven 运行时可用时调用 `JavaAnalyzer.scan()`
- **THEN** 系统先执行 analyze 再执行 metrics，写入 raw 和 metrics JSON 文件，并返回包含顶层 `metrics` 对象的 Atlas document

#### Scenario: 分析器输出版本不兼容
- **WHEN** Java 分析器返回的 JSON 中 `atlas.version` 与当前 Python schema 版本不一致
- **THEN** 系统 MUST 校验失败，而不是静默消费不兼容 document

### Requirement: 分析器 root 选择遵循 source 配置
系统 SHALL 根据加载后的 `sources` 配置推导 Java 分析器 root。

#### Scenario: Maven 多模块 source 配置
- **WHEN** `sources.type` 为 `maven-multi-module`
- **THEN** 系统把配置的 `sources.root` 传给 Java 分析器，并把已配置的模块过滤项作为 analyzer module 参数传入

#### Scenario: 多项目 source 配置
- **WHEN** `sources.type` 为 `multi-project`
- **THEN** 系统使用每个已配置 project path 作为 root 调用 Java 分析器

### Requirement: Java 分析器发现 Maven 模块
Java 分析器 SHALL 在提取 fingerprints 和 relationships 之前，从配置 root 中解析可分析的 Maven 模块。

#### Scenario: 未提供显式模块过滤
- **WHEN** analyze 命令收到 root 且没有显式 modules
- **THEN** 分析器从 root 中解析 Maven modules，并排除不含源码的 aggregator modules

#### Scenario: 提供显式模块过滤
- **WHEN** analyze 命令收到一个或多个 module name 或 module path
- **THEN** 分析器只分析匹配的已发现模块，或匹配且包含 `src/main/java` 的手动模块路径

### Requirement: 从 Java 源码提取实体 fingerprints
Java 分析器 SHALL 解析生产 Java 源文件，并为顶层 Java 类型输出 entity fingerprints。

#### Scenario: Java 类型成功解析
- **WHEN** 模块 `src/main/java` 下的源文件包含顶层 class、interface、enum、annotation、abstract class 或 record
- **THEN** 分析器输出 entity fingerprint，包含全限定名、类名、Java package、module、module path、kind、modifiers、roles、继承列表、方法计数、注入标记、规模指标和复杂度指标

#### Scenario: Java 类型带有 Spring 或框架注解
- **WHEN** 已解析的类型或方法包含可识别注解，例如 Spring stereotype、transactional annotation、bean annotation 或 listener annotation
- **THEN** 分析器在 entity fingerprint 中记录对应架构角色或事件监听元数据

#### Scenario: Java 源码无法解析
- **WHEN** 某个源文件在 fingerprint 提取过程中 JavaParser 解析失败
- **THEN** 分析器跳过该文件，并继续处理剩余文件

### Requirement: 在已知实体之间提取 relationships
Java 分析器 SHALL 只在 source 和 target 都能解析为已知已分析实体时提取 relationship。

#### Scenario: 类型引用成功解析
- **WHEN** 一个已知实体 extends、implements、injects、configures、instantiates 或 invokes 另一个已知实体
- **THEN** 分析器输出 relationship，包含 source FQN、target FQN、relationship type、weight、source module 和 target module

#### Scenario: 发现重复 relationships
- **WHEN** 多个 relationships 具有相同 source、target 和 type
- **THEN** 分析器通过累加 weight 将它们聚合为一个 relationship

#### Scenario: 发现非语义自关系
- **WHEN** 一个 relationship 的 source 和 target 是同一实体，且 type 不是支持的 self-relationship 类型
- **THEN** 分析器 MUST 在聚合输出中忽略该 relationship

### Requirement: 从 Atlas 数据计算图指标
Java 分析器 SHALL 从提取出的 Atlas document 计算 class 级和 module 级图指标。

#### Scenario: Metrics 命令处理原始 Atlas 数据
- **WHEN** `metrics` 子命令收到原始 Atlas JSON document
- **THEN** 它计算图衍生指标，例如 cycles、Martin metrics、hotspots 和 boundary scores，供下游报告和可视化使用

#### Scenario: 构建模块依赖图
- **WHEN** relationships 跨越 module 边界
- **THEN** 分析器在有向加权 module graph 中表示这些依赖，并从该图中排除同模块 relationships
