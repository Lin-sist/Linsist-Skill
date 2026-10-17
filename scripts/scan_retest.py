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


RE_HEADING_TITLE = re.compile(r"^#\s+(?:\[[\d\-/.]+\]\s*)?(.+)$", re.MULTILINE)
RE_THEME_LINE = re.compile(r"-\s*\*{0,2}(?:当日核心主题|核心主题|学习主题|主题名称|主题)\*{0,2}[：:]\s*(.+)$", re.MULTILINE)
RE_RETEST_DATE = re.compile(
    r"(?:\*{0,2}(?:建议(?:复测)?日期|复测日期|到期日期|到期日)\*{0,2})\s*[：:]\s*`?([0-9]{2,4}[-/.年][0-9]{1,2}[-/.月][0-9]{1,2}日?)`?",
    re.IGNORECASE
)
RE_INLINE_DATE = re.compile(
    r"[(（](?:到期日|建议(?:复测)?日期|复测日期|到期日期)[：:]\s*`?([0-9]{2,4}[-/.年][0-9]{1,2}[-/.月][0-9]{1,2}日?)`?[)）]",
    re.IGNORECASE
)
RE_RETEST_STATUS = re.compile(r"(?:\*{0,2}(?:复测状态|验收状态|状态)\*{0,2})\s*[：:]\s*([^\s\n\r|]+)", re.IGNORECASE)
RE_INLINE_STATUS = re.compile(
    r"[\[(（【](已通过|通过|待复测|未通过|不通过|待强化|二次强化|二次巩固|重测|Passed|passed|Failed|failed)[\])）】]",
    re.IGNORECASE
)
RE_RETEST_QUESTION = re.compile(
    r"^\s*[-*]?\s*(?:\d+\.|\([0-9一二两\d]\))?\s*(?:\*{0,2}(?:复测题目|复测题|题目|问题|任务)\s*[1-9一二两\d]*\*{0,2}[^：:\n\r]*[：:]|\d+\.)\s*(.+)$",
    re.MULTILINE
)
RE_TASK_CHECKBOX = re.compile(r"^\s*[-*]\s*\[([ xX])\]\s*(.+)$", re.MULTILINE)


def normalize_date(date_str: str) -> str:
    """Normalize various date formats (YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD, YYYY年MM月DD日) to YYYY-MM-DD."""
    if not date_str:
        return ""
    clean_str = date_str.replace('.', '-').replace('/', '-').replace('`', '').strip()
    m = re.search(r'(\d{2,4})[-年](\d{1,2})[-月](\d{1,2})日?', clean_str)
    if m:
        y, mo, d = m.groups()
        if len(y) == 2:
            y = "20" + y
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
    return clean_str


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
        status_clean = self.status.strip().lower()
        negatives = ["未通过", "不通过", "未完成", "待复测", "待强化", "二次强化", "二次巩固", "重测", "failed"]
        if any(neg in status_clean for neg in negatives):
            return False
        positives = ["已通过", "通过", "已完成", "passed", "mastered"]
        return any(pos in status_clean for pos in positives)

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
    except Exception:
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

    theme = re.sub(r'^[<*`]+|[>*`]+$', '', theme).strip()

    # 2. Extract note-level retest date
    date_match = RE_RETEST_DATE.search(content)
    global_due_date = normalize_date(date_match.group(1).strip()) if date_match else ""

    # 3. Extract note-level status
    global_status = "待复测"
    status_match = RE_RETEST_STATUS.search(content)
    if status_match:
        global_status = status_match.group(1).strip()

    rel_path = file_path.relative_to(workspace_root).as_posix() if workspace_root in file_path.parents or file_path == workspace_root else file_path.as_posix()

    # 4. Extract questions - task checkboxes, explicit questions, or numbered lists
    raw_questions = []

    # Check task checkboxes
    checkboxes = RE_TASK_CHECKBOX.findall(content)
    if checkboxes:
        for state, q_text in checkboxes:
            raw_questions.append({
                "text": q_text.strip(),
                "status_override": "已通过" if state.lower() == "x" else "待复测"
            })

    # Check question lines
    found_questions = RE_RETEST_QUESTION.findall(content)
    for q_text in found_questions:
        q_strip = q_text.strip()
        if not any(q_strip in q["text"] or q["text"] in q_strip for q in raw_questions):
            raw_questions.append({"text": q_strip, "status_override": None})

    if raw_questions:
        for q_entry in raw_questions:
            q_raw = q_entry["text"]
            item_status = q_entry["status_override"] or global_status
            item_date = global_due_date

            # Check for inline date
            inline_date_m = RE_INLINE_DATE.search(q_raw)
            if inline_date_m:
                item_date = normalize_date(inline_date_m.group(1).strip())
                q_raw = RE_INLINE_DATE.sub("", q_raw).strip()

            # Check for inline status
            inline_status_m = RE_INLINE_STATUS.search(q_raw)
            if inline_status_m and not q_entry["status_override"]:
                item_status = inline_status_m.group(1).strip()
                q_raw = RE_INLINE_STATUS.sub("", q_raw).strip()

            # Clean formatting
            q_clean = q_raw.strip().replace("|", "\\|")
            q_clean = re.sub(r'^[<*`]+|[>*`]+$', '', q_clean).strip()

            if item_date:
                items.append(RetestItem(item_date, theme, q_clean, rel_path, item_status))
    else:
        if global_due_date:
            items.append(RetestItem(global_due_date, theme, "机制口述与核心代码复测", rel_path, global_status))

    return items


