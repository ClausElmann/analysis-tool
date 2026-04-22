"""Remove entries with null/UNKNOWN domain from corpus/behaviors.jsonl."""
import json
from pathlib import Path

p = Path("corpus/behaviors.jsonl")
lines = [l for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
before = len(lines)

kept = []
bad_domains = {None, "", "?", "UNKNOWN"}
for line in lines:
    e = json.loads(line)
    d = e.get("domain")
    if d in bad_domains:
        print(f"  REMOVE [{d}]: {e['behavior']} / {e['component']}")
        continue
    kept.append(line)

out = "\n".join(kept) + "\n"
p.write_bytes(out.encode("utf-8"))
print(f"Before: {before}  Removed: {before - len(kept)}  After: {len(kept)}")
