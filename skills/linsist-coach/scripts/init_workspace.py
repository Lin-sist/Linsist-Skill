#!/usr/bin/env python3
"""
Linsist Workspace Initializer
Initializes a local .linsist/ directory for notes, learner profile, mistakes, and 48h spaced retrieval dashboard.
"""

import sys
import argparse
from pathlib import Path


DEFAULT_CONFIG_CONTENT = """# Linsist Local Workspace Configuration

```yaml
linsist_version: "1.0.0"

storage:
  storage_mode: "local_workspace"
  notes_dir: ".linsist/notes"
  mistakes_dir: ".linsist/mistakes"
  retest_dashboard: ".linsist/retest_dashboard.md"

learner:
  profile_path: ".linsist/learner-profile.md"
  target_role: "Java Agent / Enterprise RAG Engineer"

spaced_retrieval:
  interval_hours_tier1: 48
  interval_hours_tier2: 168
  max_retest_per_session: 2
  auto_scan_on_startup: true

active_curriculums:
  - "java-agent-rag"
```
"""

DEFAULT_DASHBOARD_CONTENT = """# 48h / 168h 双轮遗忘复测看板 (Retest Dashboard)

> 本看板由 Linsist 自动维护。日常学习卡片中的 48h 初测与 168h 巩固复测题目将登记在此。
> 使用已安装的 linsist-coach/scripts/scan_retest.py 并传入 --dir 指向本学习工作区，可更新本看板。

## 🔴 待复测 / 逾期任务 (Due for Retest)
| 到期日期 | 关联主题 | 核心复测题 | 原始卡片路径 | 状态 |
| :--- | :--- | :--- | :--- | :--- |

## 🟡 观察中任务 (Upcoming / 待到期)
| 到期日期 | 关联主题 | 核心复测题 | 原始卡片路径 | 状态 |
| :--- | :--- | :--- | :--- | :--- |

## 🟢 已通过验收 (Passed)
| 到期日期 | 关联主题 | 核心复测题 | 原始卡片路径 | 验收状态 |
| :--- | :--- | :--- | :--- | :--- |
"""


def init_workspace(target_root: Path):
    linsist_dir = target_root / ".linsist"
    notes_dir = linsist_dir / "notes"
    mistakes_dir = linsist_dir / "mistakes"

    print(f"[*] Initializing Linsist workspace at: {linsist_dir.resolve()}")

    # 1. Create directories
    linsist_dir.mkdir(parents=True, exist_ok=True)
    notes_dir.mkdir(parents=True, exist_ok=True)
    mistakes_dir.mkdir(parents=True, exist_ok=True)
    print("  [+] Created directories: .linsist/, .linsist/notes/, .linsist/mistakes/")

    # 2. Create config.md if not exists
    config_file = linsist_dir / "config.md"
    if not config_file.exists():
        config_file.write_text(DEFAULT_CONFIG_CONTENT, encoding="utf-8")
        print("  [+] Created configuration: .linsist/config.md")
    else:
        print("  [~] Existing configuration found, skipping overwrite: .linsist/config.md")

    # 3. Create learner-profile.md from template
    profile_file = linsist_dir / "learner-profile.md"
    template_file = Path(__file__).resolve().parent.parent / "references" / "learner-profile.template.md"
    if not profile_file.exists():
        if template_file.exists():
            template_content = template_file.read_text(encoding="utf-8")
            profile_file.write_text(template_content, encoding="utf-8")
            print("  [+] Initialized learner profile from template: .linsist/learner-profile.md")
        else:
            profile_file.write_text("# Learner Profile\n\nPlease configure your learning preferences here.\n", encoding="utf-8")
            print("  [+] Created default learner profile: .linsist/learner-profile.md")
    else:
        print("  [~] Existing profile found, skipping: .linsist/learner-profile.md")

    # 4. Create retest_dashboard.md if not exists
    dashboard_file = linsist_dir / "retest_dashboard.md"
    if not dashboard_file.exists():
        dashboard_file.write_text(DEFAULT_DASHBOARD_CONTENT, encoding="utf-8")
        print("  [+] Initialized 48h retest dashboard: .linsist/retest_dashboard.md")
    else:
        print("  [~] Existing dashboard found, skipping: .linsist/retest_dashboard.md")

    # 5. Place gitkeep in notes & mistakes to allow empty dirs tracking if needed
    (notes_dir / ".gitkeep").touch()
    (mistakes_dir / ".gitkeep").touch()

    print("\n[SUCCESS] Linsist workspace successfully initialized!")
    print("  Next steps:")
    print("  1. Customize your profile in: .linsist/learner-profile.md")
    print("  2. Start daily learning with: $linsist-coach")
    scanner = Path(__file__).resolve().with_name("scan_retest.py")
    print(f'  3. Run retest scan: "{sys.executable}" "{scanner}" --dir "{target_root.resolve()}"\n')


def main():
    parser = argparse.ArgumentParser(description="Initialize Linsist local workspace.")
    parser.add_argument(
        "--dir", "-d",
        default=".",
        help="Target workspace root directory (default: current directory)"
    )
    args = parser.parse_args()

    root_path = Path(args.dir).resolve()
    init_workspace(root_path)


if __name__ == "__main__":
    main()