def scan_workspace(workspace_root: Path) -> list:
    all_items = []
    seen_files = set()

    search_dirs = [
        workspace_root / ".linsist" / "notes",
        workspace_root / ".linsist" / "mistakes",
        workspace_root / "notes",
    ]

    # Check if .linsist/config.md exists and has custom notes_dir/mistakes_dir
    config_file = workspace_root / ".linsist" / "config.md"
    if config_file.exists():
        try:
            cfg_text = config_file.read_text(encoding="utf-8")
            for line in cfg_text.splitlines():
                if "notes_dir:" in line:
                    custom_notes = line.split(":", 1)[1].strip().strip('"').strip("'")
                    search_dirs.append(workspace_root / custom_notes)
                elif "mistakes_dir:" in line:
                    custom_mistakes = line.split(":", 1)[1].strip().strip('"').strip("'")
                    search_dirs.append(workspace_root / custom_mistakes)
        except Exception:
            pass

    for s_dir in search_dirs:
        if s_dir.exists() and s_dir.is_dir():
            for md_file in s_dir.rglob("*.md"):
                resolved_path = md_file.resolve()
                if resolved_path in seen_files:
                    continue
                seen_files.add(resolved_path)
                if md_file.name in ("retest_dashboard.md", "config.md", ".gitkeep"):
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
    parser.add_argument(
        "--no-dashboard", "--no-update",
        dest="update_dashboard",
        action="store_false",
        default=True,
        help="Do not write updates to .linsist/retest_dashboard.md (dry-run)"
    )
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
        # Support custom dashboard path from config.md if present
        config_file = root_path / ".linsist" / "config.md"
        if config_file.exists():
            try:
                for line in config_file.read_text(encoding="utf-8").splitlines():
                    if "retest_dashboard:" in line:
                        custom_dash = line.split(":", 1)[1].strip().strip('"').strip("'")
                        dashboard_file = root_path / custom_dash
            except Exception:
                pass

        dashboard_file.parent.mkdir(parents=True, exist_ok=True)
        new_content = generate_dashboard_markdown(items)
        dashboard_file.write_text(new_content, encoding="utf-8")
        rel_dash = dashboard_file.relative_to(root_path) if root_path in dashboard_file.parents else dashboard_file
        print(f"\n[+] Updated dashboard: {rel_dash}")

    print("\nScan completed successfully.\n")


if __name__ == "__main__":
    main()
