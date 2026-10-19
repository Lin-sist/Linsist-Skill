#!/usr/bin/env python3
"""
Comprehensive Automated Test Suite for Linsist
Tests workspace initialization, 48h spaced retrieval scanning, regex robustness,
date normalization, link verification, YAML frontmatter, and PII desensitization.
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

# Add repo root and scripts to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "skills/linsist-coach/scripts"))

import init_workspace
import scan_retest


class TestLinsistWorkspace(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_init_workspace_local(self):
        """Test workspace initialization in local root."""
        init_workspace.init_workspace(self.test_dir)
        linsist_dir = self.test_dir / ".linsist"
        self.assertTrue(linsist_dir.exists())
        self.assertTrue((linsist_dir / "notes").exists())
        self.assertTrue((linsist_dir / "mistakes").exists())
        self.assertTrue((linsist_dir / "config.md").exists())
        self.assertTrue((linsist_dir / "learner-profile.md").exists())
        self.assertTrue((linsist_dir / "retest_dashboard.md").exists())

        # Verify learner-profile content is initialized from template
        profile_text = (linsist_dir / "learner-profile.md").read_text(encoding="utf-8")
        self.assertIn("学习者背景配置模板", profile_text)

        # Verify dashboard schema has 5 columns in Passed table
        dash_text = (linsist_dir / "retest_dashboard.md").read_text(encoding="utf-8")
        self.assertIn("| 到期日期 | 关联主题 | 核心复测题 | 原始卡片路径 | 验收状态 |", dash_text)

    def test_init_workspace_external(self):
        """Test workspace initialization when target_root is an external directory."""
        external_dir = self.test_dir / "my_external_vault"
        external_dir.mkdir()
        init_workspace.init_workspace(external_dir)

        profile_text = (external_dir / ".linsist" / "learner-profile.md").read_text(encoding="utf-8")
        self.assertIn("学习者背景配置模板", profile_text)
        self.assertNotIn("# Learner Profile\n\nPlease configure your learning preferences here.", profile_text)

    def test_init_workspace_idempotence(self):
        """Test that running init_workspace twice does not overwrite existing customized files."""
        init_workspace.init_workspace(self.test_dir)
        cfg_path = self.test_dir / ".linsist" / "config.md"
        cfg_path.write_text("# Customized Config", encoding="utf-8")

        # Run again
        init_workspace.init_workspace(self.test_dir)
        self.assertEqual(cfg_path.read_text(encoding="utf-8"), "# Customized Config")


class TestScanRetest(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        init_workspace.init_workspace(self.test_dir)
        self.notes_dir = self.test_dir / ".linsist" / "notes"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_date_normalization(self):
        """Test various date formats normalize to YYYY-MM-DD."""
        self.assertEqual(scan_retest.normalize_date("2026-10-19"), "2026-10-19")
        self.assertEqual(scan_retest.normalize_date("2026/10/19"), "2026-10-19")
        self.assertEqual(scan_retest.normalize_date("2026.10.19"), "2026-10-19")
        self.assertEqual(scan_retest.normalize_date("2026年10月19日"), "2026-10-19")
        self.assertEqual(scan_retest.normalize_date("26年10月19日"), "2026-10-19")
        self.assertEqual(scan_retest.normalize_date("`2026-10-19`"), "2026-10-19")

    def test_is_passed_negative_safety(self):
        """Test that negative statuses (未通过, 不通过, 待复测) are NEVER marked as passed."""
        neg_item_1 = scan_retest.RetestItem("2026-10-10", "主题", "问题", "path", "未通过")
        neg_item_2 = scan_retest.RetestItem("2026-10-10", "主题", "问题", "path", "不通过")
        neg_item_3 = scan_retest.RetestItem("2026-10-10", "主题", "问题", "path", "待复测")
        neg_item_4 = scan_retest.RetestItem("2026-10-10", "主题", "问题", "path", "未通过/二次强化")

        self.assertFalse(neg_item_1.is_passed())
        self.assertFalse(neg_item_2.is_passed())
        self.assertFalse(neg_item_3.is_passed())
        self.assertFalse(neg_item_4.is_passed())

        # If date is past, negative items must be due
        self.assertTrue(neg_item_1.is_due())
        self.assertTrue(neg_item_2.is_due())

        # Positive statuses
        pos_item_1 = scan_retest.RetestItem("2026-10-10", "主题", "问题", "path", "已通过")
        pos_item_2 = scan_retest.RetestItem("2026-10-10", "主题", "问题", "path", "通过")
        pos_item_3 = scan_retest.RetestItem("2026-10-10", "主题", "问题", "path", "Passed")
        self.assertTrue(pos_item_1.is_passed())
        self.assertTrue(pos_item_2.is_passed())
        self.assertTrue(pos_item_3.is_passed())
        self.assertFalse(pos_item_1.is_due())

    def test_bold_tags_and_question_regexes(self):
        """Test extracting cards with bold tags, multiple questions, and varied syntax."""
        yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        note_content = f"""# [2026-10-10] Native Function Calling
