#!/usr/bin/env python3
"""
Linsist 48h Spaced Retrieval Scanner (scan_retest.py)
Scans .linsist/notes/ and .linsist/mistakes/ for markdown study cards,
extracts 48h spaced retrieval retest items, checks due status against current date,
and updates .linsist/retest_dashboard.md.
"""

import os
import re
import sys
import json
import argparse
from datetime import datetime, date
from pathlib import Path


RE_HEADING_TITLE = re.compile(r"^#\s+(?:\[[\d-]+\]\s*)?(.+)$", re.MULTILINE)
RE_THEME_LINE = re.compile(r"-\s*\*\*?(?:当日核心主题|主题名称|学习主题)\*\*?[：:]\s*(.+)$", re.MULTILINE)
RE_RETEST_DATE = re.compile(r"(?:建议(?:复测)?日期|到期日)[：:]\s*`?(\d{4}-\d{2}-\d{2})`?", re.IGNORECASE)
RE_RETEST_STATUS = re.compile(r"复测状态[：:]\s*([^\s\n\r]+)")
RE_RETEST_QUESTION = re.compile(r"^\s*[-*]?\s*(?:题目|复测题)\s*[1-9一二\d]+[^：:\n\r]*[：:]\s*(.+)$", re.MULTILINE)


class RetestItem:
    def __init__(self, due_date: str, theme: str, question: str, file_path: str, status: str):
        self.due_date = due_date
        self.theme = theme
        self.question = question
        self.file_path = file_path
        self.status = status

    def to_dict(self):
        return {
            "due_date": self.due_date,
            "theme": self.theme,
            "question": self.question,
            "file_path": self.file_path,
            "status": self.status,
            "is_due": self.is_due(),
            "is_passed": self.is_passed()
        }

    def is_passed(self) -> bool:
        return any(term in self.status for term in ["已通过", "通过", "Passed", "passed"])

    def is_due(self) -> bool:
        if self.is_passed():
            return False
        try:
            d = datetime.strptime(self.due_date, "%Y-%m-%d").date()
            return d <= date.today()
        except ValueError:
            return False


def parse_note_file(file_path: Path, workspace_root: Path) -> list:
    items = []
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return []

    # 1. Extract theme/title
    theme = "未命名主题"
    theme_match = RE_THEME_LINE.search(content)
    if theme_match:
        theme = theme_match.group(1).strip()
    else:
        heading_match = RE_HEADING_TITLE.search(content)
        if heading_match:
            theme = heading_match.group(1).strip()

    # 2. Extract retest date
    date_match = RE_RETEST_DATE.search(content)
    if not date_match:
        return []
    due_date = date_match.group(1).strip()

    # 3. Extract status
    status = "待复测"
    status_match = RE_RETEST_STATUS.search(content)
    if status_match:
        status = status_match.group(1).strip()

    # 4. Extract questions
    questions = RE_RETEST_QUESTION.findall(content)
    rel_path = file_path.relative_to(workspace_root).as_posix() if workspace_root in file_path.parents or file_path == workspace_root else file_path.as_posix()

    if questions:
        for q in questions:
            q_clean = q.strip().replace("|", "\\|")
            items.append(RetestItem(due_date, theme, q_clean, rel_path, status))
    else:
        # Generic retest item
        items.append(RetestItem(due_date, theme, "机制口述与核心代码复测", rel_path, status))

    return items


def scan_workspace(workspace_root: Path) -> list:
    all_items = []
    search_dirs = [
        workspace_root / ".linsist" / "notes",
        workspace_root / ".linsist" / "mistakes",
        workspace_root / "notes",
    ]

    for s_dir in search_dirs:
        if s_dir.exists() and s_dir.is_dir():
            for md_file in s_dir.rglob("*.md"):
                if md_file.name == "retest_dashboard.md" or md_file.name == "config.md":
                    continue
                all_items.extend(parse_note_file(md_file, workspace_root))

    return all_items


