"""
Build Architect Review Package
Generates a dynamic README from current system state, then zips all relevant
harvest/pipeline files for architect review.

Usage:
    python scripts/build_review_package.py [--output FILE]

Output: architect_review_<timestamp>.zip
"""
from __future__ import annotations

import argparse
import json
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--output", default=None,
                    help="Output zip path (default: architect_review_<ts>.zip)")
args = parser.parse_args()

REPO_ROOT  = Path(__file__).parent.parent
CORPUS_DIR = REPO_ROOT / "corpus"
HARVEST    = REPO_ROOT / "harvest"
SCRIPTS_H  = REPO_ROOT / "scripts" / "harvest"
SCRIPTS_L2 = REPO_ROOT / "scripts" / "layer2"


# ── Helpers ───────────────────────────────────────────────────────────────────

def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                lines.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return lines


def manifest_stats(path: Path) -> dict:
    if not path.exists():
        return {}
    m = json.loads(path.read_text(encoding="utf-8"))
    stats = Counter(v.get("status", "PENDING") for v in m.values())
    pipeline = Counter(
        v.get("pipeline_status") for v in m.values()
        if v.get("pipeline_status")
    )
    return {
        "total":        len(m),
        "done":         stats["DONE"],
        "skipped":      stats["SKIPPED"],
        "failed":       stats["FAILED"] + stats.get("PERMANENT_FAILED", 0),
        "pending":      stats["PENDING"],
        "pipeline":     dict(pipeline),
    }


def corpus_stats() -> dict:
    behaviors    = read_jsonl(CORPUS_DIR / "behaviors.jsonl")
    flows        = read_jsonl(CORPUS_DIR / "flows.jsonl")
    requirements = read_jsonl(CORPUS_DIR / "requirements.jsonl")
    capabilities = read_jsonl(CORPUS_DIR / "capabilities.jsonl")

    domain_dist = Counter(b.get("domain", "UNKNOWN") for b in behaviors)
    type_dist   = Counter(b.get("type", "?") for b in behaviors)

    return {
        "behaviors":    len(behaviors),
        "flows":        len(flows),
        "requirements": len(requirements),
        "capabilities": len(capabilities),
        "domain_dist":  dict(domain_dist.most_common()),
        "type_dist":    dict(type_dist.most_common()),
        "unknown_domain": domain_dist.get("UNKNOWN", 0) + domain_dist.get("null", 0),
    }


def audit_stats(path: Path) -> dict:
    entries = read_jsonl(path)
    if not entries:
        return {"total_runs": 0}
    status_dist = Counter(e.get("status") for e in entries)
    pipeline_dist = Counter(e.get("pipeline_status") for e in entries)
    first_ts = entries[0].get("ts", "?")
    last_ts  = entries[-1].get("ts", "?")
    return {
        "total_runs":    len(entries),
        "status_dist":   dict(status_dist.most_common()),
        "pipeline_dist": dict(pipeline_dist.most_common()),
        "first_run":     first_ts,
        "last_run":      last_ts,
    }


# ── README generator ──────────────────────────────────────────────────────────