- **当日核心主题**：Native Function Calling 协议与反序列化
- **48h 遗忘复测题（闭卷）**：
  - **建议复测日期**：`{yesterday}`
  - 题目 1（概念机制）：脱稿解释 Native Function Calling
  - 题目 2（边界代码）：手写参数校验逻辑 [已通过]
  - **复测状态**：待复测
"""
        note_path = self.notes_dir / "2026-10-10_function_calling.md"
        note_path.write_text(note_content, encoding="utf-8")

        items = scan_retest.scan_workspace(self.test_dir)
        self.assertEqual(len(items), 2)

        # Question 1: due
        q1 = next(it for it in items if "Native Function Calling" in it.question)
        self.assertEqual(q1.due_date, yesterday)
        self.assertEqual(q1.status, "待复测")
        self.assertTrue(q1.is_due())
        self.assertFalse(q1.is_passed())

        # Question 2: passed via inline tag [已通过]
        q2 = next(it for it in items if "手写参数校验逻辑" in it.question)
        self.assertEqual(q2.due_date, yesterday)
        self.assertEqual(q2.status, "已通过")
        self.assertFalse(q2.is_due())
        self.assertTrue(q2.is_passed())

    def test_basics_format_with_retest_question_keyword(self):
        """Test basics practice format: '复测题目 1' and '未通过'."""
        past_date = "2026-10-01"
        note_content = f"""# 基础手写与算法训练卡
- **当日核心主题**：HashMap 词频统计与碰撞处理
- **48h 闭卷复测设计**：
  - 建议复测日期：`{past_date}`
  - 复测题目 1（概念机制）：脱稿口述核心语法/机制原理
  - 复测题目 2（白板手写）：手写同类变种题或核心代码段
  - 复测状态：未通过
"""
        note_path = self.notes_dir / "2026-10-01_basics.md"
        note_path.write_text(note_content, encoding="utf-8")

        items = scan_retest.scan_workspace(self.test_dir)
        self.assertEqual(len(items), 2)
        for it in items:
            self.assertEqual(it.due_date, past_date)
            self.assertEqual(it.status, "未通过")
            self.assertTrue(it.is_due())
            self.assertFalse(it.is_passed())

    def test_handoff_card_inline_dates(self):
        """Test handoff cards with numbered items and inline dates."""
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        next_week = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
        note_content = f"""# 跨会话学习交接卡
- **已完成主题**：Flashback 确定性状态机
- **48h 到期复测题目清单**：
  1. 画出 AgentStageMachine 的 5 个核心状态 (到期日: {tomorrow})
  2. 解释超时挂起状态一致性保障 (到期日: {next_week})
