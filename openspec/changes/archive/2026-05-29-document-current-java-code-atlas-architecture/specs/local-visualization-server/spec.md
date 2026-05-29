## ADDED Requirements

### Requirement: Serve 命令从加载后的配置启动
`serve` 命令 SHALL 加载项目配置，应用 CLI overrides，执行初始 scan，并启动本地 HTTP server。

#### Scenario: 提供 host 和 port overrides
- **WHEN** 执行带 `--host` 或 `--port` 的 `atlas serve`
- **THEN** server 使用提供的 host 或 port，而不是配置中的值

#### Scenario: 禁用浏览器自动打开
- **WHEN** 执行 `atlas serve --no-browser`
- **THEN** server 启动时不会自动打开浏览器窗口

#### Scenario: 禁用 watch 模式
- **WHEN** 执行 `atlas serve --no-watch`
- **THEN** server 启动时不会创建 file watcher

### Requirement: Server 暴露 Atlas Web routes
本地 server SHALL 暴露用于交互页面、Atlas data、scan status、manual reload 和 WebSocket communication 的 routes。

#### Scenario: 用户打开 root route
- **WHEN** client 请求 `GET /`
- **THEN** server 返回渲染后的交互式 HTML shell

#### Scenario: Client 请求 Atlas data
- **WHEN** 成功 scan 后 client 请求 `GET /api/atlas` 或 `GET /api/atlas.json`
- **THEN** server 以 JSON 返回当前内存中的 Atlas document

#### Scenario: Atlas data 不可用
- **WHEN** 任何 Atlas document 存在之前 client 请求 Atlas data
- **THEN** server 返回 not-found response，而不是空的成功 document

#### Scenario: Client 请求 scan status
- **WHEN** client 请求 `GET /api/status`
- **THEN** server 返回 JSON，其中包含当前 scan status 和当前 error message

#### Scenario: Client 请求 manual reload
- **WHEN** client 发送 `POST /api/reload`
- **THEN** server 调度一次 rescan，并立即返回表示 scanning status 的 JSON

### Requirement: WebSocket clients 接收 reload 状态
本地 server SHALL 维护已连接 WebSocket clients，并广播 scan lifecycle messages。

#### Scenario: WebSocket client 连接
- **WHEN** client 连接 `GET /ws`
- **THEN** server 注册该 client，用于后续 JSON broadcasts

#### Scenario: WebSocket client 发送 reload 命令
- **WHEN** 已连接 WebSocket client 发送文本消息 `reload`
- **THEN** server 调度一次启用 broadcast 的 rescan

#### Scenario: 启用 broadcast 的 rescan 成功
- **WHEN** 一次 broadcast rescan 成功完成
- **THEN** server 广播 JSON message，其中 type 为 `full-reload`，并包含 Atlas metadata

#### Scenario: 启用 broadcast 的 rescan 失败
- **WHEN** 一次 broadcast rescan 抛出异常
- **THEN** server 广播 JSON message，其中 type 为 `error`，并包含 error message

### Requirement: Watch 模式响应 Java 源码变化
file watcher SHALL 监听已配置 source roots，并在 Java source 创建或修改时通知 server。

#### Scenario: 显式配置 watch roots
- **WHEN** `serve.watch_dirs` 包含 paths
- **THEN** watcher 递归监听这些 paths

#### Scenario: 从 multi-project sources 推导 watch roots
- **WHEN** 没有显式 watch dirs 且 `sources.type` 为 `multi-project`
- **THEN** watcher 递归监听每个已配置 project path

#### Scenario: 从 Maven multi-module sources 推导 watch root
- **WHEN** 没有显式 watch dirs 且 `sources.type` 为 `maven-multi-module`
- **THEN** watcher 递归监听已配置 source root

#### Scenario: Java 文件变化
- **WHEN** `.java` 文件被创建或修改，且该 path 的 debounce window 已经过期
- **THEN** watcher 使用 changed path 调用 server change callback

#### Scenario: 非 Java 文件变化
- **WHEN** changed file path 不以 `.java` 结尾
- **THEN** watcher 忽略该事件

### Requirement: Watch 触发的 scans 使用 full reload 基线行为
server SHALL 通过运行现有 full scan path 并广播 full reload 来处理 watch-triggered changes。

#### Scenario: 被监听 Java 文件变化
- **WHEN** server 从 watcher 收到 file-change callback
- **THEN** 它广播 scanning status，运行 `JavaAnalyzer.scan()`，更新内存中的 Atlas data，重写已配置 reports，并广播 `full-reload`

#### Scenario: 多个 rescans 重叠
- **WHEN** 一个 rescan 活跃期间收到多个 reload triggers
- **THEN** server 通过 scan lock 串行化 rescans，确保同一时间只有一个 scan 运行
