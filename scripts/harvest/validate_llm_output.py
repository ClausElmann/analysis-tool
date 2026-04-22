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
from datetime import datetime
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
        # Also accept service methods from service_http_calls
        method_in_service = next(
            (h for h in (pack.get("service_http_calls") or []) if h.get("service_method") == flow["method"]),
            None,
        )
        if not method_in_service:
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


# ── Step 3: Truth gate ─────────────────────────────────────────────────────────
_HTTP_VERBS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}


def is_provable_from_evidence(item: dict, pack: dict) -> bool:
    """Return True if item is directly traceable to data in evidence_pack."""
    http_calls = (pack.get("service_http_calls") or []) + (pack.get("direct_http_calls") or [])
    http_methods_in_pack = {(h.get("service_method") or "").strip() for h in http_calls}
    http_urls_in_pack = {(h.get("url") or "").strip() for h in http_calls if h.get("url")}

    method = (item.get("method") or "").strip()
    http_str = (item.get("http") or "").strip()
    endpoint = (item.get("endpoint") or "").strip()
    check_url = http_str.split(" ", 1)[-1].strip() if " " in http_str else (http_str or endpoint)

    # HTTP verbs (GET/POST/...) are not service method names — skip service_method check
    if method and method.upper() not in _HTTP_VERBS and method not in http_methods_in_pack:
        return False
    if check_url:
        matched = any(
            check_url in u or u in check_url or check_url.split("/")[-1] == u.split("/")[-1]
            for u in http_urls_in_pack if u
        )
        if not matched:
            return False
    return bool(method or check_url)  # must have at least one traceable field


def _classify_behavior(b: dict, pack: dict) -> str:
    """VERIFIED_UI if evidence_method matches a template_action handler; INFERRED_UI otherwise."""
    evidence_method = (b.get("evidence_method") or "").strip()
    if evidence_method:
        handlers = {a.get("handler", "") for a in (pack.get("template_actions") or [])}
        if evidence_method in handlers:
            return "VERIFIED_UI"
    return "INFERRED_UI"


