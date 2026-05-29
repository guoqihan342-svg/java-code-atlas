# Java Code Atlas v0.2 — 实施方案

> 基于 DESIGN.md v0.2 · 修复 9 个已知 bug · 新增 config/ 统一配置 · 新增 atlas serve + Watch

---

## 项目状态

```
Phase 0 · 设计完成   ████████████  100%  ← 现在在这里
Phase 1 · 骨架       ░░░░░░░░░░░░    0%
Phase 2 · 度量       ░░░░░░░░░░░░    0%
Phase 3 · 模式识别   ░░░░░░░░░░░░    0%
Phase 4 · 可视化     ░░░░░░░░░░░░    0%
Phase 5 · Agent化    ░░░░░░░░░░░░    0%
```

---

## Phase 0 · 配置系统（第 1 天，优先实现）

> **为什么先做配置**：所有后续 Phase 依赖 config/ 目录。先建配置骨架，后填充解析器。

### 0.1 配置文件模板

**`config/atlas.yaml.example`**：

```yaml
# Java Code Atlas 主配置 v1
version: 1

project:
  name: "my-project"

sources:
  config_file: "config/sources.yaml"

java:
  jdk_version: ""
  maven_home: ""
  maven_args: ""

llm:
  config_file: "config/model.yaml"
  enabled: true

output:
  dir: ".atlas/output"
  formats: ["html", "md", "mmd", "json"]
  human_first: true

serve:
  host: "127.0.0.1"
  port: 8765
  watch: true
  watch_dirs: []
  open_browser: true

cache:
  dir: ".atlas/cache"
  ttl_hours: 24

logging:
  level: "info"
  file: ".atlas/atlas.log"
```

**`config/sources.yaml.example`**：

```yaml
version: 1
type: maven-multi-module
root: "/path/to/spring-project"
modules: []
exclude:
  - "**/target/**"
  - "**/node_modules/**"
  - "**/.git/**"
  - "**/test/**"
```

**`config/model.yaml.example`**：

```yaml
version: 1
backend: "deepseek"
model: "deepseek-chat"
temperature: 0.0
max_tokens: 4096
max_concurrency: 2
batch_size: 50
retry: 3
endpoint: "https://api.deepseek.com/v1/chat/completions"
api_key: "${DEEPSEEK_API_KEY}"
headers: {}
```

### 0.2 `atlas.py config` 命令

```bash
# 交互式生成配置
python atlas.py config init

# 验证已有配置
python atlas.py config validate

# 显示当前配置
python atlas.py config show
```

### 0.3 配置加载逻辑 (Python)

```python
# src/config.py
import os
import yaml
from pathlib import Path
from typing import Any

class ConfigLoader:
    CONFIG_DIR = Path("config")

    @classmethod
    def load(cls) -> dict[str, Any]:
        atlas = cls._load_yaml("atlas.yaml")
        sources = cls._load_yaml(atlas["sources"].get("config_file", "sources.yaml"))
        model = cls._load_yaml(atlas["llm"].get("config_file", "model.yaml"))
        atlas["sources"] = sources
        atlas["llm"] = model
        cls._resolve_env_vars(atlas)
        cls._validate(atlas)
        return atlas

    @classmethod
    def _load_yaml(cls, filename: str) -> dict:
        path = cls.CONFIG_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    @classmethod
    def _resolve_env_vars(cls, config: dict) -> None:
        """递归替换 ${VAR_NAME} 为环境变量值"""
        def resolve(value):
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                var = value[2:-1]
                return os.environ.get(var, value)
            if isinstance(value, dict):
                return {k: resolve(v) for k, v in value.items()}
            if isinstance(value, list):
                return [resolve(v) for v in value]
            return value
        for key in config:
            config[key] = resolve(config[key])

    @classmethod
    def _validate(cls, config: dict) -> None:
        required = ["project", "sources", "java", "output", "serve"]
        for key in required:
            if key not in config:
                raise ValueError(f"atlas.yaml 缺少必填项: {key}")
        if "root" not in config["sources"]:
            raise ValueError("sources.yaml 缺少 root")
```

---

## Phase 1 · Java 分析器（3 天）

### 1.1 Maven 项目搭建 (修复 bug#5: 多模块)

**`java-analyzer/pom.xml`**：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>

  <groupId>io.github.javacodeatlas</groupId>
  <artifactId>java-code-atlas-analyzer</artifactId>
  <version>0.2.0</version>
  <packaging>jar</packaging>

  <properties>
    <maven.compiler.release>17</maven.compiler.release>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    <javaparser.version>3.26.4</javaparser.version>
    <jackson.version>2.17.2</jackson.version>
    <picocli.version>4.7.6</picocli.version>
    <jgrapht.version>1.5.2</jgrapht.version>
  </properties>

  <dependencies>
    <!-- AST 解析 -->
    <dependency>
      <groupId>com.github.javaparser</groupId>
      <artifactId>javaparser-core</artifactId>
      <version>${javaparser.version}</version>
    </dependency>
    <dependency>
      <groupId>com.github.javaparser</groupId>
      <artifactId>javaparser-symbol-solver-core</artifactId>
      <version>${javaparser.version}</version>
    </dependency>

    <!-- JSON -->
    <dependency>
      <groupId>com.fasterxml.jackson.core</groupId>
      <artifactId>jackson-databind</artifactId>
      <version>${jackson.version}</version>
    </dependency>

    <!-- CLI -->
    <dependency>
      <groupId>info.picocli</groupId>
      <artifactId>picocli</artifactId>
      <version>${picocli.version}</version>
    </dependency>

    <!-- 图计算 (Phase 2) -->
    <dependency>
      <groupId>org.jgrapht</groupId>
      <artifactId>jgrapht-core</artifactId>
      <version>${jgrapht.version}</version>
    </dependency>
  </dependencies>

  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-shade-plugin</artifactId>
        <version>3.6.0</version>
        <executions>
          <execution>
            <phase>package</phase>
            <goals><goal>shade</goal></goals>
            <configuration>
              <transformers>
                <transformer
                  implementation="org.apache.maven.plugins.shade.resource.ManifestResourceTransformer">
                  <mainClass>io.github.javacodeatlas.AnalyzerCli</mainClass>
                </transformer>
              </transformers>
            </configuration>
          </execution>
        </executions>
      </plugin>
    </plugins>
  </build>
</project>
```

### 1.2 MavenModuleResolver (修复 bug#5)

```java
package io.github.javacodeatlas.util;

import java.io.IOException;
import java.nio.file.*;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Maven 多模块自动发现。
 * 读 root/pom.xml → 找 <modules> → 过滤 packaging=pom → 返回源码路径。
 */
