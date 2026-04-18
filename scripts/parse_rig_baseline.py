"""Parse RIG baseline JSON and print summary."""
import json
from pathlib import Path

SEP = chr(92)

data = json.loads(Path("analysis/integrity/full_baseline_post_fix.json").read_text(encoding="utf-8"))

print(f"GATE: {data['gate_status']}")
print(f"Total files: {data['total_files']}")
print(f"Failed files: {data['failed_files']}")
print()

# Failed files
failed = [f for f in data["files"] if f["gate_failed"]]
print(f"=== FAILED ({len(failed)}) ===")
for f in failed:
    name = f["greenai_file"].split(SEP)[-1]
    s = f["scores"]
    print(f"  FAIL: {name}  behav={s['behavior']}  dom={s['domain']}")
    for fl in f["flags"][:3]:
        print(f"    FLAG: {fl}")

print()
# Medium risk (not failed)
medium = [f for f in data["files"] if f["risk_level"] == "MEDIUM" and not f["gate_failed"]]
print(f"=== MEDIUM RISK (not failed) — top 10 ===")
for f in medium[:10]:
    name = f["greenai_file"].split(SEP)[-1]
    s = f["scores"]
    print(f"  MED: {name}  struct={s['structure']}  behav={s['behavior']}  dom={s['domain']}")

print()
# Domain breakdown
from collections import defaultdict
domain_fails = defaultdict(int)
domain_total = defaultdict(int)
for f in data["files"]:
    parts = f["greenai_file"].replace("/", SEP).split(SEP)
    # find 'Features' in path to extract domain
    try:
        fi = parts.index("Features")
        domain = parts[fi + 1] if fi + 1 < len(parts) else "Other"
    except ValueError:
        domain = "SharedKernel" if "SharedKernel" in f["greenai_file"] else "Other"
    domain_total[domain] += 1
    if f["gate_failed"]:
        domain_fails[domain] += 1

print("=== DOMAIN HEATMAP ===")
for domain in sorted(domain_total.keys()):
    fails = domain_fails.get(domain, 0)
    total = domain_total[domain]
    bar = "X" * fails + "." * (total - fails)
    print(f"  {domain:<35} {fails}/{total} FAIL  [{bar}]")

print()
# PasswordHasher whitelist check
pw = [f for f in data["files"] if "PasswordHasher" in f["greenai_file"]]
print(f"PasswordHasher in report: {len(pw)} entries (0 = correctly whitelisted)")

print()
# Schema flags
schema = [f for f in data["files"] if any("SCHEMA" in fl for fl in f.get("flags", []))]
print(f"=== SCHEMA HIGH RISK files ({len(schema)}) ===")
for f in schema:
    name = f["greenai_file"].split(SEP)[-1]
    schema_flags = [fl for fl in f["flags"] if "SCHEMA" in fl]
    for fl in schema_flags[:3]:
        print(f"  {name}: {fl}")

print()
# behavior_signature patterns for failed files
print("=== BEHAVIOR SIGNATURES (failed files) ===")
for f in failed:
    name = f["greenai_file"].split(SEP)[-1]
    sig = f.get("behavior_signature", [])
    print(f"  {name}: {sig}")
