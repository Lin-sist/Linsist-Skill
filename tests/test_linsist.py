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
sys.path.insert(0, str(REPO_ROOT / "scripts"))

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
            self.assertFalse(manifest["policy"]["allow_implicit_invocation"])


if __name__ == "__main__":
    unittest.main()
