"""
FULL HARVEST RESET — CLEAN STATE FOR 100% RUN
Slet genererede artefakter, reset manifest, behold source data.
"""
import json, shutil
from pathlib import Path

CORPUS  = Path("corpus")
LAYER2  = Path("harvest/layer2")
HARVEST = Path("harvest")
TEMP_MD = Path("temp.md")

deleted = []
kept    = []
errors  = []

def rm(p):
    p = Path(p)
    if p.exists():
        p.unlink()
        deleted.append(str(p))
    # else silently skip

# ── TRIN 1 — Slet corpus JSONL (behold capabilities.json) ────────────────────
for fname in ["flows.jsonl","requirements.jsonl","ui_behaviors_verified.jsonl",
              "ui_behaviors_inferred.jsonl","rejected_outputs.jsonl"]:
    rm(CORPUS / fname)
# Behold
cap_json = CORPUS / "capabilities.json"
kept.append(str(cap_json) + (" (exists)" if cap_json.exists() else " (not present)"))

# ── TRIN 2 — Slet layer2 output ───────────────────────────────────────────────
for fname in ["capabilities_detailed.json","capabilities_grouped.json",
              "domains_grouped.json","domains.json","gaps.json","capabilities.json"]:
    rm(LAYER2 / fname)

# ── TRIN 3 — Slet llm_output*.json ───────────────────────────────────────────
for p in HARVEST.rglob("llm_output.json"):
    rm(p)
for p in HARVEST.rglob("llm_output_validated.json"):
    rm(p)

# ── TRIN 4 — Slet evidence_pack.json ─────────────────────────────────────────
for p in HARVEST.rglob("evidence_pack.json"):
    rm(p)

# ── TRIN 5 — Reset manifest ───────────────────────────────────────────────────
manifest_path = HARVEST / "harvest-manifest.json"
manifest_reset_count = 0
if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    for key in manifest:
        manifest[key]["status"] = "PENDING"
        # Remove history fields if present
        for field in ["done_at","failed_at","skip_reason","pipeline_status"]:
            manifest[key].pop(field, None)
        manifest_reset_count += 1
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    deleted.append(f"[manifest reset] {manifest_reset_count} components → PENDING")
else:
    errors.append("harvest-manifest.json not found!")

# ── TRIN 6 — Ryd temp files ───────────────────────────────────────────────────
for p in list(HARVEST.glob("_seq_tmp_*.json")) + list(HARVEST.glob("tmp*.json")):
    if p.is_file():
        rm(p)

# ── TRIN 7 — Reset audit ─────────────────────────────────────────────────────
audit_path = HARVEST / "harvest_audit.jsonl"
if audit_path.exists():
    audit_path.unlink()
    deleted.append(str(audit_path))
audit_path.write_text("", encoding="utf-8")

# ── TRIN 8 — Verification check ──────────────────────────────────────────────
manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
total_comp     = len(manifest)
pending_count  = sum(1 for v in manifest.values() if v.get("status") == "PENDING")
done_count     = sum(1 for v in manifest.values() if v.get("status") == "DONE")
skipped_count  = sum(1 for v in manifest.values() if v.get("status") == "SKIPPED")
failed_count   = sum(1 for v in manifest.values() if v.get("status") == "FAILED")

corpus_files   = [f.name for f in CORPUS.iterdir() if f.is_file()] if CORPUS.exists() else []
layer2_files   = [f.name for f in LAYER2.iterdir() if f.is_file()] if LAYER2.exists() else []
remaining_eps  = list(HARVEST.rglob("evidence_pack.json"))
remaining_llm  = list(HARVEST.rglob("llm_output.json")) + list(HARVEST.rglob("llm_output_validated.json"))

print(f"total_components:  {total_comp}")
print(f"PENDING:           {pending_count}")
print(f"DONE:              {done_count}")
print(f"SKIPPED:           {skipped_count}")
print(f"FAILED:            {failed_count}")
print(f"corpus_files:      {corpus_files}")
print(f"layer2_files:      {layer2_files}")
print(f"evidence_packs:    {len(remaining_eps)}")
print(f"llm_outputs:       {len(remaining_llm)}")
print(f"deleted:           {len(deleted)} items")
print(f"errors:            {errors}")

stop_ok = (done_count == 0 and pending_count == total_comp
           and len(remaining_eps) == 0 and len(remaining_llm) == 0)
# corpus: only capabilities.json allowed
corpus_clean = all(f in ("capabilities.json", "capabilities.jsonl") for f in corpus_files)

stop_cond = "HARVEST_RESET_COMPLETE" if (stop_ok and corpus_clean) else (
    f"RESET_INCOMPLETE: DONE={done_count} pending={pending_count}/{total_comp} "
    f"eps={len(remaining_eps)} llm={len(remaining_llm)} corpus={corpus_files}"
)
print(stop_cond)

# ── Write temp.md ─────────────────────────────────────────────────────────────
report = f"""
## HARVEST_RESET_COMPLETE — 2026-04-22

### TRIN 1–7 — Slettet / nulstillet

| Action | Resultat |
|---|---|
| corpus JSONL slettet | {sum(1 for d in deleted if 'corpus' in d)} filer |
| layer2 output slettet | {sum(1 for d in deleted if 'layer2' in d)} filer |
| evidence_packs slettet | {sum(1 for d in deleted if 'evidence_pack' in d)} filer |
| llm_output slettet | {sum(1 for d in deleted if 'llm_output' in d)} filer |
| manifest reset | {manifest_reset_count} komponenter → PENDING |
| temp-filer slettet | {sum(1 for d in deleted if '_seq_tmp_' in d or ('tmp' in d and 'harvest' in d))} filer |
| audit nulstillet | tom fil oprettet |

### TRIN 8 — Verification

| Check | Resultat | Krav | Status |
|---|---|---|---|
| total_components | {total_comp} | | |
| PENDING | {pending_count} | = total | {"✅" if pending_count == total_comp else "❌"} |
| DONE | {done_count} | = 0 | {"✅" if done_count == 0 else "❌"} |
| SKIPPED | {skipped_count} | | |
| FAILED | {failed_count} | | |
| corpus tom (excl. capabilities.json) | {corpus_files} | kun capabilities.json | {"✅" if corpus_clean else "❌"} |
| layer2 tom | {layer2_files if layer2_files else "[]"} | tom | {"✅" if not layer2_files else "❌"} |
| evidence_packs | {len(remaining_eps)} | = 0 | {"✅" if len(remaining_eps) == 0 else "❌"} |
| llm_outputs | {len(remaining_llm)} | = 0 | {"✅" if len(remaining_llm) == 0 else "❌"} |

{stop_cond}

---
"""

existing = TEMP_MD.read_text(encoding="utf-8")
TEMP_MD.write_text(existing + "\n" + report.lstrip("\n"), encoding="utf-8")
print("temp.md updated.")