- **下次启动第一题 / 动作**：定位测试类
"""
        note_path = self.notes_dir / "handoff_fsm.md"
        note_path.write_text(note_content, encoding="utf-8")

        items = scan_retest.scan_workspace(self.test_dir)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].due_date, tomorrow)
        self.assertFalse(items[0].is_due())
        self.assertEqual(items[1].due_date, next_week)
        self.assertFalse(items[1].is_due())

    def test_task_checkboxes(self):
        """Test task list syntax: - [ ] and - [x]."""
        past_date = "2026-10-01"
        note_content = f"""# [2026-10-01] 测试驱动练习
- **核心主题**：AAA 模式断言
- **48h 闭卷复测题**：
  - 到期日期：{past_date}
  - [ ] 编写非法状态跳转断言
  - [x] 解析 Mockito 桩代码
"""
        note_path = self.notes_dir / "2026-10-01_testlab.md"
        note_path.write_text(note_content, encoding="utf-8")

        items = scan_retest.scan_workspace(self.test_dir)
        self.assertEqual(len(items), 2)
        todo_item = next(it for it in items if "非法状态跳转" in it.question)
        done_item = next(it for it in items if "Mockito" in it.question)

        self.assertTrue(todo_item.is_due())
        self.assertFalse(todo_item.is_passed())
        self.assertFalse(done_item.is_due())
        self.assertTrue(done_item.is_passed())

    def test_dashboard_generation_and_cli(self):
        """Test markdown dashboard generation and CLI execution."""
        past_date = "2026-10-01"
        note_content = f"""# [2026-10-01] OS 实验
- **当日核心主题**：进程上下文切换
- **48h 闭卷复测设计**：
  - 复测日期：{past_date}
  - 题目 1：内核上下文切换开销
  - 复测状态：已通过
"""
        note_path = self.notes_dir / "os.md"
        note_path.write_text(note_content, encoding="utf-8")

        items = scan_retest.scan_workspace(self.test_dir)
        md = scan_retest.generate_dashboard_markdown(items)
        self.assertIn("## 🟢 已通过验收 (Passed)", md)
        self.assertIn("进程上下文切换", md)
        self.assertIn("内核上下文切换开销", md)

        # Test CLI execution with --json
        cmd = [sys.executable, str(REPO_ROOT / "scripts" / "scan_retest.py"), "--dir", str(self.test_dir), "--json"]
        import subprocess
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(proc.stdout)
        self.assertEqual(data["total_items"], 1)
        self.assertEqual(data["passed_count"], 1)
        self.assertEqual(data["due_count"], 0)

    def test_two_stage_spaced_retrieval_scheduling(self):
        """Test Stage 1 passed status automatically schedules Stage 2 due in 7 days (168h)."""
        seven_days_ago = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
        note_content = f"""# [2026-10-10] Native Function Calling
- **当日核心主题**：Native Function Calling 协议与反序列化
- **48h / 168h 间隔复测题（闭卷）**：
  - 建议复测日期：`{seven_days_ago}`
  - 题目 1：脱稿解释 Native Function Calling
  - 复测状态：第1轮已通过
"""
        note_path = self.notes_dir / "function_calling_2stage.md"
        note_path.write_text(note_content, encoding="utf-8")

        items = scan_retest.scan_workspace(self.test_dir)
        self.assertEqual(len(items), 2)

        s1_item = next(it for it in items if it.stage == 1)
        s2_item = next(it for it in items if it.stage == 2)

        self.assertEqual(s1_item.due_date, seven_days_ago)
        self.assertTrue(s1_item.is_passed())
        self.assertFalse(s1_item.is_due())

        # Stage 2 should be scheduled for today (seven_days_ago + 7 days = today)
        self.assertEqual(s2_item.due_date, date.today().strftime("%Y-%m-%d"))
        self.assertFalse(s2_item.is_passed())
        self.assertTrue(s2_item.is_due())

    def test_two_stage_upcoming_and_mastered(self):
        """Test Stage 2 upcoming when scheduled in the future, and mastered when passed."""
        two_days_ago = (date.today() - timedelta(days=2)).strftime("%Y-%m-%d")
        note_content = f"""# [2026-10-15] BM25 稀疏检索