def generate_dashboard_markdown(items: list) -> str:
    due_items = [it for it in items if it.is_due()]
    upcoming_items = [it for it in items if not it.is_due() and not it.is_passed()]
    passed_items = [it for it in items if it.is_passed()]

    lines = [
        "# 48h 遗忘复测看板 (Retest Dashboard)",
        "",
        "> 本看板由 Linsist 自动维护。日常学习卡片中的复测题目将登记在此。",
        f"> 最后扫描时间: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`",
        "",
        "## 🔴 待复测 / 逾期任务 (Due for Retest)",
        "| 到期日期 | 关联主题 | 核心复测题 | 原始卡片路径 | 状态 |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]

    if due_items:
        for it in sorted(due_items, key=lambda x: x.due_date):
            lines.append(f"| {it.due_date} | {it.theme} | {it.question} | `{it.file_path}` | **{it.status}** |")
    else:
        lines.append("| - | 当前无待复测任务 | 今日已达成记忆闭环 | - | 达成 |")

    lines.extend([
        "",
        "## 🟡 观察中任务 (Upcoming within 48h)",
        "| 到期日期 | 关联主题 | 核心复测题 | 原始卡片路径 | 状态 |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ])

    if upcoming_items:
        for it in sorted(upcoming_items, key=lambda x: x.due_date):
            lines.append(f"| {it.due_date} | {it.theme} | {it.question} | `{it.file_path}` | {it.status} |")
    else:
        lines.append("| - | 暂无未来 48h 到期任务 | 保持每日学习切片推进 | - | 正常 |")

    lines.extend([
        "",
        "## 🟢 已通过验收 (Passed)",
        "| 到期日期 | 关联主题 | 核心复测题 | 原始卡片路径 | 验收状态 |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ])

    if passed_items:
        for it in sorted(passed_items, key=lambda x: x.due_date, reverse=True):
            lines.append(f"| {it.due_date} | {it.theme} | {it.question} | `{it.file_path}` | {it.status} |")
    else:
        lines.append("| - | 尚无归档通过记录 | 完成复测后更新卡片状态为“已通过” | - | - |")

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Scan Linsist notes for due 48h retest items.")
    parser.add_argument("--dir", "-d", default=".", help="Workspace root directory")
    parser.add_argument("--update-dashboard", "-u", action="store_true", default=True, help="Update .linsist/retest_dashboard.md")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    root_path = Path(args.dir).resolve()
    items = scan_workspace(root_path)

    if args.json:
        data = {
            "total_items": len(items),
            "due_count": sum(1 for it in items if it.is_due()),
            "upcoming_count": sum(1 for it in items if not it.is_due() and not it.is_passed()),
            "passed_count": sum(1 for it in items if it.is_passed()),
            "items": [it.to_dict() for it in items]
        }
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    due_count = sum(1 for it in items if it.is_due())
    upcoming_count = sum(1 for it in items if not it.is_due() and not it.is_passed())
    passed_count = sum(1 for it in items if it.is_passed())

    print(f"\n=======================================================")
    print(f"       Linsist 48h Spaced Retrieval Scanner            ")
    print(f"=======================================================")
    print(f"  [+] Scanned Directory: {root_path}")
    print(f"  [*] Total Retest Tasks: {len(items)}")
    print(f"  [!] 🔴 Due / Overdue Tasks: {due_count}")
    print(f"  [*] 🟡 Upcoming (within 48h): {upcoming_count}")
    print(f"  [*] 🟢 Passed & Mastered: {passed_count}")
    print(f"-------------------------------------------------------")

    if due_count > 0:
        print("\n[!] Immediate Retest Recommended:")
        for it in items:
            if it.is_due():
                print(f"  - [{it.due_date}] {it.theme}: {it.question} ({it.file_path})")

    if args.update_dashboard:
        dashboard_file = root_path / ".linsist" / "retest_dashboard.md"
        if dashboard_file.parent.exists():
            new_content = generate_dashboard_markdown(items)
            dashboard_file.write_text(new_content, encoding="utf-8")
            print(f"\n[+] Updated dashboard: {dashboard_file.relative_to(root_path)}")

    print("\nScan completed successfully.\n")


if __name__ == "__main__":
    main()
