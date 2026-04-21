"""
ACDDA v4 - Phase 1: Discovery
Builds evidence_pack.json + copilot_prompt.md per component.
NO LLM. NO domain interpretation. Structural extraction only.

Usage:
    python build_evidence_packs.py [--component-list FILE] [--app-root DIR] [--output-dir DIR]
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ── Argument parsing ──────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--component-list", default=r".\harvest\component-list.json")
parser.add_argument("--app-root", default=r"C:\Udvikling\sms-service\ServiceAlert.Web\ClientApp")
parser.add_argument("--output-dir", default=r".\harvest\angular\raw")
args = parser.parse_args()

COMPONENT_LIST = Path(args.component_list)
APP_ROOT = Path(args.app_root)
OUTPUT_DIR = Path(args.output_dir)


# ── Alias map from tsconfig ────────────────────────────────────────────────────
def get_alias_map(root: Path) -> dict:
    alias_map = {}
    tsconfig = root / "tsconfig.json"
    if tsconfig.exists():
        try:
            data = json.loads(tsconfig.read_text(encoding="utf-8"))
            paths = (data.get("compilerOptions") or {}).get("paths") or {}
            for alias, targets in paths.items():
                key = alias.rstrip("/*")
                if targets:
                    rel = targets[0].rstrip("/*").lstrip("./")
                    alias_map[key] = root / rel
        except Exception:
            pass
    # Fallback guesses
    for a in ("@core", "@app", "@shared", "@features", "@environments"):
        if a not in alias_map:
            candidate = root / "src" / "app" / a.lstrip("@")
            if candidate.exists():
                alias_map[a] = candidate
    return alias_map


# ── Find service implementation file ──────────────────────────────────────────
def find_service_file(class_name: str, root: Path) -> str | None:
    pattern = f"export class {class_name}"
    for f in root.rglob("*.ts"):
        try:
            if pattern in f.read_text(encoding="utf-8", errors="ignore"):
                return str(f)
        except Exception:
            pass
    return None


# ── Extract template actions from HTML ────────────────────────────────────────
def get_template_actions(html: str) -> list:
    if not html:
        return []
    result = []
    for i, line in enumerate(html.splitlines(), 1):
        # (click)="handler()"
        for m in re.finditer(r'\(click\)\s*=\s*"([^"$][^"]*)"', line):
            h = re.sub(r"\(.*$", "", m.group(1)).strip().strip("!")
            if h and len(h) > 1:
                result.append({"type": "click", "handler": h, "line": i})
        # (ngSubmit)="handler()"
        for m in re.finditer(r'\(ngSubmit\)\s*=\s*"([^"$][^"]*)"', line):
            h = re.sub(r"\(.*$", "", m.group(1)).strip()
            if h:
                result.append({"type": "submit", "handler": h, "element": "form", "line": i})
        # *ngIf="expr"
        for m in re.finditer(r'\*ngIf\s*=\s*"([^"]+)"', line):
            expr = m.group(1).strip()
            if expr.lower() not in ("true", "false"):
                result.append({"type": "ngIf", "expression": expr, "line": i})
        # [disabled]="expr"
        for m in re.finditer(r'\[disabled\]\s*=\s*"([^"]+)"', line):
            result.append({"type": "disabled", "expression": m.group(1).strip(), "line": i})
    return result


# ── Extract TS methods ─────────────────────────────────────────────────────────
def get_ts_methods(ts: str) -> list:
    result = []
    lines = ts.splitlines()
    lifecycle = {"ngOnInit", "ngOnDestroy", "ngOnChanges", "ngAfterViewInit",
                 "constructor", "ngAfterContentInit"}
    skip = {"if", "for", "while", "switch", "catch", "class", "get", "set",
            "return", "throw"}
    no_svc = {"router", "route", "form", "fb", "snackBar", "dialog", "translate",
              "store", "logger", "cdr", "ref", "renderer", "el"}

    method_re = re.compile(
        r"^\s+(?:(?:public|private|protected|async|override|static)\s+)*"
        r"([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*(?::\s*\S+)?\s*\{"
    )

    for i, line in enumerate(lines):
        m = method_re.match(line)
        if not m:
            continue
        mn = m.group(1)
        if mn in skip or mn.startswith("_"):
            continue

        body_lines = lines[i: min(i + 40, len(lines))]
        body = "\n".join(body_lines)
        # Join split method chains: "this.svc\n  .method(" → "this.svc.method("
        body = re.sub(r"\n\s+\.", ".", body)

        calls = []
        for cm in re.finditer(
            r"this\.([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", body
        ):
            svc, meth = cm.group(1), cm.group(2)
            if svc not in no_svc:
                entry = f"{svc}.{meth}()"
                if entry not in calls:
                    calls.append(entry)

        result.append({
            "name": mn,
            "line": i + 1,
            "calls": calls,
            "is_lifecycle": mn in lifecycle,
        })
    return result


# ── Extract injected services ──────────────────────────────────────────────────
def get_injected_services(ts: str) -> list:
    result = []
    seen = set()
    svc_pattern = re.compile(
        r"Service|Repository|Client|Gateway|Provider|Facade|Store|Bus"
    )
    # Constructor DI
    for m in re.finditer(
        r"(?:private|public|protected|readonly)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*([A-Z][a-zA-Z0-9_]*)",
        ts,
    ):
        vn, cn = m.group(1), m.group(2)
        if svc_pattern.search(cn) and cn not in seen:
            seen.add(cn)
            result.append({"var_name": vn, "class_name": cn, "source": "constructor"})
    # inject()
    for m in re.finditer(
        r"(?:private\s+|readonly\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*inject\(([A-Z][a-zA-Z0-9_]*)\)",
        ts,
    ):
        vn, cn = m.group(1), m.group(2)
        if cn not in seen:
            seen.add(cn)
            result.append({"var_name": vn, "class_name": cn, "source": "inject"})
    return result


# ── Extract HTTP calls from service file (targeted tracing) ───────────────────
def _extract_url(jl: str) -> str | None:
    """Extract URL string from an HTTP call line."""
    sq = re.search(r"'([a-zA-Z][^']+)'", jl)
    if sq:
        return sq.group(1)
    dq = re.search(r'"([a-zA-Z][^"]+)"', jl)
    if dq:
        return dq.group(1)
    tl = re.search(r"`([^`]+)`", jl)
    if tl:
        return re.sub(r"\$\{[^}]+\}", "{param}", tl.group(1))
    ar = re.search(r"ApiRoutes\.([A-Za-z0-9_.]+)", jl)
    if ar:
        return f"{{ApiRoutes.{ar.group(1)}}}"
    return None


def _normalize_url(url: str) -> str | None:
    url_clean = url.lstrip("/")
    if url_clean.startswith("http"):
        return None  # skip absolute
    if not url_clean.startswith("api/") and not url_clean.startswith("{"):
        url_clean = f"api/{url_clean}"
    return url_clean


def get_service_http_calls(svc_file: str | None, called_methods: list,
                           root: Path | None = None, _depth: int = 0) -> list:
    """
    Trace HTTP calls from a service file for the given methods.
    When root is provided and depth < 1, also traces one level deeper into
    service-to-service calls (e.g. sharedService → templateService → HTTP).
    """
    if not svc_file or not Path(svc_file).exists():
        return []
    try:
        content = Path(svc_file).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    lines = content.splitlines()
    result = []

    for i, line in enumerate(lines):
        for target_method in called_methods:
            escaped = re.escape(target_method)
            if re.match(
                rf"^\s+(?:(?:public|private|protected|async|override)\s+)*{escaped}\s*\(",
                line,
            ):
                depth = 0
                end = min(i + 80, len(lines))
                body_calls = []  # service calls found in this method body

                for j in range(i, end):
                    jl = lines[j]
                    depth += jl.count("{")
                    depth -= jl.count("}")

                    http_m = re.search(
                        r"\.(get|post|put|delete|patch)(?:<[^>]*>)?\s*\(", jl
                    )
                    if http_m:
                        verb = http_m.group(1).upper()
                        url = _extract_url(jl)
                        if url:
                            norm = _normalize_url(url)
                            if norm:
                                result.append({
                                    "service_method": target_method,
                                    "http_method": verb,
                                    "url": norm,
                                    "line": j + 1,
                                })

                    # Track calls to other services (for 2-level tracing)
                    if _depth < 1:
                        for cm in re.finditer(
                            r"this\.([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
                            jl,
                        ):
                            entry = f"{cm.group(1)}.{cm.group(2)}()"
                            if entry not in body_calls:
                                body_calls.append(entry)

                    if j > i and depth <= 0:
                        break

                # 2-level tracing: if no HTTP found and we have deeper service calls
                if not any(r["service_method"] == target_method for r in result) \
                        and body_calls and root and _depth < 1:
                    svc_injections = get_injected_services(content)
                    for call_entry in body_calls:
                        parts = call_entry.split(".")
                        if len(parts) < 2:
                            continue
                        call_var = parts[0]
                        call_meth = parts[1].rstrip("()")
                        for inj in svc_injections:
                            if inj["var_name"] == call_var:
                                deeper_file = find_service_file(inj["class_name"], root)
                                if deeper_file and deeper_file != svc_file:
                                    deeper = get_service_http_calls(
                                        deeper_file, [call_meth], root, _depth + 1
                                    )
                                    for d in deeper:
                                        result.append({
                                            **d,
                                            "service_method": target_method,
                                            "via": inj["class_name"],
                                        })
                break
    return result

def build_prompt(pack: dict) -> str:
    pack_json = json.dumps(pack, ensure_ascii=False, separators=(",", ":"))
    comp = pack["meta"]["component"]
    comp_type = pack["meta"]["type"]
    is_dumb = comp_type in ("DUMB", "CONTAINER")

    if is_dumb:
        type_rule = (
            f"TYPE {comp_type}: KUN ui_behaviors (hvad brugeren ser/goer) - ingen flows, ingen requirements.\n"
            f"Lad flows og requirements vaere tomme lister.\n"
            f"behaviors maa IKKE bruges."
        )
        output_schema = '{"ui_behaviors":[],"flows":[],"requirements":[]}'
    else:
        type_rule = (
            f"TYPE {comp_type}: behaviors SKAL udfyldes (mindst 2 forretningshandlinger bevist i evidence pack).\n"
            f"flows og requirements tilladt naar direkte bevist.\n"
            f"flows: kun naar alle 4 led er direkte bevist (trigger → method → service_call → http).\n"
            f"requirements: KUN endpoints der er direkte i service_http_calls eller direct_http_calls i pack.\n"
            f"ui_behaviors maa IKKE bruges."
        )
        output_schema = '{"behaviors":[],"flows":[],"requirements":[]}'

    return f"""## ACDDA v4 - Angular Component Domain Analysis

