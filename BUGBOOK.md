# 🐛 错题本

> 「出现的问题都要记在错题本上」—— 用户指令 2026-05-29
>
> 格式：编号 · 日期 · 严重度 · 根因 · 症状 · 修复 · 教训

---

## 设计阶段 (v0.1 → v0.2 重写前)

### B01 · 2026-05-29 · 🔴 · JSON 数据契约无版本号

**症状**：Java 端改了字段名，Python 端静默失败，排查困难。

**根因**：`AtlasDocument` 没有版本字段，两端各自假设 schema 一致。

**修复**：`atlas.version = "1.0.0"`，Python 端加载时校验版本号。不匹配→报错+提示重建 JAR。

**教训**：任何跨语言/跨进程的数据契约必须有版本号。语义化版本 `MAJOR.MINOR.PATCH`。

---

### B02 · 2026-05-29 · 🔴 · `module` 字段定义模糊

**症状**：GraphAnalyzer 和 FingerprintExtractor 对 `module` 理解不一致——一个当 Maven artifact，一个当 Java package。聚合结果错乱。

**根因**：一个字段承载了多层语义。

**修复**：拆分为 `module`(artifact-id) + `modulePath`(源码路径) + `javaPackage`(Java package)。三级聚合各取所需。

**教训**：字段名必须精确定义。禁止一个字段表达多种含义。

---

### B03 · 2026-05-29 · 🟡 · `@SpringBootApplication` 未识别

**症状**：`@SpringBootApplication` 标注的类没有被识别为 `CONFIG`。

**根因**：`@SpringBootApplication` 内含 `@Configuration` + `@ComponentScan`，但 AnnotationRoleMapper 只做直接名称匹配，不做元注解解包。

**修复**：`META_UNWRAP` 映射表：`@SpringBootApplication → [CONFIG, SPRING_BEAN]`。

**教训**：Spring 的"组合注解"模式（一个注解打包多个注解）很常见。注解识别必须支持元注解展开。

---

### B04 · 2026-05-29 · 🔴 · HTML 内联全部数据

**症状**：12000 类的 Cytoscape.js 图谱，HTML 单文件 >50MB，浏览器直接崩溃。

**根因**：数据（JSON）和渲染逻辑（JS）混在一个 HTML 文件里。

**修复**：HTML 只含渲染逻辑 (<100KB)，数据通过 `fetch('/api/atlas.json')` 外部加载。渐进渲染。

**教训**：数据永远不要内联在 HTML 里。浏览器内存上限约 2GB，但 DOM 操作 50MB 数据就会卡死。

---

### B05 · 2026-05-29 · 🔴 · Maven 多模块漏扫

**症状**：`macrozheng/mall` 有 7 个子模块，但只扫到根目录的 `src/main/java`。

**根因**：FingerprintExtractor 只扫传入的单一 `Path`，不知道 Maven 有父子模块。

**修复**：新增 `MavenModuleResolver`，读根 pom.xml `<modules>` 标签，逐个解析子模块的 `src/main/java`。

**教训**：Maven 多模块是 Spring 项目的事实标准。只扫根目录等于只覆盖 10% 的场景。

---

### B06 · 2026-05-29 · 🟡 · JDK 版本硬编码 17

**症状**：`pom.xml` 写死 `<maven.compiler.release>17</maven.compiler.release>`，实际项目可能是 JDK 8/11/21。

**根因**：没有从项目推断 JDK 版本。

**修复**：`JdkVersionDetector`：四级检测 → `pom.xml(maven.compiler.release/source)` → `build.gradle(sourceCompatibility)` → `.java-version` → `System.getProperty("java.version")`。配置里可以显式覆盖。

**教训**：基础设施参数（JDK/Maven 路径/端口）必须支持自动检测+可配置覆盖，不能硬编码假设。

---

### B07 · 2026-05-29 · 🟡 · LLM 端点硬编码 DeepSeek

**症状**：`LlmBackend` 写死 `https://api.deepseek.com/v1/chat/completions`，换模型要改代码。

**根因**：没有抽象 LLM 后端。

**修复**：`LlmBackend` 支持任意 OpenAI 兼容 API。`config/model.yaml` 配置 `endpoint/api_key/headers/model`。支持 `${ENV_VAR}` 环境变量引用。

**教训**：任何外部服务都应该是可替换的。密钥禁止写死在代码或配置文件里。

---

### B08 · 2026-05-29 · 🟡 · 配置文件散落各处

**症状**：配置在根目录、`java-analyzer/`、环境变量三处分散。

**根因**：没有统一的配置管理策略。

**修复**：全部放在 `config/` 目录（除 `pom.xml`、`requirements.txt`、`.gitignore` 这些工具约定文件）。`model.yaml` 单独拆出支持 `.gitignore`。

**教训**：所有可配置放一个文件夹。与工具强绑定的文件（pom/requirements）放约定位置，并在文档里说明为什么不在 `config/`。

