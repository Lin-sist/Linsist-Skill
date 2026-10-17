# Linsist 本地工作区配置规范 (linsist.config.example.md)

> Linsist 系列 Skill 采用**纯文本 Markdown 物理持久化**机制，将每日学习卡片、代码证据、错题与 48h / 168h 双轮复测看板保存在本地，彻底消除大语言模型跨会话无状态带来的“学完即忘”缺陷。
> 运行 `python scripts/init_workspace.py` 会自动生成 `.linsist/` 工作区并生成初始配置。

---

## 配置文件模板

将以下内容保存为 `.linsist/config.md`（或由初始化脚本自动生成）：

```yaml
linsist_version: "1.0.0"

# 1. 本地存储路径配置
storage:
  # 可选: local_workspace (当前工程根目录) | obsidian_vault (外部知识库根路径)
  storage_mode: "local_workspace"
  base_dir: ".linsist"
  notes_dir: ".linsist/notes"
  mistakes_dir: ".linsist/mistakes"
  retest_dashboard: ".linsist/retest_dashboard.md"

# 2. 学习者画像路径
learner:
  profile_path: ".linsist/learner-profile.md"
  target_role: "Java Agent / Enterprise RAG Engineer"

# 3. 48h / 168h 双轮遗忘复测引擎策略
spaced_retrieval:
  # 间隔复测周期（小时）：默认第 1 轮 48 小时 (2天)，第 2 轮 168 小时 (7天)
  interval_hours_tier1: 48
  interval_hours_tier2: 168
  # 每次开场最多激活复测题数（防止用户产生疲劳）
  max_retest_per_session: 2
  # 开场是否自动扫描已逾期/到期卡片
  auto_scan_on_startup: true

# 4. 当前挂载激活的课程包
active_curriculums:
  - "curriculums/java-agent-rag"
```

---

## 目录结构说明

初始化后，本地工作区结构如下：

```text
.linsist/
├── config.md                 # 工作区配置
├── learner-profile.md        # 个人学习画像与时间预算
├── retest_dashboard.md       # 48h / 168h 双轮待复测错题物理看板
├── notes/                    # 每日单点突破学习卡片 (YYYY-MM-DD_<主题>.md)
└── mistakes/                 # 核心踩坑与反复卡点专题
```
