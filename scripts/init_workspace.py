#!/usr/bin/env python3
"""Compatibility entry point for the runtime bundled with linsist-coach."""
import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parents[1] /
                      "skills/linsist-coach/scripts/init_workspace.py"), run_name="__main__")
