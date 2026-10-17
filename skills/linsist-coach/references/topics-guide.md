# 学习候选主题与选题指南 (Topics Guide)

> **核心原则**：
> 1. **每日单点闭环**：每天只专注一个 30～60 分钟可完成的最小知识切片。严禁把“Spring Boot”“数据库”“Agent 架构”这种宏观命题直接作为单日主题。
> 2. **拒绝机械刷单**：禁止自上而下按列表机械通读。所有主题应由到期复测、模拟面试暴露缺口、项目代码定位需求或摸底诊断按需触发。
> 3. **领域路线解耦**：企业实战项目路线已下沉至 `curriculums/` 目录；通用计算机基础与工程规范由本指南提供索引。

---

## 一、主线任务推荐路径

### 1. 领域项目实战主线 (Curriculum Packs)
- **Java 原生受控 Agent 与 Enterprise RAG 体系**：
  直接加载并查阅官方精选路线 [`curriculums/java-agent-rag/syllabus.md`](../../../curriculums/java-agent-rag/syllabus.md) 与架构快照 [`curriculums/java-agent-rag/projects-context.md`](../../../curriculums/java-agent-rag/projects-context.md)。
  涵盖从 FSM 状态机、Native Function Calling、HITL 二段确认，到 Dense+BM25 混合检索、RRF 融合与 Citation Validator 的 20 个硬核切片。
- **自定义项目路线**：
  参考 [`curriculums/custom-template/my-project.template.md`](../../../curriculums/custom-template/my-project.template.md) 接入个人或团队专属业务架构。

---

## 二、通用工程与计算机基础候选池 (P0 ~ P2)

### P0：高频手写与编程基石（由 `linsist-basics` 承接）
- 字符串处理、遍历、统计与反转
- 数组与双指针基本应用
- HashMap 频次统计与底层哈希碰撞机制
- ArrayList 扩容与遍历踩坑 (ConcurrentModificationException)
- 二分查找及其边界防溢出
- 基础递归与回溯终止条件
- 常见 SQL (GROUP BY / HAVING / 多表 JOIN / 聚合统计)

### P0：Java 后端核心机制
- 基本类型与对象包装、内存模型浅析
- `String`、`StringBuilder`、`StringBuffer` 不可变性与性能差异
- `equals()` 与 `hashCode()` 契约与哈希表映射原理
- 泛型擦除与编译期类型检查
- 接口 vs 抽象类设计意图
- 常见受检异常与运行时异常处理策略
- 线程基础、生命周期与线程池关键参数 (Core / Max / Queue / Reject)

### P0：网络传输与 Web 通信
- HTTP 请求行、头、体与状态码规范 (200, 301, 302, 400, 401, 403, 404, 500, 502, 504)
- GET 与 POST 幂等性与安全性语义区别
- Content-Type 与 JSON 序列化 / 反序列化原理
- TCP 三次握手与四次挥手直观理解
- RESTful API 资源设计与 URL 规范

### P0：关系型数据库核心
- 事务 ACID 特性与直观生活实例
- 事务隔离级别与脏读、不可重复读、幻读
- 聚簇索引 vs 非聚簇索引（二级索引）的物理结构差异
- B+ 树为什么适合关系型数据库
- 联合索引最左匹配原则与索引下推 (ICP)
- `EXPLAIN` 执行计划关键列解读 (`type`, `key`, `rows`, `Extra`)

---

## 三、专项深化池

### P1：操作系统与系统编程（由 `linsist-os` 承接）
- 进程与线程的本质差异、PCB 结构与上下文切换代价
- 用户态与内核态的切换与系统调用
- 虚拟内存、分页机制与 TLB 命中
- 文件描述符、inode 与 Linux 文件系统直观模型
- 阻塞 I/O、非阻塞 I/O 与 I/O 多路复用 (select/poll/epoll)
- 零拷贝 (`sendfile`, `mmap`) 原理

### P1：测试驱动与质量防护（由 `linsist-testlab` 承接）
- JUnit 5 单元测试基础与 `@Test`, `@BeforeEach`, `@ParameterizedTest`
- AAA 模式（Arrange - Act - Assert）规范
- Mockito 模拟外部依赖（`when().thenReturn()`, `verify()`）
- 等价类划分与边界值分析 (Boundary Value Analysis)
- 回归测试与 CI 流水线测试准入门禁
