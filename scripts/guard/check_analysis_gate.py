"""
check_analysis_gate.py — Pre-build analysis quality gate.

Gate is capability-driven. Domain layer is analytical artifact and must not block build.

Validates:
  1. flows.jsonl        → min 90% classification == VERIFIED_STRUCTURAL
  2. requirements.jsonl → min 90% classification == VERIFIED_STRUCTURAL

PASS IF both ≥ 0.90
FAIL OTHERWISE

Reads ONLY from:
  harvest/angularharvest/flows.jsonl
  harvest/angularharvest/requirements.jsonl

Returns:
  0 = PASS
  1 = FAIL

HARD RULES:
  - No silent fallback
  - No best-effort
  - No continuation after failure
  - Only outputs: PASS or FAIL
"""

import json
import sys
from pathlib import Path

REPO_ROOT         = Path(__file__).resolve().parents[2]
FLOWS_FILE        = REPO_ROOT / "harvest" / "angularharvest" / "flows.jsonl"
REQUIREMENTS_FILE = REPO_ROOT / "harvest" / "angularharvest" / "requirements.jsonl"

THRESHOLD = 0.90


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def check_verified_ratio(records: list[dict], label: str) -> tuple[bool, str]:
    if not records:
        return False, f"{label}: 0 records — FAIL"
    verified = sum(1 for r in records if r.get("classification") == "VERIFIED_STRUCTURAL")
    ratio = verified / len(records)
    if ratio < THRESHOLD:
        return False, f"{label}: {verified}/{len(records)} VERIFIED_STRUCTURAL = {ratio:.0%} (min {THRESHOLD:.0%})"
    return True, f"{label}: {verified}/{len(records)} = {ratio:.0%} OK"


def main() -> int:
    failures: list[str] = []

    # 1. flows.jsonl
    flows = load_jsonl(FLOWS_FILE)
    ok, msg = check_verified_ratio(flows, "flows.jsonl")
    print(msg)
    if not ok:
        failures.append(msg)

    # 2. requirements.jsonl
    reqs = load_jsonl(REQUIREMENTS_FILE)
    ok, msg = check_verified_ratio(reqs, "requirements.jsonl")
    print(msg)
    if not ok:
        failures.append(msg)

    if failures:
        print("\nANALYSIS GATE: FAIL")
        for f in failures:
            print(f"  BLOCK reason: {f}")
        return 1

    print("\nANALYSIS GATE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

