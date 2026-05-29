"""Prompt templates for architecture and design-pattern recognition."""

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
