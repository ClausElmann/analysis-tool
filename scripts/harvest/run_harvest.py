"""
ACDDA v4 - Harvest Orchestrator
Runs the full harvest pipeline for a batch of Angular components.

Normal workflow (Copilot chat som LLM):
    1. --prepare   → byg evidence packs + skriv copilot_prompt.md per komponent
    2. Copilot læser prompt og skriver llm_output.json (dette chat-vindue)
    3. --finalize  → validate + emit til corpus/ (LLM-step springes over)

Automatisk workflow (Copilot API, kræver GITHUB_TOKEN):
    python scripts/harvest/run_harvest.py --batch-size 10 --auto-mark-done

Manifest:
    harvest/harvest-manifest.json  — tracks status per component (DONE/FAILED/PENDING)
    Status DONE er KUN sat via pass_rate >= 0.75 (PASS or PASS_UI_ONLY) + validated output.
    Status DONE sættes ALDRIG manuelt.

Pipeline per component:
    1. build_evidence_packs.py  — structural extraction (no LLM)
    2. LLM step                 — Copilot chat skriver llm_output.json (eller API-kald)
    3. validate_llm_output.py   — validates against evidence_pack
    4. emit_to_jsonl.py         — appends to corpus/ (PASS only)
    5. manifest update          — DONE | FAILED
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
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


def call_llm(prompt_path: Path, output_path: Path) -> bool:
    """Call GitHub Copilot API with copilot_prompt.md → write llm_output.json."""
    if not prompt_path.exists():
        print(f"  [FAIL] LLM: prompt not found: {prompt_path}")
        return False

    sys.path.insert(0, str(REPO_ROOT))
    try:
        from core.ai_processor import CopilotAIProcessor  # type: ignore
    except ImportError as exc:
        print(f"  [FAIL] LLM: cannot import CopilotAIProcessor: {exc}")
        return False

    try:
        processor = CopilotAIProcessor(model="gpt-4.1", temperature=0.2)
    except ValueError as exc:
        print(f"  [FAIL] LLM: {exc}")
        return False

    prompt_text = prompt_path.read_text(encoding="utf-8")

    system_prompt = (
        "You are a domain knowledge extraction engine for an Angular application. "
        "Extract ONLY what the user can DO — not code internals. "
        "NEVER copy source code, method names, or implementation details. "
        "ALWAYS extract user-visible intent and capability. "
        "ALWAYS use normalized domain language. "
        "ALWAYS return strict JSON matching the schema in the prompt."
    )

    try:
        response = processor._client.chat.completions.create(
            model=processor._model,
            temperature=processor._temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_text},
            ],
        )
        raw = response.choices[0].message.content or "{}"
        output_path.write_text(raw, encoding="utf-8")
        return True
    except Exception as exc:
        print(f"  [FAIL] LLM call: {exc}")
        return False


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


# ── Batch runner ──────────────────────────────────────────────────────────────

def _run_batch(args, components: list, manifest: dict, manifest_path: Path,
               raw_dir: Path, corpus_dir: Path) -> None:
    pending = [c for c in components
               if manifest.get(c, {}).get("status") not in ("DONE", "FAILED")]
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
            # ── Step 1: Build evidence pack ────────────────────────────────
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

            # ── Step 2: LLM ────────────────────────────────────────────────
            prompt_path  = raw_dir / name / "copilot_prompt.md"
            llm_out_path = raw_dir / name / "llm_output.json"

            if args.prepare:
                print(f"  [READY] Prompt: {prompt_path}")
                print(f"          Skriv output til: {llm_out_path}")
                continue  # stop after evidence pack — Copilot chat handles LLM step

            if llm_out_path.exists():
                print(f"  [SKIP] LLM — reusing existing llm_output.json")
            elif args.finalize:
                print(f"  [FAIL] --finalize: llm_output.json mangler for {name}")
                print(f"         Læs prompt: {prompt_path}")
                manifest[comp_path] = {"status": "FAILED", "reason": "llm_output_missing"}
                save_manifest(manifest_path, manifest)
                continue
            else:
                ok = call_llm(prompt_path, llm_out_path)
                if not ok:
                    manifest[comp_path] = {"status": "FAILED", "reason": "llm_failed"}
                    save_manifest(manifest_path, manifest)
                    continue

            # ── Step 3: Validate ───────────────────────────────────────────
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

            # ── Step 4: Read status ────────────────────────────────────────
            summary_path    = raw_dir / "_validation_summary.json"
            pipeline_status = read_component_status(summary_path, name)
            print(f"  pipeline_status: {pipeline_status}")

            is_pass = pipeline_status in ("PASS", "PASS_UI_ONLY")
            is_fail = pipeline_status in ("FAIL",)

            if is_pass:
                # ── Step 5: Emit to corpus ─────────────────────────────────
                run_step([
                    PYTHON,
                    str(SCRIPTS_DIR / "emit_to_jsonl.py"),
                    "--component-list",  str(temp_list),
                    "--raw-dir",         str(raw_dir),
                    "--normalized-dir",  str(corpus_dir),
                ], "emit_to_jsonl")

                if args.auto_mark_done:
                    manifest[comp_path] = {"status": "DONE", "pipeline_status": pipeline_status}
                    print(f"  → DONE")
                else:
                    manifest[comp_path] = {"status": "PENDING_REVIEW", "pipeline_status": pipeline_status}
                    print(f"  → PENDING_REVIEW (run with --auto-mark-done to commit)")

            elif is_fail and args.auto_mark_done:
                manifest[comp_path] = {"status": "FAILED", "pipeline_status": pipeline_status}
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

    components = json.loads(comp_list_path.read_text(encoding="utf-8-sig"))

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
