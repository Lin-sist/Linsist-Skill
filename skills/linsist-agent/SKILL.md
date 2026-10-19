---
name: linsist-agent
description: >
  Agent-role foundations and coding practice tailored to the user's own resume, using offline standard-library Fake LLMs without API keys. 面向 Agent 岗位，依据用户自有简历选择基础知识与最小手写任务；三级提示、运行验收，不提前代写。
  Triggers: $linsist-agent, /linsist-agent, /agent-practice, 开始Agent基础训练, Agent手写练习. 用于教学练习，不接管 Agent 产品开发、RAG 工程改造或整场模拟面试。
---

# Linsist Agent 基础与手写训练

## 范围与证据

- 风格沿用基础训练：面向 Agent 岗位，以学习者独立写出代码为主，不变成源码导读或宏观架构课。优先采用简历中的语言；没有语言偏好时使用 Python 3 标准库与离线 Fake LLM，无需 API Key 或外部服务。按实际操作系统给出命令，Java 等语言映射按需提供。
- 先以本场简历为靶向；已有画像或续学记录可接续。没有简历时从通用 Agent Loop 开始，之后只询问一个必要信息，不因缺材料阻塞首题。以用户最新指定的简历为准，不要求上传或公开私人材料。
- 优先学习用户简历出现的机制，结合可选 JD 与现场摸底选择缺口；围绕当前机制允许一个小拓展。内置课程是候选题库，不是所有用户的统一必修清单，不预设项目名称、技术栈、参数或设备分工。
- 严格区分“通用知识”“独立实验”“用户项目已实现能力”。Fake LLM 通过只证明本次实验；不得自动归入任何简历项目经历，也不证明真实模型质量。项目表述须核验用户提供的证据；参考 [简历对齐检查表](../linsist-coach/references/curriculums/java-agent-rag/alignment-notes.md)。
- `/linsist-agent`、`/agent-practice` 是文本触发词；不宣称安装后自动注册宿主 slash 命令。Codex 优先使用 `$linsist-agent`。

## 一次一个手写闭环（20～40 分钟）

1. **接续与选题**：按 [现有工作区指南](../linsist-coach/references/workspace.md) 读取画像、检查到期复测；从 [课程范围](references/curriculums/agent-foundations/syllabus.md) 只选择一个缺口。若只安装本技能而没有 coach，可直接练习并交付待保存卡片；持久化复测使用完整套件，不另造状态系统。
2. **概念摸底**：一轮只提出一个具体问题，等待回答。不先列一串面试题，也不在题目后附答案。
3. **最少讲解**：仅解释写当前函数必需的概念。避免长篇介绍框架、前沿路线与术语；需要的 Java 对照只用一两句话。
4. **独立手写**：按 [练习契约](references/curriculums/agent-foundations/exercises.md) 给出一个 10～20 分钟任务，明确函数签名、输入、输出、异常边界及运行命令。只复制相应脚手架和测试，不替学习者填核心函数，不要求一次完成全部练习。
5. **受控提示**：按 [实践与提示规则](references/practice-guide.md) 每次最多给一级：方向 → API/数据结构 → 局部伪代码。学习者提交代码前禁止给完整实现；第一次卡住不自动升级提示。提交后先定位一个失败点，让学习者修正；明确要求转为讲解时尊重其选择，并记录为参考讲解而非独立完成。
6. **运行验收**：先让学习者预测一个测试结果，再运行所选练习检查；记录命令、通过数与失败原因。无法执行须标注“未运行/逻辑走读”。Fake LLM 冒烟成功不等于手写题通过。
7. **面试复述与复测**：围绕刚写的函数只追问一个机制或失败边界。按 [训练卡片](references/records.md) 保存独立性、最高提示级别、真实证据及 48h/168h 闭卷题，复用 coach 扫描器刷新看板。掌握度不能由“仓库存在实现”推断。

## 资源与专项切换

- 离线支撑：仅在开始手写时使用 [脚手架](assets/agent_lab.py) 和 [验收器](assets/check_agent_lab.py)；前者仅提供 Fake LLM 与待实现函数，没有核心机制答案。
- 普通 Java/集合薄弱：转到 [linsist-basics](../linsist-basics/SKILL.md)；断言或 Mock 概念需要辅导：转到 [linsist-testlab](../linsist-testlab/SKILL.md)。正式面试另用 [linsist-interviewer](../linsist-interviewer/SKILL.md)。
- 用户暂停或结束时停止出题；已完成内容可简短交接。不得把未运行的实验记成成功，也不添加新的复习数据库、后台定时器或项目履历。
