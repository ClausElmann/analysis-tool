"""
ACDDA v4 - Phase 3a: Validation
Validates llm_output.json against evidence_pack.json.
Writes llm_output_validated.json + _validation_summary.json per component.

Usage:
    python validate_llm_output.py [--component-list FILE] [--raw-dir DIR]
"""

import argparse
import json
import re
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--component-list", default=r".\harvest\component-list.json")
parser.add_argument("--raw-dir", default=r".\harvest\angular\raw")
args = parser.parse_args()

COMPONENT_LIST = Path(args.component_list)
RAW_DIR = Path(args.raw_dir)

# Domain violation words — hard REJECT
REJECT_WORDS = {
    "component", "service", "method", "load", "init", "fetch",
    "handler", "initialize", "subscribe", "observable", "lifecycle",
}


def test_behavior_text(text: str, methods: list) -> dict:
    if not text or len(text.strip()) < 4:
        return {"valid": False, "reason": "too_short"}
    # camelCase
    if re.search(r"[a-z][A-Z]", text):
        return {"valid": False, "reason": "camelCase"}
    # Too long
    if len(text.strip().split()) > 10:
        return {"valid": False, "reason": "too_long"}
    # Exact method name match (case-insensitive, both raw and expanded)
    text_lower = text.lower().strip()
    for m in methods:
        expanded = re.sub(r"([A-Z])", r" \1", m["name"]).strip().lower()
        if text_lower == expanded or text_lower == m["name"].lower():
            return {"valid": False, "reason": "method_name_match"}
    # Domain violation — hard REJECT
    for w in REJECT_WORDS:
        if re.search(rf"\b{re.escape(w)}\b", text_lower):
            return {"valid": False, "reason": f"domain_violation:{w}"}
    return {"valid": True}


def test_flow_chain(flow: dict, pack: dict) -> dict:
    if not flow.get("method"):
        return {"valid": False, "reason": "missing_method"}

    method_in_pack = next(
        (m for m in (pack.get("ts_methods") or []) if m["name"] == flow["method"]),
        None,
    )
    if not method_in_pack:
        return {"valid": False, "reason": f"method_not_in_pack:{flow['method']}"}

    if not flow.get("service_call"):
        return {"valid": False, "reason": "missing_service_call"}

    svc_m = re.search(r"\.([a-zA-Z0-9_]+)\(\)$", flow["service_call"])
    if not svc_m:
        return {"valid": False, "reason": "service_call_format"}
    svc_method = svc_m.group(1)

    http_in_pack = [
        h for h in (pack.get("service_http_calls") or [])
        if h.get("service_method") == svc_method
    ]
    if not http_in_pack:
        direct = pack.get("direct_http_calls") or []
        if not direct:
            return {"valid": False, "reason": f"service_call_not_traced:{svc_method}"}

    if (flow.get("confidence") or 1.0) < 0.70:
        return {"valid": False, "reason": "low_confidence"}

    return {"valid": True}


def test_requirement(req: dict, pack: dict) -> dict:
    if not req.get("endpoint"):
        return {"valid": False, "reason": "missing_endpoint"}

    all_urls = []
    for h in (pack.get("service_http_calls") or []):
        if h.get("url"):
            all_urls.append(h["url"])
    for h in (pack.get("direct_http_calls") or []):
        if h.get("url"):
            all_urls.append(h["url"])

    req_url = req["endpoint"].lstrip("/")

    def urls_match(pu: str, ru: str) -> bool:
        pu = pu.lstrip("/")
        return (
            pu in ru
            or ru in pu
            or pu.split("/")[-1] == ru.split("/")[-1]
            or pu.startswith("{ApiRoutes")  # ApiRoutes traced — accept
        )

    found = any(urls_match(u, req_url) for u in all_urls)
    if not found:
        return {"valid": False, "reason": f"endpoint_not_in_evidence:{req_url}"}
    return {"valid": True}


# ── Main ───────────────────────────────────────────────────────────────────────
if not COMPONENT_LIST.exists():
    print(f"ERROR: Not found: {COMPONENT_LIST}", file=sys.stderr)
    sys.exit(1)

entries = json.loads(COMPONENT_LIST.read_text(encoding="utf-8-sig"))
summary = []

print(f"ACDDA v4 - validate_llm_output ({len(entries)} components)")
print()