- **当日核心主题**：BM25 稀疏检索原理
- **48h / 168h 间隔复测题（闭卷）**：
  - 建议复测日期：`{two_days_ago}`
  - 题目 1：解释 TF、IDF 与文档长度归一化
  - 复测状态：第1轮已通过
"""
        note_path = self.notes_dir / "bm25_2stage.md"
        note_path.write_text(note_content, encoding="utf-8")

        items = scan_retest.scan_workspace(self.test_dir)
        s2_item = next(it for it in items if it.stage == 2)
        expected_s2_date = (date.today() + timedelta(days=5)).strftime("%Y-%m-%d")
        self.assertEqual(s2_item.due_date, expected_s2_date)
        self.assertFalse(s2_item.is_due())
        self.assertFalse(s2_item.is_passed())

        # Now mark as fully mastered (Stage 2 passed)
        note_content_mastered = note_content.replace("复测状态：第1轮已通过", "复测状态：第2轮已通过")
        note_path.write_text(note_content_mastered, encoding="utf-8")

        items_mastered = scan_retest.scan_workspace(self.test_dir)
        self.assertEqual(len(items_mastered), 1)
        self.assertEqual(items_mastered[0].stage, 2)
        self.assertTrue(items_mastered[0].is_passed())
        self.assertFalse(items_mastered[0].is_due())

    def test_records_template_format_parsing(self):
        """Test scanning notes created in exact format of records-template.md."""
        note_content = """# [2026-10-10] Native Function Calling
- **当日核心主题**：Native Function Calling 协议与反序列化
- **48h / 168h 间隔复测题（闭卷）**：
  - 第 1 轮建议复测日期 (48h)：`2026-10-12`
  - 第 2 轮建议复测日期 (168h)：`2026-10-19`
  - 题目 1（概念机制）：脱稿解释 Native Function Calling
  - 题目 2（边界/代码）：手写参数校验逻辑
  - 复测状态：待复测
"""
        note_path = self.notes_dir / "official_template_note.md"
        note_path.write_text(note_content, encoding="utf-8")

        items = scan_retest.scan_workspace(self.test_dir)
        self.assertEqual(len(items), 4)

        # 2 questions * 2 stages
        s1_items = [it for it in items if it.stage == 1]
        s2_items = [it for it in items if it.stage == 2]
        self.assertEqual(len(s1_items), 2)
        self.assertEqual(len(s2_items), 2)

        for it in s1_items:
            self.assertEqual(it.due_date, "2026-10-12")
            self.assertEqual(it.status, "待复测")
            self.assertFalse(it.is_passed())

        for it in s2_items:
            self.assertEqual(it.due_date, "2026-10-19")
            self.assertIn("待第1轮通过", it.status)
            self.assertFalse(it.is_due())

    def test_two_stage_status_variations_and_general_passed(self):
        """Test spaces, Chinese punctuation, and general passed status in 2-stage workflow."""
        note_content_spaced = """# [2026-10-10] Shared Deadline Budget
- **当日核心主题**：全局共享超时预算
- **48h / 168h 间隔复测题（闭卷）**：
  - 第 1 轮建议复测日期 (48h)：`2026-10-12`
  - 第 2 轮建议复测日期 (168h)：`2026-10-19`
  - 题目 1：脱稿解释超时预算拦截机制
  - 复测状态：第 1 轮已通过