def generate_readme() -> str:
    ts       = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    m_stats  = manifest_stats(HARVEST / "harvest-manifest.json")
    c_stats  = corpus_stats()
    a_stats  = audit_stats(HARVEST / "harvest_audit.jsonl")

    pct_done = (
        round(m_stats["done"] / m_stats["total"] * 100, 1)
        if m_stats.get("total") else 0
    )

    lines = [
        "# Angular Harvest — Architect Review Package",
        f"> Auto-generated: {ts}",
        "",
        "---",
        "",
        "## Pipeline Overview",
        "",
        "```",
        "component-list.json (549 Angular components)",
        "        │",
        "        ▼",
        "Phase 1 — build_evidence_packs.py",
        "  Strukturel ekstraktion: template actions, HTTP-kald, service-injektioner",
        "  Output: harvest/angular/raw/<name>/evidence_pack.json",
        "          harvest/angular/raw/<name>/copilot_prompt.md",
        "        │",
        "        ▼",
        "Phase 2 — auto_respond.py  (watcher / batch responder)",
        "  Læser evidence_pack → genererer behaviors, flows, requirements",
        "  Kommunikationsbus: harvest/pipeline_bus.md",
        "  Output: harvest/angular/raw/<name>/llm_output.json",
        "        │",
        "        ▼",
        "Phase 3a — validate_llm_output.py",
        "  Validerer mod evidence_pack (metode-match, HTTP-chain, reject-ord)",
        "  Output: harvest/angular/raw/<name>/llm_output_validated.json",
        "        │",
        "        ▼",
        "Phase 3c — emit_to_jsonl.py",
        "  Append-only emit til corpus/*.jsonl",
        "  Output: corpus/behaviors.jsonl",
        "          corpus/flows.jsonl",
        "          corpus/requirements.jsonl",
        "        │",
        "        ▼",
        "Layer 2 — build_capabilities.py",
        "  Keyword-clustering → capabilities per domæne",
        "  Output: corpus/capabilities.jsonl",
        "```",
        "",
        "**Orchestrator:** `run_sequential.py --target N`  ",
        "Kører én komponent ad gangen, genstart-safe, audit log i `harvest/harvest_audit.jsonl`.",
        "",
        "---",
        "",
        "## Komponent-typer",
        "",
        "| Type | Beskrivelse | Output |",
        "|------|-------------|--------|",
        "| SMART | Har HTTP-kald / business logic | behaviors + flows + requirements |",
        "| CONTAINER | Orkestrerer child-komponenter | ui_behaviors (ikke emitteret til corpus) |",
        "| DUMB | Ren præsentation | ui_behaviors (ikke emitteret til corpus) |",
        "",
        "---",
        "",
        "## Aktuel Status",
        f"> Opdateret: {ts}",
        "",
        "### Manifest",
        "",
    ]

    if m_stats:
        lines += [
            f"| Metric | Antal |",
            f"|--------|-------|",
            f"| Total komponenter | {m_stats['total']} |",
            f"| DONE | {m_stats['done']} ({pct_done}%) |",
            f"| SKIPPED | {m_stats['skipped']} |",
            f"| FAILED | {m_stats['failed']} |",
            f"| PENDING | {m_stats['pending']} |",
            "",
        ]
        if m_stats.get("pipeline"):
            lines.append("**Pipeline status distribution:**")
            lines.append("")
            for k, v in sorted(m_stats["pipeline"].items(), key=lambda x: -x[1]):
                lines.append(f"- {k}: {v}")
            lines.append("")
    else:
        lines += ["_(manifest ikke fundet)_", ""]

    lines += [
        "### Corpus",
        "",
        f"| Fil | Entries |",
        f"|-----|---------|",
        f"| behaviors.jsonl | {c_stats['behaviors']} |",
        f"| flows.jsonl | {c_stats['flows']} |",
        f"| requirements.jsonl | {c_stats['requirements']} |",
        f"| capabilities.jsonl | {c_stats['capabilities']} |",
        f"| UNKNOWN domain | {c_stats['unknown_domain']} |",
        "",
    ]

    if c_stats.get("domain_dist"):
        lines.append("**Domain distribution (behaviors):**")
        lines.append("")
        for d, cnt in c_stats["domain_dist"].items():
            lines.append(f"- {d}: {cnt}")
        lines.append("")

    lines += [
        "### Audit Log",
        "",
    ]
    if a_stats.get("total_runs"):
        lines += [
            f"- Kørsel start: {a_stats['first_run']}",
            f"- Seneste kørsel: {a_stats['last_run']}",
            f"- Total komponent-runs: {a_stats['total_runs']}",
            "",
            "**Status distribution:**",
            "",
        ]
        for k, v in sorted(a_stats.get("status_dist", {}).items(), key=lambda x: -x[1]):
            lines.append(f"- {k}: {v}")
        lines += [
            "",
            "**Pipeline distribution:**",
            "",
        ]
        for k, v in sorted(a_stats.get("pipeline_dist", {}).items(), key=lambda x: -x[1]):
            lines.append(f"- {k or 'None'}: {v}")
        lines.append("")
    else:
        lines += ["_(ingen audit log endnu)_", ""]

    lines += [
        "---",
        "",
        "## Filer i denne pakke",
        "",
        "| Fil | Rolle |",
        "|-----|-------|",
        "| `scripts/harvest/build_evidence_packs.py` | Phase 1 — strukturel ekstraktion |",
        "| `scripts/harvest/auto_respond.py` | Phase 2 — batch LLM-responder (watcher) |",
        "| `scripts/harvest/validate_llm_output.py` | Phase 3a — validering mod evidence |",
        "| `scripts/harvest/emit_to_jsonl.py` | Phase 3c — emit til corpus JSONL |",
        "| `scripts/harvest/run_harvest.py` | Pipeline runner per batch |",
        "| `scripts/harvest/run_sequential.py` | Orchestrator — kører én ad gangen |",
        "| `scripts/harvest/score_components.py` | Scoring og pass-rate rapport |",
        "| `scripts/layer2/build_capabilities.py` | Layer 2A — capability clustering |",
        "| `scripts/layer2/diagnostic.py` | Layer 2 — diagnostisk analyse |",
        "| `corpus/behaviors.jsonl` | Output: bruger-behaviors |",
        "| `corpus/flows.jsonl` | Output: HTTP-flows |",
        "| `corpus/requirements.jsonl` | Output: API-requirements |",
        "| `corpus/capabilities.jsonl` | Output: Layer 2 capabilities (hvis genereret) |",
        "| `harvest/harvest-manifest.json` | Komponent-status (per component) |",
        "| `harvest/harvest_audit.jsonl` | Append-only revisionsspor |",
        "| `harvest/component-list.json` | Input: liste over 549 Angular-komponenter |",
        "",
        "---",
        "",
        "## Kørsel",
        "",
        "```powershell",
        "# Terminal 1 — start watcher",
        "$env:PYTHONIOENCODING='utf-8'",
        ".venv\\Scripts\\python.exe scripts/harvest/auto_respond.py",
        "",
        "# Terminal 2 — kør harvest (N komponenter)",
        "$env:PYTHONIOENCODING='utf-8'",
        ".venv\\Scripts\\python.exe scripts/harvest/run_sequential.py --target N",
        "",
        "# Layer 2 (efter harvest)",
        ".venv\\Scripts\\python.exe scripts/layer2/build_capabilities.py",
        "",
        "# Byg ny review-pakke",
        ".venv\\Scripts\\python.exe scripts/build_review_package.py",
        "```",
        "",
    ]

    return "\n".join(lines)


