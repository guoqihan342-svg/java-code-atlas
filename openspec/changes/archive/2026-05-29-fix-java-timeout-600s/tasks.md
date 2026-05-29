## 1. 配置层：新增超时字段

- [x] 1.1 在 `config/atlas.yaml` 的 `java` 段中增加 `analyze_timeout_seconds: 600` 和 `build_timeout_seconds: 900`
- [x] 1.2 在 `src/config.py` 的 `DEFAULTS` 字典中增加 `analyze_timeout_seconds` (600) 和 `build_timeout_seconds` (900)
- [x] 1.3 在 `src/config.py` 中增加超时配置验证：拒绝负数值，0 表示无限制

## 2. 编排层：从配置读取超时值

- [x] 2.1 修改 `JavaAnalyzer._run()` 从 `self.config["java"]["analyze_timeout_seconds"]` 读取超时（0 转换为 `None`），替代硬编码的 `timeout=600`
- [x] 2.2 修改 `JavaAnalyzer._build_jar()` 从 `self.config["java"]["build_timeout_seconds"]` 读取构建超时，替代硬编码的 `timeout=900`

## 3. 超时降级：分析阶段返回部分结果

- [x] 3.1 修改 `JavaAnalyzer._run()` 中的 `subprocess.TimeoutExpired` 捕获逻辑：先检查 `output_path` 是否存在且可解析，存在则返回数据并附加 `_warning` 字段，不存在则抛 `AnalyzerError`
- [x] 3.2 修改 `JavaAnalyzer.analyze()` 方法：接收 `_warning` 字段并将其传递到返回结果中

## 4. 服务端：超时不丢弃已有数据

- [x] 4.1 修改 `server.py` `_rescan()` 的 `except` 块：捕获 `AnalyzerError`（超时场景）时不丢弃 `self.atlas_data` 已有数据，仅更新 `self.status = "error"` 和 `self.error`
- [x] 4.2 确保 WebSocket 广播超时错误消息给前端，前端可显示"分析超时，显示上次结果"提示

## 5. 配置示例文件同步

- [x] 5.1 同步更新 `config/atlas.example.yaml`，补充新增的 `analyze_timeout_seconds` 和 `build_timeout_seconds` 字段及注释
