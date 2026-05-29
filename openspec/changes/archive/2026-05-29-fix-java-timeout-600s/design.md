## Context

当前 `JavaAnalyzer._run()` 和 `_build_jar()` 中 `subprocess.run(timeout=...)` 是硬编码常量（600s / 900s）。对于超过 5000 个类的代码库，JavaParser 全量 AST 解析 + JGraphT 图分析可能在 10 分钟内无法完成，尤其是首次运行需要下载 Maven 依赖。

超时后当前行为是直接抛出 `AnalyzerError`，已有的 `atlas-raw.json` 不会被检查，服务端 `_rescan()` 中也不会保留上次成功数据。

## Goals / Non-Goals

**Goals:**
- 将超时值从硬编码改为 `atlas.yaml` 可配置项，向后兼容（默认值不变）
- 分析超时时优先返回部分结果，而非仅报错
- 服务端超时后保留已有数据，不破坏 Web UI 体验

**Non-Goals:**
- 不在 Java 端做子进程内的时间分片检查（改动范围太大）
- 不引入重试机制（超出本次 scope）
- 不做分析进度推送到 WebSocket（Java 端改动大，留到后续 change）

## Decisions

### 1. 配置字段设计

将超时值放在 `java` 段而非新建 `timeout` 段：

```yaml
java:
  analyze_timeout_seconds: 600   # 新增，默认 600
  build_timeout_seconds: 900     # 新增，默认 900
```

**理由**: 超时与 Java 执行环境强相关，和 `jdk_version` / `maven_home` 同属一个配置域。放在 `java` 段下语义更清晰。

**替代方案**: 放在顶层 `timeout:` 段 — 被否决，因为项目中配置结构已按领域划分（`java`、`llm`、`serve`、`output`），不应破坏既有组织方式。

### 2. 超时值 0 表示无限制

当 `analyze_timeout_seconds: 0` 时，`subprocess.run(timeout=None)`，子进程无时间限制。

**理由**: 对大型代码库的分析有时需要完全无限制运行，`0` 是 Unix 风格的常见约定。

**替代方案**: 使用特殊字符串 `"none"` — 被否决，字段类型不统一会带来额外的类型转换和文档成本。

### 3. 部分结果降级策略

`_run()` 中超时后不直接抛异常，而是：
1. 检查 `output_path` 是否存在且可解析为 JSON
2. 存在则返回数据 + 附加 `_warning` 字段
3. 不存在则抛 `AnalyzerError`

`analyze()` 和 `scan()` 中不修改超时捕获逻辑 — 它们无需知道自己拿到的是部分结果。部分结果的 `_warning` 字段在 `metrics()` 中会被保留，最终出现在 `atlas.json` 中。

**理由**: 最小侵入。Java 端 `analyze` 子命令写入 `atlas-raw.json` 是逐 entity 追加的（JSON数组），即使在未完成状态下被终止，文件也可能是合法的截断 JSON 数组。Python 端用 `json.load()` 解析时可能失败，此时同样 fallback 到抛异常。

**风险**: 截断的 JSON 可能无法解析。缓解：`json.load()` 失败 → 抛 `AnalyzerError`，行为等同于"无输出文件"。

### 4. 服务端降级策略

`server.py` `_rescan()` 中修改 `except` 块：将 `if self.atlas_data is None: raise` 改为始终保留旧数据并更新 `self.error`。

```python
except subprocess.TimeoutExpired:
    if self.atlas_data is None:
        raise
    self.error = "分析超时，显示上次扫描结果"
```

**理由**: 在 watch 模式下，用户改一个文件触发重扫，如果重扫超时就把整个 UI 弄崩了体验很差。保留旧数据让用户至少还能看到上次结果。

## Risks / Trade-offs

- **[分析超时返回截断 JSON]** → 缓解：`json.load()` 解析失败时 fallback 到抛异常；截断 JSON 被成功解析为部分数组时，metrics 阶段会跳过缺失 entity，最终 `atlas.json` 中的实体数可能少于实际
- **[用户不知道超时正在发生]** → 缓解：状态 API `/api/status` 返回 `scanning` 状态 + WebSocket 广播 `scanning` 消息，用户可通过界面判断是否仍在分析
- **[配置向后兼容]** → 缓解：默认值完全保持不变（600/900），已有 `atlas.yaml` 无需修改

## Open Questions

<!-- 无待解决的问题 -->
