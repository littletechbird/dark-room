#!/usr/bin/env python3
"""
Run automated Dark Room attack / boundary tests and print a scorecard JSON.

Exit code 0 only if all automated tests PASS.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_pytest(args: list[str], name: str) -> dict:
    started = time.time()
    cmd = [sys.executable, "-m", "pytest", *args, "-q", "--tb=line"]
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    elapsed = round(time.time() - started, 3)
    passed = proc.returncode == 0
    return {
        "name": name,
        "result": "PASS" if passed else "FAIL",
        "exit_code": proc.returncode,
        "elapsed_s": elapsed,
        "stdout_tail": (proc.stdout or "")[-800:],
        "stderr_tail": (proc.stderr or "")[-400:],
    }


def main() -> int:
    rows = [
        _run_pytest(["tests/test_vault.py"], "vault_unit"),
        _run_pytest(
            ["attacks/test_vault_boundary.py"],
            "vault_boundary_exfil",
        ),
        _run_pytest(
            ["attacks/test_redaction_sim.py"],
            "redaction_sim",
        ),
    ]

    # Document live screenshot expectation without requiring DISPLAY OCR
    live = {
        "name": "live_screenshot_linux",
        "result": "EXPECT_FAIL_OR_INCONCLUSIVE",
        "note": (
            "On Linux without OS exclude-from-capture, a real screenshot of "
            "the modal WILL leak pixels (product claim needs host WDA / "
            "compositor shield). Automated suite does not assert PASS here. "
            "See attacks/attack_live_screenshot.md. Simulated redaction "
            "(redaction_sim) is the PASS path proving intended architecture."
        ),
    }
    rows.append(live)

    automated = [r for r in rows if r["name"] != "live_screenshot_linux"]
    all_pass = all(r["result"] == "PASS" for r in automated)
    scorecard = {
        "suite": "dark-room-attacks",
        "all_automated_pass": all_pass,
        "tests": rows,
        "summary": {
            "pass": sum(1 for r in automated if r["result"] == "PASS"),
            "fail": sum(1 for r in automated if r["result"] == "FAIL"),
            "documented_non_automated": 1,
        },
    }
    print(json.dumps(scorecard, indent=2))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
