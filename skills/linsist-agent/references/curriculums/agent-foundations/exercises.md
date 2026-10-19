# 最小手写任务契约

只读取今天选中的一个编号，给任务时不要一次展示全表。函数位于技能 `assets/agent_lab.py` 的空实现；复制到获准的学习目录后独立填写。验收统一使用 `python3 "<技能目录>/assets/check_agent_lab.py" --exercise Axx --submission "<学习目录>/agent_lab.py"`。每个编号仅运行本题契约，初始空函数应失败。

以下均为合成数据的独立实验，字段、状态和阈值是教学契约，不冒充 Flashback/RAG 的完整协议。返回字典只包含题目指定字段；需要异常时明确抛出 `ValueError`，不靠打印文本代替返回值。

## A01：有界 Agent Loop（P0）

- **签名**：`run_loop(llm, max_steps)`。`llm.next()` 按脚本返回 `{"type":"continue"}` 或 `{"type":"final","answer":"done"}`。
- **输出**：遇 final 返回 `{"status":"completed","answer":"done","steps":2}`（如第二次返回 final）；步数耗尽返回 `{"status":"budget_exhausted","answer":null,"steps":max_steps}`。每次请求消耗一步，不得多调用一次探测结束。
- **边界**：非正步数或未知消息类型抛 ValueError；脚本耗尽的 RuntimeError 原样向上传递，不重试。final 后停止调用。
- **验收**：第二步 final、一直 continue、非法上限、未知类型、脚本耗尽。面试只追问“为什么是最多 N 次调用”。

## A02：工具白名单与参数（P0）

- **签名**：`dispatch(call, tools)`；`call={"name":"add","arguments":{"a":2,"b":3}}`，`tools={"add":一个求和函数}`。
- **输出**：成功 `{"result":5}`；名字不在 tools 返回 `{"error":"unknown_tool"}`；参数必须恰好是 a、b 两个整数，否则 `{"error":"invalid_arguments"}`。bool 不作为整数接受。
- **边界**：缺字段、多字段、字符串数字、布尔值；失败时工具调用次数必须为零。禁止 eval、exec、动态 shell 或按模型文本导入函数。
- **验收**：正确求和与四种非法参数；用调用计数证明校验发生在执行前。通用 JSON Schema 校验是可选拓展，本题不是通用 Schema 引擎。

## A03：ReAct 的动作与观测关联（P0）

- **签名**：`append_observation(messages, call_id, result)`。输入已有 `{"role":"assistant","tool_call":{"id":"c1","name":"add"}}`。
- **输出**：返回新列表，追加 `{"role":"tool","tool_call_id":"c1","content":"5"}`，content 使用 `str(result)`。不修改原列表。
- **边界**：找不到对应 assistant tool_call.id 时抛 ValueError；不凭空伪造成功观测。
- **验收**：ID 关联、缺失 ID、输入未变。只讲可见的 action → observation → 下一步决策，不输出私有思维链；本题不实现完整 ReAct Agent。

## A04：状态机（P0）

- **签名**：`transition(state, event)`。
- **迁移表**：IDLE/start→RUNNING；RUNNING/propose→WAITING_CONFIRMATION；WAITING_CONFIRMATION/approve→RUNNING；RUNNING/final→COMPLETED；RUNNING/timeout→FAILED。
- **输出/边界**：返回目标状态；其余组合全部抛 ValueError，COMPLETED 与 FAILED 无出边。
- **验收**：每个合法迁移与终态重启、IDLE 审批等非法迁移。这是通用教学 FSM，不是 Flashback 的真实阶段枚举；有状态机仍需步数、时间和失败边界。

## A05：上下文字符预算（P0）

- **签名**：`trim_context(messages, max_chars)`；本题合法消息列表首条 system、末条当前 user，content 均为字符串。
- **输出**：返回新列表，始终保留首条与末条；从最近历史向前逐条尝试，放得下才加入，最后保持原顺序。字符总数按 `len(content)` 相加，不能截半条消息或修改输入。
- **例子**：内容为 rule / old / ok / now 时，预算 9 返回 rule / ok / now；预算 7 返回 rule / now。
- **边界/验收**：空列表、预算连 system+当前 user 都容不下时抛 ValueError；大预算保留全部。字符数只是离线代理，不宣称等于真实 tokenizer 的 token 数。

## A06：记忆的分档预算（P0）

- **签名**：`memory_budget(age_days, base)`；base 为非负字符数。
- **输出**：本题用合成阈值：0～29 天保留 100%，30～179 天 75%，180 天起 50%，向下取整；age_days 为 None 则返回 `min(base,40)`。
- **边界**：负天数或负 base 抛 ValueError，base=0 返回 0。30、180、未知时间、小预算均需验证。
- **验收**：base=100 时，29/30/179/180 天分别得到 100/75/75/50。只实现预算纯函数；不做检索、不改用户日记。阈值是教学数据，真实工程应读取配置与时钟，未知时间策略也不照搬到项目。

