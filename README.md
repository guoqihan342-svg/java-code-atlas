# Java Code Atlas v0.2 — Windows 版

> 多仓 Java Spring 代码结构图谱 · 边改代码边看图 · 人读优先

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Architecture](https://img.shields.io/badge/arch-v0.2-blue)]()

> **分支**：`windows`（主力开发） | `main`（Linux 版，维护模式）
>
> `main` 分支为 Linux/WSL 版本，`windows` 分支为 Windows 原生版本。

---

## 一句话

**`atlas serve` → 启动 Web 服务 → 浏览器打开** → 边改代码边看图谱自动刷新。

---

## 快速开始 (Windows)

```powershell
# 1. 初始化配置
python atlas.py config init
# 编辑 config\sources.yaml → root: "D:\你的Java项目"

# 2. 安装依赖
pip install -r requirements.txt

# 3. 编译 Java 分析器（不用 Maven，javac 直编）
cd java-analyzer
javac -cp "%USERPROFILE%\.m2\repository\*" -d target\classes src\main\java\io\github\javacodeatlas\**\*.java
cd ..

# 4. 启动
python atlas.py serve

# 浏览器打开 http://127.0.0.1:8765
# 修改代码 → 保存 → 图谱自动刷新
```

---

## 三种使用方式

| 命令 | 说明 |
|------|------|
| `atlas serve` | 启动 Web + Watch，边改代码边看图（日常开发） |
| `atlas scan` | 一次性扫描 → 生成静态报告（CI/CD） |
| `atlas dump --format json` | 输出纯数据 JSON（给下游 Agent，Phase 5） |

---

## 配置

所有可配置文件统一放在 `config/` 目录：

```
config/
├── atlas.yaml       # 主配置（端口/JDK/输出格式）
├── sources.yaml     # 代码源目录（Maven多模块/独立多项目）
└── model.yaml       # LLM 模型配置（可配任意 OpenAI 兼容 API）
```

详见 [DESIGN.md](./DESIGN.md)

---

## 四种视图

| 视图 | 说明 |
|------|------|
| 依赖拓扑 | 有向图，节点大小=被依赖数，红色边=环依赖 |
| A/I 矩阵 | Martin 抽象度/不稳定度散点，一眼找到痛苦区 |
| 分层透视 | 层级依赖方向验证，反向箭头标红 |
| 热点热力 | 文件树热力图，标注高修改风险类 |

---

## 与旧版差异 (v0.1 → v0.2)

| 变更 | 说明 |
|------|------|
| ✅ config/ 统一目录 | 所有配置集中管理 |
| ✅ JDK 自动检测 | 从 pom.xml / gradle / .java-version 读取 |
| ✅ Maven 多模块支持 | 自动发现父子模块 |
| ✅ LLM 可配置 | 支持任意 OpenAI 兼容 API |
| ✅ atlas serve + Watch | Web 服务 + 文件监听 + 浏览器实时刷新 |
| ✅ 数据外部加载 | HTML <100KB，JSON 独立，不再 50MB 单文件 |
| ✅ 注解元信息解析 | @SpringBootApplication 等组合注解正确识别 |
| ✅ JSON schema 版本化 | 数据契约版本号，避免静默失败 |

---

## 技术栈

| 层 | 工具 | 语言 |
|----|------|------|
| AST 解析 | JavaParser | Java |
| 图计算 | JGraphT | Java |
| 模式识别 | 可配置 LLM 后端 | Python |
| Web 服务 | aiohttp + WebSocket | Python |
| 文件监听 | watchdog | Python |
| 可视化 | Cytoscape.js + D3.js | JavaScript |
| 模板渲染 | Jinja2 | Python |

---

## License

MIT