public class MavenModuleResolver {

    public record ModuleInfo(
        String artifactId,
        String packaging,      // jar | war | pom
        Path moduleRoot,       // 模块根目录
        Path sourceRoot        // src/main/java
    ) {}

    public static List<ModuleInfo> resolve(Path projectRoot) throws IOException {
        Path rootPom = projectRoot.resolve("pom.xml");
        if (!Files.exists(rootPom)) {
            // 不是 Maven 项目，直接扫 src/main/java
            Path src = projectRoot.resolve("src/main/java");
            if (Files.exists(src)) {
                return List.of(new ModuleInfo(
                    projectRoot.getFileName().toString(),
                    "jar", projectRoot, src));
            }
            return List.of();
        }

        List<ModuleInfo> modules = new ArrayList<>();
        // 读取父 pom 的 <modules>
        List<String> moduleNames = parseModules(rootPom);

        if (moduleNames.isEmpty()) {
            // 单模块项目
            Path src = projectRoot.resolve("src/main/java");
            if (Files.exists(src)) {
                modules.add(new ModuleInfo(
                    projectRoot.getFileName().toString(),
                    "jar", projectRoot, src));
            }
        } else {
            for (String name : moduleNames) {
                Path moduleDir = projectRoot.resolve(name);
                Path modulePom = moduleDir.resolve("pom.xml");
                String packaging = "jar";
                if (Files.exists(modulePom)) {
                    packaging = parsePackaging(modulePom);
                }
                if ("pom".equals(packaging)) continue;  // 跳过聚合模块

                Path src = moduleDir.resolve("src/main/java");
                if (Files.exists(src)) {
                    modules.add(new ModuleInfo(name, packaging, moduleDir, src));
                }
            }
        }
        return modules;
    }

    // 简单 XML 解析（不引入额外依赖）
    private static List<String> parseModules(Path pom) throws IOException {
        String content = Files.readString(pom);
        List<String> modules = new ArrayList<>();
        int start = content.indexOf("<modules>");
        if (start < 0) return modules;
        int end = content.indexOf("</modules>", start);
        if (end < 0) return modules;
        String block = content.substring(start, end);
        // 找所有 <module>xxx</module>
        for (int i = 0; i < block.length(); ) {
            int ms = block.indexOf("<module>", i);
            if (ms < 0) break;
            int me = block.indexOf("</module>", ms);
            if (me < 0) break;
            modules.add(block.substring(ms + 8, me).trim());
            i = me + 9;
        }
        return modules;
    }

    private static String parsePackaging(Path pom) throws IOException {
        String content = Files.readString(pom);
        int start = content.indexOf("<packaging>");
        if (start < 0) return "jar";  // 默认 jar
        int end = content.indexOf("</packaging>", start);
        return content.substring(start + 12, end).trim();
    }
}
```

### 1.3 JDK 版本检测 (修复 bug#6)

```java
package io.github.javacodeatlas.util;

import java.io.IOException;
import java.nio.file.*;
import java.util.regex.*;

/**
 * JDK 版本自动检测。
 * 优先级：pom.xml <maven.compiler.release> > <maven.compiler.source>
 *        > build.gradle sourceCompatibility > .java-version > 系统默认
 */
public class JdkVersionDetector {

    public static String detect(Path projectRoot) {
        // 1. pom.xml
        Path pom = projectRoot.resolve("pom.xml");
        if (Files.exists(pom)) {
            String v = fromPom(pom);
            if (v != null) return v;
        }

        // 2. build.gradle / build.gradle.kts
        for (String name : new String[]{"build.gradle", "build.gradle.kts"}) {
            Path gradle = projectRoot.resolve(name);
            if (Files.exists(gradle)) {
                String v = fromGradle(gradle);
                if (v != null) return v;
            }
        }

        // 3. .java-version (jenv / sdkman)
        Path jv = projectRoot.resolve(".java-version");
        if (Files.exists(jv)) {
            try {
                return Files.readString(jv).trim();
            } catch (IOException ignored) {}
        }

        // 4. 系统默认
        return System.getProperty("java.version");
    }

    private static String fromPom(Path pom) {
        try {
            String content = Files.readString(pom);
            Pattern p = Pattern.compile(
                "<maven\\.compiler\\.(release|source)>\\s*(\\d+)\\s*</");
            Matcher m = p.matcher(content);
            if (m.find()) return m.group(2);
        } catch (IOException ignored) {}
        return null;
    }

    private static String fromGradle(Path gradle) {
        try {
            String content = Files.readString(gradle);
            Pattern p = Pattern.compile(
                "(source|target)Compatibility\\s*=\\s*['\"]?(\\d+\\.?\\d*)['\"]?");
            Matcher m = p.matcher(content);
            if (m.find()) return m.group(2);
        } catch (IOException ignored) {}
        return null;
    }
}
```

### 1.4 EntityFingerprint 数据类 (修复 bug#2)

```java
package io.github.javacodeatlas.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import java.util.*;

@JsonInclude(JsonInclude.Include.NON_EMPTY)
public class EntityFingerprint {
    public String fqn;                    // 全限定名（唯一 ID）
    public String className;              // 短类名
    public String module;                 // Maven artifact-id
    public String modulePath;             // 模块源码根路径
    public String javaPackage;            // Java package (com.example.order)

    public String kind;                   // class | interface | abstract | enum | annotation | record
    public List<String> modifiers;

    // 角色（从注解推断，修复 bug#3）
    public List<String> roles;

    // 继承/实现
    public List<String> extends_;
    public List<String> implements_;

    // 方法统计
    public int methods;
    public int publicMethods;
    public int getters;
    public int setters;
    public int constructors;
    public int overrides;

    // 依赖注入
    public int injectedDeps;
    public boolean constructorInjection;
    public boolean fieldInjection;

    // 事务
    public List<String> transactionalMethods;

    // 复杂度
    public int loc;
    public double avgMethodLength;
    public int maxMethodLength;
    public int cyclomaticComplexityMax;
    public int nestedDepthMax;

    // 事件
    public List<String> eventListenerTypes;
}
```

### 1.5 注解角色映射 (修复 bug#3, #9)

```java
package io.github.javacodeatlas.extract;

import com.github.javaparser.ast.expr.AnnotationExpr;
import java.util.*;

/**
 * 注解 → 角色映射。
 * 修复：支持组合注解的元注解解包。
 */
public class AnnotationRoleMapper {

