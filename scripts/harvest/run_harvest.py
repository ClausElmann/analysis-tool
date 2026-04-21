"""
ACDDA v4 - Harvest Orchestrator
Kører kun lokal pipeline for Angular-komponenter.
Ingen ekstern LLM, Copilot API eller token-brug tilladt.
Pipeline: evidence packs → validate → emit → manifest update.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
REPO_ROOT = SCRIPTS_DIR.parent.parent          # analysis-tool/
PYTHON = sys.executable


# ── Manifest ──────────────────────────────────────────────────────────────────

def load_manifest(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_manifest(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Helpers ───────────────────────────────────────────────────────────────────

def component_name(comp_path: str) -> str:
    return Path(comp_path).stem.replace(".component", "")


def run_step(cmd: list[str], label: str) -> bool:
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "")[-400:].strip()
        print(f"  [FAIL] {label}:\n    {tail}")
        return False
    return True





def read_component_status(summary_path: Path, name: str) -> str:
    """Read status for a single component from _validation_summary.json."""
    if not summary_path.exists():
        return "UNKNOWN"
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        for r in summary:
            if r.get("component") == name:
                return r.get("status", "UNKNOWN")
    except Exception:
        pass
    return "UNKNOWN"


def print_manifest_status(components: list, manifest: dict) -> None:
    counts = {"DONE": 0, "FAILED": 0, "PENDING": 0}
    for c in components:
        s = manifest.get(c, {}).get("status", "PENDING")
        counts[s if s in counts else "PENDING"] += 1
    total = len(components)
    print(f"Total: {total}  DONE: {counts['DONE']}  FAILED: {counts['FAILED']}  PENDING: {counts['PENDING']}")
    print()
    for c in components:
        entry = manifest.get(c, {})
        status = entry.get("status", "PENDING")
        pipeline = entry.get("pipeline_status", "")
        name = component_name(c)
        suffix = f"  [{pipeline}]" if pipeline else ""
        print(f"  {status:<8} {name}{suffix}")


# ── Auto-mode helpers (temp.md communication bus) ────────────────────────────

def _write_prompt_to_temp_md(temp_md: Path, name: str, raw_dir: Path) -> None:
    """Append component prompt block to temp.md."""
    prompt_file = raw_dir / name / "copilot_prompt.md"
    prompt_text = prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else "(NO PROMPT FOUND)"
    block = (
        f"\n=== COMPONENT START: {name} ===\n"
        f"{prompt_text}\n"
        f"=== END PROMPT ===\n"
    )
    with open(temp_md, "a", encoding="utf-8") as f:
        f.write(block)


def _cleanup_temp_md(temp_md: Path, keep_last: int = 5) -> None:
    """Remove completed component blocks from temp.md, keeping only the last `keep_last` DONE blocks."""
    if not temp_md.exists():
        return
    content = temp_md.read_text(encoding="utf-8")
    # Split on COMPONENT START markers
    start_marker = "=== COMPONENT START:"
    end_output_marker = "=== END OUTPUT ==="
    parts = content.split(start_marker)
    header = parts[0]  # everything before first block

    blocks = parts[1:]  # each starts right after "=== COMPONENT START:"
    # A block is "done" if it contains END OUTPUT
    done_blocks = [b for b in blocks if end_output_marker in b]
    pending_blocks = [b for b in blocks if end_output_marker not in b]

    # Keep only last `keep_last` done blocks
    kept_done = done_blocks[-keep_last:] if len(done_blocks) > keep_last else done_blocks

    remaining = kept_done + pending_blocks
    if remaining:
        new_content = header + start_marker.join([""] + remaining)
    else:
        new_content = header
    temp_md.write_text(new_content, encoding="utf-8")


def _poll_temp_md_for_output(
    temp_md: Path, name: str, timeout_sec: int = 300, poll_interval: float = 2.0
) -> "str | None":
    """Poll temp.md until LLM output for this component appears. Returns JSON string or None on timeout."""
    import time
    marker_start = f"=== COMPONENT START: {name} ==="
    llm_marker   = "=== LLM OUTPUT ==="
    end_marker   = "=== END OUTPUT ==="
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            content = temp_md.read_text(encoding="utf-8")
            idx = content.rfind(marker_start)
            if idx != -1:
                after = content[idx:]
                if llm_marker in after and end_marker in after:
                    llm_start = after.index(llm_marker) + len(llm_marker)
                    llm_end   = after.index(end_marker)
                    return after[llm_start:llm_end].strip()
        except Exception:
            pass
        time.sleep(poll_interval)
    return None


# ── Batch runner ──────────────────────────────────────────────────────────────

def _run_batch(args, components: list, manifest: dict, manifest_path: Path,
               raw_dir: Path, corpus_dir: Path) -> None:
    # In --auto mode always mark DONE (full automation)
    if getattr(args, "auto", False):
        args.auto_mark_done = True

    if getattr(args, "finalize", False):
        pending = [c for c in components
                   if manifest.get(c, {}).get("status") not in ("DONE", "FAILED")]
    elif getattr(args, "prepare", False):
        pending = [c for c in components
                   if manifest.get(c, {}).get("status") == "PENDING"]
    elif getattr(args, "auto", False):
        pending = [c for c in components
                   if manifest.get(c, {}).get("status") not in ("DONE", "FAILED")]
    else:
        pending = [c for c in components
                   if manifest.get(c, {}).get("status") not in ("DONE", "FAILED", "SKIPPED_FOR_TEST", "AWAITING_LLM")]
    batch = pending[:args.batch_size]

    done_count  = sum(1 for v in manifest.values() if v.get("status") == "DONE")
    total_count = len(components)

    if not batch:
        print(f"No pending components. Done: {done_count}/{total_count}")
        return

    print(f"Batch: {len(batch)} of {len(pending)} pending  (done: {done_count}/{total_count})")
    print()


    for comp_path in batch:
        name = component_name(comp_path)
        print(f"→ {name}")

        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8",
            dir=str(REPO_ROOT / "harvest"),
        )
        json.dump([comp_path], tmp)
        tmp.close()
        temp_list = Path(tmp.name)

        try:
            if not getattr(args, "finalize", False):
                # Step 1: Build evidence pack
                ok = run_step([
                    PYTHON,
                    str(SCRIPTS_DIR / "build_evidence_packs.py"),
                    "--component-list", str(temp_list),
                    "--app-root",       args.app_root,
                    "--output-dir",     str(raw_dir),
                ], "build_evidence_packs")

                if not ok:
                    manifest[comp_path] = {"status": "FAILED", "reason": "build_failed"}
                    save_manifest(manifest_path, manifest)
                    continue

            # --auto: write prompt to temp.md and poll for LLM response
            if getattr(args, "auto", False):
                temp_md = REPO_ROOT / "temp.md"
                _write_prompt_to_temp_md(temp_md, name, raw_dir)
                timeout_sec = getattr(args, "auto_timeout", 300)
                print(f"  → prompt written to temp.md — polling {timeout_sec}s for LLM output...")
                llm_json = _poll_temp_md_for_output(temp_md, name, timeout_sec=timeout_sec)
                if llm_json is None:
                    print(f"  [TIMEOUT] no LLM output after {timeout_sec}s")
                    manifest[comp_path] = {"status": "FAILED", "reason": "llm_timeout",
                                           "lastProcessed": datetime.now(timezone.utc).isoformat()}
                    save_manifest(manifest_path, manifest)
                    continue
                llm_out_path = raw_dir / name / "llm_output.json"
                try:
                    parsed = json.loads(llm_json)
                    llm_out_path.write_text(
                        json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8"
                    )
                    print(f"  → llm_output.json written")
                except json.JSONDecodeError as exc:
                    print(f"  [FAIL] invalid JSON from LLM: {exc}")
                    manifest[comp_path] = {"status": "FAILED", "reason": "invalid_json",
                                           "lastProcessed": datetime.now(timezone.utc).isoformat()}
                    save_manifest(manifest_path, manifest)
                    continue
                # Fall through to validate / emit / DONE

            # --prepare: stop here, wait for LLM output
            elif getattr(args, "prepare", False):
                manifest[comp_path] = {"status": "AWAITING_LLM", "pipeline_status": "AWAITING_LLM"}
                save_manifest(manifest_path, manifest)
                print(f"  → evidence built, awaiting LLM output")
                continue

            # Step 2: Validate (llm_output.json skal være genereret af Copilot LLM her)
            ok = run_step([
                PYTHON,
                str(SCRIPTS_DIR / "validate_llm_output.py"),
                "--component-list", str(temp_list),
                "--raw-dir",        str(raw_dir),
            ], "validate")

            if not ok:
                manifest[comp_path] = {"status": "FAILED", "reason": "validate_failed"}
                save_manifest(manifest_path, manifest)
                continue

            # Step 3: Read status
            summary_path    = raw_dir / "_validation_summary.json"
            pipeline_status = read_component_status(summary_path, name)
            print(f"  pipeline_status: {pipeline_status}")

            is_pass = pipeline_status in ("PASS", "PASS_UI_ONLY")
            is_fail = pipeline_status in ("FAIL",)

            if is_pass:
                # Step 4: Emit to corpus
                run_step([
                    PYTHON,
                    str(SCRIPTS_DIR / "emit_to_jsonl.py"),
                    "--component-list",  str(temp_list),
                    "--raw-dir",         str(raw_dir),
                    "--normalized-dir",  str(corpus_dir),
                ], "emit_to_jsonl")

                if args.auto_mark_done:
                    manifest[comp_path] = {"status": "DONE", "pipeline_status": pipeline_status, "lastProcessed": datetime.now(timezone.utc).isoformat()}
                    print(f"  → DONE")
                    if getattr(args, "auto", False):
                        _cleanup_temp_md(REPO_ROOT / "temp.md")
                else:
                    manifest[comp_path] = {"status": "PENDING_REVIEW", "pipeline_status": pipeline_status, "lastProcessed": None}
                    print(f"  → PENDING_REVIEW (run with --auto-mark-done to commit)")

            elif is_fail and args.auto_mark_done:
                manifest[comp_path] = {"status": "FAILED", "pipeline_status": pipeline_status, "lastProcessed": datetime.now(timezone.utc).isoformat()}
                print(f"  → FAILED")

            else:
                manifest[comp_path] = {"status": "PENDING_REVIEW", "pipeline_status": pipeline_status}
                print(f"  → PENDING_REVIEW [{pipeline_status}]")

            save_manifest(manifest_path, manifest)

        finally:
            temp_list.unlink(missing_ok=True)

        print()

    done    = sum(1 for v in manifest.values() if v.get("status") == "DONE")
    failed  = sum(1 for v in manifest.values() if v.get("status") == "FAILED")
    remaining = total_count - done - failed
    print(f"DONE: {done}/{total_count}  FAILED: {failed}  REMAINING: {remaining}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="ACDDA v4 harvest orchestrator")
    parser.add_argument("--batch-size",     type=int, default=10)
    parser.add_argument("--auto-mark-done", action="store_true",
                        help="Mark DONE/FAILED automatically based on validation result")
    parser.add_argument("--loop",           action="store_true",
                        help="Run batches continuously until all components are DONE/FAILED")
    parser.add_argument("--status",         action="store_true",
                        help="Show manifest status and exit")
    parser.add_argument("--reset",          action="store_true",
                        help="Delete manifest and exit (start harvest from scratch)")
    parser.add_argument("--prepare",        action="store_true",
                        help="Build evidence packs only (generate copilot_prompt.md) — no LLM, no validate")
    parser.add_argument("--finalize",       action="store_true",
                        help="Skip LLM step entirely — assumes llm_output.json written by Copilot chat")
    parser.add_argument("--auto",           action="store_true",
                        help="Full automation: build evidence, poll temp.md for LLM output, validate, emit")
    parser.add_argument("--auto-timeout",   type=int, default=300,
                        dest="auto_timeout",
                        help="Seconds to wait for LLM output in --auto mode (default: 300)")
    parser.add_argument("--component-list", default=r"harvest/component-list.json")
    parser.add_argument("--app-root",
                        default=r"C:\Udvikling\sms-service\ServiceAlert.Web\ClientApp")
    parser.add_argument("--raw-dir",        default=r"harvest/angular/raw")
    parser.add_argument("--corpus-dir",     default=r"corpus")
    parser.add_argument("--manifest",       default=r"harvest/harvest-manifest.json")
    args = parser.parse_args()

    comp_list_path = REPO_ROOT / args.component_list
    manifest_path  = REPO_ROOT / args.manifest
    raw_dir        = REPO_ROOT / args.raw_dir
    corpus_dir     = REPO_ROOT / args.corpus_dir

    if not comp_list_path.exists():
        print(f"ERROR: component-list not found: {comp_list_path}", file=sys.stderr)
        sys.exit(1)

    raw_components = json.loads(comp_list_path.read_text(encoding="utf-8-sig"))
    if raw_components and isinstance(raw_components[0], dict):
        seen_paths: set = set()
        deduped = []
        for c in raw_components:
            p = c.get("path") or c.get("filePath")
            if p in seen_paths:
                print(f"[WARN] Duplicate component-list entry skipped: {p}", file=sys.stderr)
            else:
                seen_paths.add(p)
                deduped.append(c)
        components = [c["path"] for c in deduped]
    else:
        components = raw_components

    if args.reset:
        if manifest_path.exists():
            manifest_path.unlink()
            print(f"Manifest slettet: {manifest_path}")
        else:
            print("Manifest eksisterede ikke — ingenting at nulstille.")
        print(f"Klar til at starte høst forfra ({len(components)} komponenter PENDING).")
        return

    manifest   = load_manifest(manifest_path)

    if args.status:
        print_manifest_status(components, manifest)
        return

    if args.loop:
        round_num = 0
        while True:
            pending = [c for c in components
                       if manifest.get(c, {}).get("status") not in ("DONE", "FAILED")]
            if not pending:
                done    = sum(1 for v in manifest.values() if v.get("status") == "DONE")
                failed  = sum(1 for v in manifest.values() if v.get("status") == "FAILED")
                print(f"All components processed. DONE: {done}  FAILED: {failed}")
                break
            round_num += 1
            done_so_far = sum(1 for v in manifest.values() if v.get("status") == "DONE")
            print(f"══ ROUND {round_num} — {len(pending)} pending  (done: {done_so_far}/{len(components)}) ══")
            args.loop = False  # avoid recursion flag confusion
            _run_batch(args, components, manifest, manifest_path, raw_dir, corpus_dir)
            args.loop = True
            manifest = load_manifest(manifest_path)  # reload after batch
        return

    _run_batch(args, components, manifest, manifest_path, raw_dir, corpus_dir)


if __name__ == "__main__":
    main()
