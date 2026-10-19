# 项目口径差异与修复依据

2026-10-19 审阅。先比对本场提供的当前简历、`RESUME_TARGET_STUDY_PLAN.md`、`ROADMAP_2027_AI_AGENT_ENGINEER.md`，再只读核对相关实现。私人材料不随开源套件发布；以下只保留课程修正所需的机制差异。它不是对项目当前全部能力的审计，也不是任何学习者的已掌握证明。

| 旧课程或资料表述 | 本次证据 | 修复判断 |
| --- | --- | --- |
| Flashback 使用指数时间衰减、自动摘要旧对话 | 简历描述分档预算；`MySqlMemoryPort` 不取正文，`AgentTemporalPolicy.decay` 按时间档位读取预算比例 | 改为元数据检索、时间标签与分档裁剪；指数衰减只作通用对比，不作为已实现功能 |
| HITL 通过 `WAITING_CONFIRMATION` 挂起整个 Agent，确认后恢复 | 简历为工具参数 `PROPOSED` 落库，由用户经独立端点确认执行 | 改为提议与执行分离；暂停恢复状态机保留为通用模型，不虚构项目枚举或事务机制 |
| 任意工具结果失败都可触发反思 | 当前 `AgentReflectionPolicy.instructionFor` 是封闭策略，支持时间归属缺失及特定问题数违规，排除 CLOSING，重写硬上限 1 | 修正触发边界；简历只介绍了时间归属情形，不能反向认定代码没有其他获准触发 |
| RAG 默认 Cross-Encoder；故障时退回纯 RRF，承诺 200ms | 简历、`HeuristicReranker`、`RerankerRegistry` 表明默认启发式，模型为可选，失败回退启发式 | 改为默认启发式与可选模型；删除未经核验的时延承诺 |
| 引用校验使用 Claim/NLI 推理；学习规划称 Token Jaccard | 简历只称 token 重合度；`CitationValidator.matchSnippet` 先 exact，再计算交集数 / snippetTokens.size，阈值 0.58 | 修正为引用片段重合覆盖检查，不是除以并集的 Jaccard，也不能证明语义蕴含或彻底消灭幻觉 |
| Milvus HNSW 是当前项目索引 | 当前简历明确 IVF_FLAT + 标量过滤 | IVF_FLAT 作为简历口径，HNSW 作为可选比较题；部署现状仍需具体配置和版本证据 |
| `AgentStageMachine`、若干 `*Test` 类名是现成项目凭证 | 提供材料与可读实现使用 `AgentWitnessTurnPolicy` 等类型 | 项目映射与教学示例分开；具名示例不等于真实类，必须先定位再引用 |
| Flashback 已接入 OpenTelemetry、50+ 样本及 CI 门禁 | 简历将 OTel 放在 RAG；Flashback 介绍离线快照；其归档说明明确“可运行的 Maven 命令不等于 CI 门槛” | 不把 RAG 的 OTel 搬到 Flashback，不把离线用例当作已配置 CI；不发布未经本轮运行核验的测试总数 |
| 2027 路线中 LangGraph 重构、MCP Client、多智能体、GraphRAG 等是既有能力 | 路线文档是未来里程碑；简历当前 RAG 是只读 MCP Server，没有 Agent Loop | 全部列为可选拓展，不能替代当前简历的基础手写；不得变成已完成经历 |

确定性校验、类型绑定与 n-gram 覆盖率都有适用边界，不代表完整安全保证；状态机也不会自动消灭所有死循环。超时预算应看剩余时间与上限，不能仅由平均耗时断言一次重试必然超过前端期限。

学习卡片应标注“通用知识 / 独立实验 / 项目证据”及其来源。新实验通过后，可说“在独立实验中验证了……”，不能自动写成“在 Flashback/RAG 中实现了……”。