    private static final Map<String, List<String>> DIRECT_MAP = Map.ofEntries(
        Map.entry("org.springframework.web.bind.annotation.RestController",
                  List.of("REST_ENTRY")),
        Map.entry("org.springframework.stereotype.Controller",
                  List.of("MVC_ENTRY")),
        Map.entry("org.springframework.stereotype.Service",
                  List.of("BUSINESS_LOGIC", "SPRING_BEAN")),
        Map.entry("org.springframework.stereotype.Component",
                  List.of("BUSINESS_LOGIC", "SPRING_BEAN")),
        Map.entry("org.springframework.stereotype.Repository",
                  List.of("DATA_ACCESS", "SPRING_BEAN")),
        Map.entry("org.springframework.context.annotation.Configuration",
                  List.of("CONFIG", "SPRING_BEAN")),
        Map.entry("org.springframework.transaction.annotation.Transactional",
                  List.of("TRANSACTIONAL")),
        Map.entry("org.springframework.kafka.annotation.KafkaListener",
                  List.of("MESSAGE_CONSUMER")),
        Map.entry("org.springframework.amqp.rabbit.annotation.RabbitListener",
                  List.of("MESSAGE_CONSUMER")),
        Map.entry("org.springframework.scheduling.annotation.Scheduled",
                  List.of("SCHEDULED_TASK")),
        Map.entry("org.springframework.cloud.openfeign.FeignClient",
                  List.of("RPC_CLIENT")),
        Map.entry("org.aspectj.lang.annotation.Aspect",
                  List.of("ASPECT")),
        Map.entry("org.springframework.web.bind.annotation.ControllerAdvice",
                  List.of("GLOBAL_ADVICE")),
        Map.entry("jakarta.persistence.Entity",
                  List.of("PERSISTENCE_MODEL")),
        Map.entry("javax.persistence.Entity",
                  List.of("PERSISTENCE_MODEL"))
    );

    // 组合注解解包：@SpringBootApplication → @Configuration + @ComponentScan
    private static final Map<String, List<String>> META_UNWRAP = Map.of(
        "org.springframework.boot.autoconfigure.SpringBootApplication",
        List.of("CONFIG", "SPRING_BEAN")
    );

    public static List<String> resolve(AnnotationExpr annotation) {
        String name = annotation.getNameAsString();
        List<String> roles = new ArrayList<>();

        // 直接匹配
        for (var entry : DIRECT_MAP.entrySet()) {
            if (name.equals(entry.getKey()) || name.endsWith("." + shortName(entry.getKey()))) {
                roles.addAll(entry.getValue());
            }
        }

        // 组合注解解包
        for (var entry : META_UNWRAP.entrySet()) {
            if (name.equals(entry.getKey()) || name.endsWith("." + shortName(entry.getKey()))) {
                roles.addAll(entry.getValue());
            }
        }

        return roles;
    }

    private static String shortName(String fqn) {
        int lastDot = fqn.lastIndexOf('.');
        return lastDot >= 0 ? fqn.substring(lastDot + 1) : fqn;
    }
}
```

### 1.6 AtlasDocument — JSON schema 版本化 (修复 bug#1)

```java
package io.github.javacodeatlas.model;

import com.fasterxml.jackson.annotation.JsonPropertyOrder;
import java.util.*;

@JsonPropertyOrder({"atlas", "modules", "entities", "relationships"})
public class AtlasDocument {
    public static final String CURRENT_VERSION = "1.0.0";

    public AtlasMeta atlas;
    public List<ModuleFingerprint> modules;
    public List<EntityFingerprint> entities;
    public List<Relationship> relationships;

    public static class AtlasMeta {
        public String version;           // 数据契约版本号
        public String generatedAt;
        public String project;
        public String jdkVersion;
        public int totalModules;
        public int totalEntities;
        public int totalRelationships;
    }
}
```

### 1.7 Python 调用 Java JAR

```python
# src/orchestrator.py
import subprocess
import json
import os
from pathlib import Path
from .config import ConfigLoader

class JavaAnalyzer:
    def __init__(self, config: dict):
        self.config = config
        self.jar_path = Path("java-analyzer/target/java-code-atlas-analyzer-0.2.0.jar")
        self.jdk_version = config["java"].get("jdk_version") or self._detect_jdk()
        self.maven_home = config["java"].get("maven_home", "")

    def analyze(self, output_path: Path) -> dict:
        """执行 analyze 子命令"""
        cmd = self._build_command("analyze")
        cmd.extend(["--output", str(output_path)])
        return self._run(cmd, output_path)

    def metrics(self, input_path: Path, output_path: Path) -> dict:
        """执行 metrics 子命令"""
        cmd = self._build_command("metrics")
        cmd.extend(["--input", str(input_path), "--output", str(output_path)])
        return self._run(cmd, output_path)

    def _build_command(self, subcommand: str) -> list[str]:
        cmd = ["java"]
        # JDK 版本指定（如有 JAVA_HOME）
        java_home = os.environ.get(f"JAVA_{self.jdk_version}_HOME", "")
        if java_home:
            cmd[0] = f"{java_home}/bin/java"

        cmd.extend(["-jar", str(self.jar_path), subcommand])

        # Maven 路径
        mvnhome = self.maven_home or os.environ.get("M2_HOME", "")
        if mvnhome:
            cmd.extend(["--maven-home", mvnhome])

        # 源码目录
        sources = self.config["sources"]
        cmd.extend(["--root", sources["root"]])
        for mod in sources.get("modules", []):
            cmd.extend(["--module", mod])

        return cmd

    def _run(self, cmd: list[str], output_path: Path) -> dict:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError(f"Java分析器失败:\n{result.stderr}")
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 校验版本
        if data["atlas"]["version"] != "1.0.0":
            raise ValueError(
                f"数据版本不匹配: 期望 1.0.0, 收到 {data['atlas']['version']}")
        return data
```

---

## Phase 2 · 度量计算（3 天）

### 2.1 JGraphT 图构建

```java
package io.github.javacodeatlas.metrics;

import io.github.javacodeatlas.model.*;
import org.jgrapht.Graph;
import org.jgrapht.graph.*;
import org.jgrapht.alg.scoring.*;
import java.util.*;
import java.util.stream.Collectors;

public class GraphAnalyzer {
    private final AtlasDocument doc;

    public GraphAnalyzer(AtlasDocument doc) { this.doc = doc; }

    // === 类级图 ===
    public Graph<String, DefaultWeightedEdge> classGraph() {
        Graph<String, DefaultWeightedEdge> g =
            new DefaultDirectedWeightedGraph<>(DefaultWeightedEdge.class);
        doc.entities.forEach(e -> g.addVertex(e.fqn));
        for (Relationship r : doc.relationships) {
            if (!g.containsVertex(r.source)) g.addVertex(r.source);
            if (!g.containsVertex(r.target)) g.addVertex(r.target);
            DefaultWeightedEdge edge = g.getEdge(r.source, r.target);
            if (edge == null) {
                edge = g.addEdge(r.source, r.target);
                if (edge != null) g.setEdgeWeight(edge, r.weight);
            } else {
                g.setEdgeWeight(edge, g.getEdgeWeight(edge) + r.weight);
            }
        }
        return g;
    }

