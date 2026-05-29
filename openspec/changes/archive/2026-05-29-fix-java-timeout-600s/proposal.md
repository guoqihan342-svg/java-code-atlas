## Why

Java 分析器的执行超时（`subprocess.run(timeout=600)`）和 Maven 构建超时（`timeout=900`）目前是硬编码常量。对于小型项目这没有问题，但在分析 5000+ 类的大型 Spring 代码库时，600 秒可能不够，导致分析被无条件中断，且没有任何中间输出可复用。同时超时缺乏进度反馈，用户无法判断是正常在进行还是已经卡死。

## What Changes

- 将 `timeout=600` 和 `timeout=900` 从硬编码改为 `atlas.yaml` 配置项，默认值保持不变
- 新增 `java.analyze_timeout_seconds`（默认 600）和 `java.build_timeout_seconds`（默认 900）配置字段
- 超时后不再只抛 `AnalyzerError`，优先检查输出文件是否存在并返回部分结果
- `_rescan()` 中捕获超时异常时不丢弃已有数据，保持上次成功扫描的结果可用
- 分析过程中通过 stderr 输出进度日志（"已处理 X/Y 个文件..."），服务端转发到 WebSocket 状态消息

## Capabilities

### New Capabilities
- `java-timeout-config`: 通过 `atlas.yaml` 的 `java.analyze_timeout_seconds` 和 `java.build_timeout_seconds` 配置 Java 子进程超时时长
- `graceful-timeout`: 超时时返回已生成的部分分析结果，而非仅抛出错误

### Modified Capabilities
<!-- 无现有 spec 需要修改 -->

## Impact

- `src/orchestrator.py`: 修改 `_run()` 和 `_build_jar()` 的超时逻辑，从 config 读取超时值
- `src/config.py`: 在 DEFAULTS 字典中增加 `analyze_timeout_seconds` 和 `build_timeout_seconds`
- `src/web/server.py`: `_rescan()` 中超时异常时保留已有 `self.atlas_data`，不丢弃上次成功扫描
- `config/atlas.yaml`: 在 `java` 段新增两个可选配置字段
- Java 端（`AnalyzerCli.java` 等）无需修改 — 超时控制完全由 Python 端负责
