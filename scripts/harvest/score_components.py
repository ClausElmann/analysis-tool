## LLM-ENFORCEMENT: Scriptet stopper hvis LLM-output mangler eller fejler

"""
ACDDA v4 - Phase 3b: Scoring
Reads _validation_summary.json, computes pass_rate, appends full report to temp.md.

Usage:
    python score_components.py [--raw-dir DIR] [--temp-md FILE]
"""

import argparse
import json
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--raw-dir",  default=r".\harvest\angular\raw")
parser.add_argument("--temp-md",  default=r".\temp.md")
args = parser.parse_args()

RAW_DIR = Path(args.raw_dir)
TEMP_MD = Path(args.temp_md)


# LLM-output enforcement: check for llm_output.json and validation summary
llm_output_path = RAW_DIR / "llm_output.json"
if not llm_output_path.exists():
    print(f"LLM-ERROR: llm_output.json mangler — Copilot chat har ikke kørt eller fejlet.", file=sys.stderr)
    sys.exit(2)

try:
    llm_output = json.loads(llm_output_path.read_text(encoding="utf-8"))
except Exception as e:
    print(f"LLM-ERROR: llm_output.json kunne ikke indlæses: {e}", file=sys.stderr)
    sys.exit(3)

summary_path = RAW_DIR / "_validation_summary.json"
if not summary_path.exists():
    print(f"ERROR: Not found: {summary_path}", file=sys.stderr)
    sys.exit(1)

summary = json.loads(summary_path.read_text(encoding="utf-8"))

n_pass = n_partial = n_fail = n_pass_ui = n_skip_ui = n_waiting = 0
for r in summary:
    match r["status"]:
        case "PASS":         n_pass += 1
        case "PARTIAL":      n_partial += 1
        case "FAIL":         n_fail += 1
        case "PASS_UI_ONLY": n_pass_ui += 1
        case "SKIP_UI_ONLY": n_skip_ui += 1
        pass

backend_eligible = n_pass + n_partial + n_fail
pass_rate = round((n_pass + 0.5 * n_partial) / backend_eligible, 2) if backend_eligible > 0 else 0

b_reject_total = sum(r.get("b_reject", 0) for r in summary)
b_pass_total   = sum(r.get("b_pass",   0) for r in summary)
b_reject_rate  = (round(b_reject_total / (b_pass_total + b_reject_total), 2)
                  if (b_pass_total + b_reject_total) > 0 else 0)

accept_pass_rate   = pass_rate >= 0.70
accept_fail        = n_fail <= 1
accept_reject_rate = b_reject_rate < 0.20
verdict = "ACCEPTED" if (accept_pass_rate and accept_fail and accept_reject_rate) else "REJECTED"

# Build table rows
table_rows = ""
for r in summary:
    table_rows += (
        f"\n| {r['component']:<48} | {r['type']:<10} | {r['status']:<14} "
        f"| {r.get('b_pass',0):>3} | {r.get('b_reject',0):>3} "
        f"| {r.get('f_pass',0):>3} | {r.get('r_pass',0):>3} |"
    )

pass
deep_examples = ""
ex_count = 0
for r in summary:
    if ex_count >= 2:
        break
    pass
    v = json.loads(valid_path.read_text(encoding="utf-8"))
    ex_count += 1

    deep_examples += f"\n\nEksempel {ex_count}: {r['component']} [{r['type']}] -> {r['status']}"
    deep_examples += "\n  Behaviors:"
    shown = 0
    for b in (v.get("behaviors") or []):
        if b.get("status") == "PASS" and shown < 3:
            deep_examples += f"\n    [PASS] {b['text']}  (conf={b.get('confidence','-')})"
            shown += 1
    for b in (v.get("behaviors") or []):
        if b.get("status") == "REJECTED" and shown < 5:
            deep_examples += f"\n    [AFVIST] {b['text']}  reason={b.get('reason')}"
            shown += 1

    f_pass_list = [f for f in (v.get("flows") or []) if f.get("status") == "PASS"]
    if f_pass_list:
        deep_examples += "\n  Flows (passed):"
        for f in f_pass_list[:2]:
            deep_examples += f"\n    trigger={f.get('trigger')} -> {f.get('http')}"
    else:
        deep_examples += "\n  Flows: (ingen godkendte flows)"

    r_pass_list = [r2 for r2 in (v.get("requirements") or []) if r2.get("status") == "PASS"]
    if r_pass_list:
        deep_examples += "\n  Requirements (passed):"
        for req in r_pass_list[:3]:
            deep_examples += f"\n    [{req.get('type','?')}] {req.get('method')} {req.get('endpoint')}"

report = f"""
---

## COPILOT → ARCHITECT — ACDDA v4 RESULTAT

**Dato:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}
**Mode:** Copilot Chat GPT-4.1

### VERDICT: {verdict}

| Kriterie | Vaerdi | Krav | OK? |
|----------|--------|------|-----|
| pass_rate | {pass_rate} | >= 0.70 | {"✅" if accept_pass_rate else "❌"} |
| fail_count | {n_fail} | <= 1 | {"✅" if accept_fail else "❌"} |
| behavior_reject_rate | {b_reject_rate} | < 0.20 | {"✅" if accept_reject_rate else "❌"} |

### SCORE TABEL

| Komponent | Type | Status | b_pass | b_reject | f_pass | r_pass |
|-----------|------|--------|--------|----------|--------|--------|{table_rows}

**Totaler:**
- PASS: {n_pass}  |  PARTIAL: {n_partial}  |  FAIL: {n_fail}
-- PASS_UI_ONLY: {n_pass_ui}  |  SKIP_UI_ONLY: {n_skip_ui}
- backend_eligible: {backend_eligible}  |  pass_rate: {pass_rate}

### DYBDE VALIDERING (2 eksempler){deep_examples}

---
"""

# Append to temp.md
with open(TEMP_MD, "a", encoding="utf-8") as f:
    f.write(report)

print(f"Score report appended to {TEMP_MD}")
print(f"VERDICT: {verdict}  (pass={n_pass} partial={n_partial} fail={n_fail} pass_rate={pass_rate})")