    // === 模块级图（按 module 字段聚合，不是 java_package）===
    public Graph<String, DefaultWeightedEdge> moduleGraph() {
        Graph<String, DefaultWeightedEdge> g =
            new DefaultDirectedWeightedGraph<>(DefaultWeightedEdge.class);
        Set<String> modules = doc.entities.stream()
            .map(e -> e.module).collect(Collectors.toSet());
        modules.forEach(g::addVertex);
        for (Relationship r : doc.relationships) {
            String srcMod = entityModule(r.source);
            String tgtMod = entityModule(r.target);
            if (srcMod == null || tgtMod == null) continue;
            if (srcMod.equals(tgtMod)) continue;  // 跳过模块内自环
            DefaultWeightedEdge edge = g.getEdge(srcMod, tgtMod);
            if (edge == null) {
                edge = g.addEdge(srcMod, tgtMod);
                if (edge != null) g.setEdgeWeight(edge, r.weight);
            } else {
                g.setEdgeWeight(edge, g.getEdgeWeight(edge) + r.weight);
            }
        }
        return g;
    }

    private String entityModule(String fqn) {
        return doc.entities.stream()
            .filter(e -> e.fqn.equals(fqn))
            .findFirst().map(e -> e.module).orElse(null);
    }

    // === 入度/出度 ===
    public Map<String, int[]> degrees(Graph<String, ?> g) {
        Map<String, int[]> result = new HashMap<>();
        for (String v : g.vertexSet()) {
            result.put(v, new int[]{g.inDegreeOf(v), g.outDegreeOf(v)});
        }
        return result;
    }

    // === Tarjan SCC ===
    public List<List<String>> scc(Graph<String, ?> g) {
        var alg = new org.jgrapht.alg.connectivity.
            KosarajuStrongConnectivityInspector<>(g);
        return alg.stronglyConnectedSets().stream()
            .filter(set -> set.size() > 1)
            .map(ArrayList::new)
            .collect(Collectors.toList());
    }

    // === Martin A/I 矩阵 ===
    public record ModuleMetric(
        String module, int ca, int ce, double instability,
        double abstractness, double distance, String zone) {}

    public List<ModuleMetric> martinMetrics() {
        Graph<String, DefaultWeightedEdge> mg = moduleGraph();
        List<ModuleMetric> result = new ArrayList<>();
        for (String mod : mg.vertexSet()) {
            int ca = mg.inDegreeOf(mod);
            int ce = mg.outDegreeOf(mod);
            double I = (ca + ce) == 0 ? 0 : (double) ce / (ca + ce);
            double A = abstractness(mod);
            double D = Math.abs(A + I - 1);
            String zone = classifyZone(I, A);
            result.add(new ModuleMetric(mod, ca, ce, I, A, D, zone));
        }
        return result;
    }

    private double abstractness(String module) {
        long total = doc.entities.stream()
            .filter(e -> e.module.equals(module)).count();
        if (total == 0) return 1.0;
        long absCount = doc.entities.stream()
            .filter(e -> e.module.equals(module))
            .filter(e -> "abstract".equals(e.kind)
                      || "interface".equals(e.kind)).count();
        return (double) absCount / total;
    }

    private String classifyZone(double I, double A) {
        if (I < 0.5 && A < 0.5) return "pain";       // 痛苦区
        if (I >= 0.5 && A >= 0.5) return "good";     // 好区
        if (I < 0.5 && A >= 0.5) return "useless";   // 无用区
        return "normal";                               // 稳定区
    }

    // === 热点评分 ===
    public record Hotspot(String fqn, double score, String severity) {}

    public List<Hotspot> hotspots(int topN) {
        Graph<String, DefaultWeightedEdge> cg = classGraph();
        return doc.entities.stream().map(e -> {
            double score = cg.inDegreeOf(e.fqn) * 1.0
                + cg.outDegreeOf(e.fqn) * 0.5
                + e.cyclomaticComplexityMax * 0.3
                + e.loc * 0.01
                + e.transactionalMethods.size() * 0.2
                + e.implements_.size() * 0.1;
            String severity = score > 20 ? "red"
                : score > 10 ? "yellow" : "green";
            return new Hotspot(e.fqn, score, severity);
        }).sorted((a, b) -> Double.compare(b.score, a.score))
          .limit(topN).collect(Collectors.toList());
    }

    // === 模块边界质量评分 ===
    public record BoundaryScore(
        String module, int total, double interfaceRatio,
        int cycles, int publicMethods, int score, String grade) {}

    public List<BoundaryScore> boundaryScores() {
        Graph<String, DefaultWeightedEdge> mg = moduleGraph();
        List<List<String>> cycles = scc(mg);
        Set<String> cyclicModules = cycles.stream()
            .flatMap(List::stream).collect(Collectors.toSet());

        return mg.vertexSet().stream().map(mod -> {
            List<EntityFingerprint> ents = doc.entities.stream()
                .filter(e -> e.module.equals(mod)).toList();
            long interfaces = ents.stream()
                .filter(e -> "interface".equals(e.kind)
                         || "abstract".equals(e.kind)).count();
            double ir = ents.isEmpty() ? 0 : (double) interfaces / ents.size();
            int pubMethods = ents.stream()
                .mapToInt(e -> e.publicMethods).sum();
            int cyclePenalty = cyclicModules.contains(mod)
                ? cycles.stream()
                    .filter(c -> c.contains(mod))
                    .mapToInt(List::size).max().orElse(0) * 5
                : 0;

            int score = 100 - cyclePenalty
                - Math.max(0, (int)((0.25 - Math.abs(ir - 0.25)) * 100))
                - Math.min(20, pubMethods / 50);
            String grade = score >= 80 ? "良好"
                : score >= 60 ? "一般" : score >= 40 ? "弱" : "无边界";

            return new BoundaryScore(
                mod, ents.size(), ir,
                cyclicModules.contains(mod) ? 1 : 0,
                pubMethods, Math.max(0, score), grade);
        }).collect(Collectors.toList());
    }
}
```

---

## Phase 3 · LLM 模式识别（3 天）(修复 bug#7: LLM 可配置)

### 3.1 LLM 后端抽象

```python
# src/llm/backend.py
import httpx
import json
from typing import Any
from dataclasses import dataclass