"""
        note_path = self.notes_dir / "deadline_budget.md"
        note_path.write_text(note_content_spaced, encoding="utf-8")

        items = scan_retest.scan_workspace(self.test_dir)
        self.assertEqual(len(items), 2)
        s1 = next(it for it in items if it.stage == 1)
        s2 = next(it for it in items if it.stage == 2)
        self.assertTrue(s1.is_passed())
        self.assertFalse(s2.is_passed())
        self.assertEqual(s2.status, "待第2轮复测 (168h)")

        # Test full-width Chinese parens
        note_path.write_text(note_content_spaced.replace("第 1 轮已通过", "已通过（48h）"), encoding="utf-8")
        items_parens = scan_retest.scan_workspace(self.test_dir)
        s1_p = next(it for it in items_parens if it.stage == 1)
        s2_p = next(it for it in items_parens if it.stage == 2)
        self.assertTrue(s1_p.is_passed())
        self.assertEqual(s2_p.status, "待第2轮复测 (168h)")

        # Test general 已通过 on 2-stage note automatically promoting Stage 2
        note_path.write_text(note_content_spaced.replace("第 1 轮已通过", "已通过"), encoding="utf-8")
        items_gen = scan_retest.scan_workspace(self.test_dir)
        s1_g = next(it for it in items_gen if it.stage == 1)
        s2_g = next(it for it in items_gen if it.stage == 2)
        self.assertTrue(s1_g.is_passed())
        self.assertEqual(s2_g.status, "待第2轮复测 (168h)")

        # Test mastered with space and Chinese tag
        note_path.write_text(note_content_spaced.replace("第 1 轮已通过", "已完全掌握"), encoding="utf-8")
        items_mast = scan_retest.scan_workspace(self.test_dir)
        self.assertEqual(len(items_mast), 1)
        self.assertEqual(items_mast[0].stage, 2)
        self.assertTrue(items_mast[0].is_passed())


class TestRepositorySanity(unittest.TestCase):
    def test_no_pii_in_tracked_files(self):
        """Ensure no sensitive personal identity leaks remain in the repository."""
        pii_terms = ["萍" + "乡", "长" + "沙", "杭" + "州", "补" + "考", "Ping" + "xiang", "Chang" + "sha", "Hang" + "zhou"]
        violations = []
        for path in REPO_ROOT.rglob("*"):
            if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts and "tests" not in path.parts:
                content = path.read_text(encoding="utf-8", errors="ignore")
                for term in pii_terms:
                    if term in content:
                        violations.append((path.relative_to(REPO_ROOT).as_posix(), term))
        self.assertEqual(violations, [], f"Found PII leaks: {violations}")

    def test_all_markdown_links_valid(self):
        """Verify that every relative markdown link resolves to a valid file."""
        import re
        link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        broken = []
        for md in REPO_ROOT.rglob("*.md"):
            if ".git" in md.parts:
                continue
            content = md.read_text(encoding="utf-8", errors="ignore")
            for m in link_pattern.finditer(content):
                _, url = m.groups()
                if url.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                target_path = url.split("#")[0]
                if not target_path:
                    continue
                dest = (md.parent / target_path).resolve()
                if not dest.exists():
                    broken.append((md.relative_to(REPO_ROOT).as_posix(), url))
        self.assertEqual(broken, [], f"Broken markdown links found: {broken}")

    def test_skills_frontmatter_and_agents_manifest(self):
        """Verify all 5 skills have valid YAML frontmatter and agents/openai.yaml manifests."""
        import yaml
        expected_skills = [
            "linsist-coach",
            "linsist-interviewer",
            "linsist-basics",
            "linsist-os",
            "linsist-testlab",
        ]
        for sk in expected_skills:
            skill_md = REPO_ROOT / "skills" / sk / "SKILL.md"
            self.assertTrue(skill_md.exists(), f"Missing SKILL.md for {sk}")
            parts = skill_md.read_text(encoding="utf-8").split("---", 2)
            self.assertGreaterEqual(len(parts), 3, f"Missing YAML frontmatter in {sk}")
            front = yaml.safe_load(parts[1])
            self.assertEqual(front.get("name"), sk)
            self.assertIn("Triggers:", front.get("description", ""))

            # Verify openai.yaml
            openai_yaml = REPO_ROOT / "skills" / sk / "agents" / "openai.yaml"
            self.assertTrue(openai_yaml.exists(), f"Missing agents/openai.yaml for {sk}")
            manifest = yaml.safe_load(openai_yaml.read_text(encoding="utf-8"))
            self.assertEqual(manifest["interface"]["display_name"], sk)
            self.assertTrue(manifest["policy"]["allow_implicit_invocation"])

    def test_gitignore_ignores_linsist_entirely(self):
        """Verify .gitignore ignores .linsist/ entirely including retest_dashboard.md."""
        gitignore_path = REPO_ROOT / ".gitignore"
        self.assertTrue(gitignore_path.exists())
        content = gitignore_path.read_text(encoding="utf-8")
        self.assertIn(".linsist/", content)

        # Test with git check-ignore
        import subprocess
        proc = subprocess.run(
            ["git", "check-ignore", ".linsist/retest_dashboard.md"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True
        )
        self.assertEqual(proc.returncode, 0, ".linsist/retest_dashboard.md is not ignored by git!")

    def test_recall_precision_metric_definitions(self):
        """Verify Recall@K and Precision@K are accurately defined and differentiated in syllabus.md."""
        syllabus_path = REPO_ROOT / "skills/linsist-coach/references/curriculums" / "java-agent-rag" / "syllabus.md"
        self.assertTrue(syllabus_path.exists())
        content = syllabus_path.read_text(encoding="utf-8")

        self.assertIn("Recall@K", content)
        self.assertIn("Precision@K", content)
        self.assertIn("MRR (Mean Reciprocal Rank)", content)
        self.assertIn("真实相关文档总数", content)
        self.assertIn("相关文档数 / K", content)

    def test_evidence_based_pitch_constraint_enforced(self):
        """Verify hard rule constraint for evidence-based interview pitches is present in core documents."""
        rule_snippet = "只有用户真实项目中已经实现，并能提供代码或测试证据的技术成果，才能作为个人项目经历陈述"
        prohibition_snippet = "严禁使用『我们实现了/建立了』的确定性第一人称经历表达"

        targets = [
            REPO_ROOT / "skills" / "linsist-coach" / "SKILL.md",
            REPO_ROOT / "skills" / "linsist-interviewer" / "SKILL.md",
            REPO_ROOT / "skills/linsist-coach/references/curriculums" / "java-agent-rag" / "syllabus.md",
            REPO_ROOT / "skills/linsist-coach/references/curriculums" / "java-agent-rag" / "projects-context.md",
        ]

        for target in targets:
            self.assertTrue(target.exists(), f"Target file does not exist: {target}")
            content = target.read_text(encoding="utf-8")
            self.assertIn(rule_snippet, content, f"Rule missing from {target.relative_to(REPO_ROOT)}")
            self.assertIn(prohibition_snippet, content, f"Prohibition missing from {target.relative_to(REPO_ROOT)}")

    def test_ci_workflow_and_dev_dependencies(self):
        """Verify CI workflow, requirements-dev.txt declarations, and CI badges."""
        ci_path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        self.assertTrue(ci_path.exists(), "Missing .github/workflows/ci.yml")
        import yaml
        ci_yaml = yaml.safe_load(ci_path.read_text(encoding="utf-8"))
        self.assertIn("jobs", ci_yaml)
        self.assertIn("test", ci_yaml["jobs"])

        req_path = REPO_ROOT / "requirements-dev.txt"
        self.assertTrue(req_path.exists(), "Missing requirements-dev.txt")
        self.assertIn("pyyaml", req_path.read_text(encoding="utf-8").lower())

        readme_en = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        readme_zh = (REPO_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
        self.assertIn("actions/workflows/ci.yml/badge.svg", readme_en)
        self.assertIn("actions/workflows/ci.yml/badge.svg", readme_zh)

    def test_readme_client_installation_instructions(self):
        """Verify README contains copy-pasteable installation instructions for major Agent clients."""
        readme_en = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        readme_zh = (REPO_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

        clients = ["Claude Code", "Codex", "Cursor", "Windsurf", "OpenCodeInterpreter"]
        for client in clients:
            self.assertIn(client, readme_en, f"Missing {client} in README.md")
            self.assertIn(client, readme_zh, f"Missing {client} in README.zh-CN.md")


if __name__ == "__main__":
    unittest.main()
