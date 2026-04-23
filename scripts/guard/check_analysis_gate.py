"""
check_analysis_gate.py — Pre-build analysis quality gate.

Validates:
  1. flows.jsonl      → min 90% classification == VERIFIED_STRUCTURAL
  2. requirements.jsonl → min 90% classification == VERIFIED_STRUCTURAL
  3. domains (domain_state.json) → no domain with status == "UNKNOWN"
  4. domain coverage  → domains with status in {complete, done, locked} / total non-global >= 0.90

Reads ONLY from:
  harvest/angularharvest/flows.jsonl
  harvest/angularharvest/requirements.jsonl
  domains/domain_state.json

Returns:
  0 = PASS
  1 = FAIL (prints reason, coverage, verified %)

No fallback. No bypass. No README read.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FLOWS_FILE        = REPO_ROOT / "harvest" / "angularharvest" / "flows.jsonl"
REQUIREMENTS_FILE = REPO_ROOT / "harvest" / "angularharvest" / "requirements.jsonl"
DOMAIN_STATE_FILE = REPO_ROOT / "domains" / "domain_state.json"

THRESHOLD = 0.90
DONE_STATUSES = {"complete", "done", "locked"}


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


def check_domains(state: dict) -> tuple[bool, str, str]:
    entries = {k: v for k, v in state.items() if not k.startswith("_")}
    unknown = [k for k, v in entries.items() if str(v.get("status", "")).upper() == "UNKNOWN"]
    if unknown:
        return False, f"domains with status UNKNOWN: {unknown}", ""

    total = len(entries)
    done_count = sum(1 for v in entries.values() if v.get("status", "").lower() in DONE_STATUSES)
    ratio = done_count / total if total else 0.0
    if ratio < THRESHOLD:
        return False, f"domain coverage: {done_count}/{total} = {ratio:.0%} (min {THRESHOLD:.0%})", f"{ratio:.0%}"
    return True, f"domain coverage: {done_count}/{total} = {ratio:.0%} OK", f"{ratio:.0%}"


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

    # 3 + 4. domain_state.json
    with DOMAIN_STATE_FILE.open(encoding="utf-8") as f:
        state = json.load(f)

    ok, msg, _ = check_domains(state)
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
