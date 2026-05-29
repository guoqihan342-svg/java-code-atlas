# Java Code Atlas

> 纯代码结构图谱 Agent — 自动扫描多仓 Java 代码，生成架构级可视化图谱（不依赖业务语义）

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 为什么做这个？

现有工具（SourceGraph / Doxygen / SonarQube）能告诉你在哪里有什么代码，但不能告诉你**代码是什么**。

Java 项目有大量隐式依赖——Spring IOC 注入、AOP 切面、事件总线、Feign 远程调用——这些是架构的核心，但静态分析工具看不到。

**Java Code Atlas 专门解决这个问题：不看业务命名，只看结构指纹，还原代码的真实架构。**

---

## 一句话

**不看 `createOrder()` 叫什么，只看它有什么注解、被谁依赖、改了会怎样。**

---

## 核心理念：去业务化

```
业务视角：  「这是个订单服务」
结构视角：  「高入度·SpringBoot·REST入口·依赖3个内部模块·事务边界·JPA持久化」
```

图谱的受众是架构师——他们要的就是结构特征，不需要业务描述。

---

## 五层数据模型

```
┌─────────────────────────────────────────────────┐
│ L5 · 图谱投影层  交互式可视化 + 多视角切换        │
├─────────────────────────────────────────────────┤
│ L4 · 模式识别层  「分层架构 / 六边形架构 / 环依赖」│  ← LLM Agent
├─────────────────────────────────────────────────┤
│ L3 · 度量计算层  内聚/耦合/抽象度/稳定性/环复杂度 │  ← 经典软件度量
├─────────────────────────────────────────────────┤
│ L2 · 关系提取层  调用/继承/注入/事件/切面/RPC     │  ← JavaParser + 注解分析
├─────────────────────────────────────────────────┤
│ L1 · 实体提取层  类/接口/抽象类/枚举/注解/方法     │  ← JavaParser AST
└─────────────────────────────────────────────────┘
```

---

## 四种输出视图

### 1. 依赖拓扑图
- 节点大小 = 被依赖数
- 边粗细 = 调用权重
- 红色边 = 环依赖
- 节点颜色 = 架构角色（REST=绿, Service=蓝, DB=橙）

### 2. A/I 矩阵散点图
- Martin 的抽象度/不稳定度矩阵
- 一眼找到「痛苦区」和「无用区」

### 3. 架构分层透视图
- 依赖方向是否单向
- 哪些层被跳过（Controller 直接调 DAO）

### 4. 热点热力图
- 文件树 + 热度颜色
- 标注「改一个类会影响多少其他类」

---

## 架构设计

```
                            ┌──────────────────────────┐
                            │    Java Code Atlas CLI    │
                            │   python3 atlas.py <repo> │
                            └────────────┬─────────────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              │                          │                          │
    ┌─────────▼─────────┐    ┌──────────▼──────────┐    ┌──────────▼──────────┐
    │   JavaParser      │    │   JGraphT (Java)    │    │   DeepSeek API      │
    │   AST → JSON      │    │   图计算 + 度量      │    │   模式识别 + 解释    │
    └───────────────────┘    └─────────────────────┘    └─────────────────────┘
              │                          │                          │
              └──────────────────────────┼──────────────────────────┘
                                         │
                              ┌──────────▼──────────┐
                              │   Cytoscape.js      │
                              │   交互式 HTML (单文件)│
                              └─────────────────────┘
```

---

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 扫描单个仓库
python atlas.py /path/to/java-project -o output/

# 扫描多仓
python atlas.py --repos repo1,repo2,repo3 -o output/

# 输出格式
python atlas.py /path/to/project --format mermaid    # Mermaid 代码块
python atlas.py /path/to/project --format html       # 交互式 HTML (默认)
python atlas.py /path/to/project --format json       # 结构化 JSON
```

---

## 项目结构

```
java-code-atlas/
├── README.md                    # 本文件
├── DESIGN.md                    # 完整设计文档
├── docs/
│   ├── fingerprint-spec.md      # 结构指纹规格
│   ├── relationship-types.md    # 9种关系类型定义
│   ├── metrics.md               # 度量指标公式
│   └── multi-repo-strategy.md   # 多仓融合策略
├── src/
│   ├── parser/                  # JavaParser 封装
│   ├── graph/                   # JGraphT 图计算
│   ├── metrics/                 # 度量计算
│   ├── llm/                     # LLM 模式识别管线
│   └── visualize/               # HTML 渲染
├── templates/
│   ├── graph.html.j2            # Cytoscape.js 模板
│   └── report.md.j2             # Markdown 报告模板
├── tests/
├── requirements.txt
└── atlas.py                     # CLI 入口
```

---

## 9种关系类型

| 关系 | Java 特征 | 权重 |
|------|----------|------|
| `EXTENDS` | `class B extends A` | 1.0 |
| `INVOKES` | 方法体内调用其他类 | 1.0 |
| `IMPLEMENTS` | `class B implements A` | 0.8 |
| `INJECTS` | `@Autowired` / `@Resource` | 0.6 |
| `LISTENS` | `@EventListener` / `@KafkaListener` | 0.3 |
| `CONFIGURES` | `@Bean` 方法声明 | 0.3 |
| `ADVISED_BY` | `@Aspect` 切面拦截 | 0.1 |
| `RPC_CALLS` | `@FeignClient` | 0.5 |
| `TX_BOUNDARY` | `@Transactional` | 0.2 |

---

## 实现路线图

| Phase | 内容 | 时间 |
|-------|------|------|
| **P1 骨架** | JavaParser CLI → JSON。实体指纹 + 关系提取 (L1+L2) | 3天 |
| **P2 度量** | 图计算：入度/出度/环检测/热点。A/I矩阵。Markdown+Mermaid | 3天 |
| **P3 模式识别** | LLM管线：架构风格检测 + 设计模式识别 + 边界质量评估 | 3天 |
| **P4 多仓+可视化** | 多仓扫描 + 跨仓依赖解析 + Cytoscape.js交互式HTML | 4天 |
| **P5 Agent化** | 封装为 Hermes Skill，自然语言问答 | 2天 |

---

## 相关资源

- [JavaParser](https://github.com/javaparser/javaparser) — Java AST 解析
- [JGraphT](https://github.com/jgrapht/jgrapht) — 图算法库
- [Cytoscape.js](https://js.cytoscape.org/) — 图可视化
- [Martin's A/I Matrix](https://en.wikipedia.org/wiki/Software_package_metrics) — 抽象度/不稳定度矩阵

---

## License

MIT