Token: {comp}  |  Type: {comp_type}

FUNDAMENTAL RULE: Beskriv ALDRIG komponenten. Beskriv KUN hvad systemet goer for kunden.
Abstraction: Angular UI --> User capability --> Domain behavior --> System capability

TEST FOER DU SKRIVER: Giver saetningen mening for en person uden kode?
  JA = ok. NEJ = afvis.

UI_BEHAVIORS - hvad brugeren KAN i systemet:
  OK:  'Soeg efter sendte beskeder'
  OK:  'Opdater eksisterende brugerprofil'
  OK:  'Opret ny samtale med kunde'
  NEJ: 'Execute doSearch method'       (indeholder kode-navn)
  NEJ: 'Initialize component'          (teknisk intern, ingen brugervaerdi)
  NEJ: 'Fetch data from service'       (teknisk intern)
  NEJ: 'getTileStyleClasses activated' (camelCase)

HARD REJECT - behavior maatte ALDRIG indeholde:
  component, service, method, load, init, fetch, handler, initialize, subscribe
  camelCase ord (fx doSearch, getUsersByCustomer, getTileStyleClasses)

{type_rule}

EVIDENCE PACK:
{pack_json}

OUTPUT - kun dette JSON objekt, ingen forklaring, ingen markdown:
{output_schema}"""


# ── Main ───────────────────────────────────────────────────────────────────────
if not COMPONENT_LIST.exists():
    print(f"ERROR: Not found: {COMPONENT_LIST}", file=sys.stderr)
    sys.exit(1)

entries = json.loads(COMPONENT_LIST.read_text(encoding="utf-8-sig"))
alias_map = get_alias_map(APP_ROOT)
processed = 0
failed = 0

print(f"ACDDA v4 - build_evidence_packs ({len(entries)} components)")
print(f"AppRoot:    {APP_ROOT}")
print(f"OutputDir:  {OUTPUT_DIR}")
print()

for entry in entries:
    if isinstance(entry, str):
        rel = entry
    elif isinstance(entry, dict):
        rel = entry.get("path") or entry.get("filePath") or str(entry)
    else:
        rel = str(entry)
    comp_path = Path(rel)
    if not comp_path.is_absolute():
        comp_path = APP_ROOT / comp_path
    comp_path = comp_path.resolve()

    if not comp_path.exists():
        print(f"  SKIP (not found): {comp_path}")
        failed += 1
        continue

    comp_name = comp_path.stem.replace(".component", "")
    src_dir = comp_path.parent
    out_dir = OUTPUT_DIR / comp_name
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        ts = comp_path.read_text(encoding="utf-8", errors="ignore")

        # Find template
        html_path = src_dir / f"{comp_path.stem}.html"
        if not html_path.exists():
            m = re.search(r"templateUrl\s*:\s*['\"]([^'\"]+)['\"]", ts)
            if m:
                html_path = src_dir / m.group(1).lstrip("./")
        html = html_path.read_text(encoding="utf-8", errors="ignore") if html_path.exists() else ""

        # Detect component type
        template_actions = get_template_actions(html)
        methods = get_ts_methods(ts)
        services_raw = get_injected_services(ts)

        # Resolve service files
        resolved_svcs = []
        for svc in services_raw:
            resolved = find_service_file(svc["class_name"], APP_ROOT)
            resolved_svcs.append({**svc, "resolved_file": resolved, "resolved": resolved is not None})

        svc_count = len(resolved_svcs)
        if svc_count == 0:
            comp_type = "DUMB"
        elif svc_count <= 2:
            comp_type = "CONTAINER"
        else:
            comp_type = "SMART"

        # Targeted HTTP extraction via service files
        svc_http_calls = []
        for svc in resolved_svcs:
            if svc["resolved_file"]:
                # Find which methods this component calls on this service
                var = svc["var_name"]
                called = []
                for meth in methods:
                    for call in meth.get("calls", []):
                        if call.startswith(f"{var}."):
                            svc_method = call.split(".")[1].rstrip("()")
                            if svc_method not in called:
                                called.append(svc_method)
                if called:
                    http_calls = get_service_http_calls(svc["resolved_file"], called, APP_ROOT)
                    for h in http_calls:
                        svc_http_calls.append({
                            "service": svc["class_name"],
                            "service_method": h["service_method"],
                            "http_method": h["http_method"],
                            "url": h["url"],
                            "line": h["line"],
                        })

        # Direct HTTP in component
        direct_http = []
        ts_lines = ts.splitlines()
        for i, line in enumerate(ts_lines):
            m = re.search(r"this\.http\.(get|post|put|delete|patch)", line)
            if m:
                verb = m.group(1).upper()
                sq = re.search(r"'([a-zA-Z][^']+)'", line)
                dq = re.search(r'"([a-zA-Z][^"]+)"', line)
                url_val = (sq or dq)
                if url_val:
                    direct_http.append({"http_method": verb, "url": url_val.group(1), "line": i + 1})

        # Routes
        routes = []
        for i, line in enumerate(ts_lines):
            m = re.search(r"snapshot\.params\['([^']+)'\]|snapshot\.paramMap\.get\('([^']+)'\)", line)
            if m:
                pn = m.group(1) or m.group(2)
                routes.append({"type": "param", "name": pn, "source": "ActivatedRoute", "line": i + 1})
            if "this.router.navigate" in line:
                routes.append({"type": "navigate", "line": i + 1})

        nav_count = sum(1 for r in routes if r["type"] == "navigate")
        child_comp = len(re.findall(r"app-[a-z][a-z0-9-]+", html))
        cluster_required = (
            nav_count >= 3
            or child_comp >= 3
            or svc_count >= 5
        )

        pack = {
            "meta": {
                "component": comp_name,
                "file": str(comp_path).replace(str(APP_ROOT), "").lstrip("\\/").replace("\\", "/"),
                "type": comp_type,
                "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            },
            "template_actions": template_actions,
            "ts_methods": methods,
            "injected_services": resolved_svcs,
            "service_http_calls": svc_http_calls,
            "direct_http_calls": direct_http,
            "routes": routes,
            "cluster_signals": {
                "navigates_to_routes": nav_count,
                "uses_child_components": child_comp,
                "cluster_required": cluster_required,
            },
        }

        (out_dir / "evidence_pack.json").write_text(
            json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (out_dir / "copilot_prompt.md").write_text(
            build_prompt(pack), encoding="utf-8"
        )

        print(
            f"  {comp_name:<48} type={comp_type:<10} "
            f"svc={svc_count}  http={len(svc_http_calls)}  actions={len(template_actions)}"
        )
        processed += 1

    except Exception as e:
        print(f"  ERROR {comp_name}: {e}")
        failed += 1

print()
print(f"DONE: {processed} processed, {failed} failed")
print(f"Output: {OUTPUT_DIR}")