---

## 实现阶段

### B09 · 2026-05-29 · 🔴 · Maven Wagon HTTP 与代理不兼容

**症状**：`mvn compile` 卡在 `Downloading from central: ...` 永远不完成。curl 同 URL 正常（0.86s）。所有镜像源（阿里云/华为云/Maven Central）均相同症状。

**根因**：Maven 的 Wagon HTTP 客户端（Apache HttpClient 4.x）与 Clash 代理（127.0.0.1:7890）的 TLS 握手不兼容。`https_proxy` 环境变量和 `settings.xml` 代理配置均无效。

**修复**：
1. 用 Python/curl 直接下载所有依赖 jar 到 `~/.m2/repository`
2. `javac -cp` 直接编译（绕开 Maven 编译阶段）
3. `java -cp` 启动（不用 `-jar`，手动组 classpath）
4. `src/orchestrator.py` 改用 `java -cp` 模式

**教训**：
- 构建工具的 HTTP 栈不可靠时，要有纯 CLI 的 fallback 方案
- `javac` + `jar` 可以替代 Maven 80% 的编译功能
- 依赖 jar 的本地缓存（`~/.m2/repository`）是救命稻草

---

### B10 · 2026-05-29 · 🔴 · MavenModuleResolver 不递归嵌套模块

**症状**：`yudao-cloud` 根 pom 列出 16 个子模块，但只扫到 2 个（`yudao-gateway`、`yudao-server`）。`yudao-module-system` 等带子模块的聚合模块全部丢失。最终丢失 53 个模块。

**根因**：`MavenModuleResolver.resolve()` 读取根 pom 的 `<modules>` 后，对每个子模块：如果是 `packaging=pom` → 直接 `continue` 跳过。但实际上这些模块是"嵌套聚合模块"——自身不含源码，但有自己的 `<modules>` 指向更深层的子模块。

**修复**：`packaging=pom` 时改为递归调用 `resolve(moduleDir)`，继续挖掘子模块的 `<modules>`。

**教训**：Maven 的 `<modules>` 是递归结构，不是扁平的。做多模块扫描必须深度优先遍历。

---

### B11 · 2026-05-29 · 🔴 · `parsePackaging` 偏移量 +12→+11

**症状**：B10 修复后仍然只扫到 2 个模块。调试发现 `parsePackaging` 返回 "ar" 而不是 "jar"，导致 `"pom".equals(packaging)` 永远为 false，递归体从未执行。

**根因**：`<packaging>` 标签是 11 个字符（`<packaging>` = 1+1+1+1+1+1+1+1+1+1+1 = 11），代码写成了 `substring(start + 12, end)`，多跳了一个字符，把 "jar" 截成 "ar"。

**修复**：`start + 12` → `start + 11`。

**教训**：
- 字符串偏移量是 bug 高发区。永远不要心算标签长度——直接写 `tag.length()`。
- XML 解析宁可用现成的 SAX/DOM 也别手写 `indexOf` 解析。本项目为免依赖才手写，但必须加单元测试覆盖边界。

---

### B12 · 2026-05-29 · 🟡 · JavaParser 不支持 JDK 14+ 语法

**症状**：`yudao-cloud` 的 `yudao-module-ai` 模块解析时报：`Record Declarations are not supported` 和 `Text Block Literals are not supported`。部分文件被跳过。

**根因**：JavaParser 默认语言级别为较早版本，不支持 Java 14 的 record 和 Java 15 的 text block。

**修复**：（待处理）需要配置 `ParserConfiguration.setLanguageLevel(LanguageLevel.JAVA_17)` 或在 CLI 参数中加入 `--language-level`。

**教训**：JavaParser 的语言级别必须可配置。JDK 新特性（record/sealed/pattern matching/text block）越来越常见，默认级别必须跟上。

---

## 统计

| 阶段 | 🔴致命 | 🟡严重 | 🟢轻微 | 合计 |
|------|:---:|:---:|:---:|:---:|
| 设计 | 4 | 5 | 0 | 9 |
| 实现 | 3 | 1 | 0 | 4 |
| **总计** | **7** | **6** | **0** | **13** |

---

## 铁律

1. **跨语言数据契约必须有版本号**
2. **字段名只表达一种语义**
3. **Spring 注解必须支持元注解展开**
4. **数据永远不内联在 HTML 里**
5. **Maven 多模块必须递归遍历**
6. **基础设施参数必须可配置+自动检测**
7. **外部服务必须可替换，密钥用环境变量**
8. **配置文件集中管理，有例外要文档说明**
9. **构建工具不可靠时要有 CLI fallback**
10. **字符串偏移量用 `length()` 别心算**
11. **XML 解析用库别手写，手写了就加测试**
12. **JavaParser 语言级别必须可配置**
13. **所有 bug 必须在修复后立即记录**