@dataclass
class LlmConfig:
    endpoint: str
    api_key: str
    model: str
    temperature: float = 0.0
    max_tokens: int = 4096
    headers: dict = None
    max_concurrency: int = 2
    retry: int = 3

    def __post_init__(self):
        if self.headers is None:
            self.headers = {}

class LlmBackend:
    """OpenAI 兼容 API 抽象层。支持 DeepSeek / OpenAI / 自部署模型。"""

    def __init__(self, config: LlmConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0),
            headers=self._build_headers())

    def _build_headers(self) -> dict:
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        headers.update(self.config.headers)
        return headers

    async def chat(self, messages: list[dict]) -> str:
        for attempt in range(self.config.retry + 1):
            try:
                resp = await self.client.post(
                    self.config.endpoint,
                    json={
                        "model": self.config.model,
                        "messages": messages,
                        "temperature": self.config.temperature,
                        "max_tokens": self.config.max_tokens,
                        "response_format": {"type": "json_object"},
                    })
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except (httpx.HTTPError, KeyError) as e:
                if attempt == self.config.retry:
                    raise
                await asyncio.sleep(2 ** attempt)
        raise RuntimeError("LLM 调用失败")
```

### 3.2 批量推理管线

```python
# src/llm/pipeline.py
import asyncio
import json
from .backend import LlmBackend
from .prompts import ARCHITECTURE_PROMPT, DESIGN_PATTERN_PROMPT

class LlmPipeline:
    def __init__(self, backend: LlmBackend, batch_size: int = 50):
        self.backend = backend
        self.batch_size = batch_size
        self.semaphore = asyncio.Semaphore(backend.config.max_concurrency)

    async def detect_architecture(self, modules: list[dict]) -> list[dict]:
        """架构风格检测"""
        tasks = []
        for batch in self._batches(modules):
            tasks.append(self._arch_batch(batch))
        results = await asyncio.gather(*tasks)
        return [item for batch in results for item in batch]

    async def detect_patterns(self, classes: list[dict]) -> list[dict]:
        """设计模式识别"""
        tasks = []
        for batch in self._batches(classes):
            tasks.append(self._pattern_batch(batch))
        results = await asyncio.gather(*tasks)
        return [item for batch in results for item in batch]

    async def _arch_batch(self, modules: list[dict]) -> list[dict]:
        async with self.semaphore:
            prompt = ARCHITECTURE_PROMPT.format(
                modules=json.dumps(modules, ensure_ascii=False))
            resp = await self.backend.chat([
                {"role": "system", "content": "你是 Java 架构分析器。只基于结构特征判断。"},
                {"role": "user", "content": prompt}
            ])
            return json.loads(resp)["results"]

    async def _pattern_batch(self, classes: list[dict]) -> list[dict]:
        async with self.semaphore:
            prompt = DESIGN_PATTERN_PROMPT.format(
                classes=json.dumps(classes, ensure_ascii=False))
            resp = await self.backend.chat([
                {"role": "system", "content": "你是设计模式识别器。只基于结构特征判断。"},
                {"role": "user", "content": prompt}
            ])
            return json.loads(resp)["results"]

    def _batches(self, items: list) -> list[list]:
        return [items[i:i + self.batch_size]
                for i in range(0, len(items), self.batch_size)]
```

### 3.3 Prompt 模板

```python
# src/llm/prompts.py

ARCHITECTURE_PROMPT = """
你是一个 Java 代码结构分析器。分析以下模块的结构指纹（不含类名和方法名的业务语义），
判断每个模块的架构风格。

输入（模块指纹，JSON）：
{modules}

判断规则：
- "layered": controller 只调 service，service 只调 repository，单向依赖
- "hexagonal": domain 包 0 框架注解，infrastructure 包实现 domain 的接口
- "cqrs": command 和 query 被分离到不同的包/类
- "event-driven": ≥15% 的类有消息监听注解
- "none": 以上皆不满足

返回严格 JSON：
{{"results": [{{"module": "...", "style": "layered", "confidence": 0.9}}]}}
"""

DESIGN_PATTERN_PROMPT = """
你是一个设计模式识别器。以下类的结构指纹已去除业务语义。
基于继承、实现、字段依赖、构造器特征识别设计模式。

输入（类指纹，JSON）：
{classes}

可识别模式及判断条件：
- Singleton: private 构造 + static getInstance
- Builder: 内部 static Builder 类 + build() 返回外部类型
- Strategy: interface + ≥3 个实现 + 调用方持有 interface 引用
- Factory: 接口 + 多个实现 + 专有工厂类（方法返回接口类型）
- Adapter: 实现接口 A + 持有类型 B + 方法内调用 B
- Decorator: 实现接口 A + 持有同接口 A 的引用 + 方法内 delegate
- Proxy: 实现接口 A + 持有同接口 A 的引用 + 额外控制逻辑
- Observer: 一对多依赖 + 通知机制
- Template Method: abstract class + final 模板方法 + 子类覆写
- Repository: extends JpaRepository + 无自定义 SQL

返回严格 JSON：
{{"results": [{{"fqn": "...", "patterns": ["Singleton"], "confidence": 0.9}}]}}
"""
```

### 3.4 成本估算

```
5000 类的场景：
  架构检测：~5 个模块 × 1 次调用 × (200 input + 150 output) tokens ≈ 1,750 tokens
  模式识别：5000 类 / 50 batch × (5,000 input + 2,000 output) tokens ≈ 700,000 tokens
  总计：~701,750 tokens
  
DeepSeek 价格：~¥0.002/1K tokens → ~¥1.40
OpenAI gpt-4o-mini：~$0.15/1M input + $0.60/1M output → ~$0.13
```

---

## Phase 4 · Web 服务 + 可视化（4 天）

### 4.1 aiohttp Web 服务器

```python
# src/web/server.py
import asyncio
import json
import webbrowser
from pathlib import Path
from aiohttp import web

