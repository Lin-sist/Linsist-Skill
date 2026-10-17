# 真实测试运行与故障驱动学习指南 (Practice Guide)

> **原则**：单元测试只看代码不算完成，必须实际运行并观察断言。若测试遭遇失败（红条），不急于直接给出现成修复方案，而是把失败日志本身作为最佳教学素材。

---

## 1. 真实运行与断言核验

根据被测工程的技术栈和目录结构，选择最小颗粒度的执行命令：

```bash
# Maven 单测执行示例 (优先单个测试类或方法，避免无差别跑全量套件)
mvn test -Dtest=AgentStateMachineTest
mvn test -Dtest=CitationValidatorTest#testHallucinatedClaimInterception

# Gradle 单测执行示例
./gradlew test --tests "com.linsist.rag.retrieval.Bm25SearchTest"

# Python 评测脚本运行示例
pytest tests/test_rag_eval.py -k "test_rrf_scoring"
```

### 运行后必须引导关注的核心指标：
- `Passed`（通过） / `Failed`（断言失败） / `Skipped`（跳过）
- 关键异常堆栈 (`Stack Trace`) 与定位行号
- 期望值 (`expected`) vs 实际值 (`actual`) 的精确差异

---

## 2. 故障驱动排障教学模型 (Failure-Driven Learning)

当测试执行抛出红色错误时，严格按六步递进法引导学习者自主定位：

```mermaid
graph LR
    S1[1. 观测现象] --> S2[2. 提取报错信息]
    S2 --> S3[3. 定位源码断言]
    S3 --> S4[4. 建立排查假设]
    S4 --> S5[5. 验证假设]
    S5 --> S6[6. 精准修复]
```

### 优先让学习者自主定性：
- **编译/语法错误**：类型不匹配、包引入遗漏、方法签名变更。
- **断言逻辑失败**：业务边界值不符合预期、浮点精度误差、排序结果未稳定。
- **Mock/桩依赖失效**：未打桩的方法被调用、参数匹配器使用不当 (`any()` 与具体值混用)。
- **外部环境与资源缺失**：测试数据库未启动、配置文件加载路径错误、网络端口被占用。

---

## 3. AAA 测试用例结构规范

每个优质的测试用例均应遵循 AAA 标准：
1. **Arrange（准备上下文）**：构造被测对象、假数据输入、配置 Mock 打桩行为。
2. **Act（触发动作）**：调用被测方法或触发核心事件。
3. **Assert（严密断言）**：对返回值、状态机转移、异常抛出类型或交互次数执行断言。