def _build_deterministic_flows(pack: dict, source_file: str) -> tuple[list, list]:
    """
    Build VERIFIED_STRUCTURAL flows + requirements from evidence_pack deterministically.
    No LLM dependency.

    Returns (flows, requirements)
    """
    flows = []
    requirements = []
    ts = datetime.utcnow().isoformat() + "Z"

    shc = pack.get("service_http_calls") or []
    method_graph = pack.get("method_graph") or {}
    lifecycle_flows = pack.get("lifecycle_flows") or []
    template_actions = pack.get("template_actions") or []

    # Build lookup: service_method → http entry
    shc_by_method: dict[str, dict] = {h["service_method"]: h for h in shc}

    emitted_flow_keys: set[tuple] = set()

    def _emit_flow(trigger: str, method: str, service_call: str, h: dict) -> None:
        key = (trigger, h.get("service_method", ""), h.get("url", ""))
        if key in emitted_flow_keys:
            return
        emitted_flow_keys.add(key)
        flows.append({
            "trigger": trigger,
            "method": method,
            "service_call": service_call,
            "http": f"{h.get('http_method', '?')} {h.get('url', '')}",
            "result": f"HTTP {h.get('http_method', '?')} til {h.get('service', '')}",
            "status": "PASS",
            "classification": "VERIFIED_STRUCTURAL",
            "pipeline_status": "VERIFIED_STRUCTURAL",
            "evidence_ids": [h.get("url", "")],
            "source_files": [source_file],
            "confidence_score": 0.95,
        })

    # 1. Template handlers via method_graph
    template_handler_names = {a.get("handler", "") for a in template_actions}
    for handler in template_handler_names:
        if not handler:
            continue
        bridged = method_graph.get(handler, [])
        for svc_method in bridged:
            if svc_method in shc_by_method:
                h = shc_by_method[svc_method]
                _emit_flow(
                    trigger=f"user:{handler}",
                    method=handler,
                    service_call=f"{h.get('service', '?')}.{svc_method}()",
                    h=h,
                )

    # 2. Direct: template handler IS already a service_method (1-hop)
    for handler in template_handler_names:
        if handler and handler in shc_by_method:
            h = shc_by_method[handler]
            _emit_flow(
                trigger=f"user:{handler}",
                method=handler,
                service_call=f"{h.get('service', '?')}.{handler}()",
                h=h,
            )

    # 3. Lifecycle flows (ngOnInit, constructor, ngOnChanges)
    for lf in lifecycle_flows:
        svc_method = lf.get("service_method", "")
        if svc_method in shc_by_method:
            h = shc_by_method[svc_method]
            _emit_flow(
                trigger=f"component_init:{lf.get('lifecycle', 'ngOnInit')}",
                method=lf.get("lifecycle", "ngOnInit"),
                service_call=f"{h.get('service', '?')}.{svc_method}()",
                h=h,
            )

    # 4. Requirements — one per unique service_http_call
    seen_endpoints: set[str] = set()
    for h in shc:
        url = h.get("url", "")
        if url and url not in seen_endpoints:
            seen_endpoints.add(url)
            requirements.append({
                "method": h.get("http_method", "?"),
                "endpoint": url,
                "type": "QUERY" if h.get("http_method") == "GET" else "COMMAND",
                "evidence_method": h.get("service_method", ""),
                "status": "PASS",
                "classification": "VERIFIED_STRUCTURAL",
                "pipeline_status": "VERIFIED_STRUCTURAL",
                "evidence_ids": [url],
                "source_files": [source_file],
                "confidence_score": 0.95,
            })

    return flows, requirements


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
        # No LLM output — deterministic-only mode (SMART/CONTAINER get flows from evidence_pack)
        llm = {"behaviors": [], "flows": [], "requirements": [], "ui_behaviors": []}
    else:
        llm = None  # will be loaded below

    try:
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        if llm is None:
            llm = json.loads(llm_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"  [ERROR] could not parse JSON for {comp_name}: {exc}")
        summary.append({"component": comp_name, "status": "FAIL", "type": "?",
                        "b_pass": 0, "b_reject": 0, "f_pass": 0, "r_pass": 0})
        continue
    is_dumb = pack["meta"]["type"] in ("DUMB", "CONTAINER")
    pack_methods = pack.get("ts_methods") or []

    # Validate behaviors
    b_pass = b_reject = 0
    v_behaviors = []
    for b in (llm.get("behaviors") or []):
        if isinstance(b, str):
            b = {"text": b}
        if not b.get("text"):
            continue
        r = test_behavior_text(b["text"], pack_methods)
        if r["valid"]:
            b_pass += 1
            cls = _classify_behavior(b, pack)
            v_behaviors.append({
                "text": b["text"],
                "evidence_method": b.get("evidence_method"),
                "confidence": b.get("confidence"),
                "status": "PASS",
                "classification": cls,
                "pipeline_status": cls,
            })
        else:
            b_reject += 1
            v_behaviors.append({"text": b["text"], "status": "REJECTED", "reason": r["reason"]})

    # Validate flows (DUMB: skip)
    f_pass = f_reject = 0
    v_flows = []
    if not is_dumb:
        # ── TRIN 3: Deterministic flows from evidence_pack (replaces LLM flows) ──
        det_flows, det_reqs = _build_deterministic_flows(pack, pack["meta"].get("file", ""))
        v_flows = det_flows
        f_pass = len(det_flows)
        # Also try LLM flows that are NOT covered by deterministic — keep if valid+provable
        for f in (llm.get("flows") or []):
            if not f or isinstance(f, str):
                continue
            r = test_flow_chain(f, pack)
            if r["valid"] and is_provable_from_evidence(f, pack):
                # Avoid duplicate trigger+method combos already covered deterministically
                dup = any(
                    df.get("trigger") == f.get("trigger") and df.get("method") == f.get("method")
                    for df in v_flows
                )
                if not dup:
                    ev_ids = [
                        h.get("url") for h in (pack.get("service_http_calls") or [])
                        if h.get("service_method") == f.get("method") and h.get("url")
                    ]
                    v_flows.append({
                        **f,
                        "status": "PASS",
                        "classification": "VERIFIED_STRUCTURAL",
                        "pipeline_status": "VERIFIED_STRUCTURAL",
                        "evidence_ids": ev_ids,
                        "source_files": [pack["meta"].get("file", "")],
                        "confidence_score": f.get("confidence", 0.0),
                    })
                    f_pass += 1
            else:
                f_reject += 1

    # Validate requirements (DUMB: skip)
    r_pass = r_reject = 0
    v_reqs = []
    if not is_dumb:
        # ── TRIN 3: Deterministic requirements from evidence_pack ──
        v_reqs = det_reqs  # already built above
        r_pass = len(det_reqs)
        # Also keep valid+provable LLM requirements not already covered
        for req in (llm.get("requirements") or []):
            if not req or isinstance(req, str):
                continue
            r = test_requirement(req, pack)
            if r["valid"] and is_provable_from_evidence(req, pack):
                dup = any(
                    dr.get("endpoint") == req.get("endpoint")
                    for dr in v_reqs
                )
                if not dup:
                    all_http = (pack.get("service_http_calls") or []) + (pack.get("direct_http_calls") or [])
                    req_ep = (req.get("endpoint") or "").lstrip("/")
                    ev_ids = [
                        h.get("url") for h in all_http
                        if h.get("url") and (req_ep in h["url"] or h["url"] in req_ep)
                    ]
                    v_reqs.append({
                        **req,
                        "status": "PASS",
                        "classification": "VERIFIED_STRUCTURAL",
                        "pipeline_status": "VERIFIED_STRUCTURAL",
                        "evidence_ids": ev_ids,
                        "source_files": [pack["meta"].get("file", "")],
                        "confidence_score": 0.7,
                    })
                    r_pass += 1
            else:
                r_reject += 1

    # UI behaviors (DUMB/CONTAINER) — wrapped with VERIFIED_UI classification
    ui_behaviors = []
    if is_dumb:
        raw_ui = llm.get("ui_behaviors") or []
        if not raw_ui and b_pass > 0:
            raw_ui = [b["text"] for b in v_behaviors if b["status"] == "PASS"]
        for u in raw_ui:
            text = u if isinstance(u, str) else u.get("text", "")
            if text:
                ui_behaviors.append({"text": text, "classification": "VERIFIED_UI"})

    # Score per component
    if is_dumb:
        status = "VERIFIED_UI" if ui_behaviors else "VERIFIED_STRUCTURAL_NULL"
    else:
        if b_pass >= 2:
            status = "PASS"
        elif b_pass >= 1 or f_pass >= 1 or r_pass >= 1:
            status = "PARTIAL"
        elif _has_no_backend:
            status = "VERIFIED_STRUCTURAL_NULL"
        else:
            status = "FAIL"

    # Step 3: Compute component-level pipeline_status
    verified_flows = [f for f in v_flows if f.get("pipeline_status") == "VERIFIED_STRUCTURAL"]
    verified_reqs  = [r for r in v_reqs  if r.get("pipeline_status") == "VERIFIED_STRUCTURAL"]

    # VERIFIED_STRUCTURAL_NULL: evidence pack parsed OK but component has no backend calls
    # (no service_http_calls, no method_graph entries, no lifecycle_flows)
    # This is a valid structural state — not a failure.
    _has_no_backend = (
        len(pack.get("service_http_calls") or []) == 0
        and len(pack.get("method_graph") or {}) == 0
        and len(pack.get("lifecycle_flows") or []) == 0
    )

    if is_dumb:
        if ui_behaviors:
            pipeline_status = "VERIFIED_UI"
        elif _has_no_backend:
            pipeline_status = "VERIFIED_STRUCTURAL_NULL"
        else:
            pipeline_status = "FAIL"
    else:
        if verified_flows or verified_reqs:
            pipeline_status = "VERIFIED_STRUCTURAL"
        elif _has_no_backend:
            # SMART/CONTAINER with no backend evidence — structurally clean, just frontend-only
            pipeline_status = "VERIFIED_STRUCTURAL_NULL"
        elif b_pass >= 1 or f_pass >= 1 or r_pass >= 1:
            pipeline_status = "INFERRED_UI"
        else:
            # FAIL only if: service_http_calls exist but could not be matched
            shc_count = len(pack.get("service_http_calls") or [])
            if shc_count > 0:
                pipeline_status = "FAIL"
            else:
                pipeline_status = "VERIFIED_STRUCTURAL_NULL"

    # Step 8: Output contract — pipeline_status + classification in validated output
    validated = {
        "component": comp_name,
        "type": pack["meta"]["type"],
        "status": status,
        "pipeline_status": pipeline_status,
        "behaviors": v_behaviors,
        "flows": v_flows,
        "requirements": v_reqs,
        "ui_behaviors": ui_behaviors,
    }
    valid_path.write_text(json.dumps(validated, indent=2, ensure_ascii=False), encoding="utf-8")

    summary.append({
        "component": comp_name,
        "status": status,
        "pipeline_status": pipeline_status,
        "type": pack["meta"]["type"],
        "b_pass": b_pass,
        "b_reject": b_reject,
        "f_pass": f_pass,
        "r_pass": r_pass,
    })
    print(f"  {comp_name:<48} [{pack['meta']['type']:<10}] {pipeline_status:<14} "
          f"b={b_pass}/{b_pass+b_reject} f={f_pass} r={r_pass}")

# Write summary
summary_path = RAW_DIR / "_validation_summary.json"
summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
print()
print(f"Summary written: {summary_path}")
