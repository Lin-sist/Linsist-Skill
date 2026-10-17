# 失败模式、项目测试映射与主题池 (Failure Modes & Topics)

> **原则**：单元测试的核心价值在于“防止代码在边界和异常情况下发生不可控的灾难性破坏”。通过分析失败模式，建立健壮的质量防御意识。

---

## 1. 核心实战项目测试映射

### 领域 1：受控 Agent 架构关键测试模式（参考 Flashback 模式）
- **确定性状态机测试**：断言非预期指令是否会被拒绝，验证非法状态跃迁必定抛出异常。
- **Function Calling 参数校验**：断言大模型返回的畸形 JSON 或非法类型入参是否会被提前拦截。
- **Human-in-the-Loop (HITL) 二段式确认**：断言在用户明确授权前，危险写操作绝不被执行。
- **Guardrails 输入输出安全**：断言 Prompt 注入、敏感词和越权字段被 100% 阻断。
- **超时与预算约束 (Deadline Budget)**：模拟网络挂起，断言系统在达到预算后优雅降级而非无限卡死。
- **幂等性与重试拦截**：断言外部非幂等工具在网络抖动时不会被静默自动重试。

### 领域 2：Enterprise RAG 系统关键测试模式
- **混合检索与 RRF 融合测试**：断言空结果集、单路召回为空时的融合分计算。
- **Citation Validator 引用校验**：构造模型幻觉回答，断言校验器能精准检测并标记无源事实。
- **多租户隔离断言**：在查询中注入跨租户 ID，断言检索结果严格为零。
- **分布式租约看门狗 (Lease Guard)**：模拟节点心跳中断，断言索引任务会被安全释放并由新节点抢占。
- **模型降级 Fallback 断言**：模拟 Reranker 服务超时，断言系统无缝退化为基础混合检索打分。

---

## 2. 软件测试主题池与技能树

### P0：核心高频测试技能（优先掌握）
- JUnit 5 核心注解：`@Test`, `@BeforeEach`, `@AfterEach`, `@DisplayName`。
- 断言库核心用法：`assertEquals`, `assertTrue`, `assertThrows`, `assertTimeoutPreemptively`。
- AAA 模式（Arrange - Act - Assert）编写规范。
- 等价类划分法与边界值分析法（边界值往往是最容易隐藏 Bug 的地方）。
- Mockito 核心技能：`mock()`, `when().thenReturn()`, `verify()`, `ArgumentCaptor`。
- 如何快速阅读 Maven / Gradle 抛出的测试失败日志堆栈。

### P1：工程级自动化测试
- 参数化测试 (`@ParameterizedTest`, `@ValueSource`, `@CsvSource`)。
- Spring Boot 整合测试与 `@MockBean`, `@SpringBootTest`。
- MockMvc / WebMvcTest 进行 Controller 接口测试。
- 测试数据隔离与上下文清理。
- 代码覆盖率工具 (JaCoCo) 的正确理解（高覆盖率不等于没有 Bug）。

### P2：高级质量保障体系（按需查阅）
- 基于属性的测试 (Property-based Testing)。
- 契约测试 (Contract Testing / Pact)。
- 基于 Testcontainers 的真实数据库/中间件集成测试。
- 变异测试 (Mutation Testing) 检验单测用例本身的有效性。
