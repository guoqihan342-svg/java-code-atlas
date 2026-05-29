# Java Code Atlas — 完整设计文档

> 版本：v0.1.0 · 2026-05-29 · 郭启涵

---

## 目录

1. [设计哲学](#1-设计哲学)
2. [数据模型](#2-数据模型)
3. [提取层详解](#3-提取层详解)
4. [度量层详解](#4-度量层详解)
5. [模式识别层](#5-模式识别层)
6. [多仓融合策略](#6-多仓融合策略)
7. [可视化方案](#7-可视化方案)
8. [技术选型](#8-技术选型)
9. [实现路线图](#9-实现路线图)
10. [关键决策记录](#10-关键决策记录)

---

## 1. 设计哲学

### 1.1 去业务化的本质

**不是「忽略业务词」，而是「用结构特征替代语义命名」。**

```
业务命名（不可靠，不做）：
  "订单模块" → 但可能这个类改名叫 OrderModule
  "支付服务" → 但可能 PaymentService 也不处理支付

结构指纹（数学事实，可靠）：
  "高入度·SpringBoot·REST入口·依赖3个内部模块·事务边界·JPA持久化"
```

### 1.2 三层分离原则

| 层 | 做什么 | 用什么 | 为什么分离 |
|----|--------|--------|-----------|
| L1-L3 数学事实层 | AST解析 + 图计算 + 度量 | 硬编码规则 | 可靠性——数学不需要LLM |
| L4 语义推断层 | 模式识别 + 中文解释 | LLM (DeepSeek) | LLM只做它擅长的事 |
| L5 可视化层 | 同一份数据多视角投射 | Cytoscape.js | 不同角色看不同的图 |

### 1.3 核心命题

**不看方法名和注释，能从代码结构本身推断出什么？**

答案：
- ✅ 架构风格（分层/六边形/CQRS）
- ✅ 设计模式（从类结构指纹识别）
- ✅ 依赖健康度（环依赖/神模块/孤儿模块）
- ✅ 模块边界质量（接口比/依赖方向）
- ❌ 业务意图（这个 Agent 只做代码结构，不做业务语义）

---

## 2. 数据模型

### 2.1 五层架构

```
L5 · 图谱投影层  ─  交互式可视化 + 多视角切换
                    依赖拓扑图 / A/I散点图 / 分层透视图 / 热点热力图

L4 · 模式识别层  ─  LLM Agent
                    架构风格检测 / 设计模式识别 / 模块边界质量评估

L3 · 度量计算层  ─  经典软件度量
                    Ce/Ca/I/A/D / 环复杂度 / 热点评分 / SCC环检测

L2 · 关系提取层  ─  JavaParser + 注解分析
                    9种关系：EXTENDS/INVOKES/IMPLEMENTS/INJECTS/LISTENS/
                    ADVISED_BY/CONFIGURES/RPC_CALLS/TX_BOUNDARY

L1 · 实体提取层  ─  JavaParser AST
                    类/接口/抽象类/枚举/注解/记录/方法
```

### 2.2 数据流

```
.java 源码
  │
  ▼
JavaParser → AST
  │
  ├── L1: 实体指纹 (class/method level)
  │      · 类型/修饰符/注解/泛型/LOC/环复杂度
  │
  ├── L2: 关系提取
  │      · 调用/继承/注入/事件/切面/RPC
  │      · 边权重计算
  │
  ├── L3: 图计算 + 度量
  │      · 入度/出度/环检测/热点
  │      · A/I矩阵
  │
  ├── L4: LLM批量推理
  │      · 架构风格检测
  │      · 设计模式识别
  │      · 模块边界评估
  │
  └── L5: 渲染输出
         · Cytoscape.js HTML
         · Mermaid 代码块
         · 结构化 JSON
```

---

## 3. 提取层详解

### 3.1 实体指纹

每个 Java 类提取以下结构指纹，**不关心类名和方法名的业务含义**：

```json
{
  "fqn": "com.example.xxx.OrderServiceImpl",
  "fingerprint": {
    "type": "class",
    "modifiers": ["public"],
    "roles": ["REST_ENTRY", "BUSINESS_LOGIC", "TRANSACTIONAL"],
    "extends": ["AbstractBaseService"],
    "implements": ["OrderService", "InitializingBean"],
    "methods": 23,
    "public_methods": 8,
    "getters": 5,
    "setters": 3,
    "constructors": 2,
    "overrides": 3,
    "injected_deps": 4,
    "constructor_injection": true,
    "field_injection": false,
    "loc": 342,
    "avg_method_length": 14.8,
    "max_method_length": 67,
    "cyclomatic_complexity_max": 12,
    "nested_depth_max": 4,
    "type_params": 1,
    "wildcard_usage": 3
  }
}
```

### 3.2 注解→角色映射表

角色的推断**只依赖注解，不依赖类名**：

| 注解 | 推断角色 | 说明 |
|------|---------|------|
| `@RestController` / `@Controller` | `REST_ENTRY` | HTTP 请求入口 |
| `@Service` / `@Component` | `BUSINESS_LOGIC` | 业务逻辑 |
| `@Repository` | `DATA_ACCESS` | 数据访问 |
| `@Configuration` | `CONFIG` | 配置类 |
| `@Transactional` | `TRANSACTIONAL` | 事务边界 |
| `@KafkaListener` / `@RabbitListener` | `MESSAGE_CONSUMER` | 消息消费者 |
| `@Scheduled` | `SCHEDULED_TASK` | 定时任务 |
| `@FeignClient` | `RPC_CLIENT` | 远程调用客户端 |
| `@Aspect` | `ASPECT` | AOP 切面 |
| `@ControllerAdvice` | `GLOBAL_ADVICE` | 全局异常处理 |
| `@Entity` / `@Document` | `PERSISTENCE_MODEL` | 持久化模型 |
| 无框架注解 + `getXxx/setXxx` | `DTO` | 数据传输对象 |
| 无框架注解 + `static` 方法为主 | `UTIL` | 工具类 |

### 3.3 9种关系类型

```
┌──────────────────┬─────────────────────────────────┬──────┐
│ 关系类型          │ Java 特征                        │ 权重  │
├──────────────────┼─────────────────────────────────┼──────┤
│ EXTENDS          │ class B extends A               │ 1.0  │
│ INVOKES          │ 方法体内调用其他类的方法          │ 1.0  │
│ IMPLEMENTS       │ class B implements A            │ 0.8  │
│ INJECTS          │ @Autowired / @Resource           │ 0.6  │
│ LISTENS          │ @EventListener / @KafkaListener  │ 0.3  │
│ ADVISED_BY       │ @Aspect 切面拦截                  │ 0.1  │
│ CONFIGURES       │ @Bean 方法声明                    │ 0.3  │
│ RPC_CALLS        │ @FeignClient                     │ 0.5  │
│ TX_BOUNDARY      │ @Transactional 方法              │ 0.2  │
└──────────────────┴─────────────────────────────────┴──────┘
```

**边权重公式**：
```
边权重 = 调用次数 × 关系类型系数
```

**边不标注方法名**——不关心「调用了 createOrder()」，只关心「存在调用关系」和「关系的性质」。

### 3.4 模块指纹

Maven 模块或 Gradle 子项目的聚合视图：

```json
{
  "module": ":order-service",
  "type": "executable-jar",
  "artifact_id": "order-service",
  "group_id": "com.example",
  "fingerprint": {
    "classes": 127,
    "interfaces": 18,
    "abstract_classes": 7,
    "enums": 12,
    "annotations": 4,
    "records": 0,
    "internal_deps": 3,
    "external_deps": 23,
    "test_classes": 42,
    "test_ratio": 0.33,
    "architecture_roles": {
      "REST_ENTRY": 5,
      "BUSINESS_LOGIC": 12,
      "DATA_ACCESS": 8,
      "CONFIG": 3,
      "MESSAGE_CONSUMER": 2,
      "SCHEDULED_TASK": 1,
      "DTO": 15,
      "UTIL": 6
    }
  }
}
```

---

## 4. 度量层详解

### 4.1 模块级度量（Martin's A/I Matrix）

```
对每个模块计算：

  Ca (Afferent Coupling)   = 依赖这个模块的其他模块数
  Ce (Efferent Coupling)   = 这个模块依赖的其他模块数
  I  (Instability)         = Ce / (Ca + Ce)
  A  (Abstractness)        = 抽象类数 / 总类数
  D  (Distance)            = |A + I - 1|
```

**A/I 矩阵四象限**：

```
                    I = 1 (不稳定)
                         │
    (1,0) 无用区         │  (1,1) 好区
    · 全是抽象，没人用    │  · 抽象+不稳定
    · 过度设计           │  · 理想的扩展点
A=0 ─────────────────────┼────────────────────── A=1
    (0,0) 痛苦区         │  (0,1) 稳定区
    · 具体+稳定          │  · 具体+不稳定
    · 改不动也不敢改      │  · 依赖方（正常）
                         │
                    I = 0 (稳定)
```

### 4.2 类级热点评分

```
热点评分 =
    入度(被依赖数) × 1.0
  + 出度(依赖其他) × 0.5
  + 环复杂度最大值 × 0.3
  + LOC × 0.01
  + @Transactional 方法数 × 0.2   (事务边界=高风险)
  + 实现接口数 × 0.1               (接口越多越难改)

得分前10% → 标注「🔴 热点类，修改需谨慎」
```

### 4.3 环依赖检测

```
Tarjan SCC 算法 → 找出所有强连通分量

SCC 大小 severity:
  2个节点：   ⚠️ 轻微
  3-5个节点： 🔶 中度
  6+个节点：  🔴 严重

额外检测：
  跨模块环依赖 → 架构坏味道
  跨仓环依赖   → 架构灾难（需要立即重构）
```

### 4.4 模块边界质量评分

```
满分 100

组成部分：
  依赖方向正确性 (40分)：无反向依赖，无跨层跳过
  接口/实现比 (25分)：接口数 / (接口+实现) 在 0.15-0.40
  循环依赖 (20分)：无环依赖=满分，每多一个环-5
  对外暴露 (15分)：public方法数适中，不过度暴露

评分等级：
  ≥80：边界良好
  60-79：边界一般
  40-59：边界弱
  <40：无边界
```

---

## 5. 模式识别层

### 5.1 架构风格检测

LLM 输入：结构化指纹数据（不含类名和方法名的业务语义）

**可识别的架构风格**：

| 风格 | 检测特征 |
|------|---------|
| 分层架构 | `controller → service → repository` 单向依赖 |
| 六边形架构 | `domain` 零框架注解 + `infrastructure` 实现 `domain` 的接口 |
| CQRS | `command` 和 `query` 分离的包结构 |
| 事件驱动 | ≥15% 的类标注 `MESSAGE_CONSUMER` 或事件相关注解 |
| 无架构 | 无清晰的分层，Controller 直接调 DAO，Service 逻辑散落 |

### 5.2 设计模式识别

从类结构指纹 + 关联关系识别 15 种常见模式：

**创建型** (5种)：Singleton, Factory Method, Abstract Factory, Builder, Prototype
**结构型** (5种)：Adapter, Decorator, Proxy, Composite, Bridge
**行为型** (5种)：Strategy, Observer, Template Method, Chain of Responsibility, Repository

**识别方式：LLM 批量推理，不用硬编码规则（因为变体太多）**

LLM Prompt 模板：
```
你是一个 Java 代码结构分析器。以下是类的结构指纹（不包含类名和方法名的业务语义）：

{指纹JSON}

请识别该类实现了哪些设计模式，只基于结构特征判断：
- 继承/实现关系
- 字段依赖关系
- 方法签名模式
- 构造器特征

只返回确定的模式，不确定的不要猜测。
```

### 5.3 模块边界质量评估

LLM 综合评估每个模块的"边界质量"：

```json
{
  "boundary_quality": "良好",
  "boundary_type": "显式接口边界",
  "internal_cohesion": "高",
  "external_coupling": "低",
  "suggestions": [
    "service 包内 7 个类只有 1 个接口 → 建议提取接口",
    "config 被 5 个模块直接依赖 → 考虑拆分为 api-config"
  ]
}
```

---

## 6. 多仓融合策略

### 6.1 仓库角色自动推断

```
仓库类型            │ 指纹特征
────────────────────┼───────────────────────────────────
业务服务             │ 有 REST_ENTRY + BUSINESS_LOGIC
API SDK             │ ≥50% 的类有 public 方法，无 BUSINESS_LOGIC
公共库/工具          │ 无框架注解，高抽象度，被多仓依赖
BOM/Parent POM      │ 只有 pom.xml，0 个 Java 文件
基础设施             │ 全是 CONFIG，无业务逻辑
数据层               │ ≥60% 的类是 DATA_ACCESS
消息中间件            │ ≥30% 的类是 MESSAGE_CONSUMER/PUB
```

### 6.2 跨仓依赖解析

**来源**：
1. Maven/Gradle `<dependency>` → `groupId:artifactId` → 定位到其他仓
2. `@FeignClient(name="xxx")` → 根据服务名匹配到其他仓
3. 共享 `package` 路径 → `com.example.common.*` 被多仓使用

**融合**：
- 仓级依赖图 + 模块级依赖图双层叠加
- 标注跨仓边的类型：`COMPILE / RUNTIME / RPC / MESSAGE`

### 6.3 全局统计

```
- 总仓库数 / 总模块数 / 总类数 / 总接口数
- 跨仓依赖边数
- 环依赖（跨仓）
- 孤儿模块（0 入度 + 0 出度）
- 神模块（被 80% 以上其他模块依赖）
- 重复实现（不同仓有相同指纹的类）
```

---

## 7. 可视化方案

### 7.1 四种视图模式

**视图1：依赖拓扑图（有向图）**
- 节点大小 = 被依赖数
- 边粗细 = 调用权重
- 红色边 = 环依赖
- 节点颜色 = 架构角色

**视图2：A/I 矩阵散点图**
- 横轴 = A (抽象度)，纵轴 = I (不稳定度)
- 一个点 = 一个模块
- 颜色 = 距离 D (绿=理想，红=最差)

**视图3：架构分层透视图**
- 层级化的模块排列
- 箭头必须单向，反向箭头标红

**视图4：热点热力图**
- 文件树 + 热度颜色
- 点击展开模块内部类

### 7.2 输出格式

| 格式 | 适用场景 |
|------|---------|
| Mermaid 代码块 | Markdown 文档内嵌，微信可直接看 |
| HTML 单文件 (Cytoscape.js) | 默认输出，拖进浏览器即可交互 |
| 结构化 JSON | 对接 Neo4j / Draw.io / Graphviz |

### 7.3 多视角报告

同一份数据，三种角色三种报告：

| 视角 | 受众 | 关注点 |
|------|------|--------|
| 架构概览 | 架构师 | 风格分布、依赖健康度、模块角色分布 |
| 重构热力图 | Tech Lead | Top 10 重构候选、技术债评分、改进建议 |
| 新人导航 | 新人 | 推荐阅读顺序、核心模块标注、范例代码 |

---

## 8. 技术选型

| 层 | 工具 | 理由 |
|----|------|------|
| AST 解析 | **JavaParser** (Java) | Maven 插件直接用，API 成熟，支持注解+泛型 |
| 模块分析 | **Maven API** (内置) | `MavenXpp3Reader` 直接读 pom.xml |
| 字节码补充 | **ASM** (可选) | 有 .class 无源码时反推依赖 |
| 图计算 | **JGraphT** (Java) | Tarjan SCC、PageRank、最短路径内置 |
| 模式识别 | **DeepSeek API** | 批量推理，中文输出 |
| 可视化 | **Cytoscape.js** + **D3.js** | 单 HTML，零依赖，拖浏览器就能看 |
| 编排层 | **Python CLI** | 调用 JavaParser CLI，调 LLM，生成 HTML |

---

## 9. 实现路线图

```
Phase 1 · 骨架 ───────────────────── 3天
  JavaParser CLI：解析单仓 → 输出 JSON
  内容：实体指纹 + 关系提取 (L1+L2)
  验证：跑一个 Spring Boot 项目，对比手工分析

Phase 2 · 度量 ───────────────────── 3天
  图计算：入度/出度/环检测/热点
  A/I 矩阵计算
  输出：Markdown 报告 + Mermaid 图
  验证：跑 Nox (74 源文件)，看与已知结构是否吻合

Phase 3 · 模式识别 ───────────────── 3天
  LLM 管线：
    架构风格检测 (prompt 模板)
    设计模式识别 (批量)
    模块边界质量评估
  输出：中文架构分析报告

Phase 4 · 多仓 + 可视化 ──────────── 4天
  多仓扫描 + 跨仓依赖解析
  Cytoscape.js 交互式 HTML
  批量测试 12 个不同类型的仓

Phase 5 · Agent 化 ──────────────── 2天
  封装为 Hermes Skill
  触发条件：cd 到项目根目录 → 自动扫描 → 输出图谱
  支持：自然语言问答（"哪些模块最需要重构？"）
```

---

## 10. 关键决策记录

| 决策 | 选择 | 原因 |
|------|------|------|
| 业务词 vs 结构特征 | **只用结构特征** | 业务词不可靠/不一致，结构特征是数学事实 |
| 硬编码规则 vs LLM | **分层**：L1-L3 硬编码，L4 用 LLM | 度量是数学，模式识别是语义 |
| 图计算在 Java 还是 Python | **Java (JGraphT)** | 数据已在 JVM，避免序列化开销 |
| 实时 vs 预计算 | **预计算** | 5000 类图谱是全量计算，不适合实时 |
| 单 HTML vs 服务 | **单 HTML** | 零部署，扔浏览器就能看 |
| 方法名标注 vs 不标注 | **不标注** | 关系边上只标注类型+权重，不关心具体方法名 |

---

## 附录 A：Java 特有的"隐形边"

这些关系在源码中是隐式的，静态分析工具看不到，但 Atlas 能抓到：

```
显式依赖                  import → new → 方法调用 → 继承         ✅ 传统工具
Spring IOC 注入           @Autowired → 运行时注入                  ✅ Atlas
AOP 切面                  @Transactional → 代理对象                ✅ Atlas
事件总线                  @EventListener → 跨模块解耦              ✅ Atlas
反射/SPI                  ServiceLoader.load() → 动态加载          ⚠️ 部分
注解处理器                @Entity → Hibernate 生成 SQL              ❌ 不做
```

---

## 附录 B：LLM Prompt 设计原则

1. **输入只给结构指纹，不给类名/方法名** → 防止 LLM 被业务语义误导
2. **要求结构化输出** → JSON Schema 约束，不靠自然语言解析
3. **批量推理** → 一次输入 50 个类的指纹，减少 API 调用
4. **强制不猜测** → Prompt 明确要求"不确定的模式不要返回"
5. **分层递进** → 先做模块级推断，再做类级推断，减少 Token 消耗
