### Requirement: 可配置的 Java 分析超时
系统 SHALL 允许用户通过 `atlas.yaml` 的 `java.analyze_timeout_seconds` 字段配置 Java 分析器子进程的执行超时（秒）。未配置时 SHALL 默认使用 600 秒。

#### Scenario: 默认超时值
- **WHEN** `atlas.yaml` 中未设置 `java.analyze_timeout_seconds`
- **THEN** 系统使用 600 秒作为 Java 分析子进程超时

#### Scenario: 自定义超时值
- **WHEN** `atlas.yaml` 中设置 `java.analyze_timeout_seconds: 1200`
- **THEN** 系统使用 1200 秒作为 Java 分析子进程超时

#### Scenario: 超时值为 0 表示无限制
- **WHEN** `atlas.yaml` 中设置 `java.analyze_timeout_seconds: 0`
- **THEN** 系统不设置超时，子进程可无限执行

### Requirement: 可配置的 Maven 构建超时
系统 SHALL 允许用户通过 `atlas.yaml` 的 `java.build_timeout_seconds` 字段配置 Maven 构建子进程的执行超时（秒）。未配置时 SHALL 默认使用 900 秒。

#### Scenario: 默认构建超时
- **WHEN** `atlas.yaml` 中未设置 `java.build_timeout_seconds`
- **THEN** 系统使用 900 秒作为 Maven 构建超时

#### Scenario: 自定义构建超时
- **WHEN** `atlas.yaml` 中设置 `java.build_timeout_seconds: 1800`
- **THEN** 系统使用 1800 秒作为 Maven 构建超时

### Requirement: 配置验证
系统 SHALL 验证超时配置字段为合法值。SHALL 拒绝负数超时值，并在启动时报告配置错误。

#### Scenario: 负数超时被拒绝
- **WHEN** `atlas.yaml` 中设置 `java.analyze_timeout_seconds: -1`
- **THEN** 系统启动时抛出 `ConfigError`，提示无效配置值