for entry in entries:
    if isinstance(entry, str):
        comp_path = entry
    elif isinstance(entry, dict):
        comp_path = entry.get("path") or entry.get("filePath") or str(entry)
    else:
        comp_path = str(entry)
    comp_name = Path(comp_path).stem.replace(".component", "")

    pack_path  = RAW_DIR / comp_name / "evidence_pack.json"
    llm_path   = RAW_DIR / comp_name / "llm_output.json"
    valid_path = RAW_DIR / comp_name / "llm_output_validated.json"

    if not pack_path.exists():
        print(f"  SKIP (no evidence_pack): {comp_name}")
        summary.append({"component": comp_name, "status": "NO_PACK", "type": "?",
                        "b_pass": 0, "b_reject": 0, "f_pass": 0, "r_pass": 0})
        continue
    if not llm_path.exists():
        print(f"  SKIP (no llm_output): {comp_name}")
        summary.append({"component": comp_name, "status": "NO_LLM_OUTPUT", "type": "?",
                        "b_pass": 0, "b_reject": 0, "f_pass": 0, "r_pass": 0})
        continue

    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    llm  = json.loads(llm_path.read_text(encoding="utf-8"))
    is_dumb = pack["meta"]["type"] in ("DUMB", "CONTAINER")
    pack_methods = pack.get("ts_methods") or []

    # Validate behaviors
    b_pass = b_reject = 0
    v_behaviors = []
    for b in (llm.get("behaviors") or []):
        if not b.get("text"):
            continue
        r = test_behavior_text(b["text"], pack_methods)
        if r["valid"]:
            b_pass += 1
            v_behaviors.append({
                "text": b["text"],
                "evidence_method": b.get("evidence_method"),
                "confidence": b.get("confidence"),
                "status": "PASS",
            })
        else:
            b_reject += 1
            v_behaviors.append({"text": b["text"], "status": "REJECTED", "reason": r["reason"]})

    # Validate flows (DUMB: skip)
    f_pass = f_reject = 0
    v_flows = []
    if not is_dumb:
        for f in (llm.get("flows") or []):
            if not f:
                continue
            r = test_flow_chain(f, pack)
            if r["valid"]:
                f_pass += 1
                v_flows.append({**f, "status": "PASS"})
            else:
                f_reject += 1
                v_flows.append({"trigger": f.get("trigger"), "method": f.get("method"),
                                "status": "REJECTED", "reason": r["reason"]})

    # Validate requirements (DUMB: skip)
    r_pass = r_reject = 0
    v_reqs = []
    if not is_dumb:
        for req in (llm.get("requirements") or []):
            if not req:
                continue
            r = test_requirement(req, pack)
            if r["valid"]:
                r_pass += 1
                v_reqs.append({**req, "status": "PASS"})
            else:
                r_reject += 1
                v_reqs.append({"endpoint": req.get("endpoint"), "status": "REJECTED",
                               "reason": r["reason"]})

    # UI behaviors (DUMB only)
    ui_behaviors = []
    if is_dumb:
        ui_behaviors = llm.get("ui_behaviors") or []
        if not ui_behaviors and b_pass > 0:
            ui_behaviors = [b["text"] for b in v_behaviors if b["status"] == "PASS"]

    # Score per component
    if is_dumb:
        status = "PASS_UI_ONLY" if (b_pass > 0 or ui_behaviors) else "SKIP_UI_ONLY"
    else:
        if b_pass >= 2:
            status = "PASS"
        elif b_pass >= 1 or f_pass >= 1 or r_pass >= 1:
            status = "PARTIAL"
        else:
            status = "FAIL"

    validated = {
        "component": comp_name,
        "type": pack["meta"]["type"],
        "status": status,
        "behaviors": v_behaviors,
        "flows": v_flows,
        "requirements": v_reqs,
        "ui_behaviors": ui_behaviors,
    }
    valid_path.write_text(json.dumps(validated, indent=2, ensure_ascii=False), encoding="utf-8")

    summary.append({
        "component": comp_name,
        "status": status,
        "type": pack["meta"]["type"],
        "b_pass": b_pass,
        "b_reject": b_reject,
        "f_pass": f_pass,
        "r_pass": r_pass,
    })
    print(f"  {comp_name:<48} [{pack['meta']['type']:<10}] {status:<14} "
          f"b={b_pass}/{b_pass+b_reject} f={f_pass} r={r_pass}")

# Write summary
summary_path = RAW_DIR / "_validation_summary.json"
summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
print()
print(f"Summary written: {summary_path}")
