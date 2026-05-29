# Java Code Atlas — 设计文档 v0.2

> 多仓 Java Spring 代码结构图谱 · 人读优先 · Agent 兼容
>
> ![架构](https://img.shields.io/badge/arch-v0.2-blue)
> ![阶段](https://img.shields.io/badge/stage-design-red)

---

## 0. 核心决策

| 决策 | 选择 | 理由 |
|------|------|------|
| **人读 vs Agent 读** | Phase 1-4 先做人读（HTML报告）| 用户原话：「先输出给人看的，后续再弄输出给 agent 看」 |
| **配置位置** | 全部放 `config/` 目录 | 用户要求「可配置的文件尽量放到一个文件夹下面」 |
| **多代码目录** | 默认 Maven 多模块，支持独立多项目 | 最常见 Spring 项目形态 |
| **输出方式** | `atlas serve` — 本地 Web + 浏览器 | 持续迭代场景的最优体验 |
| **Watch 模式** | 内置文件监听 + WebSocket 推送 | 改代码立即可见图谱变化 |
| **语言** | Java(解析) + Python(编排) | 不引入 Rust——瓶颈在 I/O 不在 CPU |
| **Java 解析器** | JavaParser (JVM) | 注解/泛型/类型推断比 tree-sitter 强太多 |

---

## 1. 项目结构

```
java-code-atlas/
├── config/                         # 所有可配置文件（一个文件夹）
│   ├── atlas.yaml                  # 主配置
│   ├── model.yaml                  # LLM 模型配置
│   └── sources.yaml                # 代码源目录配置
│
├── java-analyzer/                  # Java 分析器（Maven 项目）
│   ├── pom.xml
│   └── src/main/java/io/github/javacodeatlas/
│       ├── AnalyzerCli.java        # CLI 入口（analyze / metrics 两个子命令）
│       ├── extract/
│       │   ├── FingerprintExtractor.java
│       │   ├── RelationshipExtractor.java
│       │   └── AnnotationRoleMapper.java
│       ├── metrics/
│       │   ├── GraphBuilder.java
│       │   ├── TarjanScc.java
│       │   ├── MartinMetrics.java
│       │   ├── HotspotScorer.java
│       │   └── BoundaryScorer.java
│       ├── model/
│       │   ├── AtlasDocument.java       # 顶层 JSON schema（含版本号）
│       │   ├── EntityFingerprint.java
│       │   ├── Relationship.java
│       │   └── ModuleFingerprint.java
│       └── util/
│           ├── MavenModuleResolver.java  # NEW: 多模块识别
│           └── JdkVersionDetector.java   # NEW: JDK 版本检测
│
├── atlas.py                        # Python CLI 入口
├── src/                            # Python 编排逻辑
│   ├── __init__.py
│   ├── cli.py                      # click 命令组
│   ├── config.py                   # 配置加载/验证
│   ├── orchestrator.py             # 扫描编排
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── backend.py              # LLM 后端抽象（支持任意 OpenAI 兼容 API）
│   │   ├── pipeline.py             # 批量推理管线
│   │   └── prompts.py              # Prompt 模板
│   ├── web/
│   │   ├── __init__.py
│   │   ├── server.py               # aiohttp Web 服务器
│   │   ├── watcher.py              # watchdog 文件监听
│   │   └── websocket.py            # WebSocket 推送
│   └── render/
│       ├── __init__.py
│       ├── html.py                 # HTML 渲染器（Cytoscape.js）
│       ├── mermaid.py              # Mermaid 生成器
│       └── markdown.py             # Markdown 报告
│
├── templates/                      # Jinja2 模板
│   ├── graph.html.j2               # 交互式图谱 HTML（数据外部加载）
│   ├── report.md.j2                # Markdown 报告模板
│   └── mermaid.mmd.j2              # Mermaid 模板
│
├── tests/
│   ├── test_java/                  # Java 单元测试
│   └── test_python/                # Python 单元测试
│
├── requirements.txt
├── DESIGN.md                       # 本文件
├── IMPLEMENTATION_PLAN.md          # 实施方案
└── README.md
```

**为什么有些配置不在 config/ 里（特殊说明）：**
- `requirements.txt` → Python 项目标准，放根目录（pip 约定）
- `pom.xml` → Maven 项目标准，放 `java-analyzer/` 下（Maven 约定）
- `.gitignore` → Git 标准，放根目录（Git 约定）
- `templates/` → 不是配置，是模板文件，放独立目录

---

## 2. 配置系统

### 2.1 `config/atlas.yaml` — 主配置

```yaml
# Java Code Atlas 主配置 v1
version: 1

project:
  name: "my-project"                  # 项目名（用于报告标题）

sources:
  config_file: "config/sources.yaml"  # 源码目录配置（可内联可引用外部文件）

java:
  # JDK 版本：可显式指定、或留空自动检测
  jdk_version: ""                     # "8" | "11" | "17" | "21" | ""=自动
  maven_home: ""                      # Maven 安装路径，""=从 PATH 找
  maven_args: ""                      # 额外 Maven 参数，如 "-s /path/to/settings.xml"

llm:
  config_file: "config/model.yaml"    # 模型配置（可内联可引用外部文件）
  enabled: true                       # false=跳过 L4 模式识别层

output:
  dir: ".atlas/output"                # 输出目录
  formats: ["html", "md", "mmd", "json"]
  human_first: true                   # true=优先生成人读格式

serve:
  host: "127.0.0.1"
  port: 8765
  watch: true                         # 启动文件监听
  watch_dirs: []                      # 额外监听目录，空=监听 sources 里的所有目录
  open_browser: true                  # 自动打开浏览器

cache:
  dir: ".atlas/cache"
  ttl_hours: 24                       # 缓存有效期

logging:
  level: "info"                       # debug/info/warn/error
  file: ".atlas/atlas.log"
```

### 2.2 `config/sources.yaml` — 代码源目录

```yaml
# 源码目录配置 v1
version: 1

# 模式1：Maven 多模块（推荐）
type: maven-multi-module
root: "/home/user/workspace/my-spring-project"
modules: []                           # 空=自动扫描 pom.xml <modules>
# modules: ["service-a", "service-b"] # 或显式列出

# 模式2：独立多项目
# type: multi-project
# projects:
#   - path: "/home/user/project-a"
#     role: business-service          # 仓库角色（可选）
#   - path: "/home/user/project-b"
#     role: common-lib

# 忽略目录（支持 glob）
exclude:
  - "**/target/**"
  - "**/node_modules/**"
  - "**/.git/**"
  - "**/test/**"                      # 正式分析时可排除测试
```

**Maven 多模块自动发现逻辑**：

```
1. 读 root/pom.xml → 找 <modules> 标签
2. 对每个 module，找 module/pom.xml → 找 <packaging>
3. 过滤掉 type=pom 的聚合模块（不包含 Java 源码）
4. 对每个有效模块，扫描 src/main/java/**/*.java
5. 汇总所有模块的 class → 统一图谱
```

### 2.3 `config/model.yaml` — LLM 模型配置

```yaml
# LLM 模型配置 v1
version: 1

# 后端类型：openai_compatible | deepseek | openai
backend: "deepseek"

# 通用配置（所有后端共用）
model: "deepseek-chat"
temperature: 0.0                     # 结构性任务用 0
max_tokens: 4096
max_concurrency: 2                   # 并发请求数
batch_size: 50                       # 每批处理的类数量
retry: 3                             # 失败重试次数

# 端点 & 认证
endpoint: "https://api.deepseek.com/v1/chat/completions"
api_key: "${DEEPSEEK_API_KEY}"       # 支持环境变量引用
headers:                              # 额外 HTTP 头
  # X-Custom-Header: "value"

# 切换其他后端示例：
# backend: "openai_compatible"
# endpoint: "http://192.168.1.100:8080/v1/chat/completions"
# api_key: "sk-xxx"
# model: "qwen2.5-72b"
```

**配置优先级**：`环境变量 > config/model.yaml > 内置默认值`

**为什么模型配置单拆一个文件**：安全隔离。`model.yaml` 包含密钥，可以 `.gitignore` 掉，而 `atlas.yaml` 可以提交到仓库。

---

## 3. 启动方式设计

### 3.1 三种启动模式

| 命令 | 行为 | 适用场景 |
|------|------|---------|
| `atlas serve` | 启动 Web 服务 → 扫描 → 渲染 → 浏览器打开 → 监听文件变化 → WebSocket 推送 | **日常开发，边改代码边看图** |
| `atlas scan` | 一次性扫描 → 生成静态报告 → 退出 | CI/CD、批量分析 |
| `atlas dump` | 输出纯数据 JSON | 给下游 Agent 消费（Phase 5） |

### 3.2 `atlas serve` 完整流程

```
┌─────────────────────────────────────────────────────────────┐
│  $ atlas serve                                               │
│                                                              │
│  ① 加载 config/atlas.yaml                                    │
│  ② 加载 config/sources.yaml → 解析多模块                     │
│  ③ 检测 JDK 版本（从 pom.xml / .java-version / 系统默认）    │
│  ④ 检查 Maven 可用性（mvn --version）                        │
│  ⑤ 构建 java-analyzer JAR（如需要）                          │
│  ⑥ 执行全量扫描 → atlas-raw.json                             │
│  ⑦ 执行度量计算 → atlas-metrics.json                         │
│  ⑧ 执行 LLM 模式识别 → atlas-patterns.json  (if enabled)     │
│  ⑨ 渲染 HTML + JSON 数据文件                                 │
│  ⑩ 启动 aiohttp 服务器（127.0.0.1:8765）                    │
│  ⑪ 打开浏览器 → http://127.0.0.1:8765                       │
│  ⑫ 启动 watchdog 文件监听（watch_dirs）                      │
│                                                              │
│  浏览器端：                                                   │
│  · 首次加载 → 请求 /api/atlas.json → 渲染图谱                │
│  · WebSocket 连接 → 等待增量更新                             │
│  · 文件变化 → 增量重扫变更文件 → 局部更新图谱                │
│  · 浏览器自动刷新受影响的视图                                │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Web 服务 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 主页面（交互式图谱） |
| `/api/atlas.json` | GET | 完整图谱数据 |
| `/api/status` | GET | 扫描状态（scanning/done/error） |
| `/api/reload` | POST | 手动触发全量重扫 |
| `/ws` | WS | 增量更新推送 |

### 3.4 Watch 模式增量更新

```python
# 核心逻辑
class FileWatcher:
    def on_modified(self, file_path):
        if not file_path.endswith('.java'):
            return
        # 只重扫变更文件
        delta = analyzer.scan_files([file_path])
        # 计算受影响的图节点
        affected = graph.find_affected_nodes(delta)
        # 通过 WebSocket 推送增量
        websocket.broadcast({
            "type": "incremental",
            "changed": delta,
            "affected_nodes": affected
        })
```

**前端收到增量后**：Cytoscape.js 只更新受影响节点，不重新渲染整个图。

---

## 4. 数据契约（修复 bug#1）

### 4.1 JSON Schema 版本化

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "AtlasDocument",
  "version": "1.0.0",
  "atlas": {
    "version": "1.0.0",
    "generated_at": "2026-05-29T10:30:00Z",
    "project": "my-project"
  },
  "modules": [...],
  "entities": [...],
  "relationships": [...]
}
```

**版本约束**：Java 端输出时写入 `atlas.version`，Python 端读取时校验。版本不匹配 → 报错 + 提示重建 JAR。

### 4.2 `module` 字段精确定义（修复 bug#2）

```json
{
  "module": "order-service",           // Maven/Gradle 模块名（artifact-id）
  "module_path": "order-service/src/main/java",  // 模块源码根路径
  "java_package": "com.example.order", // Java package（二级聚类用）
}
```

**三级聚合**：`module(artifact) → java_package → class`，不再混淆 module 和 package。

### 4.3 注解角色映射补全（修复 bug#3、#9）

```java
// 新增：组合注解的解包
@SpringBootApplication → 自动识别为 [CONFIG, COMPONENT_SCAN]
@RestController → REST_ENTRY + @Controller + @ResponseBody
@Repository → DATA_ACCESS + @Component

// 新增：注解继承链
if (annotation.isMetaAnnotatedWith("org.springframework.stereotype.Component")) {
    roles.add("SPRING_BEAN");
}
```

---

## 5. 可视化（修复 bug#4）

### 5.1 数据外部加载

**旧方案（bug）**：Cytoscape.js + 数据全部内联在一个 HTML 文件里。12000 类 ≈ 50MB 单文件 → 浏览器崩溃。

**新方案**：

```
graph.html         (~50KB)  ← 纯页面框架 + JS 逻辑
atlas.json         (~5MB)   ← 图谱数据（独立 JSON）
atlas-metrics.json (~1MB)   ← 度量数据
atlas-patterns.json(~500KB) ← 模式识别结果
```

HTML 通过 `fetch('/api/atlas.json')` 加载数据，按需请求，渐进渲染。

### 5.2 四种视图不变

依赖拓扑图 / A/I 矩阵 / 分层透视 / 热点热力图，WebSocket 增量更新。

---

## 6. Agent 可消费输出（Phase 5 预留）

```json
{
  "format": "atlas-agent-v1",
  "timestamp": "...",
  "summary": { "total_modules": 12, "total_classes": 3842, "hotspots": [...] },
  "modules": [{
    "id": "order-service",
    "role": "business-service",
    "quality": { "boundary_score": 82, "ai_score": 0.72 },
    "deps": ["common-utils", "payment-service"]
  }],
  "recommendations": [
    {"type": "refactor", "target": "legacy-data", "reason": "SCC=1, A=0.1, I=0.0"},
    {"type": "extract_interface", "target": "common-utils", "reason": "被12模块依赖, 0接口"}
  ]
}
```

Agent 读这个 JSON 可以直接做决策（重构优先级、影响分析、新人导航）。

---

## 7. 修复清单

| 原bug | 修复方案 |
|-------|---------|
| #1 JSON 无版本号 | `atlas.version` 字段，解析端校验 |
| #2 module 定义模糊 | 拆为 `module` + `module_path` + `java_package` |
| #3 组合注解未识别 | 注解 meta-annotation 解包逻辑 |
| #4 HTML 内联 50MB | 数据外部加载 + fetch API |
| #5 Maven 多模块漏扫 | MavenModuleResolver 自动发现 |
| #6 JDK 硬编码 17 | 从 pom.xml / gradle / .java-version 自动检测 |
| #7 LLM 硬编码 DeepSeek | OpenAI-compatible 抽象层，model.yaml 配置 |
| #8 配置文件散落 | 统一到 config/ 目录 |
| #9 SpringBootApplication | 注解元信息解析 |
