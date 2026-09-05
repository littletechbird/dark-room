#!/usr/bin/env python3
"""Alias entrypoint — delegates to run_all.py scorecard."""

from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("run_all.py")), run_name="__main__")
