#!/usr/bin/env python3
"""Install the complete local Linsist suite without network or Python dependencies."""

import argparse
from pathlib import Path
import re
import shutil
import tempfile


SOURCE = Path(__file__).resolve().parents[1] / "skills"
SKILLS = ("linsist-coach", "linsist-interviewer", "linsist-basics", "linsist-os", "linsist-testlab")


def check_installation(destination):
    """Check the same installed files the agent will read and execute."""
    errors = []
    for name in SKILLS:
        folder = destination / name
        for resource in ("SKILL.md", "agents/openai.yaml"):
            if not (folder / resource).is_file():
                errors.append(f"Missing {folder / resource}")
        for document in folder.rglob("*.md"):
            for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                if target.startswith(("http:", "https:", "mailto:", "#")):
                    continue
                if not (document.parent / target.split("#")[0]).exists():
                    errors.append(f"Broken resource link: {document}: {target}")
    coach = destination / "linsist-coach"
    for resource in ("scripts/init_workspace.py", "scripts/scan_retest.py",
                     "references/curriculums/java-agent-rag/syllabus.md"):
        if not (coach / resource).is_file():
            errors.append(f"Missing {coach / resource}")
    if errors:
        raise ValueError("\n".join(errors))


def install(destination, update=False):
    if destination == SOURCE or destination.is_relative_to(SOURCE):
        raise ValueError("The installation destination must not replace or be inside the source skills directory.")
    destination.mkdir(parents=True, exist_ok=True)
    # Codex scans recursively and deduplicates canonical paths. If the checkout
    # already lives under this root, copies would register every skill twice.
    link_source = SOURCE.is_relative_to(destination)
    conflicts = [destination / name for name in SKILLS if (destination / name).exists() or (destination / name).is_symlink()]
    if conflicts and not update:
        raise ValueError("Existing skills were preserved. Use --update to replace this suite:\n" +
                         "\n".join(map(str, conflicts)))
    # Validate a complete staged installation before changing any existing skill.
    with tempfile.TemporaryDirectory(prefix=".linsist-install-", dir=destination) as temp:
        staging = Path(temp) / "new"
        backups = Path(temp) / "previous"
        staging.mkdir()
        backups.mkdir()
        for name in SKILLS:
            if link_source:
                try:
                    (staging / name).symlink_to(SOURCE / name, target_is_directory=True)
                except OSError as error:
                    raise ValueError("This checkout is inside the skill root. Move the checkout outside it "
                                     "or enable directory symlinks to avoid duplicate skills.") from error
            else:
                shutil.copytree(SOURCE / name, staging / name,
                                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        check_installation(staging)
        replaced, installed = [], []
        try:
            for name in SKILLS:
                target = destination / name
                if target.exists() or target.is_symlink():
                    target.rename(backups / name)
                    replaced.append(name)
                (staging / name).rename(target)
                installed.append(name)
            check_installation(destination)
        except Exception:
            for name in reversed(installed):
                target = destination / name
                if target.is_symlink():
                    target.unlink()
                else:
                    shutil.rmtree(target)
            for name in replaced:
                (backups / name).rename(destination / name)
            raise
    return "linked" if link_source else "copied"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=Path.home() / ".agents/skills",
                        help="Client skill root (default: ~/.agents/skills)")
    parser.add_argument("--check", action="store_true", help="Verify an existing installation without changing it")
    parser.add_argument("--update", action="store_true", help="Replace existing linsist-* skill folders")
    args = parser.parse_args()
    destination = args.dest.expanduser().resolve()
    try:
        if not args.check:
            mode = install(destination, update=args.update)
            print(f"Installation mode: {mode}")
        else:
            check_installation(destination)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Installation failed: {error}\n")
    print(f"Verified all {len(SKILLS)} Linsist skills: {destination}")
    print("Use $linsist-coach on your next turn. If it does not appear, restart the client.")


if __name__ == "__main__":
    main()
