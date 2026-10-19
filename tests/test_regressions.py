"""Regressions using shipped cards and an isolated, installed skill suite."""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNTIME = REPO_ROOT / "skills/linsist-coach/scripts"
sys.path.insert(0, str(RUNTIME if RUNTIME.exists() else REPO_ROOT / "scripts"))
import scan_retest


def filled_card(relative_path, replacements):
    text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    card = re.search(r"```markdown\n(.*?)\n```", text, re.DOTALL).group(1)
    for before, after in replacements.items():
        card = card.replace(before, after)
    return card


class TestFullCards(unittest.TestCase):
    def parse(self, content):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            note = root / "note.md"
            note.write_text(content, encoding="utf-8")
            return scan_retest.parse_note_file(note, root)

    def test_coach_execution_pass_is_not_retest_pass(self):
        card = filled_card("skills/linsist-coach/references/records-template.md", {
            "YYYY-MM-DD": "2026-10-12",
            "第 2 轮建议复测日期 (168h)：`2026-10-12`":
                "第 2 轮建议复测日期 (168h)：`2026-10-19`",
            "已运行 (Passed) / 编译通过未运行 / 未运行 (纯推演)": "已运行 (Passed)",
            "待复测 / 第1轮已通过 / 已完全掌握": "待复测",
        })
        items = self.parse(card)
        self.assertEqual(len(items), 4, "Only two retest questions, with two stages each")
        self.assertFalse(any(item.is_passed() for item in items))
        self.assertEqual(sum(item.stage == 1 for item in items), 2)
        self.assertTrue(all("待第1轮通过" in item.status for item in items if item.stage == 2))

    def test_basics_diagnostic_status_does_not_hide_retest_pass(self):
        card = filled_card("skills/linsist-basics/references/records.md", {
            "YYYY-MM-DD": "2026-10-12",
            "独立写出 / 提示后写出 / 仅能理解思路 / 暂未掌握": "独立写出",
            "待复测 / 已通过 / 二次巩固": "已通过",
        })
        items = self.parse(card)
        self.assertEqual(len(items), 2)
        self.assertTrue(all(item.is_passed() for item in items))

    def test_only_retest_section_is_scanned(self):
        items = self.parse("""# 学习卡片
- 实际执行状态：Passed
- 任务目标：实现词频统计
- [x] 完成课前准备
- **48h 闭卷复测设计**：
  - 建议复测日期：2026-10-12
  - 题目 1：解释哈希碰撞
  - 复测状态：待复测
- **下次启动第一步**：
  1. 打开 IDE
  - [ ] 准备环境
""")
        self.assertEqual([item.question for item in items], ["解释哈希碰撞"])
        self.assertFalse(items[0].is_passed())

    def test_os_and_testlab_full_templates(self):
        for skill in ("linsist-os", "linsist-testlab"):
            for status in ("待复测", "已通过"):
                with self.subTest(skill=skill, status=status):
                    card = filled_card(f"skills/{skill}/references/records.md", {
                        "YYYY-MM-DD": "2000-01-01",
                        "待复测 / 已通过 / 二次强化": status,
                    })
                    items = self.parse(card)
                    self.assertEqual(len(items), 2)
                    self.assertTrue(all(item.is_passed() == (status == "已通过") for item in items))

    def test_per_question_status_and_code_examples(self):
        items = self.parse("""# 复测
- 48h / 168h 间隔复测题：
  - 第1轮复测日期：2000-01-01
  - 第2轮复测日期：2000-01-08
  - 题目 1：解释哈希碰撞 [第1轮已通过]
  - 题目 2：手写词频统计 [未通过]
  - 复测状态：待复测
  ```text
  - 题目 3：这里仅是格式示例
  - 复测状态：已完全掌握
  ```
""")
        self.assertEqual(len(items), 4)
        first = [item for item in items if item.question == "解释哈希碰撞"]
        second = [item for item in items if item.question == "手写词频统计"]
        self.assertEqual(sum(item.is_passed() for item in first), 1)
        self.assertFalse(any(item.is_passed() for item in second))
        self.assertFalse(any(item.is_due() for item in second if item.stage == 2))

    def test_explicit_stage_two_item_does_not_create_stage_one(self):
        items = self.parse("""# 复测卡
- 复测日期：2026-10-12
- 第2轮复测日期：2026-10-19
- 复测轮次：第2轮
- 题目 1：解释缓存失效
- 复测状态：待复测
""")
        self.assertEqual(len(items), 1)
        self.assertEqual((items[0].stage, items[0].due_date), (2, "2026-10-19"))


