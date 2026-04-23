"""
check_build_gate.py — Build gate guard.

Reads ONLY from: harvest/architect-review/build_state.json
Returns:
  0 = ALLOW  (nbApproved == true)
  1 = BLOCK  (nbApproved != true)

README is NOT used. No fallback to memory or implicit state.
"""

import json
import sys
from pathlib import Path

BUILD_STATE_FILE = Path(__file__).parents[2] / "harvest" / "architect-review" / "build_state.json"


def check() -> int:
    if not BUILD_STATE_FILE.exists():
        print(f"BLOCK: build_state.json not found at {BUILD_STATE_FILE}")
        return 1

    with BUILD_STATE_FILE.open(encoding="utf-8") as f:
        state = json.load(f)

    if state.get("state") == "N-B APPROVED":
        print(f"ALLOW: state=N-B APPROVED")
        return 0

    print(f"BLOCK: state={state.get('state')} — no N-B approval in build_state.json")
    return 1


if __name__ == "__main__":
    sys.exit(check())