class AtlasServer:
    def __init__(self, config: dict):
        self.config = config
        self.app = web.Application()
        self.atlas_data = None     # 当前图谱数据
        self.status = "idle"
        self._setup_routes()

    def _setup_routes(self):
        self.app.router.add_get("/", self._index)
        self.app.router.add_get("/api/atlas.json", self._atlas_json)
        self.app.router.add_get("/api/status", self._status)
        self.app.router.add_post("/api/reload", self._reload)
        self.app.router.add_get("/ws", self._websocket)

    async def _index(self, request):
        template = Path("templates/graph.html.j2").read_text()
        return web.Response(text=template, content_type="text/html")

    async def _atlas_json(self, request):
        if not self.atlas_data:
            raise web.HTTPNotFound(text="图谱尚未生成")
        return web.json_response(self.atlas_data)

    async def _status(self, request):
        return web.json_response({"status": self.status})

    async def _reload(self, request):
        self.status = "scanning"
        # 异步触发重扫
        asyncio.create_task(self._rescan())
        return web.json_response({"status": "scanning"})

    async def _websocket(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._ws_clients.append(ws)
        async for msg in ws:
            pass  # 客户端可以发送命令
        self._ws_clients.remove(ws)
        return ws

    async def start(self):
        """启动服务"""
        host = self.config["serve"]["host"]
        port = self.config["serve"]["port"]
        open_browser = self.config["serve"]["open_browser"]

        # 先做首次扫描
        await self._rescan()

        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()

        url = f"http://{host}:{port}"
        print(f"\n  📊 Java Code Atlas → {url}")
        print(f"  📁 监控目录: {self.config['sources']['root']}")
        print(f"  🔄 Watch 模式: {'启用' if self.config['serve']['watch'] else '关闭'}\n")

        if open_browser:
            webbrowser.open(url)

        # 启动文件监听
        if self.config["serve"]["watch"]:
            from .watcher import FileWatcher
            watcher = FileWatcher(self.config, self._on_file_changed)
            asyncio.create_task(watcher.start())

        # 保持运行
        await asyncio.Event().wait()
```

### 4.2 Watch 文件监听

```python
# src/web/watcher.py
import asyncio
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FileWatcher:
    def __init__(self, config: dict, callback):
        self.config = config
        self.callback = callback
        self.observer = Observer()
        self._last_scan = 0
        self._debounce = 2.0  # 2秒防抖

    async def start(self):
        root = self.config["sources"]["root"]
        handler = _Handler(self._on_event)
        self.observer.schedule(handler, str(root), recursive=True)
        self.observer.start()

    def _on_event(self, path: str):
        if not path.endswith(".java"):
            return
        now = time.time()
        if now - self._last_scan < self._debounce:
            return  # 防抖
        self._last_scan = now
        asyncio.create_task(self.callback(path))

class _Handler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_modified(self, event):
        if not event.is_directory:
            self.callback(event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            self.callback(event.src_path)
```

### 4.3 HTML 模板 (修复 bug#4: 数据外部加载)

```html
<!-- templates/graph.html.j2 -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>Java Code Atlas</title>
  <script src="https://cdn.jsdelivr.net/npm/cytoscape@3.30.0/dist/cytoscape.min.js"></script>
  <script src="https://d3js.org/d3.v7.min.js"></script>
  <style>
    * { margin:0; padding:0; box-sizing:border-box; }
    body { font-family:system-ui; display:flex; flex-direction:column; height:100vh;
           background:#0f172a; color:#e2e8f0; }
    header { padding:12px 20px; background:#1e293b; display:flex;
             justify-content:space-between; align-items:center; }
    header strong { font-size:18px; }
    main { display:flex; flex:1; overflow:hidden; }
    aside { width:280px; background:#1e293b; padding:16px; overflow-y:auto; }
    section { flex:1; position:relative; }
    .views { display:flex; flex-direction:column; gap:8px; margin-bottom:20px; }
    .views button { padding:10px; border:1px solid #334155; background:#0f172a;
                    color:#94a3b8; cursor:pointer; border-radius:6px; font-size:14px; }
    .views button.active { background:#2563eb; color:white; border-color:#2563eb; }
    #stage { position:relative; }
    #stage > div, #stage > svg { position:absolute; inset:0; display:none; }
    #stage > div.active, #stage > svg.active { display:block; }
    #tooltip { position:absolute; padding:8px 12px; background:#1e293b;
               border:1px solid #334155; border-radius:6px; font-size:12px;
               pointer-events:none; display:none; z-index:100; }
    #status-bar { padding:8px 20px; background:#1e293b; font-size:12px; color:#64748b;
                  display:flex; gap:20px; }
  </style>
</head>
<body>
<header>
  <strong>📊 Java Code Atlas</strong>
  <span id="project-name"></span>
</header>
<main>
  <aside>
    <div class="views">
      <button id="btn-topo" class="active" onclick="switchView('topo')">🔗 依赖拓扑</button>
      <button id="btn-matrix" onclick="switchView('matrix')">📐 A/I 矩阵</button>
      <button id="btn-layers" onclick="switchView('layers')">📚 分层透视</button>
      <button id="btn-hot" onclick="switchView('hot')">🔥 热点热力</button>
    </div>
    <div id="summary"></div>
  </aside>
  <section id="stage">
    <div id="topo" class="active"></div>
    <svg id="matrix"></svg>
    <svg id="layers"></svg>
    <svg id="hot"></svg>
    <div id="tooltip"></div>
  </section>
</main>
<div id="status-bar">
  <span id="status-text">加载中...</span>
  <span id="update-time"></span>
</div>

<script>
// === 数据加载（外部 JSON，不是内联） ===
let atlas = null;

async function loadAtlas() {
  try {
    const resp = await fetch('/api/atlas.json');
    atlas = await resp.json();
    document.getElementById('project-name').textContent = atlas.atlas.project;
    document.getElementById('status-text').textContent =
      `${atlas.atlas.totalModules}模块 · ${atlas.atlas.totalEntities}类 · ${atlas.atlas.totalRelationships}关系`;
    renderTopology();
    updateSummary();
    connectWebSocket();
  } catch (e) {
    document.getElementById('status-text').textContent = '图谱加载失败';
  }
}

// === WebSocket 增量更新 ===
function connectWebSocket() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${protocol}//${location.host}/ws`);
  ws.onmessage = (event) => {
    const delta = JSON.parse(event.data);
    if (delta.type === 'incremental') {
      applyDelta(delta);
    } else if (delta.type === 'full-reload') {
      loadAtlas();
    }
  };
}

function applyDelta(delta) {
  // 局部更新图谱节点，不重新渲染整个图
  delta.changed.forEach(item => {
    if (item.type === 'entity') {
      const node = cy.getElementById(item.fqn);
      if (node.length) node.data(item.data);
    }
  });
  document.getElementById('update-time').textContent =
    `最后更新: ${new Date().toLocaleTimeString()}`;
}

// === 依赖拓扑图 ===
let cy;
function renderTopology() {
  const elements = [];
  atlas.entities.forEach(e => {
    elements.push({
      data: { id: e.fqn, label: e.className, module: e.module, roles: e.roles }
    });
  });
  atlas.relationships.forEach(r => {
    elements.push({
      data: { id: `${r.source}->${r.target}`, source: r.source,
              target: r.target, weight: r.weight, type: r.type }
    });
  });

  cy = cytoscape({
    container: document.getElementById('topo'),
    elements: elements,
    style: [
      { selector: 'node', style: {
        'label': 'data(label)',
        'background-color': ele => roleColor(ele.data('roles')),
        'width': ele => Math.max(20, Math.min(60, ele.degree() * 4 + 20)),
        'height': ele => Math.max(20, Math.min(60, ele.degree() * 4 + 20)),
        'font-size': '10px', 'color': '#e2e8f0'
      }},
      { selector: 'edge', style: {
        'width': ele => Math.max(1, Math.min(5, ele.data('weight'))),
        'line-color': ele => isCyclic(ele) ? '#ef4444' : '#475569',
        'target-arrow-color': ele => isCyclic(ele) ? '#ef4444' : '#475569',
        'target-arrow-shape': 'triangle'
      }}
    ],
    layout: { name: 'cose', animate: false }
  });

  cy.on('tap', 'node', (evt) => {
    const node = evt.target;
    tooltip.innerHTML = `
      <b>${node.data('label')}</b><br>
      模块: ${node.data('module')}<br>
      角色: ${node.data('roles').join(', ')}<br>
      入度: ${node.degree(true)} · 出度: ${node.degree(false)}
    `;
  });
}

function roleColor(roles) {
  if (!roles || !roles.length) return '#64748b';
  if (roles.includes('REST_ENTRY')) return '#16a34a';
  if (roles.includes('BUSINESS_LOGIC')) return '#2563eb';
  if (roles.includes('DATA_ACCESS')) return '#f97316';
  if (roles.includes('CONFIG')) return '#7c3aed';
  return '#64748b';
}

function isCyclic(edge) {
  return edge.data('type') === 'EXTENDS' || edge.data('type') === 'IMPLEMENTS'
    ? false : edge.data('weight') > 5;
}

const tooltip = document.getElementById('tooltip');
cy?.on('mouseover', 'node', e => {
  tooltip.style.display = 'block';
  tooltip.style.left = e.originalEvent.clientX + 10 + 'px';
  tooltip.style.top = e.originalEvent.clientY + 10 + 'px';
});
cy?.on('mouseout', 'node', () => { tooltip.style.display = 'none'; });

// === 视图切换 ===
let currentView = 'topo';
function switchView(view) {
  document.querySelectorAll('#stage > div, #stage > svg')
    .forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.views button')
    .forEach(b => b.classList.remove('active'));
  document.getElementById(view).classList.add('active');
  document.getElementById('btn-' + view).classList.add('active');

  if (view === 'topo') loadAtlas();
  else if (view === 'matrix') renderMatrix();
  else if (view === 'layers') renderLayers();
  else if (view === 'hot') renderHotspots();
}

function updateSummary() {
  const hotspots = atlas.metrics?.hotspots || [];
  const cycles = atlas.metrics?.cycles || [];
  document.getElementById('summary').innerHTML = `
    <div style="margin-top:20px;font-size:13px;">
      <p>🔴 环依赖: ${cycles.length} 处</p>
      <p>🔥 热点类 Top3:</p>
      ${hotspots.slice(0,3).map(h =>
        `<p style="font-size:11px;color:#f97316;">· ${h.fqn.split('.').pop()}</p>`
      ).join('')}
    </div>
  `;
}

function renderMatrix() {
  // D3.js A/I 矩阵散点图
  const svg = d3.select('#matrix');
  svg.selectAll('*').remove();
  const data = atlas.metrics?.martin || [];
  const w = svg.node().clientWidth, h = svg.node().clientHeight;
  const margin = 40;
  const x = d3.scaleLinear().domain([0,1]).range([margin, w-margin]);
  const y = d3.scaleLinear().domain([1,0]).range([margin, h-margin]);

  svg.append('g').call(d3.axisBottom(x)).attr('transform', `translate(0,${h-margin})`);
  svg.append('g').call(d3.axisLeft(y)).attr('transform', `translate(${margin},0)`);

  // 象限线
  svg.append('line').attr('x1',x(0.5)).attr('x2',x(0.5))
     .attr('y1',margin).attr('y2',h-margin).attr('stroke','#334155').attr('stroke-dasharray','4');
  svg.append('line').attr('x1',margin).attr('x2',w-margin)
     .attr('y1',y(0.5)).attr('y2',y(0.5)).attr('stroke','#334155').attr('stroke-dasharray','4');

  // 标签
  svg.append('text').attr('x',margin+5).attr('y',margin+15).attr('fill','#64748b').text('痛苦区');
  svg.append('text').attr('x',w-margin-50).attr('y',margin+15).attr('fill','#64748b').text('好区');

  // 散点
  svg.selectAll('circle').data(data).enter()
    .append('circle')
    .attr('cx', d => x(d.instability))
    .attr('cy', d => y(d.abstractness))
    .attr('r', 6)
    .attr('fill', d => d.zone === 'pain' ? '#ef4444'
      : d.zone === 'good' ? '#22c55e'
      : d.zone === 'useless' ? '#eab308' : '#64748b')
    .append('title').text(d => `${d.module}\nI=${d.instability.toFixed(2)} A=${d.abstractness.toFixed(2)}`);
}

function renderLayers() { /* 分层透视图 — Phase 4 实现 */ }
function renderHotspots() { /* 热力图 — Phase 4 实现 */ }

// 启动
loadAtlas();
</script>
</body>
</html>
```

---

## Phase 5 · Agent 化（2 天）

### 5.1 Agent 消费格式

```json
{
  "format": "atlas-agent-v1",
  "atlas_version": "1.0.0",
  "timestamp": "2026-05-29T10:30:00Z",
  "project": "my-project",
  "summary": {
    "total_modules": 12,
    "total_classes": 3842,
    "total_relationships": 15600,
    "cycles": 2,
    "pain_modules": 4,
    "architecture_styles": {
      "layered": 8,
      "hexagonal": 2,
      "none": 3
    }
  },
  "modules": [
    {
      "id": "order-service",
      "role": "business-service",
      "quality": {"boundary_score": 82, "ai_instability": 0.72},
      "deps_in": ["common-utils"],
      "deps_out": ["payment-service", "data-layer"],
      "hotspots": ["OrderService", "OrderValidator"],
      "patterns": ["Strategy", "Template Method"]
    }
  ],
  "recommendations": [
    {
      "type": "refactor",
      "target": "legacy-data",
      "severity": "high",
      "reason": "SCC=1, A=0.1, I=0.0 → 痛苦区，建议提取接口",
      "effected_modules": ["order-service", "payment-service"]
    }
  ]
}
```

### 5.2 Hermes Skill 封装

```python
# hermes-skill: java-code-atlas
# 触发条件: cd 到 Java 项目根目录 → 自动检测 config/atlas.yaml
# 命令: /atlas serve | /atlas scan | /atlas dump

# ~/.hermes/skills/java-code-atlas/SKILL.md 内容：
"""
当用户在 Java 项目根目录时，自动检测 config/atlas.yaml 是否存在。
如果存在，提供以下能力：
  /atlas serve  → 启动 Web 图谱服务
  /atlas scan  → 生成一次性报告
  /atlas dump  → 输出 Agent 消费 JSON

问题示例：
  "哪些模块需要重构？"       → 查询 pain_modules
  "支付流程涉及哪些文件？"   → 查询模块依赖链
  "改 OrderService 会影响什么？" → 查询被依赖关系
"""
```

---

## 附录 A · 完整目录树

```
java-code-atlas/
├── .gitignore
├── README.md
├── DESIGN.md
├── IMPLEMENTATION_PLAN.md          # 本文件
├── requirements.txt
│
├── config/                         # 🔧 所有可配置（一个文件夹）
│   ├── atlas.yaml.example
│   ├── sources.yaml.example
│   └── model.yaml.example
│
├── atlas.py                        # CLI 入口
├── src/                            # Python 编排
│   ├── __init__.py
│   ├── cli.py                      # click: serve/scan/dump/config
│   ├── config.py                   # ConfigLoader (YAML + env vars)
│   ├── orchestrator.py             # JavaAnalyzer (subprocess 调用 JAR)
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── backend.py              # LlmBackend (OpenAI 兼容抽象)
│   │   ├── pipeline.py             # LlmPipeline (批量推理)
│   │   └── prompts.py              # ARCHITECTURE_PROMPT, DESIGN_PATTERN_PROMPT
│   ├── web/
│   │   ├── __init__.py
│   │   ├── server.py               # AtlasServer (aiohttp)
│   │   ├── watcher.py              # FileWatcher (watchdog)
│   │   └── websocket.py            # WebSocket 增量推送
│   └── render/
│       ├── __init__.py
│       ├── html.py                 # HTML 渲染器
│       ├── mermaid.py              # Mermaid 生成
│       └── markdown.py             # Markdown 报告
│
├── java-analyzer/                  # Java 分析器 (Maven 项目)
│   ├── pom.xml
│   └── src/main/java/io/github/javacodeatlas/
│       ├── AnalyzerCli.java        # Picocli CLI 入口
│       ├── extract/
│       │   ├── FingerprintExtractor.java
│       │   ├── RelationshipExtractor.java
│       │   └── AnnotationRoleMapper.java
│       ├── metrics/
│       │   ├── GraphAnalyzer.java  # 图构建+SCC+A/I+热点+边界
│       │   └── MetricsCli.java
│       ├── model/
│       │   ├── AtlasDocument.java
│       │   ├── EntityFingerprint.java
│       │   ├── Relationship.java
│       │   └── ModuleFingerprint.java
│       └── util/
│           ├── MavenModuleResolver.java
│           └── JdkVersionDetector.java
│
├── templates/
│   ├── graph.html.j2               # Cytoscape.js 交互式模板
│   ├── report.md.j2
│   └── mermaid.mmd.j2
│
└── tests/
    ├── test_java/
    │   ├── FingerprintExtractorTest.java
    │   ├── RelationshipExtractorTest.java
    │   ├── AnnotationRoleMapperTest.java
    │   ├── MavenModuleResolverTest.java
    │   ├── JdkVersionDetectorTest.java
    │   ├── GraphAnalyzerTest.java
    │   └── ModelSerializationTest.java
    └── test_python/
        ├── test_config.py
        ├── test_orchestrator.py
        ├── test_llm_pipeline.py
        ├── test_web_server.py
        └── test_mermaid_export.py
```

---

## 附录 B · 测试策略

### Java 单元测试

| 测试类 | 用例数 | 覆盖 |
|--------|:-----:|------|
| `FingerprintExtractorTest` | 8 | 类/接口/抽象/枚举/记录/注解类型 + getter/setter/构造器计数 |
| `RelationshipExtractorTest` | 9 | 9 种关系类型各自提取正确 |
| `AnnotationRoleMapperTest` | 7 | 直接注解 + 组合注解解包 + 注解继承链 |
| `MavenModuleResolverTest` | 4 | 单模块/多模块/pom聚合过滤/Gradle项目fallback |
| `JdkVersionDetectorTest` | 4 | pom release/source/gradle/.java-version 各优先级 |
| `GraphAnalyzerTest` | 6 | 图构建/入度出度/SCC/AI矩阵/热点/边界评分 |
| `ModelSerializationTest` | 2 | JSON序列化/反序列化 + 版本号校验 |

### Python 单元测试

| 测试文件 | 用例数 | 覆盖 |
|---------|:-----:|------|
| `test_config.py` | 5 | 加载/环境变量解析/验证/缺失字段报错/多文件合并 |
| `test_orchestrator.py` | 3 | JAR调用/版本校验/错误处理 |
| `test_llm_pipeline.py` | 4 | 批量分片/semaphore/重试/Mock响应schema验证 |
| `test_web_server.py` | 3 | 路由/JSON响应/WebSocket连接 |
| `test_mermaid_export.py` | 2 | 合法Mermaid语法/模块图生成 |

### 集成测试

1. `spring-layered` fixture → 分层架构正确识别
2. `cyclic-modules` fixture → SCC 检测 + HTML 红色边
3. `patterns` fixture → 15 个模式样本 LLM 识别
4. `multi-repo` fixture → 跨仓依赖 COMPILE + RPC_CALLS

### CI 验收

```bash
mvn -f java-analyzer/pom.xml test
pytest -q
python atlas.py scan tests/fixtures/spring-layered -o .atlas-test/
python atlas.py serve --no-browser --port 18765 &  # 后台启动
curl -s http://127.0.0.1:18765/api/status | grep '"status":"idle"'
```

---

## 附录 C · 性能基准

### 目标

| 规模 | Java 文件 | 类/接口 | 解析 | 度量 | 内存 |
|------|:---:|:---:|------|------|:---:|
| 小型 | 100 | 180 | <5s | <1s | <512MB |
| 中型 | 1000 | 1800 | <45s | <8s | <2GB |
| 大型 | 3000 | 5000 | <120s | <15s | <3GB |
| 多仓 | 8000 | 12000 | <8min | <60s | <5GB |

### 优化

- AST 解析按文件并行，线程数 = min(CPU核数, 8)
- JSON 输出一次性写文件
- Symbol solver 默认关闭（`--resolve-symbols` 开启），避免下载 Maven 依赖
- HTML 数据外部加载，单文件 <100KB
- LLM 批处理并发数 = 2，避免限流
- Watch 增量只重扫变更文件，不重建全图