# ── Zip builder ───────────────────────────────────────────────────────────────

def build_zip(readme_content: str, output_path: Path) -> None:
    files_to_include: list[tuple[Path, str]] = []

    # Scripts
    for script in SCRIPTS_H.glob("*.py"):
        files_to_include.append((script, f"scripts/harvest/{script.name}"))
    for script in SCRIPTS_L2.glob("*.py"):
        files_to_include.append((script, f"scripts/layer2/{script.name}"))
    this_script = Path(__file__)
    files_to_include.append((this_script, f"scripts/{this_script.name}"))

    # Corpus output
    for jsonl in CORPUS_DIR.glob("*.jsonl"):
        files_to_include.append((jsonl, f"corpus/{jsonl.name}"))

    # Harvest state
    for fname in ["harvest-manifest.json", "harvest_audit.jsonl", "component-list.json"]:
        p = HARVEST / fname
        if p.exists():
            files_to_include.append((p, f"harvest/{fname}"))

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # README first
        zf.writestr("README.md", readme_content.encode("utf-8"))
        for src, arc_name in files_to_include:
            if src.exists():
                zf.write(src, arc_name)

    print(f"Zip: {output_path}  ({output_path.stat().st_size // 1024} KB)")
    print(f"Entries: {len(files_to_include) + 1} filer (inkl. README)")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    out = Path(args.output) if args.output else REPO_ROOT / f"architect_review_{ts_str}.zip"

    print("Genererer README...")
    readme = generate_readme()

    # Skriv README til repo så den altid er up-to-date
    readme_path = REPO_ROOT / "HARVEST_README.md"
    readme_path.write_text(readme, encoding="utf-8")
    print(f"README opdateret: {readme_path.name}")

    print("Bygger zip...")
    build_zip(readme, out)
    print("Færdig.")
