"""
set_nb_approved.py — The ONLY authorized way to set state = "N-B APPROVED".

Single source of truth for gate is check_analysis_gate.py.
set_nb_approved.py must not duplicate or diverge.

Flow:
  1. Delegate entirely to check_analysis_gate.py
  2. If gate returns 0 (PASS) → write {"state": "N-B APPROVED"} to build_state.json
  3. If gate returns != 0 (FAIL) → append N-B BLOCKED event, exit(1)

FORBIDDEN:
  - Direct writes to build_state.json
  - Bypassing this script
  - Manual overrides
  - Reimplementing gate logic
  - Reading domain_state.json
  - Any validation outside check_analysis_gate.py

Usage:
  python scripts/guard/set_nb_approved.py
"""

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT        = Path(__file__).resolve().parents[2]
BUILD_STATE_FILE = REPO_ROOT / "harvest" / "architect-review" / "build_state.json"
ANALYSIS_GATE    = Path(__file__).parent / "check_analysis_gate.py"
README_FILE      = REPO_ROOT / "temp" / "README.md"


def append_readme(event: str) -> None:
    with README_FILE.open("a", encoding="utf-8") as f:
        f.write(f"\n{event}\n")


def main() -> int:
    # Delegate entirely to check_analysis_gate.py — no logic here
    result = subprocess.run(
        [sys.executable, str(ANALYSIS_GATE)],
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip()
    print(output)

    if result.returncode != 0:
        lines = output.splitlines()
        block_lines = "\n".join(f"  - {l}" for l in lines if l.startswith("  BLOCK") or "FAIL" in l or "%" in l)
        event = (
            f"## COPILOT → ARCHITECT — N-B BLOCKED ({date.today()})\n\n"
            f"- reason: analysis gate FAIL\n"
            f"{block_lines}"
        )
        append_readme(event)
        print("N-B APPROVAL DENIED")
        return 1

    # Gate passed — write state
    BUILD_STATE_FILE.write_text(
        json.dumps({"state": "N-B APPROVED"}, indent=2) + "\n",
        encoding="utf-8",
    )
    print("N-B APPROVED — build_state.json updated.")
    append_readme(
        f"## COPILOT → ARCHITECT — N-B APPROVED ({date.today()})\n\n"
        f"- analysis gate: PASS\n"
        f"- build_state.json: state = N-B APPROVED"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

    append_readme(
        f"## COPILOT → ARCHITECT — N-B APPROVED ({date.today()})\n\n"
        f"- analysis gate: PASS\n"
        f"- build_state.json: state = N-B APPROVED"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
