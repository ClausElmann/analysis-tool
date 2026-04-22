"""
ACDDA v4 - Phase 3c: Emit to JSONL
Appends validated entries (PASS only) from llm_output_validated.json to normalized JSONL files.
Append-only. Never overwrites existing entries.

Usage:
    python emit_to_jsonl.py [--component-list FILE] [--raw-dir DIR] [--normalized-dir DIR]
"""

import argparse
import json
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--component-list",  default=r".\harvest\component-list.json")
parser.add_argument("--raw-dir",         default=r".\harvest\angular\raw")
parser.add_argument("--normalized-dir",  default=r".\corpus")
args = parser.parse_args()

COMPONENT_LIST  = Path(args.component_list)
RAW_DIR         = Path(args.raw_dir)
NORMALIZED_DIR  = Path(args.normalized_dir)
NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)

if not COMPONENT_LIST.exists():
    print(f"ERROR: Not found: {COMPONENT_LIST}", file=sys.stderr)
    sys.exit(1)

entries = json.loads(COMPONENT_LIST.read_text(encoding="utf-8-sig"))

# Build name→path lookup for domain derivation
_name_to_path: dict[str, str] = {}
for _e in entries:
    _p = _e if isinstance(_e, str) else _e.get("filePath", str(_e))
    _name = Path(_p).stem.replace(".component", "")
    _name_to_path[_name] = _p


def derive_domain(comp_path: str) -> str:
    """Derive domain from component file path."""
    parts = comp_path.replace("\\", "/").split("/")
    p0 = parts[0] if parts else ""
    p1 = parts[1] if len(parts) > 1 else ""
    p2 = parts[2] if len(parts) > 2 else ""
    if p0 == "src":
        if p1 == "features" and p2:
            return p2
        # src/app, src/components etc. -> shared
        return "shared"
    if p0 == "app-globals":
        return "shared"
    if p0 == "side-projects":
        return p1 if p1 else "side-projects"
    # iframe paths
    if p0 in ("iframe", "iframe-modules") or (p0 == "src" and "iframe" in comp_path.lower()):
        return "iframe-modules"
    # message-wizard paths
    if "message-wizard" in comp_path.lower():
        # extract exact domain name from path if possible
        for part in parts:
            if part.startswith("message-wizard"):
                return part
        return "message-wizard"
    return "UNKNOWN"


b_count = f_count = r_count = 0


def _load_existing_keys(path: Path, key_fields: list[str]) -> set:
    if not path.exists():
        return set()
    keys = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                obj = json.loads(line)
                keys.add(tuple(obj.get(f, "") for f in key_fields))
            except json.JSONDecodeError:
                pass
    return keys


_existing_keys: dict[str, set] = {}

_REJECT_BEHAVIOR_RE = re.compile(
    r"(write value|register on change|register on touched|set disabled state|"
    r"^Brugeren kan formular$|^Brugeren kan street$|Brugeren kan zip kode|"
    r"Brugeren kan street names|Brugeren kan write|Brugeren kan register|"
    r"Brugeren kan disabled|skip to main|go to sms conversations|"
    r"Brugeren kan see status|Brugeren kan table columns|Brugeren kan year options|"
    r"Brugeren kan supply type|Brugeren kan chart|Brugeren kan street cleared|"
    r"Brugeren kan sms group$|Brugeren kan benchmarks$|Brugeren kan kpis$|"
    r"Brugeren kan kvhx|Brugeren kan causes$|Brugeren kan conflict$)",
    re.IGNORECASE,
)


def append_jsonl(path: Path, obj: dict, key_fields: list[str] | None = None):
    if key_fields:
        cache_key = str(path)
        if cache_key not in _existing_keys:
            _existing_keys[cache_key] = _load_existing_keys(path, key_fields)
        dedup_key = tuple(obj.get(f, "") for f in key_fields)
        if dedup_key in _existing_keys[cache_key]:
            return  # already exists — skip
        _existing_keys[cache_key].add(dedup_key)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")


ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

for entry in entries:
    comp_path = entry if isinstance(entry, str) else entry.get("filePath", str(entry))
    comp_name = Path(comp_path).stem.replace(".component", "")

    valid_path = RAW_DIR / comp_name / "llm_output_validated.json"
    if not valid_path.exists():
        continue

    v = json.loads(valid_path.read_text(encoding="utf-8"))
    comp_type = v.get("type", "?")
    domain = derive_domain(comp_path)

    # Emit behaviors (PASS only)
    for b in (v.get("behaviors") or []):
        if b.get("status") == "PASS":
            if _REJECT_BEHAVIOR_RE.search(b.get("text", "")):
                continue
            append_jsonl(NORMALIZED_DIR / "behaviors.jsonl", {
                "id":         str(uuid.uuid4()),
                "behavior":   b["text"],
                "domain":     domain,
                "component":  comp_name,
                "type":       comp_type,
                "confidence": b.get("confidence", 0.0),
                "source":     "angular",
                "created_at": ts,
            }, key_fields=["behavior", "component"])
            b_count += 1

    # Flows + requirements (DUMB excluded)
    if comp_type != "DUMB":
        for f in (v.get("flows") or []):
            if f.get("status") == "PASS":
                append_jsonl(NORMALIZED_DIR / "flows.jsonl", {
                    "id":           str(uuid.uuid4()),
                    "trigger":      f.get("trigger"),
                    "method":       f.get("method"),
                    "service_call": f.get("service_call"),
                    "http":         f.get("http"),
                    "result":       f.get("result"),
                    "domain":       domain,
                    "component":    comp_name,
                    "confidence":   f.get("confidence", 0.0),
                    "source":       "angular",
                    "created_at":   ts,
                }, key_fields=["trigger", "http", "component"])
                f_count += 1

        for req in (v.get("requirements") or []):
            if req.get("status") == "PASS":
                append_jsonl(NORMALIZED_DIR / "requirements.jsonl", {
                    "id":              str(uuid.uuid4()),
                    "method":          req.get("method"),
                    "endpoint":        req.get("endpoint"),
                    "type":            req.get("type"),
                    "evidence_method": req.get("evidence_method"),
                    "domain":          domain,
                    "component":       comp_name,
                    "source":          "angular",
                    "created_at":      ts,
                }, key_fields=["endpoint", "method", "component"])
                r_count += 1

print(f"Emitted: behaviors={b_count}  flows={f_count}  requirements={r_count}")
print(f"Output:  {NORMALIZED_DIR}")
