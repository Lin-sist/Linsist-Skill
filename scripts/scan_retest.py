#!/usr/bin/env python3
"""
Linsist 48h / 168h Spaced Retrieval Scanner (scan_retest.py)
Scans .linsist/notes/ and .linsist/mistakes/ for markdown study cards,
extracts 2-stage spaced retrieval retest items (Stage 1: 48h initial retest,
Stage 2: 168h / 7-day consolidation retest), checks due status against current date,
and updates .linsist/retest_dashboard.md.
"""

import os
import re
import sys
import json
import argparse
from datetime import datetime, date, timedelta
from pathlib import Path


RE_HEADING_TITLE = re.compile(r"^#\s+(?:\[[\d\-/.]+\]\s*)?(.+)$", re.MULTILINE)
RE_THEME_LINE = re.compile(r"-\s*\*{0,2}(?:当日核心主题|核心主题|学习主题|主题名称|主题)\*{0,2}[：:]\s*(.+)$", re.MULTILINE)
RE_RETEST_DATE = re.compile(
    r"(?:\*{0,2}(?:第\s*[1一]\s*轮(?:\s*[(（]48h[)）])?\s*(?:建议)?(?:复测)?日期|第\s*[1一]\s*轮\s*(?:建议)?(?:复测)?日期(?:\s*[(（]48h[)）])?|首轮(?:\s*[(（]48h[)）])?\s*(?:建议)?(?:复测)?日期|48h\s*(?:\s*[(（](?:首轮|初测)[)）])?\s*(?:建议)?(?:复测)?日期|建议(?:复测)?日期(?:\s*[(（]48h[)）])?|复测日期(?:\s*[(（]48h[)）])?|到期日期|到期日)\*{0,2})\s*[：:]\s*`?([0-9]{2,4}[-/.年][0-9]{1,2}[-/.月][0-9]{1,2}日?)`?",
    re.IGNORECASE
)
RE_TIER2_DATE = re.compile(
    r"(?:\*{0,2}(?:第\s*[2二两]\s*轮(?:\s*[(（]168h[)）])?\s*(?:建议)?(?:复测)?日期|第\s*[2二两]\s*轮\s*(?:建议)?(?:复测)?日期(?:\s*[(（]168h[)）])?|二轮(?:\s*[(（]168h[)）])?\s*(?:建议)?(?:复测)?日期|168h\s*(?:\s*[(（](?:二轮|巩固)[)）])?\s*(?:建议)?(?:复测)?日期|巩固(?:\s*[(（]168h[)）])?\s*(?:建议)?(?:复测)?日期)\*{0,2})\s*[：:]\s*`?([0-9]{2,4}[-/.年][0-9]{1,2}[-/.月][0-9]{1,2}日?)`?",
    re.IGNORECASE
)
RE_INLINE_DATE = re.compile(
    r"[(（](?:到期日|第\s*[12一二两]\s*轮(?:到期日|日期)?|建议(?:复测)?日期|复测日期|到期日期)[：:]\s*`?([0-9]{2,4}[-/.年][0-9]{1,2}[-/.月][0-9]{1,2}日?)`?[)）]",
    re.IGNORECASE
)
RE_RETEST_STATUS = re.compile(r"(?:\*{0,2}(?:复测状态|验收状态|状态)\*{0,2})\s*[：:]\s*([^|\n\r]+)", re.IGNORECASE)
RE_INLINE_STATUS = re.compile(
    r"[\[(（【](已通过|通过|待复测|未通过|不通过|待强化|二次强化|二次巩固|重测|Passed|passed|Failed|failed|已通过\s*第\s*[12一二两]\s*轮|第\s*[12一二两]\s*轮\s*已通过|第\s*[12一二两]\s*轮\s*通过|通过\s*[(（]\s*(?:48h|168h|首轮|二轮)\s*[)）]|已通过\s*[(（]\s*(?:48h|168h|首轮|二轮)\s*[)）]|已完全掌握|完全掌握|全部通过)[\])）】]",
    re.IGNORECASE
)
RE_STAGE_INDICATOR = re.compile(
    r"(?:\*{0,2}(?:复测轮次|轮次|阶段|Stage|Tier)\*{0,2})\s*[：:]\s*(?:第?\s*([12一二两])\s*轮?|Tier\s*([12])|Stage\s*([12]))",
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


def load_config(workspace_root: Path) -> dict:
    """Load configuration from .linsist/config.md if available."""
    config = {
        "interval_hours_tier1": 48,
        "interval_hours_tier2": 168,
        "max_retest_per_session": 2,
        "auto_scan_on_startup": True,
        "storage_mode": "local_workspace",
        "notes_dir": ".linsist/notes",
        "mistakes_dir": ".linsist/mistakes",
        "retest_dashboard": ".linsist/retest_dashboard.md"
    }
    cfg_file = workspace_root / ".linsist" / "config.md"
    if not cfg_file.exists():
        return config

    try:
        content = cfg_file.read_text(encoding="utf-8")
        try:
            import yaml
            yaml_content = content
            if "```yaml" in content:
                yaml_content = content.split("```yaml", 1)[1].split("```", 1)[0]
            elif "```" in content:
                yaml_content = content.split("```", 1)[1].split("```", 1)[0]
            data = yaml.safe_load(yaml_content)
            if isinstance(data, dict):
                sr = data.get("spaced_retrieval", {})
                if isinstance(sr, dict):
                    if "interval_hours_tier1" in sr:
                        config["interval_hours_tier1"] = int(sr["interval_hours_tier1"])
                    if "interval_hours_tier2" in sr:
                        config["interval_hours_tier2"] = int(sr["interval_hours_tier2"])
                    if "max_retest_per_session" in sr:
                        config["max_retest_per_session"] = int(sr["max_retest_per_session"])
                    if "auto_scan_on_startup" in sr:
                        config["auto_scan_on_startup"] = bool(sr["auto_scan_on_startup"])
                st = data.get("storage", {})
                if isinstance(st, dict):
                    for k in ("storage_mode", "notes_dir", "mistakes_dir", "retest_dashboard"):
                        if k in st:
                            config[k] = str(st[k])
                return config
        except Exception:
            pass

        for line in content.splitlines():
            line = line.strip()
            if line.startswith("interval_hours_tier1:"):
                config["interval_hours_tier1"] = int(line.split(":", 1)[1].strip())
            elif line.startswith("interval_hours_tier2:"):
                config["interval_hours_tier2"] = int(line.split(":", 1)[1].strip())
            elif line.startswith("max_retest_per_session:"):
                config["max_retest_per_session"] = int(line.split(":", 1)[1].strip())
            elif line.startswith("notes_dir:"):
                config["notes_dir"] = line.split(":", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("mistakes_dir:"):
                config["mistakes_dir"] = line.split(":", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("retest_dashboard:"):
                config["retest_dashboard"] = line.split(":", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass

    return config


class RetestItem:
    def __init__(self, due_date: str, theme: str, question: str, file_path: str, status: str, stage: int = 1):
        self.due_date = due_date
        self.theme = theme
        self.question = question
        self.file_path = file_path
        self.status = status
        self.stage = stage

    def to_dict(self):
        return {
            "due_date": self.due_date,
            "theme": self.theme,
            "question": self.question,
            "file_path": self.file_path,
            "status": self.status,
            "stage": self.stage,
            "is_due": self.is_due(),
            "is_passed": self.is_passed()
        }

    def is_passed(self) -> bool:
        status_clean = self.status.strip().lower()
        negatives = ["未通过", "不通过", "未完成", "待复测", "待强化", "二次强化", "二次巩固", "重测", "failed"]
        if any(neg in status_clean for neg in negatives):
            return False
        if re.search(r"待\s*(?:第\s*[2二两]\s*轮|二轮|168h)", status_clean):
            return False
        positives = ["已通过", "通过", "已完成", "passed", "mastered", "完全掌握"]
        return any(pos in status_clean for pos in positives)

    def is_due(self) -> bool:
        if self.is_passed():
            return False
        if re.search(r"待\s*(?:第\s*[1一]\s*轮|首轮)\s*通过", self.status):
            return False
        try:
            d = datetime.strptime(self.due_date, "%Y-%m-%d").date()
            return d <= date.today()
        except ValueError:
            return False


def _parse_stage_num(val_str: str) -> int:
    if not val_str:
        return 1
    val_clean = val_str.strip().lower()
    if "2" in val_clean or "二" in val_clean or "两" in val_clean:
        return 2
    return 1


def parse_note_file(file_path: Path, workspace_root: Path, config: dict = None) -> list:
    items = []
    if config is None:
        config = {"interval_hours_tier1": 48, "interval_hours_tier2": 168}

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

    # 2. Extract note-level retest dates (Stage 1 and Stage 2)
    tier1_match = RE_RETEST_DATE.search(content)
    global_due_date = normalize_date(tier1_match.group(1).strip()) if tier1_match else ""

    tier2_match = RE_TIER2_DATE.search(content)
    global_tier2_date = normalize_date(tier2_match.group(1).strip()) if tier2_match else ""

    # Note-level stage indicator
    global_stage = 1
    stage_m = RE_STAGE_INDICATOR.search(content)
    if stage_m:
        val = next(v for v in stage_m.groups() if v is not None)
        global_stage = _parse_stage_num(val)

    # 3. Extract note-level status
    global_status = "待复测"
    status_match = RE_RETEST_STATUS.search(content)
    if status_match:
        global_status = status_match.group(1).strip()
        global_status = re.sub(r'^[<*`]+|[>*`]+$', '', global_status).strip()

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

    def append_retest_entries(q_clean: str, item_date: str, tier2_date: str, item_status: str, item_stage: int):
        status_clean = item_status.strip()

        # Check if status indicates Stage 1 passed, triggering Stage 2 scheduling
        is_stage1_passed = bool(re.search(
            r"(?:已通过\s*第\s*[1一]\s*轮|通过\s*第\s*[1一]\s*轮|第\s*[1一]\s*轮\s*已通过|第\s*[1一]\s*轮\s*通过|通过\s*[(（]\s*(?:首轮|48h)\s*[)）]|已通过\s*[(（]\s*(?:首轮|48h)\s*[)）]|48h\s*已通过|48h\s*通过|待\s*第\s*[2二两]\s*轮(?:复测)?|待\s*二轮(?:复测)?|待\s*168h(?:复测)?)",
            status_clean,
            re.IGNORECASE
        ))

        # Check if status indicates Stage 2 passed / fully mastered
        is_stage2_passed = bool(re.search(
            r"(?:已通过\s*第\s*[2二两]\s*轮|通过\s*第\s*[2二两]\s*轮|第\s*[2二两]\s*轮\s*已通过|第\s*[2二两]\s*轮\s*通过|二轮\s*已通过|二轮\s*通过|通过\s*[(（]\s*(?:二轮|168h|巩固)\s*[)）]|已通过\s*[(（]\s*(?:二轮|168h|巩固)\s*[)）]|168h\s*已通过|168h\s*通过|已完全掌握|完全掌握|全部通过|双轮(?:已)?通过)",
            status_clean,
            re.IGNORECASE
        ))

        # If both dates exist and status is general passed (e.g. 已通过), treat as Stage 1 passed
        general_passed = RetestItem("", "", "", "", status_clean).is_passed()
        if not is_stage1_passed and not is_stage2_passed and general_passed and tier2_date and item_date and tier2_date != item_date:
            is_stage1_passed = True

        if is_stage1_passed:
            # Stage 1 passed record
            if item_date:
                items.append(RetestItem(item_date, theme, q_clean, rel_path, "已通过 (第1轮 48h)", stage=1))

            # Stage 2 scheduled record
            s2_date = tier2_date
            if not s2_date and item_date:
                try:
                    d1 = datetime.strptime(item_date, "%Y-%m-%d").date()
                    interval_days = config.get("interval_hours_tier2", 168) // 24
                    s2_date = (d1 + timedelta(days=interval_days)).strftime("%Y-%m-%d")
                except ValueError:
                    s2_date = item_date
            if s2_date:
                items.append(RetestItem(s2_date, theme, q_clean, rel_path, "待第2轮复测 (168h)", stage=2))

        elif is_stage2_passed:
            target_date = tier2_date or item_date
            if target_date:
                items.append(RetestItem(target_date, theme, q_clean, rel_path, "已通过 (第2轮 168h)", stage=2))

        elif tier2_date and item_date and item_date != tier2_date:
            # Both explicit Stage 1 and Stage 2 dates present
            items.append(RetestItem(item_date, theme, q_clean, rel_path, item_status, stage=1))
            items.append(RetestItem(tier2_date, theme, q_clean, rel_path, "待第2轮复测 (待第1轮通过)", stage=2))

        else:
            # Single stage entry
            target_date = item_date or tier2_date
            if target_date:
                items.append(RetestItem(target_date, theme, q_clean, rel_path, item_status, stage=item_stage))

    if raw_questions:
        for q_entry in raw_questions:
            q_raw = q_entry["text"]
            item_status = q_entry["status_override"] or global_status
            item_date = global_due_date
            item_tier2_date = global_tier2_date
            item_stage = global_stage

            # Inline stage detection
            if any(s2_tag in q_raw for s2_tag in ["第2轮", "168h", "二轮", "Stage 2", "stage 2", "Tier 2", "tier 2"]):
                item_stage = 2
            elif any(s1_tag in q_raw for s1_tag in ["第1轮", "48h", "首轮", "Stage 1", "stage 1", "Tier 1", "tier 1"]):
                item_stage = 1

            # Check for inline date
            inline_date_m = RE_INLINE_DATE.search(q_raw)
            if inline_date_m:
                matched_d = normalize_date(inline_date_m.group(1).strip())
                if item_stage == 2:
                    item_tier2_date = matched_d
                else:
                    item_date = matched_d
                q_raw = RE_INLINE_DATE.sub("", q_raw).strip()

            # Check for inline status
            inline_status_m = RE_INLINE_STATUS.search(q_raw)
            if inline_status_m and not q_entry["status_override"]:
                item_status = inline_status_m.group(1).strip()
                q_raw = RE_INLINE_STATUS.sub("", q_raw).strip()

            # Clean formatting
            q_clean = q_raw.strip().replace("|", "\\|")
            q_clean = re.sub(r'^[<*`]+|[>*`]+$', '', q_clean).strip()

            append_retest_entries(q_clean, item_date, item_tier2_date, item_status, item_stage)
    else:
        if global_due_date or global_tier2_date:
            append_retest_entries("机制口述与核心代码复测", global_due_date, global_tier2_date, global_status, global_stage)

    return items


def scan_workspace(workspace_root: Path) -> list:
    all_items = []
    seen_files = set()
    config = load_config(workspace_root)

    search_dirs = [
        workspace_root / ".linsist" / "notes",
        workspace_root / ".linsist" / "mistakes",
        workspace_root / "notes",
    ]

    custom_notes = config.get("notes_dir")
    if custom_notes:
        search_dirs.append(workspace_root / custom_notes)
    custom_mistakes = config.get("mistakes_dir")
    if custom_mistakes:
        search_dirs.append(workspace_root / custom_mistakes)

    for s_dir in search_dirs:
        if s_dir.exists() and s_dir.is_dir():
            for md_file in s_dir.rglob("*.md"):
                resolved_path = md_file.resolve()
                if resolved_path in seen_files:
                    continue
                seen_files.add(resolved_path)
                if md_file.name in ("retest_dashboard.md", "config.md", ".gitkeep"):
                    continue
                all_items.extend(parse_note_file(md_file, workspace_root, config))

    return all_items


def generate_dashboard_markdown(items: list) -> str:
    due_items = [it for it in items if it.is_due()]
    upcoming_items = [it for it in items if not it.is_due() and not it.is_passed()]
    passed_items = [it for it in items if it.is_passed()]

    lines = [
        "# 48h / 168h 双轮遗忘复测看板 (Retest Dashboard)",
        "",
        "> 本看板由 Linsist 自动维护。日常学习卡片中的 48h 初测与 168h 巩固复测题目将登记在此。",
        f"> 最后扫描时间: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`",
        "",
        "## 🔴 待复测 / 逾期任务 (Due for Retest)",
        "| 到期日期 | 关联主题 | 核心复测题 | 原始卡片路径 | 状态 |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]

    if due_items:
        for it in sorted(due_items, key=lambda x: (x.due_date, x.stage)):
            stage_str = f" [第{it.stage}轮]" if it.stage and f"{it.stage}轮" not in it.status and f"{it.stage}轮" not in it.question else ""
            lines.append(f"| {it.due_date} | {it.theme} | {it.question}{stage_str} | `{it.file_path}` | **{it.status}** |")
    else:
        lines.append("| - | 当前无待复测任务 | 今日已达成记忆闭环 | - | 达成 |")

    lines.extend([
        "",
        "## 🟡 观察中任务 (Upcoming / 待到期)",
        "| 到期日期 | 关联主题 | 核心复测题 | 原始卡片路径 | 状态 |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ])

    if upcoming_items:
        for it in sorted(upcoming_items, key=lambda x: (x.due_date, x.stage)):
            stage_str = f" [第{it.stage}轮]" if it.stage and f"{it.stage}轮" not in it.status and f"{it.stage}轮" not in it.question else ""
            lines.append(f"| {it.due_date} | {it.theme} | {it.question}{stage_str} | `{it.file_path}` | {it.status} |")
    else:
        lines.append("| - | 暂无待到期任务 | 保持每日学习切片推进 | - | 正常 |")

    lines.extend([
        "",
        "## 🟢 已通过验收 (Passed)",
        "| 到期日期 | 关联主题 | 核心复测题 | 原始卡片路径 | 验收状态 |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ])

    if passed_items:
        for it in sorted(passed_items, key=lambda x: (x.due_date, x.stage), reverse=True):
            stage_str = f" [第{it.stage}轮]" if it.stage and f"{it.stage}轮" not in it.status and f"{it.stage}轮" not in it.question else ""
            lines.append(f"| {it.due_date} | {it.theme} | {it.question}{stage_str} | `{it.file_path}` | {it.status} |")
    else:
        lines.append("| - | 尚无归档通过记录 | 完成复测后更新卡片状态为“已通过” | - | - |")

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Scan Linsist notes for due 48h / 168h retest items.")
    parser.add_argument("--dir", "-d", default=".", help="Workspace root directory")
    parser.add_argument(
        "--no-dashboard", "--no-update",
        dest="update_dashboard",
        action="store_false",
        default=True,
        help="Do not write updates to .linsist/retest_dashboard.md (dry-run)"
    )
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--stage", type=int, choices=[1, 2], help="Filter retests by stage (1: 48h initial, 2: 168h consolidation)")
    parser.add_argument("--max-retest", type=int, default=None, help="Maximum number of active retests to recommend per session")
    args = parser.parse_args()

    root_path = Path(args.dir).resolve()
    config = load_config(root_path)
    items = scan_workspace(root_path)

    if args.stage:
        items = [it for it in items if it.stage == args.stage]

    max_retest = args.max_retest if args.max_retest is not None else config.get("max_retest_per_session", 2)

    if args.json:
        data = {
            "total_items": len(items),
            "due_count": sum(1 for it in items if it.is_due()),
            "upcoming_count": sum(1 for it in items if not it.is_due() and not it.is_passed()),
            "passed_count": sum(1 for it in items if it.is_passed()),
            "stage1_due_count": sum(1 for it in items if it.is_due() and it.stage == 1),
            "stage2_due_count": sum(1 for it in items if it.is_due() and it.stage == 2),
            "config": {
                "interval_hours_tier1": config.get("interval_hours_tier1", 48),
                "interval_hours_tier2": config.get("interval_hours_tier2", 168),
                "max_retest_per_session": max_retest
            },
            "items": [it.to_dict() for it in items]
        }
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    due_count = sum(1 for it in items if it.is_due())
    stage1_due = sum(1 for it in items if it.is_due() and it.stage == 1)
    stage2_due = sum(1 for it in items if it.is_due() and it.stage == 2)
    upcoming_count = sum(1 for it in items if not it.is_due() and not it.is_passed())
    passed_count = sum(1 for it in items if it.is_passed())

    print(f"\n=======================================================")
    print(f"       Linsist 48h / 168h Spaced Retrieval Scanner     ")
    print(f"=======================================================")
    print(f"  [+] Scanned Directory: {root_path}")
    print(f"  [*] Total Retest Tasks: {len(items)}")
    print(f"  [!] 🔴 Due / Overdue Tasks: {due_count} (Stage 1 [48h]: {stage1_due}, Stage 2 [168h]: {stage2_due})")
    print(f"  [*] 🟡 Upcoming Tasks: {upcoming_count}")
    print(f"  [*] 🟢 Passed & Mastered: {passed_count}")
    print(f"  [*] Session Retrieval Limit: {max_retest} tasks")
    print(f"-------------------------------------------------------")

    if due_count > 0:
        print(f"\n[!] Recommended Retest for This Session (Top {min(due_count, max_retest)}):")
        due_sorted = sorted([it for it in items if it.is_due()], key=lambda x: (x.stage, x.due_date))
        for it in due_sorted[:max_retest]:
            stage_label = f"Stage {it.stage} ({'48h' if it.stage == 1 else '168h'})"
            print(f"  - [{it.due_date}] [{stage_label}] {it.theme}: {it.question} ({it.file_path})")
        if len(due_sorted) > max_retest:
            print(f"  ... and {len(due_sorted) - max_retest} more tasks scheduled for subsequent session.")

    if args.update_dashboard:
        dashboard_rel = config.get("retest_dashboard", ".linsist/retest_dashboard.md")
        dashboard_file = root_path / dashboard_rel
        dashboard_file.parent.mkdir(parents=True, exist_ok=True)
        new_content = generate_dashboard_markdown(items)
        dashboard_file.write_text(new_content, encoding="utf-8")
        rel_dash = dashboard_file.relative_to(root_path) if root_path in dashboard_file.parents else dashboard_file
        print(f"\n[+] Updated dashboard: {rel_dash}")

    print("\nScan completed successfully.\n")


if __name__ == "__main__":
    main()
