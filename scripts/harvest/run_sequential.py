"""
Sequential Re-Harvest Orchestrator.
Resets everything, processes one component at a time, stops at TARGET_DONE.
Writes status to harvest/pipeline_bus.md after each component.

Usage:
    python scripts/harvest/run_sequential.py [--target DONE_COUNT]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT       = Path(__file__).parent.parent.parent
SCRIPTS_HARVEST = Path(__file__).parent
PYTHON          = sys.executable
TEMP_MD         = REPO_ROOT / "harvest" / "pipeline_bus.md"
AUDIT_LOG       = REPO_ROOT / "harvest" / "harvest_audit.jsonl"
MANIFEST_PATH   = REPO_ROOT / "harvest" / "harvest-manifest.json"
COMP_LIST_PATH  = REPO_ROOT / "harvest" / "component-list.json"
RAW_DIR         = REPO_ROOT / "harvest" / "angular" / "raw"
CORPUS_DIR      = REPO_ROOT / "corpus"

parser = argparse.ArgumentParser()
parser.add_argument("--target", type=int, default=10, help="Stop after this many DONE")
parser.add_argument("--resume", action="store_true", help="Resume from existing manifest — skip reset")
args = parser.parse_args()
TARGET_DONE = args.target


# ── Helpers ───────────────────────────────────────────────────────────────────

def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for l in path.read_text(encoding="utf-8").splitlines() if l.strip())


def _count_unknown(path: Path) -> int:
    if not path.exists():
        return 0
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            if json.loads(line).get("domain") in (None, "", "?", "UNKNOWN"):
                n += 1
        except Exception:
            pass
    return n


def _domain_dist(path: Path) -> Counter:
    c: Counter = Counter()
    if not path.exists():
        return c
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            c[json.loads(line).get("domain", "?")] += 1
        except Exception:
            pass
    return c


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {}


# ── Audit log ────────────────────────────────────────────────────────────────

def audit(component_path: str, name: str, status: str, pipeline_status: str | None,
          retry: int, done_count: int, total: int) -> None:
    """Append one JSON line to harvest_audit.jsonl."""
    entry = {
        "ts":              datetime.now(timezone.utc).isoformat(),
        "component_path":  component_path,
        "name":            name,
        "status":          status,
        "pipeline_status": pipeline_status,
        "retry":           retry,
        "done_total":      done_count,
        "manifest_total":  total,
    }
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── temp.md writer ────────────────────────────────────────────────────────────

def write_status(manifest: dict, current_name: str | None, message: str,
                 done_count: int, retry_count: int = 0, stopped: bool = False) -> None:
    stats   = Counter(v.get("status", "PENDING") for v in manifest.values())
    total   = len(manifest)
    b_count = _count_jsonl(CORPUS_DIR / "behaviors.jsonl")
    f_count = _count_jsonl(CORPUS_DIR / "flows.jsonl")
    r_count = _count_jsonl(CORPUS_DIR / "requirements.jsonl")
    unk     = _count_unknown(CORPUS_DIR / "behaviors.jsonl")
    ts      = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        f"# SEQUENTIAL HARVEST — {ts}",
        "",
        "## Status",
        f"DONE: {stats['DONE']}/{total}  "
        f"FAILED: {stats['FAILED']}  "
        f"PERMANENT_FAILED: {stats.get('PERMANENT_FAILED', 0)}  "
        f"PENDING: {stats.get('PENDING', 0) + stats.get('PROCESSING', 0)}",
        "",
        "## Corpus",
        f"behaviors: {b_count}  flows: {f_count}  requirements: {r_count}  UNKNOWN_domain: {unk}",
        "",
        "## Current component",
        f"Name:        {current_name or '-'}",
        f"Message:     {message}",
        f"retry_count: {retry_count}",
        "",
    ]

    if stopped:
        dist = _domain_dist(CORPUS_DIR / "behaviors.jsonl")
        lines += [
            f"## STOP — {TARGET_DONE} DONE nået",
            "",
            "### Kvalitetsrapport — domain distribution (behaviors)",
        ]
        for d, c in sorted(dist.items(), key=lambda x: -x[1]):
            lines.append(f"- {d}: {c}")
        lines += ["", f"UNKNOWN domain: {unk}", "", "STOP"]

    TEMP_MD.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))


# ── Reset ─────────────────────────────────────────────────────────────────────

def reset() -> None:
    print("=== RESET ===")
    if MANIFEST_PATH.exists():
        MANIFEST_PATH.unlink()
        print("  manifest deleted")
    for f in CORPUS_DIR.glob("*.jsonl"):
        f.unlink()
        print(f"  deleted corpus/{f.name}")
    if RAW_DIR.exists():
        for d in RAW_DIR.iterdir():
            if d.is_dir():
                shutil.rmtree(d)
        print("  harvest/angular/raw/ cleared")
    print("Reset complete.\n")


def init_manifest() -> dict:
    comp_list = json.loads(COMP_LIST_PATH.read_text(encoding="utf-8-sig"))
    manifest: dict = {}
    for entry in comp_list:
        p = entry["path"] if isinstance(entry, dict) else entry
        manifest[p] = {
            "status": "PENDING",
            "pipeline_status": None,
            "lastProcessed": None,
            "retryCount": 0,
        }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Manifest initialized: {len(manifest)} components\n")
    return manifest


# ── Main loop ─────────────────────────────────────────────────────────────────

def _ensure_watcher() -> None:
    """Check if auto_respond.py is running. If not, start it automatically."""
    # Detect via psutil (preferred) or fall back to tasklist
    running = False
    try:
        import psutil
        for proc in psutil.process_iter(["cmdline"]):
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if "auto_respond.py" in cmdline:
                running = True
                break
    except ImportError:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
            capture_output=True, text=True
        )
        # Coarser check — just look for running python processes
        # and check pipeline_bus.md activity as secondary signal
        bus_mtime = TEMP_MD.stat().st_mtime if TEMP_MD.exists() else 0
        age = time.time() - bus_mtime
        running = age < 30  # bus was written within 30s → watcher likely active

    if not running:
        print("[WARN] auto_respond.py ikke detekteret — starter watcher automatisk...")
        subprocess.Popen(
            [PYTHON, str(SCRIPTS_HARVEST / "auto_respond.py")],
            cwd=str(REPO_ROOT),
        )
        time.sleep(2)  # Giv watcheren tid til at starte
        print("[INFO] Watcher startet.")
    else:
        print("[INFO] Watcher kører — OK")


def main() -> None:
    _ensure_watcher()
    if args.resume and MANIFEST_PATH.exists():
        print("[RESUME] Skipping reset — loading existing manifest")
        manifest = load_manifest()
    else:
        reset()
        manifest = init_manifest()
    write_status(manifest, None, "Initialiseret — starter loop", 0)

    while True:
        # Re-read manifest fresh each iteration (run_harvest.py updates it)
        manifest = load_manifest()
        done_count = sum(1 for v in manifest.values() if v.get("status") == "DONE")

        if done_count >= TARGET_DONE:
            write_status(manifest, None, f"DONE — {done_count} nået", done_count,
                         stopped=True)
            print(f"\n=== STOP: {TARGET_DONE} DONE nået ===")
            break

        # TERMINAL set — statuses that should never be re-processed
        _TERMINAL = {"DONE", "PERMANENT_FAILED", "SKIPPED", "PENDING_REVIEW"}

        # Check if there are any processable components
        processable = [
            path for path, v in manifest.items()
            if v.get("status") in ("PENDING", "FAILED")
            and v.get("retryCount", 0) < 3
        ]
        if not processable:
            write_status(manifest, None, "Ingen flere komponenter", done_count,
                         stopped=done_count >= TARGET_DONE)
            print("Ingen flere PENDING/FAILED komponenter.")
            break

        # Find next component to process (PENDING first, then FAILED)
        # Sorted: PENDING before FAILED
        def sort_key(p: str) -> tuple:
            v = manifest[p]
            order = 0 if v.get("status") == "PENDING" else 1
            return (order, v.get("retryCount", 0))

        next_comp = sorted(processable, key=sort_key)[0]
        next_name = Path(next_comp).stem.replace(".component", "")
        retry_count = manifest[next_comp].get("retryCount", 0)

        print(f"\n--- Processing: {next_name} (retry={retry_count}, done={done_count}/{TARGET_DONE}) ---")
        write_status(manifest, next_name, "PROCESSING", done_count, retry_count)

        # Write a temp component-list with ONLY this one component
        # so run_harvest.py cannot pick a different component
        tmp_list = REPO_ROOT / "harvest" / f"_seq_tmp_{next_name}.json"
        try:
            tmp_list.write_text(
                json.dumps([next_comp], ensure_ascii=False), encoding="utf-8"
            )

            subprocess.run(
                [
                    PYTHON,
                    str(SCRIPTS_HARVEST / "run_harvest.py"),
                    "--auto",
                    "--batch-size", "1",
                    "--auto-timeout", "300",
                    "--component-list", str(tmp_list),
                    "--manifest", str(MANIFEST_PATH),
                ],
                cwd=str(REPO_ROOT),
            )
        finally:
            tmp_list.unlink(missing_ok=True)

        # Re-read manifest to see result
        manifest = load_manifest()
        status_after = manifest.get(next_comp, {}).get("status", "UNKNOWN")
        retry_after  = manifest.get(next_comp, {}).get("retryCount", 0)
        pipeline_st  = manifest.get(next_comp, {}).get("pipeline_status", "")

        # PENDING_REVIEW / NO_PACK / unresolvable → mark SKIPPED (terminal)
        if status_after == "PENDING_REVIEW" or pipeline_st in ("NO_PACK", "SKIP"):
            manifest[next_comp]["status"] = "SKIPPED"
            MANIFEST_PATH.write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            status_after = "SKIPPED"
            print(f"  -> {next_name}: auto-SKIPPED (pipeline={pipeline_st})")

        done_count = sum(1 for v in manifest.values() if v.get("status") == "DONE")
        print(f"  -> {next_name}: {status_after}  (DONE: {done_count}/{TARGET_DONE})")
        audit(next_comp, next_name, status_after, pipeline_st, retry_after, done_count, len(manifest))
        write_status(manifest, next_name, f"Faerdig: {status_after}", done_count, retry_after)


if __name__ == "__main__":
    main()