## A07：提议确认与幂等（P0）

- **签名**：`confirm(proposal, approved, current_user)`；proposal 包含 id、owner、status，初始为 PROPOSED。
- **输出**：先校验 owner，非所有者返回 denied 且不变；已 EXECUTED 返回 already_executed；已 REJECTED 返回 rejected。PROPOSED 时 approved=None 返回 pending；False 置 REJECTED 并返回 rejected；True 置 EXECUTED 并返回 executed。
- **边界**：approved 仅接受 True/False/None，其他值抛 ValueError；未确认和越权不执行。重复确认不产生第二次效果。
- **验收**：越权、待确认、确认、重复、拒绝后再确认。这里只有内存状态变化；不调用真实写工具，也不宣称实现了数据库事务、并发安全或持久化 exactly-once。

## A08：字符 n-gram 覆盖率（P0）

- **签名**：`ngram_coverage(reference, candidate, n=4)`；两段原始字符串，不做隐式分词或归一化。
- **输出**：candidate 的不同 n-gram 中，有多少存在于 reference 的 n-gram 集合，交集数除以 candidate 集合大小。重复 gram 去重；`aaaaa` 对 `aaaaab` 的 4-gram 覆盖率是 0.5。
- **边界**：candidate 空为 1.0；非空 candidate 而 reference 空为 0.0；candidate 长度不足 n 时以完整 candidate 是否为 reference 子串判断 1/0。n 非正抛 ValueError。
- **验收**：重复 gram、中文、短文本、空文本。高覆盖率不是语义真实性证明；最长未覆盖片段与 0.85 阈值的决策可留作下一次小拓展，不在本题代写。

## A09：受控反思（P0）

- **签名**：`rewrite_once(draft, rewrite)`；draft 包含 text、stage、error；rewrite 是离线回调。
- **输出**：无 error 原样文本返回 `{"status":"completed","text":原文本,"rewrites":0}`。本题仅在非 CLOSING 的 MISSING_TIME_ATTRIBUTION 时允许一次回调，传入 draft 的副本并设置 tools_enabled=False；回调返回无 error 时 completed/新文本/1，否则 fallback/“无法可靠回答”/1。
- **边界**：其他错误或 CLOSING 直接 fallback/固定文本/0；不得再次重写，不改原 draft。回调异常向上传递，不自动重试。
- **验收**：合法纠正、再次失败、无错误、工具错误、收束阶段、工具关闭与输入未变。此题只练简历中的时间归属案例，当前工程的完整 typed 触发集合以代码为准。

## A10：理解 MCP 下层的 RPC 分发（P1）

- **签名**：`handle_rpc(request, tools)`；本题请求已带 jsonrpc="2.0"、id、method；call 的 params 包含 name、arguments。
- **输出**：响应保留 jsonrpc 与 id。tools/list 的 result 为 `{"tools":[按名称排序的工具名]}`；tools/call 将参数传给已注册 callable，result 为其返回值。未知 method 的 error.code=-32601，未知工具为 -32602，不执行未知调用。
- **验收**：列表、合法求和、未知方法、未知工具与 ID 回传。这是便于手写的 RPC 层子集：工具描述、initialize、capabilities、notifications、传输和完整错误契约均未实现，不能当作真实 MCP Server 接入客户端。

## A11：Tracing 元数据（P1）

- **签名**：`redact_event(event)`。
- **输出**：新字典仅保留已存在的 trace_id、step、tool、status、duration_ms；其他键全部丢弃，不修改原字典。
- **边界/验收**：prompt、arguments、result、密钥字段不得进入结果；只有敏感字段时返回空字典。只是字段投影练习，允许字段的值仍应由可信代码构造，不等于已集成 OpenTelemetry。

## A12：离线 Evaluation（P1）

- **签名**：`evaluate(cases)`；每项含 expected、actual、steps、max_steps（非负计数）。
- **输出**：`{"total":N,"passed":P,"pass_rate":P/N}`，expected==actual 且 steps<=max_steps 才通过，全部样本进入分母。空集返回 total=0、passed=0、pass_rate=0.0。
- **验收**：输出匹配但超预算仍失败、输出错误失败、空集不除零。可选下一题才引入 checksum；本题通过率不能冒充真实模型评测或简历项目收益。

## A13：剩余时间预算（P0）

- **签名**：`remaining_budget(deadline_ms, now_ms, min_required_ms=0)`；使用可注入的合成时钟值，不实际 sleep。
- **输出**：`{"remaining_ms":max(0,deadline_ms-now_ms),"allowed":布尔值}`；剩余量大于 0 且不少于 min_required_ms 才允许。最小需求为负抛 ValueError。
- **例子**：deadline=24000、now=23500、需求 2000，返回 remaining_ms=500、allowed=False。
- **验收**：恰好足够、已过期、需求为负；没有自动重试。真实 Java 工程应考虑单调时钟与取消传播，平均耗时不能证明重试必然击穿期限。