class TestInstalledSuite(unittest.TestCase):
    def run_cli(self, *args, cwd=None, check=True):
        return subprocess.run([sys.executable, *map(str, args)], cwd=cwd,
                              capture_output=True, text=True, check=check)

    def test_install_and_external_workspace_lifecycle(self):
        with tempfile.TemporaryDirectory(prefix="linsist install ") as temp:
            root = Path(temp)
            dest = root / "client/skills"
            workspace = root / "project"
            workspace.mkdir()
            self.run_cli(REPO_ROOT / "scripts/install.py", "--dest", dest, cwd=workspace)
            self.run_cli(REPO_ROOT / "scripts/install.py", "--dest", dest, "--check")
            self.assertEqual(len(list(dest.glob("*/SKILL.md"))), 5)
            coach = dest / "linsist-coach"
            for md in dest.rglob("*.md"):
                for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", md.read_text(encoding="utf-8")):
                    if not target.startswith(("https:", "http:", "#")):
                        self.assertTrue((md.parent / target.split("#")[0]).exists(), (md, target))

            initializer = coach / "scripts/init_workspace.py"
            scanner = coach / "scripts/scan_retest.py"
            self.run_cli(initializer, "--dir", workspace, cwd=workspace)
            profile = workspace / ".linsist/learner-profile.md"
            self.assertIn("学习者背景配置模板", profile.read_text(encoding="utf-8"))
            profile.write_text("My profile", encoding="utf-8")
            self.run_cli(initializer, "--dir", workspace, cwd=workspace)
            self.assertEqual(profile.read_text(encoding="utf-8"), "My profile")

            note = workspace / ".linsist/notes/card.md"
            note.write_text("""# 安装验收
- 48h / 168h 间隔复测题：
  - 第1轮复测日期：2000-01-01
  - 第2轮复测日期：2000-01-08
  - 题目 1：解释哈希碰撞
  - 复测状态：待复测
""", encoding="utf-8")
            result = self.run_cli(scanner, "--dir", workspace, "--json", cwd=workspace)
            data = json.loads(result.stdout)
            self.assertEqual((data["due_count"], data["passed_count"]), (1, 0))
            without_site_packages = self.run_cli("-S", scanner, "--dir", workspace, "--json")
            self.assertEqual(json.loads(without_site_packages.stdout), data)
            dashboard = workspace / ".linsist/retest_dashboard.md"
            self.assertIn("解释哈希碰撞", dashboard.read_text(encoding="utf-8"))
            before = dashboard.read_bytes()
            self.run_cli(scanner, "--dir", workspace, "--json", "--no-dashboard")
            self.assertEqual(before, dashboard.read_bytes())

            note.write_text(note.read_text(encoding="utf-8").replace("待复测", "第1轮已通过"), encoding="utf-8")
            data = json.loads(self.run_cli(scanner, "--dir", workspace, "--json").stdout)
            self.assertEqual((data["stage2_due_count"], data["passed_count"]), (1, 1))
            self.run_cli(scanner, "--dir", workspace, "--stage", "2")
            self.assertIn("已通过 (第1轮 48h)", dashboard.read_text(encoding="utf-8"))
            note.write_text(note.read_text(encoding="utf-8").replace("第1轮已通过", "已完全掌握"), encoding="utf-8")
            data = json.loads(self.run_cli(scanner, "--dir", workspace, "--json").stdout)
            self.assertEqual((data["due_count"], data["passed_count"]), (0, 1))

            sentinel = coach / "local.txt"
            sentinel.write_text("preserve", encoding="utf-8")
            retry = self.run_cli(REPO_ROOT / "scripts/install.py", "--dest", dest, check=False)
            self.assertNotEqual(retry.returncode, 0)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve")

            self.run_cli(REPO_ROOT / "scripts/install.py", "--dest", dest, "--update")
            self.run_cli(REPO_ROOT / "scripts/install.py", "--dest", dest, "--check")
            self.assertFalse(sentinel.exists())

    def test_invalid_package_cannot_replace_existing_install(self):
        import shutil
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dest = root / "installed"
            self.run_cli(REPO_ROOT / "scripts/install.py", "--dest", dest)
            sentinel = dest / "linsist-coach/local.txt"
            sentinel.write_text("preserve", encoding="utf-8")
            source = root / "source"
            shutil.copytree(REPO_ROOT / "skills", source / "skills")
            (source / "scripts").mkdir()
            shutil.copy2(REPO_ROOT / "scripts/install.py", source / "scripts/install.py")
            (source / "skills/linsist-coach/references/curriculums/java-agent-rag/syllabus.md").unlink()
            result = self.run_cli(source / "scripts/install.py", "--dest", dest, "--update", check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve")
            self.run_cli(REPO_ROOT / "scripts/install.py", "--dest", dest, "--check")

    @unittest.skipIf(sys.platform == "win32", "Directory symlinks require optional Windows privileges")
    def test_checkout_inside_skill_root_uses_canonical_links(self):
        import shutil
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "client/skills"
            checkout = dest / "Linsist"
            shutil.copytree(REPO_ROOT / "skills", checkout / "skills")
            (checkout / "scripts").mkdir()
            shutil.copy2(REPO_ROOT / "scripts/install.py", checkout / "scripts/install.py")
            installer = checkout / "scripts/install.py"
            self.run_cli(installer, "--dest", dest)
            self.run_cli(installer, "--dest", dest, "--update")
            self.run_cli(installer, "--dest", dest, "--check")
            for source in (checkout / "skills").iterdir():
                target = dest / source.name
                self.assertTrue(target.is_symlink())
                self.assertEqual(target.resolve(), source.resolve())
                self.assertTrue((source / "SKILL.md").is_file())
            unsafe = self.run_cli(installer, "--dest", checkout / "skills", "--update", check=False)
            self.assertNotEqual(unsafe.returncode, 0)
            self.assertTrue((checkout / "skills/linsist-coach/SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
