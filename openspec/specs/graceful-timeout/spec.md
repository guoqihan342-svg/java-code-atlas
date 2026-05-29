### Requirement: 分析超时时返回部分结果
当 Java 分析阶段超时时，系统 SHALL 检查输出文件（`atlas-raw.json`）是否已存在。若存在，SHALL 将其作为部分结果返回，同时在返回数据中附加 `warning` 字段说明分析未完成。

#### Scenario: 超时但输出文件已生成
- **WHEN** analyze 子进程因超时被终止
- **AND** 输出文件 `atlas-raw.json` 已存在且可解析
- **THEN** 系统返回该文件中的分析数据，并附加 `warning: "分析超时，仅返回部分结果"`

#### Scenario: 超时且无输出文件
- **WHEN** analyze 子进程因超时被终止
- **AND** 输出文件不存在
- **THEN** 系统抛出 `AnalyzerError("分析超时且未生成任何输出")`

### Requirement: 超时不影响已加载数据
Web 服务端在重扫超时时，SHALL 保留之前成功扫描的数据，不将 `self.atlas_data` 置为 `None`。

#### Scenario: 重扫超时保留旧数据
- **WHEN** `_rescan()` 因 Java 分析超时而失败
- **AND** `self.atlas_data` 已有上次成功扫描的数据
- **THEN** Web 服务继续返回旧数据，状态为 `error`，错误信息指示超时

#### Scenario: 首次扫描超时
- **WHEN** `_rescan()` 因 Java 分析超时而失败
- **AND** `self.atlas_data` 为空（首次启动）
- **THEN** Web 服务状态为 `error`，触发 500 异常

### Requirement: 构建超时不自动重试
Maven 构建超时 SHALL 仍抛出 `AnalyzerError`，不做部分结果返回。构建超时表示环境问题（依赖下载慢、Maven 版本不兼容等），不适合自动降级。

#### Scenario: 构建超时报错
- **WHEN** `_build_jar()` 中 Maven 构建因超时被终止
- **THEN** 系统抛出 `AnalyzerError`，错误信息明确指示构建超时
