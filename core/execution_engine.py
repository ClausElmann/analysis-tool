"""Persistent slice execution engine.

Runs one analysis "slice" per invocation, reads/writes state from
``protocol/state.json``, writes output to ``data/``, and appends a
dated Markdown log to ``protocol/logs/``.

Usage (CLI)::

    python -m core.execution_engine <solution_root>

Usage (library)::

    engine = ExecutionEngine(
        solution_root="C:/path/to/solution",
        protocol_root="protocol",
        data_root="data",
    )
    engine.execute_next_slice()

Defined slices
--------------
SLICE_0  Scan solution, classify projects.
         Output: data/solution_structure.json
SLICE_1  Detect Angular route entry points (routes, lazy-loaded modules).
         Output: data/angular_entries.json
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from core.solution_scanner import SolutionScanner
from core.git_analyzer import analyze_git
from core.work_item_analyzer import analyze_work_items
from core.system_fusion import fuse_system
from core.use_case_generator import generate_use_cases, build_selection
from core.gap_analyzer import analyze_gaps


# ---------------------------------------------------------------------------
# SLICE_0 – Solution structure / project classification helpers
# ---------------------------------------------------------------------------

# Files whose presence implies a particular project type.
# Each rule: (type_name, {glob-suffix or exact name}, required_count)
_PROJECT_ROOT_SIGNALS: List[tuple] = [
    # (type, set of file suffixes/names that contribute, min matches needed)
    ("angular",  {".angular.json", "angular.json", ".routing.module.ts",
                   ".routes.ts", ".component.ts"},                          1),
    ("api",      {".csproj"},                                                1),
    ("database", {".sql"},                                                  1),
    ("batch",    {".bat", ".cmd", ".sh"},                                   1),
]

# Content patterns that refine classification after the file-level pass.
_CONTENT_SIGNALS: Dict[str, List[re.Pattern]] = {
    "api":       [re.compile(r'\[HttpGet\b|\[HttpPost\b|ControllerBase|ApiController',
                             re.IGNORECASE)],
    "services":  [re.compile(r'\bpublic\s+class\s+\w+Service\b')],
    "core":      [re.compile(r'\bpublic\s+(?:interface|abstract\s+class)\b')],
    "database":  [re.compile(r'\bDapper\b|SqlConnection|SqlCommand',
                             re.IGNORECASE)],
    "batch":     [re.compile(r'\bIJob\b|\bIScheduler\b|\bQuartz\b|\bHangfire\b',
                             re.IGNORECASE)],
    "test":      [re.compile(r'\[Fact\]|\[Theory\]|\[Test\]|\[TestClass\]',
                             re.IGNORECASE)],
}

_INDICATOR_RULES: Dict[str, List[re.Pattern]] = {
    "routing_files":  [re.compile(r'(routing|\.routes?)(\.module)?\.ts$',
                                  re.IGNORECASE)],
    "components":     [re.compile(r'\.component\.ts$', re.IGNORECASE)],
    "controllers":    [re.compile(r'Controller\.cs$', re.IGNORECASE)],
    "service_classes":[re.compile(r'\.service\.ts$|\.Services?\.cs$',
                                  re.IGNORECASE)],
    "sql_files":      [re.compile(r'\.sql$', re.IGNORECASE)],
    "batch_files":    [re.compile(r'\.(bat|cmd|sh)$', re.IGNORECASE)],
    "package_json":   [re.compile(r'(?:^|[\\/])package\.json$', re.IGNORECASE)],
    "csproj":         [re.compile(r'\.csproj$', re.IGNORECASE)],
    "dapper_usage":   [re.compile(r'dapper', re.IGNORECASE)],
    "job_classes":    [re.compile(r'IJob|IScheduler', re.IGNORECASE)],
    "angular_json":   [re.compile(r'(?:^|[\\/])angular\.json$', re.IGNORECASE)],
}


def _classify_project(files: List[str], project_name: str = "") -> str:
    """Return a project type string based on file names and content signals."""
    names_lower = [os.path.basename(f).lower() for f in files]
    exts = {os.path.splitext(f)[1].lower() for f in files}

    # test -- checked first; uses project name and file basenames only
    if "test" in project_name.lower() or "spec" in project_name.lower():
        return "test"
    for pat in _CONTENT_SIGNALS["test"]:
        if any(pat.search(n) for n in names_lower):
            return "test"

    if "angular.json" in names_lower or ".angular" in "".join(names_lower):
        return "angular"
    if any(p.endswith(".routing.module.ts") or p.endswith(".routes.ts")
           or p.endswith(".component.ts") for p in names_lower):
        return "angular"

    if ".sql" in exts:
        return "database"

    if any(ext in exts for ext in (".bat", ".cmd", ".sh")):
        return "batch"

    if ".csproj" in exts or "package.json" in names_lower:
        # Refine using content signals (first file match wins)
        type_votes: Dict[str, int] = {}
        for fp in files:
            for type_name, patterns in _CONTENT_SIGNALS.items():
                if type_name == "test":
                    continue
                for pat in patterns:
                    if pat.search(fp) or pat.search(os.path.basename(fp)):
                        type_votes[type_name] = type_votes.get(type_name, 0) + 1
        if type_votes:
            return max(type_votes, key=lambda k: type_votes[k])
        return "api"

    return "unknown"


def _collect_indicators(files: List[str], content_texts: Dict[str, str]) -> List[str]:
    """Return sorted list of indicator labels present in the project."""
    found: set = set()
    for label, patterns in _INDICATOR_RULES.items():
        for pat in patterns:
            if any(pat.search(f) for f in files):
                found.add(label)
    for label, patterns in {
        "dapper_usage": _CONTENT_SIGNALS["database"],
        "job_classes":  _CONTENT_SIGNALS["batch"],
    }.items():
        for pat in patterns:
            if any(pat.search(t) for t in content_texts.values()):
                found.add(label)
    return sorted(found)


# ---------------------------------------------------------------------------
# Route extraction patterns and helpers (SLICE_1)
# ---------------------------------------------------------------------------

_ROUTE_PATH_RE = re.compile(r'''path\s*:\s*["']([^"']*)["']''')
_ROUTE_COMPONENT_RE = re.compile(r'''\bcomponent\s*:\s*(\w+)''')
_ROUTE_LOAD_CHILDREN_RE = re.compile(
    r'''loadChildren\s*:.*?import\s*\(\s*['"]([^'"]+)['"]\s*\)''',
    re.DOTALL,
)
_ROUTE_LOAD_COMPONENT_RE = re.compile(
    r'''loadComponent\s*:.*?\.then\s*\([^)]*?m\.(\w+)\)''',
    re.DOTALL,
)
_CHILDREN_RE = re.compile(r'\bchildren\s*:\s*\[')
_ROUTING_FILE_RE = re.compile(r'(routing|\.routes?)(\.module)?\.ts$', re.IGNORECASE)
_ROUTE_ARRAY_ANCHOR_RE = re.compile(r'(?:=|forRoot\s*\(|forChild\s*\()\s*\[')


def _find_block_end(content: str, open_pos: int) -> int:
    """Return position of the } matching the { at *open_pos*. Returns -1 if unmatched."""
    depth = 0
    in_string = False
    string_char = ""
    i = open_pos
    while i < len(content):
        ch = content[i]
        if in_string:
            if ch == string_char and (i == 0 or content[i - 1] != "\\"):
                in_string = False
        else:
            if ch in ('"', "'", "`"):
                in_string = True
                string_char = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return -1


def _find_array_end(content: str, open_pos: int) -> int:
    """Return position of the ] matching the [ at *open_pos*. Returns -1 if unmatched."""
    depth = 0
    in_string = False
    string_char = ""
    i = open_pos
    while i < len(content):
        ch = content[i]
        if in_string:
            if ch == string_char and (i == 0 or content[i - 1] != "\\"):
                in_string = False
        else:
            if ch in ('"', "'", "`"):
                in_string = True
                string_char = ch
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return -1


def _make_route_id(full_path: str, component: str = "") -> str:
    """Build a deterministic, stable id from a full route path with component fallback."""
    if not full_path:
        if component and component != "UNKNOWN":
            stem = re.sub(r'Component$', '', component)
            safe = re.sub(r'_+', '_',
                          re.sub(r'[^a-z0-9]+', '_', stem.lower())).strip('_')
            return f"route_root_{safe}" if safe else "route_root"
        return "route_root"
    safe = re.sub(r'_+', '_',
                  re.sub(r'[^a-z0-9]+', '_', full_path.lower())).strip('_')
    return f"route_{safe}" if safe else "route_wildcard"


def _normalize_path(path: str) -> str:
    """Normalize a route path: strip whitespace, collapse duplicate slashes, remove trailing slash."""
    p = path.strip()
    p = re.sub(r'/+', '/', p)
    if p != '/' and p.endswith('/'):
        p = p.rstrip('/')
    return p


def _extract_routes_from_array(
    content: str,
    file_path: str,
    start: int,
    end: int,
    prefix: str,
    parent_id: str,
    depth: int = 0,
) -> List[Dict]:
    """Recursively extract route entries from a [...] slice of *content*.

    *start* is the index of the first character after ``[``.
    *end*   is the index of the matching ``]``.
    *prefix* is the accumulated path from ancestor routes.
    *parent_id* is the route id of the immediate parent (empty for top-level).
    """
    results: List[Dict] = []
    i = start
    while i < end:
        if content[i] == "{":
            obj_end = _find_block_end(content, i)
            if obj_end == -1 or obj_end > end:
                break
            obj = content[i : obj_end + 1]

            path_m = _ROUTE_PATH_RE.search(obj)
            route_path = _normalize_path(path_m.group(1) if path_m else "")
            raw_full = f"{prefix}/{route_path}" if prefix else route_path
            full_path = _normalize_path(raw_full)

            component = ""
            entry_type = "route"
            comp_m = _ROUTE_COMPONENT_RE.search(obj)
            if comp_m:
                component = comp_m.group(1)
            else:
                lc_m = _ROUTE_LOAD_CHILDREN_RE.search(obj)
                if lc_m:
                    entry_type = "lazy-module"
                    parts = lc_m.group(1).rsplit("/", 1)
                    stem = re.sub(r'\.module$', '', parts[-1], flags=re.IGNORECASE)
                    component = stem.replace("-", " ").title().replace(" ", "") + "Module"
                else:
                    lcomp_m = _ROUTE_LOAD_COMPONENT_RE.search(obj)
                    if lcomp_m:
                        entry_type = "lazy-component"
                        component = lcomp_m.group(1)
            if not component:
                component = "UNKNOWN"

            entry_id = _make_route_id(full_path, component)
            results.append({
                "id": entry_id,
                "type": entry_type,
                "path": full_path,
                "component": component,
                "parent": parent_id,
                "depth": depth,
                "source_file": file_path,
            })

            # Recurse into children: [...]
            children_m = _CHILDREN_RE.search(obj)
            if children_m:
                bracket_pos = children_m.end() - 1  # position of '['
                bracket_end = _find_array_end(obj, bracket_pos)
                if bracket_end != -1:
                    results.extend(
                        _extract_routes_from_array(
                            obj, file_path,
                            bracket_pos + 1, bracket_end,
                            full_path, entry_id,
                            depth + 1,
                        )
                    )

            i = obj_end + 1
        else:
            i += 1
    return results


# ---------------------------------------------------------------------------
# SLICE_2 – Component API extraction patterns and helpers
# ---------------------------------------------------------------------------

_EVENT_HANDLER_RE = re.compile(
    r'\((click|submit|ngSubmit|change|selectionChange)\)\s*=\s*["\']([^"\'(\s]+)',
    re.IGNORECASE,
)
_EVENT_TRIGGER_MAP: Dict[str, str] = {
    "click": "click",
    "submit": "submit",
    "ngsubmit": "submit",
    "change": "change",
    "selectionchange": "change",
}
_HTTP_CALL_RE = re.compile(
    r'\b(?:http|httpClient|_http)\b\s*\.\s*'
    r'(get|post|put|delete|patch)\s*(?:<[^>]*>)?\s*'
    r'\(\s*(?:[\'"`]([^\'"` ,\)]+)[\'"`]|([\w.]+(?:\[[\w.\'\"]+\])*))',
    re.IGNORECASE,
)
_CTOR_INJECT_RE = re.compile(
    r'(?:private|public|protected|readonly)\s+(?:readonly\s+)?(\w+)\s*:\s*(\w+)',
)
_INJECT_FN_RE = re.compile(
    r'(?:private|public|protected)\s+(?:readonly\s+)?(\w+)\s*=\s*inject\s*\(\s*(\w+)',
)
_SERVICE_CALL_RE = re.compile(r'\bthis\.(\w+)\.(\w+)\s*\(')
_METHOD_DECL_START_RE = re.compile(
    r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]{0,300}\)\s*(?::[^{;]{0,80})?\s*\{',
)
_SKIP_KEYWORDS = frozenset({
    "if", "for", "while", "switch", "catch", "else", "try", "do",
    "new", "case", "return", "import", "export", "class", "super",
    "typeof", "instanceof", "throw", "await", "yield", "function",
})
_TEMPLATE_URL_RE = re.compile(r'''templateUrl\s*:\s*['"]([^'"]+)['"]''')
_INLINE_TEMPLATE_RE = re.compile(r'template\s*:\s*`([^`]*)`', re.DOTALL)
_CLASS_EXPORT_RE = re.compile(r'\bexport\s+(?:default\s+)?class\s+(\w+)')


def _extract_service_props(content: str) -> Dict[str, str]:
    """Return {property_name: ClassName} from constructor-injected or inject() parameters."""
    result = {prop: cls for prop, cls in _CTOR_INJECT_RE.findall(content)}
    result.update({prop: cls for prop, cls in _INJECT_FN_RE.findall(content)})
    return result


def _extract_method_bodies(content: str) -> Dict[str, str]:
    """Return {method_name: body_text} for named methods found in *content*."""
    bodies: Dict[str, str] = {}
    for m in _METHOD_DECL_START_RE.finditer(content):
        name = m.group(1)
        if name in _SKIP_KEYWORDS:
            continue
        brace_pos = m.end() - 1  # position of the opening '{'
        end_pos = _find_block_end(content, brace_pos)
        if end_pos == -1:
            continue
        bodies[name] = content[brace_pos : end_pos + 1]
    return bodies


def _extract_http_calls(text: str) -> List[Dict[str, str]]:
    """Return [{method, url}] for every HTTP call in *text* (literal URL or variable reference)."""
    result = []
    for m in _HTTP_CALL_RE.finditer(text):
        url = m.group(2) or m.group(3) or ""
        if url:
            result.append({"method": m.group(1).upper(), "url": url})
    return result


def _extract_event_trigger_map(template_text: str) -> Dict[str, str]:
    """Return {method_name: trigger_type} from Angular event bindings in *template_text*."""
    result: Dict[str, str] = {}
    for event, handler in _EVENT_HANDLER_RE.findall(template_text):
        method_name = re.split(r'[(\s]', handler)[0].strip()
        if method_name:
            result[method_name] = _EVENT_TRIGGER_MAP.get(event.lower(), "unknown")
    return result


# ---------------------------------------------------------------------------
# SLICE_0.5 – Wiki capability signal helpers
# ---------------------------------------------------------------------------

# Markdown heading: # Title  or  ## Title  etc.
_WIKI_HEADING_RE = re.compile(r'^#{1,6}\s+(.+)', re.MULTILINE)
# Markdown bullet: lines starting with - or *  (optionally indented)
_WIKI_BULLET_RE = re.compile(r'^[ \t]*[-*]\s+(.+)', re.MULTILINE)
# Markdown link text: [label](url)  or  [label](/path)
_WIKI_LINK_RE = re.compile(r'\[([^\]]{1,120})\]\([^)]+\)')

_WIKI_MAX_SIGNAL_WORDS = 20


def _truncate_signal(text: str) -> str:
    """Return *text* with at most _WIKI_MAX_SIGNAL_WORDS words, stripped."""
    words = text.strip().split()
    return " ".join(words[:_WIKI_MAX_SIGNAL_WORDS])


def _extract_wiki_signals(content: str) -> Dict[str, List[str]]:
    """Extract headings, bullets and link labels from *content*.

    Returns::

        {
            "headings": [...],
            "bullets":  [...],
            "links":    [...],
        }

    All values are deduplicated, truncated to max-20-words, and sorted.
    """
    headings = sorted(set(
        _truncate_signal(m.group(1))
        for m in _WIKI_HEADING_RE.finditer(content)
        if m.group(1).strip()
    ))
    # Strip inline link syntax from bullet text e.g. [label](url) → label
    bullets_raw: List[str] = []
    for m in _WIKI_BULLET_RE.finditer(content):
        text = _WIKI_LINK_RE.sub(lambda lm: lm.group(1), m.group(1))
        s = _truncate_signal(text)
        if s:
            bullets_raw.append(s)
    bullets = sorted(set(bullets_raw))

    links = sorted(set(
        _truncate_signal(m.group(1))
        for m in _WIKI_LINK_RE.finditer(content)
        if m.group(1).strip()
    ))
    return {"headings": headings, "bullets": bullets, "links": links}


# ---------------------------------------------------------------------------
# SLICE_0.7 – PDF capability extraction helpers
# ---------------------------------------------------------------------------

# Font-size thresholds (PyMuPDF point units)
_PDF_MAX_HEADING_SIZE: float = 40.0  # above this = cover/decorative title, skip
_PDF_CAP_SIZE_MIN:     float = 17.0  # >= this → capability (level 1)
_PDF_FEAT_SIZE_MIN:    float = 13.0  # >= this and < cap → feature (level 2)

# Danish + English imperative action verbs to detect as operations
_PDF_ACTION_VERB_RE = re.compile(
    r'(?<![a-zA-ZæøåÆØÅ])'
    r'(Opret|Tilmeld|Afmeld|Send|S\u00f8g|Upload|Rediger|Slet|Godkend|'
    r'Importer|Eksporter|Planl[a\u00e6]g|Ops[a\u00e6]t|Filtrer|Log\s+ind|'
    r'Download|Administrer|Opsæt|Planl\u00e6g)'
    r'(?:\s+\w+){0,4}',
    re.IGNORECASE,
)
_PDF_PAGE_NUM_RE = re.compile(r'^Side\s+\d+', re.IGNORECASE)
_PDF_TOC_LINE_RE = re.compile(r'\.{5,}')  # many dots = TOC row, skip


def _extract_pdf_toc_capabilities(toc: List) -> List[tuple]:
    """Convert fitz ``get_toc()`` output → deduplicated ``[(level, title)]`` list."""
    result: List[tuple] = []
    seen: set = set()
    for entry in toc:
        level: int = entry[0]
        title: str = entry[1].strip() if len(entry) > 1 else ""
        if not title:
            continue
        key = (level, title)
        if key not in seen:
            seen.add(key)
            result.append((level, title))
    return result


def _extract_pdf_headings_from_doc(doc) -> List[tuple]:
    """Font-size-based heading extraction from a fitz Document.

    Returns ``[(level, text)]``  where level 1 = main capability, level 2 = feature.
    Skips page 0 (cover), TOC lines, page-number markers, and blank spans.
    """
    headings: List[tuple] = []
    seen: set = set()
    for page_num in range(1, doc.page_count):  # skip cover
        blocks = doc[page_num].get_text("dict")["blocks"]
        for block in blocks:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                line_text = " ".join(s["text"] for s in spans).strip()
                if not line_text or len(line_text) < 3:
                    continue
                if _PDF_PAGE_NUM_RE.match(line_text):
                    continue
                if _PDF_TOC_LINE_RE.search(line_text):
                    continue
                max_size = max((s["size"] for s in spans), default=0.0)
                if max_size > _PDF_MAX_HEADING_SIZE:
                    continue
                if max_size >= _PDF_CAP_SIZE_MIN:
                    level = 1
                elif max_size >= _PDF_FEAT_SIZE_MIN:
                    level = 2
                else:
                    continue
                key = (level, line_text)
                if key not in seen:
                    seen.add(key)
                    headings.append((level, line_text))
    return headings


def _group_headings_into_capabilities(
    headings: List[tuple], fname: str
) -> List[Dict]:
    """Group ``[(level, title)]`` into capability dicts.

    Level-1 entries become capabilities; level 2+ become features of the
    nearest preceding level-1 parent.  Features are deduped and sorted.
    Result is sorted by capability name.
    """
    capabilities: List[Dict] = []
    current: Dict = {}
    seen_caps: set = set()

    for level, title in headings:
        if level == 1:
            if title in seen_caps:
                for c in capabilities:
                    if c["name"] == title:
                        current = c
                        break
            else:
                seen_caps.add(title)
                current = {
                    "name": title,
                    "source": "pdf",
                    "file": fname,
                    "features": [],
                }
                capabilities.append(current)
        elif current and title not in current["features"]:
            current["features"].append(title)

    for cap in capabilities:
        cap["features"] = sorted(cap["features"])

    return sorted(capabilities, key=lambda c: c["name"])


def _extract_pdf_operations(text: str) -> List[str]:
    """Return sorted, deduplicated action-verb phrases extracted from *text*."""
    ops: set = set()
    for m in _PDF_ACTION_VERB_RE.finditer(text):
        phrase = m.group(0).strip()
        # Clip to first 6 words and strip trailing punctuation
        words = phrase.split()[:6]
        clean = re.sub(r"[.,;:!?\'\"]$", "", " ".join(words)).strip()
        if clean:
            ops.add(clean)
    return sorted(ops)


# ---------------------------------------------------------------------------
# SLICE_3 – API → Database tracing helpers
# ---------------------------------------------------------------------------

# Controller route attributes and action verbs
_CONTROLLER_ACTION_RE = re.compile(
    r'\[(?:Http(?:Get|Post|Put|Delete|Patch))'  # [HttpGet] etc.
    r'(?:\s*\(\s*["\']([^"\']*)["\']\s*\))?\s*\]'  # optional ("route")
    r'(?:\s*\[[^\]]*\])*'                           # other attrs
    r'\s*(?:public|private|protected)?\s*(?:\S+\s+)?(\w+)\s*\(',
    re.DOTALL,
)

# Service call inside a method body: field.Method( or _field.Method(
_CTRL_SVC_CALL_RE = re.compile(
    r'\bthis\.?(\w+)\.([A-Z]\w+)\s*\(',
)

# Dapper invocation: conn.Query<...>(  conn.Execute(  etc.
_DAPPER_CALL_RE = re.compile(
    r'\.(?:Query|Execute|QueryFirst|QuerySingle|QueryMultiple)(?:Async)?'
    r'\s*(?:<[^>]*>)?\s*\(',
    re.IGNORECASE,
)

# Literal SQL string immediately after Dapper call:
# QueryAsync("SELECT ...")  or  QueryAsync(@"SELECT ...")
_DAPPER_LITERAL_SQL_RE = re.compile(
    r'\.(?:Query|Execute|QueryFirst|QuerySingle|QueryMultiple)(?:Async)?'
    r'\s*(?:<[^>]*>)?\s*\(\s*@?["\']([^"\'{};]{10,})["\']',
    re.IGNORECASE | re.DOTALL,
)
# SQL string assigned to a local variable: var sql = @"SELECT..."; (not dynamic)
_SQL_VAR_ASSIGN_RE = re.compile(
    r'(?:var|string)\s+\w+\s*=\s*@?"([^"]{20,})"(?!\s*\+)',
    re.IGNORECASE | re.DOTALL,
)
_SQL_KEYWORD_RE = re.compile(
    r'\b(?:SELECT|INSERT|UPDATE|DELETE|WITH|EXEC(?:UTE)?|MERGE|TRUNCATE)\b',
    re.IGNORECASE,
)

# SQL parsing
_SQL_FROM_TABLE_RE = re.compile(
    r'\bFROM\s+([\[`"]?\w+[\]`"]?)(?:\s+(?:AS\s+)?\w+)?',
    re.IGNORECASE,
)
_SQL_JOIN_TABLE_RE = re.compile(
    r'\b(?:INNER|LEFT|RIGHT|FULL|CROSS)?\s*(?:OUTER\s+)?JOIN\s+'
    r'([\[`"]?\w+[\]`"]?)(?:\s+(?:AS\s+)?\w+)?',
    re.IGNORECASE,
)
_SQL_WHERE_RE = re.compile(
    r'\bWHERE\b(.+?)(?:\bGROUP\s+BY\b|\bORDER\s+BY\b|\bHAVING\b|\bLIMIT\b|$)',
    re.IGNORECASE | re.DOTALL,
)
_SQL_WHERE_COND_RE = re.compile(
    r'([\w.]+)\s*(?:=|<>|!=|<=?|>=?|LIKE|IN|IS(?:\s+NOT)?)\s*',
    re.IGNORECASE,
)
# strip bracket/backtick/quote wrappers from a table name
_SQL_NAME_STRIP_RE = re.compile(r'[\[\]"`]')

# ---------------------------------------------------------------------------
# SLICE_9 – DB schema parsing patterns
# ---------------------------------------------------------------------------

_DB_TABLE_NAME_RE   = re.compile(r'CREATE\s+TABLE\s+(?:\[dbo\]\.)?\[(\w+)\]', re.IGNORECASE)
_DB_COLUMN_RE       = re.compile(r'^\s+\[(\w+)\]\s+([\w]+(?:\(\d+(?:,\s*\d+)?\))?)', re.MULTILINE)
_DB_PK_RE           = re.compile(r'CONSTRAINT\s+\[PK_\w+\]\s+PRIMARY KEY[^(]*\(([^)]+)\)', re.IGNORECASE)
_DB_FK_RE           = re.compile(
    r'CONSTRAINT\s+\[FK_\w+\]\s+FOREIGN KEY\s*\(([^)]+)\)\s+REFERENCES\s+(?:\[dbo\]\.)?\[(\w+)\]\s*\(([^)]+)\)',
    re.IGNORECASE,
)
_DB_INDEX_RE        = re.compile(r'CREATE\s+(?:UNIQUE\s+)?(?:NONCLUSTERED\s+)?(?:CLUSTERED\s+)?INDEX\s+\[(\w+)\]', re.IGNORECASE)
_DB_PROC_NAME_RE    = re.compile(r'CREATE\s+(?:OR\s+ALTER\s+)?PROCEDURE\s+(?:\[dbo\]\.)?\[(\w+)\]', re.IGNORECASE)
_DB_VIEW_NAME_RE    = re.compile(r'CREATE\s+VIEW\s+(?:\[dbo\]\.)?\[(\w+)\]', re.IGNORECASE)
_DB_FUNC_NAME_RE    = re.compile(r'CREATE\s+(?:OR\s+ALTER\s+)?FUNCTION\s+(?:\[dbo\]\.)?\[(\w+)\]', re.IGNORECASE)
_DB_FUNC_RETURNS_RE = re.compile(r'RETURNS\s+([\w()\s,]+?)(?:\s+AS|\s+BEGIN|\s+RETURN|$)', re.IGNORECASE)
_DB_TYPE_NAME_RE    = re.compile(
    r'CREATE\s+TYPE\s+(?:\[dbo\]\.)?\[(\w+)\]\s+(?:FROM\s+([\w]+(?:\(\d+(?:,\s*\d+)?\))?)|AS\s+(TABLE))',
    re.IGNORECASE,
)
_DB_INSERT_RE       = re.compile(r'\bINSERT\s+INTO\s+(?:\[dbo\]\.)?\[?(\w+)\]?', re.IGNORECASE)
_DB_UPDATE_RE       = re.compile(r'\bUPDATE\s+(?:\[dbo\]\.)?\[?(\w+)\]?\s+SET\b', re.IGNORECASE)
_DB_DELETE_RE       = re.compile(r'\bDELETE\s+FROM\s+(?:\[dbo\]\.)?\[?(\w+)\]?', re.IGNORECASE)

# ---------------------------------------------------------------------------
# SLICE_3 – Controller route attribute patterns and C# service-call helpers
# ---------------------------------------------------------------------------

# Class-level [Route("api/customers")] attribute
_CTRL_CLASS_ROUTE_RE = re.compile(
    r'\[Route\s*\(\s*["\']([^"\']*)["\']',
    re.IGNORECASE,
)
# Method-level HTTP verb with optional route suffix: [HttpGet("search")]
_CTRL_HTTP_ATTR_RE = re.compile(
    r'\[Http(Get|Post|Put|Delete|Patch)'
    r'(?:\s*\(\s*["\']([^"\']*)["\'])?\s*\]',
    re.IGNORECASE,
)
# Service invocation in C# method body: _svc.Method( with optional await / this.
_CS_SVC_CALL_RE = re.compile(
    r'\b(?:await\s+)?(?:this\.)?_?(\w+)\s*\.\s*([A-Z]\w+)\s*\(',
)
# Field declaration: private [readonly] XxxService [_]fieldName
_CS_FIELD_DECL_RE = re.compile(
    r'\b(?:private|protected|public)\s+(?:readonly\s+)?(\w+Service)\s+_?(\w+)\b',
    re.IGNORECASE,
)


def _parse_action_name_after_attr(content: str, pos: int) -> str:
    """Return the C# action method name immediately after an HTTP verb attribute.

    Scans forward from *pos* (end of the ``[HttpVerb...]`` match), strips any
    following ``[...]`` attributes, then returns the first identifier before the
    opening ``(`` of the method.  Return type generics like ``Task<IActionResult>``
    use ``<`` not ``(``, so are skipped automatically.
    """
    ahead = content[pos : pos + 400]
    clean = re.sub(r'\[[^\]]*\]', ' ', ahead)  # remove subsequent [attrs]
    m = re.search(r'\b(\w+)\s*\(', clean)
    return m.group(1) if m else ""


def _parse_sql_signals(sql: str) -> Dict[str, List[str]]:
    """Return {tables, joins, relations, where_conditions} from a literal SQL string."""
    tables: List[str] = []
    joins: List[str] = []
    relations: List[str] = []
    where_conditions: List[str] = []
    from_tables: List[str] = []

    for m in _SQL_FROM_TABLE_RE.finditer(sql):
        t = _SQL_NAME_STRIP_RE.sub('', m.group(1)).strip()
        if t and t not in tables:
            tables.append(t)
        if t:
            from_tables.append(t)

    for m in _SQL_JOIN_TABLE_RE.finditer(sql):
        t = _SQL_NAME_STRIP_RE.sub('', m.group(1)).strip()
        label = f"{m.group(0).split()[0].upper()} JOIN {t}"
        if label not in joins:
            joins.append(label)
        if t not in tables:
            tables.append(t)
        if from_tables and t:
            rel = f"{from_tables[0]}\u2192{t}"
            if rel not in relations:
                relations.append(rel)

    where_m = _SQL_WHERE_RE.search(sql)
    if where_m:
        clause = where_m.group(1)
        for cond_m in _SQL_WHERE_COND_RE.finditer(clause):
            col = cond_m.group(1).strip()
            if col and col not in where_conditions:
                where_conditions.append(col)

    return {
        "tables": sorted(tables),
        "joins": sorted(joins),
        "relations": sorted(relations),
        "where_conditions": sorted(where_conditions),
    }


def _extract_dapper_sqls(content: str) -> List[str]:
    """Return SQL strings from Dapper method calls and local variable assignments."""
    results: List[str] = []
    seen: set = set()
    # Pattern 1: literal SQL directly in Dapper method call argument
    for m in _DAPPER_LITERAL_SQL_RE.finditer(content):
        s = m.group(1).strip()
        if s not in seen:
            seen.add(s)
            results.append(s)
    # Pattern 2: var sql = @"SELECT..."; then passed as variable to _baseRepository.*
    for m in _SQL_VAR_ASSIGN_RE.finditer(content):
        s = m.group(1).strip()
        if s in seen:
            continue
        if _SQL_KEYWORD_RE.search(s):
            seen.add(s)
            results.append(s)
    return results


# ---------------------------------------------------------------------------
# Slice registry -- maps slice ID to handler name
# ---------------------------------------------------------------------------
_NEXT_SLICE: Dict[str, str] = {
    "SLICE_0":   "SLICE_0_5",
    "SLICE_0_5": "SLICE_0_7",
    "SLICE_0_7": "SLICE_0_8",
    "SLICE_0_8": "SLICE_9",
    "SLICE_9":   "SLICE_11",
    "SLICE_11":  "SLICE_1",
    "SLICE_1":   "SLICE_1b",
    "SLICE_1b":  "SLICE_1c",
    "SLICE_1c":  "SLICE_2",
    "SLICE_2":   "SLICE_3",
    "SLICE_3":   "SLICE_3b",
    "SLICE_3b":  "SLICE_6",
    "SLICE_6":   "SLICE_12",
    "SLICE_12":  "SLICE_13",
    "SLICE_13":  "SLICE_14",
    "SLICE_14":  "SLICE_15",
    "SLICE_15":  "SLICE_16",
    "SLICE_16":  "SLICE_17",
    "SLICE_17":  "SLICE_7",
    "SLICE_7":   "SLICE_8",
    "SLICE_8":   "SLICE_10",
    "SLICE_10":  "SLICE_7b",
    "SLICE_7b":  "SLICE_4",
}

_KNOWN_SLICES = {"SLICE_0", "SLICE_0_5", "SLICE_0_7", "SLICE_0_8", "SLICE_9", "SLICE_1", "SLICE_1b", "SLICE_1c", "SLICE_2", "SLICE_3", "SLICE_3b", "SLICE_6", "SLICE_12", "SLICE_13", "SLICE_14", "SLICE_15", "SLICE_16", "SLICE_17", "SLICE_7", "SLICE_8", "SLICE_10", "SLICE_11", "SLICE_7b"}

# Single source of truth for pipeline execution order
PIPELINE_ORDER = [
    "SLICE_0",
    "SLICE_0_5",
    "SLICE_0_7",
    "SLICE_0_8",
    "SLICE_9",
    "SLICE_11",
    "SLICE_1",
    "SLICE_1b",
    "SLICE_1c",
    "SLICE_2",
    "SLICE_3",
    "SLICE_3b",
    "SLICE_6",
    "SLICE_12",
    "SLICE_13",
    "SLICE_14",
    "SLICE_15",
    "SLICE_16",
    "SLICE_17",
    "SLICE_7",
    "SLICE_8",
    "SLICE_10",
    "SLICE_7b",
]


class ExecutionEngine:
    """Reads state, executes the current slice, persists results, advances state.

    Parameters
    ----------
    solution_root:
        Path to the solution directory to analyse.
    protocol_root:
        Directory that contains ``state.json`` and ``logs/``.
        Defaults to ``protocol`` relative to the current working directory.
    data_root:
        Directory where slice output files are written.
        Defaults to ``data`` relative to the current working directory.
    """

    def __init__(
        self,
        solution_root: str,
        protocol_root: str = "protocol",
        data_root: str = "data",
        wiki_root: str = "",
        csv_path: str = "",
        raw_root: str = "",
        db_root: str = "",
        label_path: str = "",
    ) -> None:
        self.solution_root = os.path.abspath(solution_root)
        self.protocol_root = os.path.abspath(protocol_root)
        self.data_root = os.path.abspath(data_root)
        self.wiki_root = os.path.abspath(wiki_root) if wiki_root else ""
        self.csv_path = os.path.abspath(csv_path) if csv_path else os.path.join(self.data_root, "data.csv")
        self.raw_root = os.path.abspath(raw_root) if raw_root else ""
        self.db_root = os.path.abspath(db_root) if db_root else ""
        self.label_path = os.path.abspath(label_path) if label_path else ""
        self._state_path = os.path.join(self.protocol_root, "state.json")
        self._logs_dir = os.path.join(self.protocol_root, "logs")

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def load_state(self) -> Dict:
        """Read and return state.json.  Raises if file is missing or invalid."""
        with open(self._state_path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def save_state(self, state: Dict) -> None:
        """Persist *state* to state.json (atomic overwrite)."""
        tmp = self._state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)
        os.replace(tmp, self._state_path)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def execute_next_slice(self) -> Dict:
        """Execute the slice named in ``current_slice``.

        Returns a summary dict describing what was done.
        """
        state = self.load_state()
        current = state.get("current_slice", "")

        if current not in _KNOWN_SLICES:
            summary = {
                "slice": current,
                "status": "SKIPPED",
                "reason": f"Slice '{current}' is not implemented.",
                "files_written": [],
                "items_found": 0,
                "errors": [],
            }
            self.log_run(summary)
            return summary

        # Dispatch
        handler = getattr(self, f"_run_{current.lower()}")
        summary = handler()

        # Advance state
        completed = state.get("completed_slices", [])
        if current not in completed:
            completed.append(current)
        next_slice = _NEXT_SLICE.get(current, f"{current}_DONE")
        new_state: Dict = {
            "current_slice": next_slice,
            "completed_slices": completed,
            "status": "READY",
            "last_run": datetime.now(timezone.utc).isoformat(),
        }
        self.save_state(new_state)
        self.log_run(summary)
        return summary

    def run_slice(self, slice_name: str) -> Dict:
        """Execute a single slice by name, regardless of state.json."""
        method_name = f"_run_{slice_name.lower()}"
        handler = getattr(self, method_name, None)
        if handler is None:
            return {
                "slice": slice_name,
                "status": "ERROR",
                "reason": f"No handler found for {slice_name}",
                "files_written": [],
                "items_found": 0,
                "errors": [f"No handler: {method_name}"],
            }
        return handler()

    def run_full_pipeline(self) -> list:
        """Execute all slices in PIPELINE_ORDER sequentially.

        Returns a list of result dicts with slice, status, and duration.
        """
        assert len(set(PIPELINE_ORDER)) == len(PIPELINE_ORDER), \
            "Duplicate slices in PIPELINE_ORDER!"

        results = []
        for slice_name in PIPELINE_ORDER:
            start = time.time()
            print(f"\n>> Running {slice_name}")
            try:
                result = self.run_slice(slice_name)
                status = result.get("status", "UNKNOWN")
            except Exception as ex:
                status = "ERROR"
                print(f"!! {slice_name} failed: {ex}")
                result = {"slice": slice_name, "status": "ERROR",
                          "items_found": 0, "errors": [str(ex)]}
            duration = time.time() - start
            print(f"OK {slice_name} done in {duration:.2f}s -- "
                  f"items={result.get('items_found', 0)} errors={len(result.get('errors', []))}")
            results.append({
                "slice": slice_name,
                "status": status,
                "duration": round(duration, 2),
            })
        return results

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log_run(self, summary: Dict) -> str:
        """Write a Markdown log entry to protocol/logs/{timestamp}.md.

        Returns the path of the written file.
        """
        os.makedirs(self._logs_dir, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
        log_path = os.path.join(self._logs_dir, f"{ts}.md")

        lines = [
            f"# Run Log -- {ts}",
            "",
            f"**Slice executed:** {summary.get('slice', 'UNKNOWN')}",
            f"**Status:** {summary.get('status', 'UNKNOWN')}",
            f"**Items found:** {summary.get('items_found', 0)}",
            "",
            "## Files Written",
            "",
        ]
        for path in summary.get("files_written", []):
            lines.append(f"- `{path}`")
        if not summary.get("files_written"):
            lines.append("- *(none)*")

        errors = summary.get("errors", [])
        lines += ["", "## Errors", ""]
        for err in errors:
            lines.append(f"- {err}")
        if not errors:
            lines.append("- *(none)*")

        reason = summary.get("reason")
        if reason:
            lines += ["", "## Notes", "", reason]

        with open(log_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

        return log_path

    # ------------------------------------------------------------------
    # SLICE_0 -- Solution structure extraction
    # ------------------------------------------------------------------

    def _run_slice_0(self) -> Dict:
        """Scan solution root, classify projects, write data/solution_structure.json."""
        errors: List[str] = []

        try:
            all_files = SolutionScanner().scan(self.solution_root)
        except OSError as exc:
            errors.append(f"Scanner failed: {exc}")
            all_files = []

        # Group files by immediate project directory (one level under root)
        projects_map: Dict[str, List[str]] = {}
        for fp in all_files:
            rel = os.path.relpath(fp, self.solution_root)
            parts = rel.split(os.sep)
            if len(parts) < 2:
                # file at root level -- use root as a project
                bucket = ""
            else:
                bucket = parts[0]
            projects_map.setdefault(bucket, []).append(fp)

        # For content-signal evaluation, read a sample of text files (up to 50 per bucket)
        _TEXT_EXTS = {".ts", ".cs", ".json", ".sql", ".js", ".bat", ".cmd", ".sh", ".csproj"}

        projects: List[Dict] = []
        for bucket in sorted(projects_map):
            bucket_files = sorted(projects_map[bucket])
            text_sample: Dict[str, str] = {}
            for fp in bucket_files:
                if len(text_sample) >= 50:
                    break
                if os.path.splitext(fp)[1].lower() in _TEXT_EXTS:
                    content = self._read_file(fp)
                    if content:
                        text_sample[fp] = content

            project_type = _classify_project(bucket_files, project_name=bucket)
            indicators = _collect_indicators(bucket_files, text_sample)

            if bucket == "":
                name = os.path.basename(self.solution_root)
                path = self.solution_root
            else:
                name = bucket
                path = os.path.join(self.solution_root, bucket)

            projects.append({
                "name": name,
                "path": path,
                "type": project_type,
                "indicators": indicators,
            })

        output: Dict = {"projects": projects}
        output_path = self._write_json("solution_structure.json", output)

        return {
            "slice": "SLICE_0",
            "status": "OK",
            "files_written": [output_path],
            "items_found": len(projects),
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # SLICE_0.5 -- Wiki capability signals
    # ------------------------------------------------------------------

    def _run_slice_0_5(self) -> Dict:
        """Scan wiki markdown files, extract capability signals, write data/wiki_signals.json.

        Signals are supporting evidence only -- they do not create capabilities
        and must not override code-derived signals.
        """
        errors: List[str] = []
        capabilities: List[Dict] = []

        if not self.wiki_root or not os.path.isdir(self.wiki_root):
            errors.append(
                f"wiki_root not set or not a directory: {self.wiki_root!r} "
                "— pass wiki_root= to ExecutionEngine"
            )
            result = {"capabilities": []}
            path = self._write_json("wiki_signals.json", result)
            return {
                "slice": "SLICE_0_5",
                "status": "OK",
                "files_written": [path],
                "items_found": 0,
                "errors": errors,
            }

        for fname in sorted(os.listdir(self.wiki_root)):
            if not fname.lower().endswith(".md"):
                continue
            fpath = os.path.join(self.wiki_root, fname)
            if not os.path.isfile(fpath):
                continue
            content = self._read_file(fpath) or ""
            if not content.strip():
                continue

            signals_map = _extract_wiki_signals(content)
            # Combine all signal types into a flat signals list, preserving source type
            all_signals: List[str] = (
                signals_map["headings"]
                + signals_map["bullets"]
                + signals_map["links"]
            )
            # Deduplicate while preserving sort order
            seen_s: set = set()
            deduped: List[str] = []
            for s in sorted(set(all_signals)):
                if s not in seen_s:
                    seen_s.add(s)
                    deduped.append(s)

            if not deduped:
                continue

            # Use the first heading as the capability name; fall back to filename stem
            name = (
                signals_map["headings"][0]
                if signals_map["headings"]
                else os.path.splitext(fname)[0]
            )
            capabilities.append({
                "name": name,
                "source": "wiki",
                "file": fname,
                "signals": deduped,
            })

        result = {"capabilities": sorted(capabilities, key=lambda c: c["file"])}
        path = self._write_json("wiki_signals.json", result)

        return {
            "slice": "SLICE_0_5",
            "status": "OK",
            "files_written": [path],
            "items_found": len(capabilities),
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # SLICE_0.7 -- PDF capability extraction
    # ------------------------------------------------------------------

    def _run_slice_0_7(self) -> Dict:
        """Extract capabilities from PDF manuals in solution_root, write data/pdf_capabilities.json."""
        errors: List[str] = []
        capabilities: List[Dict] = []

        try:
            import fitz  # type: ignore[import]
        except ImportError:
            errors.append("PyMuPDF (fitz) not installed -- run: pip install pymupdf")
            path = self._write_json("pdf_capabilities.json", {"capabilities": []})
            return {
                "slice": "SLICE_0_7",
                "status": "OK",
                "files_written": [path],
                "items_found": 0,
                "errors": errors,
            }

        try:
            pdf_search_dir = self.raw_root if self.raw_root and os.path.isdir(self.raw_root) else self.solution_root
            pdf_files = sorted(
                f for f in os.listdir(pdf_search_dir)
                if f.lower().endswith(".pdf")
                and os.path.isfile(os.path.join(pdf_search_dir, f))
            )
        except OSError as exc:
            errors.append(f"Cannot list pdf directory: {exc}")
            pdf_files = []

        for fname in pdf_files:
            fpath = os.path.join(pdf_search_dir, fname)
            try:
                doc = fitz.open(fpath)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Cannot open {fname}: {exc}")
                continue

            toc = doc.get_toc()
            if toc:
                headings = _extract_pdf_toc_capabilities(toc)
            else:
                headings = _extract_pdf_headings_from_doc(doc)

            caps = _group_headings_into_capabilities(headings, fname)

            # Extract action-verb operations from full document text
            full_text = "\n".join(doc[p].get_text() for p in range(doc.page_count))
            operations = _extract_pdf_operations(full_text)

            for cap in caps:
                cap["operations"] = operations

            capabilities.extend(caps)

        # Dedup by (file, name), preserve sort order
        seen_keys: set = set()
        deduped: List[Dict] = []
        for cap in sorted(capabilities, key=lambda c: (c["file"], c["name"])):
            key = (cap["file"], cap["name"])
            if key not in seen_keys:
                seen_keys.add(key)
                deduped.append(cap)

        result = {"capabilities": deduped}
        path = self._write_json("pdf_capabilities.json", result)

        return {
            "slice": "SLICE_0_7",
            "status": "OK",
            "files_written": [path],
            "items_found": len(deduped),
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # SLICE_0.8 -- Git intelligence extraction (local-only)
    # ------------------------------------------------------------------

    def _run_slice_0_8(self) -> Dict:
        """Extract business intent from local git history; write data/git_insights.json."""
        result = analyze_git(self.solution_root)
        insights = result.get("insights", [])
        errors: List[str] = result.get("errors", [])

        path = self._write_json("git_insights.json", {"insights": insights})
        return {
            "slice": "SLICE_0_8",
            "status": "OK",
            "files_written": [path],
            "items_found": len(insights),
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # SLICE_9 -- DB schema scanner
    # ------------------------------------------------------------------

    def _run_slice_9(self) -> Dict:
        """Parse ServiceAlert.DB SQL files; write data/db_schema.json."""
        errors: List[str] = []

        tables: List[Dict] = []
        procedures: List[Dict] = []
        views: List[Dict] = []
        functions: List[Dict] = []
        user_defined_types: List[Dict] = []

        if not self.db_root or not os.path.isdir(self.db_root):
            errors.append(f"db_root not set or not found: '{self.db_root}'")
            schema = {
                "tables": [], "procedures": [], "views": [],
                "functions": [], "user_defined_types": [],
            }
            path = self._write_json("db_schema.json", schema)
            return {
                "slice": "SLICE_9",
                "status": "WARN",
                "files_written": [path],
                "items_found": 0,
                "errors": errors,
            }

        _SKIP_DIRS = {"bin", "security", "extended events"}

        def _read_sql(fpath: str) -> str:
            for enc in ("utf-8-sig", "utf-8", "latin-1"):
                try:
                    with open(fpath, "r", encoding=enc) as fh:
                        return fh.read()
                except UnicodeDecodeError:
                    continue
            return ""

        def _strip(name: str) -> str:
            return _SQL_NAME_STRIP_RE.sub("", name).strip()

        # -- Tables ---------------------------------------------------------
        tables_dir = os.path.join(self.db_root, "Tables")
        if os.path.isdir(tables_dir):
            for fname in sorted(os.listdir(tables_dir)):
                if not fname.lower().endswith(".sql"):
                    continue
                fpath = os.path.join(tables_dir, fname)
                content = _read_sql(fpath)
                m = _DB_TABLE_NAME_RE.search(content)
                if not m:
                    continue
                tname = m.group(1)

                # Columns: only lines that look like column definitions (not constraints)
                columns: List[Dict] = []
                seen_cols: set = set()
                for cm in _DB_COLUMN_RE.finditer(content):
                    cname = cm.group(1)
                    ctype = cm.group(2).strip()
                    # Skip constraint/index keywords accidentally matched
                    if cname.upper() in (
                        "CONSTRAINT", "PRIMARY", "FOREIGN", "UNIQUE", "INDEX",
                        "CHECK", "DEFAULT", "WITH", "ON", "CLUSTERED",
                    ):
                        continue
                    if cname not in seen_cols:
                        seen_cols.add(cname)
                        columns.append({"name": cname, "type": ctype})

                # Primary key
                pk: List[str] = []
                pk_m = _DB_PK_RE.search(content)
                if pk_m:
                    pk = [_strip(c) for c in pk_m.group(1).split(",")]

                # Foreign keys
                fks: List[Dict] = []
                for fk_m in _DB_FK_RE.finditer(content):
                    col = _strip(fk_m.group(1))
                    ref_table = fk_m.group(2)
                    ref_col = _strip(fk_m.group(3))
                    fks.append({"column": col, "ref_table": ref_table, "ref_column": ref_col})

                # Indexes
                indexes = [im.group(1) for im in _DB_INDEX_RE.finditer(content)]

                tables.append({
                    "name": tname,
                    "columns": columns,
                    "primary_key": pk,
                    "foreign_keys": fks,
                    "indexes": indexes,
                })

        # -- Stored Procedures ----------------------------------------------
        sps_dir = os.path.join(self.db_root, "Stored Procedures")
        if os.path.isdir(sps_dir):
            for fname in sorted(os.listdir(sps_dir)):
                if not fname.lower().endswith(".sql"):
                    continue
                fpath = os.path.join(sps_dir, fname)
                content = _read_sql(fpath)
                m = _DB_PROC_NAME_RE.search(content)
                if not m:
                    continue
                pname = m.group(1)

                tables_read: List[str] = []
                tables_written: List[str] = []
                for rm in _SQL_FROM_TABLE_RE.finditer(content):
                    t = _SQL_NAME_STRIP_RE.sub("", rm.group(1)).strip()
                    if t and t not in tables_read:
                        tables_read.append(t)
                for rm in _SQL_JOIN_TABLE_RE.finditer(content):
                    t = _SQL_NAME_STRIP_RE.sub("", rm.group(1)).strip()
                    if t and t not in tables_read:
                        tables_read.append(t)
                for wm in _DB_INSERT_RE.finditer(content):
                    t = wm.group(1).strip()
                    if t and t not in tables_written:
                        tables_written.append(t)
                for wm in _DB_UPDATE_RE.finditer(content):
                    t = wm.group(1).strip()
                    if t and t not in tables_written:
                        tables_written.append(t)
                for wm in _DB_DELETE_RE.finditer(content):
                    t = wm.group(1).strip()
                    if t and t not in tables_written:
                        tables_written.append(t)

                procedures.append({
                    "name": pname,
                    "tables_read": sorted(tables_read),
                    "tables_written": sorted(tables_written),
                })

        # -- Views ----------------------------------------------------------
        views_dir = os.path.join(self.db_root, "Views")
        if os.path.isdir(views_dir):
            for fname in sorted(os.listdir(views_dir)):
                if not fname.lower().endswith(".sql"):
                    continue
                fpath = os.path.join(views_dir, fname)
                content = _read_sql(fpath)
                m = _DB_VIEW_NAME_RE.search(content)
                if not m:
                    continue
                vname = m.group(1)

                refs: List[str] = []
                for rm in _SQL_FROM_TABLE_RE.finditer(content):
                    t = _SQL_NAME_STRIP_RE.sub("", rm.group(1)).strip()
                    if t and t not in refs:
                        refs.append(t)
                for rm in _SQL_JOIN_TABLE_RE.finditer(content):
                    t = _SQL_NAME_STRIP_RE.sub("", rm.group(1)).strip()
                    if t and t not in refs:
                        refs.append(t)

                views.append({"name": vname, "tables_referenced": sorted(refs)})

        # -- Functions ------------------------------------------------------
        funcs_dir = os.path.join(self.db_root, "Functions")
        if os.path.isdir(funcs_dir):
            for fname in sorted(os.listdir(funcs_dir)):
                if not fname.lower().endswith(".sql"):
                    continue
                fpath = os.path.join(funcs_dir, fname)
                content = _read_sql(fpath)
                m = _DB_FUNC_NAME_RE.search(content)
                if not m:
                    continue
                fname_func = m.group(1)

                ret_type = ""
                rm = _DB_FUNC_RETURNS_RE.search(content)
                if rm:
                    ret_type = rm.group(1).strip()

                # Parameters: lines like @ParamName TYPE (skip SQL reserved words)
                _SQL_RESERVED = {
                    "BEGIN", "END", "AS", "RETURN", "SET", "SELECT", "FROM",
                    "WHERE", "WITH", "GO", "BY", "ON", "IS", "NOT", "NULL",
                    "AND", "OR", "IN", "EXEC", "IF", "ELSE", "THEN",
                }
                params = re.findall(r'(@\w+)\s+([\w]+(?:\(\d+(?:,\s*\d+)?\))?)', content)
                param_list = [
                    {"name": p[0], "type": p[1]}
                    for p in params
                    if p[1].upper() not in _SQL_RESERVED
                ]

                functions.append({
                    "name": fname_func,
                    "return_type": ret_type,
                    "parameters": param_list,
                })

        # -- User Defined Types ---------------------------------------------
        udt_dir = os.path.join(self.db_root, "User Defined Types")
        if os.path.isdir(udt_dir):
            for fname in sorted(os.listdir(udt_dir)):
                if not fname.lower().endswith(".sql"):
                    continue
                fpath = os.path.join(udt_dir, fname)
                content = _read_sql(fpath)
                m = _DB_TYPE_NAME_RE.search(content)
                if not m:
                    continue
                base_type = m.group(2) or m.group(3) or "UNKNOWN"
                user_defined_types.append({
                    "name": m.group(1),
                    "base_type": base_type,
                })

        schema = {
            "tables": tables,
            "procedures": procedures,
            "views": views,
            "functions": functions,
            "user_defined_types": user_defined_types,
        }
        path = self._write_json("db_schema.json", schema)
        total = len(tables) + len(procedures) + len(views) + len(functions) + len(user_defined_types)
        return {
            "slice": "SLICE_9",
            "status": "OK",
            "files_written": [path],
            "items_found": total,
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # SLICE_1 -- Angular route entry detection
    # ------------------------------------------------------------------

    def _run_slice_1(self) -> Dict:
        """Detect Angular route entry points and write data/angular_entries.json."""
        errors: List[str] = []
        seen_ids: set = set()
        all_entries: List[Dict] = []

        scanner = SolutionScanner()
        try:
            files = scanner.scan(self.solution_root)
        except OSError as exc:
            errors.append(f"Scanner failed: {exc}")
            files = []

        for file_path in sorted(files):
            if not self._is_routing_file(file_path):
                continue
            content = self._read_file(file_path)
            if content is None:
                errors.append(f"Unreadable: {file_path}")
                continue

            # Find top-level route arrays; recursion handles children
            covered: List[tuple] = []
            for m in _ROUTE_ARRAY_ANCHOR_RE.finditer(content):
                bracket_pos = m.end() - 1  # position of '['
                if any(s <= bracket_pos <= e for s, e in covered):
                    continue
                bracket_end = _find_array_end(content, bracket_pos)
                if bracket_end == -1:
                    continue
                if not _ROUTE_PATH_RE.search(content[bracket_pos : bracket_end + 1]):
                    continue
                covered.append((bracket_pos, bracket_end))
                entries = _extract_routes_from_array(
                    content, file_path,
                    bracket_pos + 1, bracket_end,
                    "", "",
                )
                for entry in entries:
                    if entry["id"] not in seen_ids:
                        seen_ids.add(entry["id"])
                        all_entries.append(entry)

        all_entries.sort(key=lambda e: e["id"])

        output: Dict = {"entry_points": all_entries}
        output_path = self._write_json("angular_entries.json", output)

        return {
            "slice": "SLICE_1",
            "status": "OK",
            "files_written": [output_path],
            "items_found": len(all_entries),
            "errors": errors,
        }

    @staticmethod
    def _is_routing_file(file_path: str) -> bool:
        """Return True only for Angular routing/routes TypeScript files."""
        name = os.path.basename(file_path).lower()
        return bool(_ROUTING_FILE_RE.search(name))

    # ------------------------------------------------------------------
    # SLICE_2 -- Component API extraction + UI coverage
    # ------------------------------------------------------------------

    def _run_slice_2(self) -> Dict:
        """Extract component APIs and validate UI coverage.

        Writes:
            data/component_api_map.json
            data/ui_coverage_report.json
        """
        errors: List[str] = []
        files_written: List[str] = []

        # Load SLICE_1 output
        entries_path = os.path.join(self.data_root, "angular_entries.json")
        if not os.path.isfile(entries_path):
            errors.append("angular_entries.json missing -- run SLICE_1 first")
            entry_points: List[Dict] = []
        else:
            with open(entries_path, "r", encoding="utf-8") as fh:
                entry_points = json.load(fh).get("entry_points", [])

        component_index = self._build_component_index()
        service_index = self._build_service_index()

        # Part 1 -- API extraction
        mappings: List[Dict] = []
        for ep in entry_points:
            component_name = ep.get("component", "")
            if not component_name or component_name == "UNKNOWN":
                continue
            # Skip lazy-loaded module references -- they are not component files
            if ep.get("type") in ("lazy-module",) or component_name.endswith("Module") or component_name.endswith("RoutingModule") or component_name.endswith("RoutesModule"):
                continue
            comp_file = component_index.get(component_name)
            if not comp_file:
                errors.append(f"Component not found: {component_name}")
                continue
            apis = self._extract_apis_from_component(comp_file, service_index)
            if not apis:
                continue  # skip entries with no APIs
            mappings.append({
                "entry_id": ep["id"],
                "component": component_name,
                "apis": apis,
                "source_file": comp_file,
            })

        mappings.sort(key=lambda m: m["entry_id"])
        api_map_path = self._write_json("component_api_map.json", {"mappings": mappings})
        files_written.append(api_map_path)

        # Part 2 -- UI coverage
        coverage = self._build_ui_coverage_report(entry_points, mappings)
        cov_path = self._write_json("ui_coverage_report.json", coverage)
        files_written.append(cov_path)

        return {
            "slice": "SLICE_2",
            "status": "OK",
            "files_written": files_written,
            "items_found": len(mappings),
            "errors": errors,
        }

    def _build_component_index(self) -> Dict[str, str]:
        """Return {ClassName: file_path} for every .component.ts in the solution."""
        try:
            files = SolutionScanner().scan(self.solution_root)
        except OSError:
            return {}
        index: Dict[str, str] = {}
        for fp in files:
            if not fp.endswith(".component.ts"):
                continue
            content = self._read_file(fp)
            if not content:
                continue
            for cls in _CLASS_EXPORT_RE.findall(content):
                if cls.endswith("Component"):
                    index[cls] = fp
        return index

    def _build_service_index(self) -> Dict[str, str]:
        """Return {ClassName: file_path} for every .service.ts in the solution."""
        try:
            files = SolutionScanner().scan(self.solution_root)
        except OSError:
            return {}
        index: Dict[str, str] = {}
        for fp in files:
            if not fp.endswith(".service.ts"):
                continue
            content = self._read_file(fp)
            if not content:
                continue
            for cls in _CLASS_EXPORT_RE.findall(content):
                if cls.endswith("Service"):
                    index[cls] = fp
        return index

    def _get_template_content(self, comp_file: str, comp_content: str) -> str:
        """Return raw template HTML: check inline backtick template, then templateUrl."""
        m = _INLINE_TEMPLATE_RE.search(comp_content)
        if m:
            return m.group(1)
        m = _TEMPLATE_URL_RE.search(comp_content)
        if m:
            template_abs = os.path.normpath(
                os.path.join(os.path.dirname(comp_file), m.group(1))
            )
            return self._read_file(template_abs) or ""
        return ""

    def _extract_apis_from_component(
        self, comp_file: str, service_index: Dict[str, str]
    ) -> List[Dict]:
        """Return sorted API dicts for all trigger-linked HTTP calls in *comp_file*."""
        content = self._read_file(comp_file)
        if not content:
            return []

        template_text = self._get_template_content(comp_file, content)
        trigger_map = _extract_event_trigger_map(template_text) if template_text else {}
        service_props = _extract_service_props(content)
        method_bodies = _extract_method_bodies(content)

        apis: List[Dict] = []
        seen: set = set()

        for method_name, body in method_bodies.items():
            if method_name == "ngOnInit":
                trigger = "init"
            elif method_name in trigger_map:
                trigger = trigger_map[method_name]
            else:
                continue  # not a known trigger -- skip

            # Direct HTTP calls
            for call in _extract_http_calls(body):
                key = (call["method"], call["url"])
                if key not in seen:
                    seen.add(key)
                    apis.append({
                        "method": call["method"],
                        "url": call["url"],
                        "source": "component",
                        "trigger": trigger,
                        "method_name": method_name,
                    })

            # Service calls -- resolve one level deep
            for prop, svc_method in _SERVICE_CALL_RE.findall(body):
                cls_name = service_props.get(prop)
                if not cls_name:
                    continue
                svc_file = service_index.get(cls_name)
                if not svc_file:
                    continue
                svc_content = self._read_file(svc_file)
                if not svc_content:
                    continue
                svc_body = _extract_method_bodies(svc_content).get(svc_method, "")
                for call in _extract_http_calls(svc_body):
                    key = (call["method"], call["url"])
                    if key not in seen:
                        seen.add(key)
                        apis.append({
                            "method": call["method"],
                            "url": call["url"],
                            "source": "service",
                            "trigger": trigger,
                            "method_name": method_name,
                        })

        return sorted(apis, key=lambda a: (a["method"], a["url"]))

    def _build_ui_coverage_report(
        self, entry_points: List[Dict], mappings: List[Dict]
    ) -> Dict:
        """Build coverage report from data/ui_observed_structure.json."""
        obs_path = os.path.join(self.data_root, "ui_observed_structure.json")
        if not os.path.isfile(obs_path):
            return {"menus": []}
        try:
            with open(obs_path, "r", encoding="utf-8") as fh:
                observed = json.load(fh)
        except (json.JSONDecodeError, OSError):
            return {"menus": []}

        route_to_id: Dict[str, str] = {ep["path"]: ep["id"] for ep in entry_points}
        id_to_apis: Dict[str, List[Dict]] = {m["entry_id"]: m["apis"] for m in mappings}
        id_to_component: Dict[str, str] = {
            m["entry_id"]: m["component"].lower() for m in mappings
        }

        menu_results: List[Dict] = []
        for menu in observed.get("menus", []):
            name = str(menu.get("name", ""))
            route = str(menu.get("route", ""))
            observed_features = sorted(str(f) for f in menu.get("observed_features", []))

            entry_id = route_to_id.get(route)
            if entry_id is None:
                status = "missing_route"
                missing = observed_features[:]
            else:
                apis = id_to_apis.get(entry_id, [])
                if not apis:
                    status = "no_api_detected"
                    missing = observed_features[:]
                else:
                    status = "covered"
                    corpus = (
                        " ".join(a["url"] for a in apis).lower()
                        + " " + id_to_component.get(entry_id, "")
                        + " " + " ".join(a.get("method_name", "") for a in apis).lower()
                        + " " + route.lower()
                    )
                    missing = sorted(f for f in observed_features if f.lower() not in corpus)

            menu_results.append({
                "name": name,
                "route": route,
                "coverage_status": status,
                "missing_features": missing,
            })

        menu_results.sort(key=lambda m: m["name"])
        return {"menus": menu_results}

    # ------------------------------------------------------------------
    # SLICE_3: API -> Database tracing
    # ------------------------------------------------------------------

    def _run_slice_3(self) -> Dict:
        api_map_path = os.path.join(self.data_root, "component_api_map.json")
        solution_path = os.path.join(self.data_root, "solution_structure.json")

        api_map_data = self._read_file(api_map_path)
        solution_data = self._read_file(solution_path)

        if not api_map_data or not solution_data:
            path = self._write_json("api_db_map.json", {"mappings": []})
            return {"slice": "SLICE_3", "status": "OK", "files_written": [path], "items_found": 0, "mappings": [], "errors": ["component_api_map.json or solution_structure.json missing"]}

        try:
            api_entries = json.loads(api_map_data).get("mappings", [])
            solution = json.loads(solution_data)
        except (json.JSONDecodeError, AttributeError):
            path = self._write_json("api_db_map.json", {"mappings": []})
            return {"slice": "SLICE_3", "status": "OK", "files_written": [path], "items_found": 0, "mappings": [], "errors": ["Failed to parse input JSON"]}

        # Gather all C# source files from api/backend projects
        cs_files: List[str] = []
        for project in solution.get("projects", []):
            proj_type = project.get("type", "")
            if proj_type in ("api", "unknown", "database", "batch", "library", "service"):
                proj_path = project.get("path", "")
                if proj_path and os.path.isdir(proj_path):
                    for dirpath, _dirs, filenames in os.walk(proj_path):
                        skip = False
                        for part in dirpath.replace("\\", "/").split("/"):
                            if part.lower() in ("bin", "obj", "node_modules", "dist", ".git"):
                                skip = True
                                break
                        if not skip:
                            for fname in filenames:
                                if fname.endswith(".cs"):
                                    cs_files.append(os.path.join(dirpath, fname))

        controller_index = self._build_controller_index(cs_files)
        service_index_3 = self._build_service_index_3(cs_files)
        route_index = self._build_controller_route_index(cs_files)
        api_routes_index = self._build_api_routes_index()

        mappings: List[Dict] = []
        for entry in api_entries:
            entry_id = entry.get("entry_id", "")
            component_name = entry.get("component", "")
            for api in entry.get("apis", []):
                url = api.get("url", "")
                if not url:
                    continue
                # Resolve ApiRoutes constant reference to actual URL string
                if url.startswith("ApiRoutes.") and url in api_routes_index:
                    url = api_routes_index[url]

                ctrl_name, ctrl_file, ctrl_method = self._find_controller_and_action(
                    url, route_index, controller_index
                )

                svc_tuples: List[tuple] = []

                if ctrl_file:
                    ctrl_content = self._read_file(ctrl_file) or ""
                    method_bodies = _extract_method_bodies(ctrl_content)
                    action_body = (
                        method_bodies[ctrl_method]
                        if ctrl_method and ctrl_method in method_bodies
                        else ctrl_content
                    )

                    # Level 1: method-level service trace
                    svc_tuples = self._extract_service_method_call(
                        action_body, service_index_3, ctrl_content
                    )

                    # Level 2: field-declaration fallback
                    if not svc_tuples:
                        for svc_name, svc_file, sqls in self._extract_service_calls_from_controller(
                            ctrl_file, service_index_3
                        ):
                            svc_tuples.append((svc_name, svc_file, "", sqls))

                    # Level 3: Dapper calls directly in controller
                    if not svc_tuples:
                        sqls = _extract_dapper_sqls(ctrl_content)
                        if sqls:
                            svc_tuples = [(ctrl_name, ctrl_file, "", sqls)]

                # FIX 1+2 -- Level 4: no controller/service found → scan service+repository files by URL segment
                if not svc_tuples:
                    # Derive keyword from URL or component name
                    url_stripped = url.lstrip("/")
                    if url_stripped.lower().startswith("api/"):
                        url_stripped = url_stripped[4:]
                    keyword = url_stripped.split("/")[0].lower()
                    if not keyword and component_name:
                        keyword = re.sub(r"(?:index)?component$", "", component_name, flags=re.IGNORECASE).lower()
                    for svc_name, svc_file in service_index_3.items():
                        if keyword and keyword not in svc_name.lower():
                            continue
                        sqls = _extract_dapper_sqls(self._read_file(svc_file) or "")
                        if sqls:
                            svc_tuples.append((svc_name, svc_file, "", sqls))

                for svc_name, _svc_file, svc_method, sqls in svc_tuples:
                    for sql in sqls:
                        signals = _parse_sql_signals(sql)
                        if not signals["tables"]:
                            continue
                        mappings.append({
                            "entry_id": entry_id,
                            "api_url": url,
                            "controller": ctrl_name,
                            "controller_method": ctrl_method or "",
                            "service": svc_name,
                            "service_method": svc_method or "",
                            "sql": signals,
                        })

        result = {"mappings": mappings}
        path = self._write_json("api_db_map.json", result)
        return {
            "slice": "SLICE_3",
            "status": "OK",
            "files_written": [path],
            "items_found": len(mappings),
            "mappings": mappings,
            "errors": [],
        }

    # ------------------------------------------------------------------
    # SLICE_6 -- Work item CSV analysis
    # ------------------------------------------------------------------

    def _run_slice_6(self) -> Dict:
        """Parse data/data.csv and write data/work_item_analysis.json."""
        csv_path = self.csv_path
        result = analyze_work_items(csv_path)

        capabilities = result.get("capabilities", [])
        features = result.get("features", [])
        errors: List[str] = result.get("errors", [])

        path = self._write_json(
            "work_item_analysis.json",
            {"capabilities": capabilities, "features": features},
        )
        return {
            "slice": "SLICE_6",
            "status": "OK",
            "files_written": [path],
            "items_found": len(features),
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # SLICE_7 -- System fusion
    # ------------------------------------------------------------------

    def _run_slice_7(self) -> Dict:
        """Fuse all prior slice outputs into data/system_model.json."""
        result = fuse_system(self.data_root)
        modules = result.get("modules", [])
        path = self._write_json("system_model.json", result)
        return {
            "slice": "SLICE_7",
            "status": "OK",
            "files_written": [path],
            "items_found": len(modules),
            "errors": [],
        }

    # ------------------------------------------------------------------
    # SLICE_8 -- Use case generator
    # ------------------------------------------------------------------

    def _run_slice_8(self) -> Dict:
        """Generate deterministic use cases from data/system_model.json."""
        errors: List[str] = []

        # STEP 9 -- analysis file (always overwrite)
        analysis = generate_use_cases(self.data_root)
        analysis_path = self._write_json("use-cases.analysis.json", analysis)

        # STEP 10 -- selection file (write-once, but regenerate if empty)
        selection_path = os.path.join(self.data_root, "use-cases.selection.json")
        existing_use_cases: List = []
        if os.path.isfile(selection_path):
            try:
                with open(selection_path, "r", encoding="utf-8") as _fh:
                    existing_use_cases = json.load(_fh).get("use_cases", [])
            except Exception:
                existing_use_cases = []
        if not existing_use_cases:
            selection = build_selection(analysis)
            self._write_json("use-cases.selection.json", selection)

        files_written = [analysis_path]
        return {
            "slice": "SLICE_8",
            "status": "OK",
            "files_written": files_written,
            "items_found": len(analysis.get("use_cases", [])),
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # SLICE_10 -- Gap analysis
    # ------------------------------------------------------------------

    def _run_slice_10(self) -> Dict:
        """Detect gaps between system model, work items, and API map."""
        result = analyze_gaps(self.data_root)
        gaps = result.get("gaps", [])
        path = self._write_json("gap_analysis.json", result)
        return {
            "slice": "SLICE_10",
            "status": "OK",
            "files_written": [path],
            "items_found": len(gaps),
            "errors": [],
        }

    # ------------------------------------------------------------------
    # SLICE_11 -- Label / i18n namespace mapper
    # ------------------------------------------------------------------

    def _run_slice_11(self) -> Dict:
        """Read labels.json, group by namespace, detect duplicates, match to modules.

        Writes data/label_map.json.
        """
        errors: List[str] = []

        # Resolve label_path: explicit param, else look in raw_root, else data_root
        label_path = self.label_path
        if not label_path or not os.path.isfile(label_path):
            candidates = []
            if self.raw_root and os.path.isdir(self.raw_root):
                candidates.append(os.path.join(self.raw_root, "labels.json"))
            candidates.append(os.path.join(self.data_root, "labels.json"))
            for c in candidates:
                if os.path.isfile(c):
                    label_path = c
                    break

        if not label_path or not os.path.isfile(label_path):
            errors.append(f"labels.json not found (checked raw_root and data_root)")
            path = self._write_json("label_map.json", {"namespaces": []})
            return {
                "slice": "SLICE_11",
                "status": "WARN",
                "files_written": [path],
                "items_found": 0,
                "errors": errors,
            }

        try:
            with open(label_path, "r", encoding="utf-8", errors="ignore") as fh:
                raw_labels = json.load(fh)
        except Exception as exc:
            errors.append(f"Failed to parse labels.json: {exc}")
            path = self._write_json("label_map.json", {"namespaces": []})
            return {
                "slice": "SLICE_11",
                "status": "WARN",
                "files_written": [path],
                "items_found": 0,
                "errors": errors,
            }

        if not isinstance(raw_labels, list):
            errors.append("labels.json is not a list -- unexpected format")
            raw_labels = []

        # --- Group by namespace prefix (first segment before '.') -------
        # Collect unique resource names per namespace (language-agnostic)
        ns_keys: Dict[str, set] = {}
        for item in raw_labels:
            resource_name = item.get("resourceName") or item.get("key") or ""
            if not resource_name:
                continue
            parts = resource_name.split(".")
            ns = parts[0] if parts else ""
            if not ns:
                continue
            ns_keys.setdefault(ns, set()).add(resource_name)

        # --- Detect duplicate namespaces (case-insensitive) -------------
        ns_lower_map: Dict[str, List[str]] = {}
        for ns in ns_keys:
            key = ns.lower()
            ns_lower_map.setdefault(key, []).append(ns)
        duplicate_namespaces: List[Dict] = [
            {"canonical": sorted(variants)[0], "variants": sorted(variants)}
            for variants in ns_lower_map.values()
            if len(variants) > 1
        ]

        # --- Load system model modules for cross-reference --------------
        modules: List[str] = []
        model_path = os.path.join(self.data_root, "system_model.json")
        if os.path.isfile(model_path):
            try:
                with open(model_path, "r", encoding="utf-8") as fh:
                    model = json.load(fh)
                modules = [m.get("name", "").lower() for m in model.get("modules", [])]
            except Exception:
                pass

        # --- Build namespace entries with module matches ----------------
        namespaces: List[Dict] = []
        for ns in sorted(ns_keys, key=lambda s: s.lower()):
            keys_list = sorted(ns_keys[ns])
            key_count = len(keys_list)

            # Match namespace to modules via substring overlap
            ns_lower = ns.lower()
            matched_modules: List[str] = []
            for mod in modules:
                mod_tokens = re.split(r'[\s_\-]+', mod)
                ns_tokens = re.split(r'(?<=[a-z])(?=[A-Z])|[\s_\-]+', ns_lower)
                ns_tokens_lower = [t.lower() for t in ns_tokens if t]
                if any(
                    t and (t in mod or mod.startswith(t) or ns_lower in mod or mod in ns_lower)
                    for t in ns_tokens_lower
                ):
                    matched_modules.append(mod)

            # Simple typo heuristic: flag namespaces very similar to another
            # (same first 4 chars, length within 2, different in case)
            is_duplicate = any(
                ns in v for v in duplicate_namespaces if ns in v.get("variants", [])
            )

            namespaces.append({
                "namespace": ns,
                "key_count": key_count,
                "sample_keys": keys_list[:5],
                "matched_modules": sorted(set(matched_modules))[:5],
                "is_duplicate": is_duplicate,
            })

        result = {
            "namespaces": namespaces,
            "duplicate_namespaces": duplicate_namespaces,
            "total_labels": len(raw_labels),
            "total_namespaces": len(namespaces),
        }
        path = self._write_json("label_map.json", result)
        return {
            "slice": "SLICE_11",
            "status": "OK",
            "files_written": [path],
            "items_found": len(namespaces),
            "errors": errors,
        }

    def _build_controller_index(self, cs_files: List[str]) -> Dict[str, str]:
        _CTRL_CLASS_RE = re.compile(
            r'\bclass\s+(\w+Controller)\b', re.IGNORECASE
        )
        index: Dict[str, str] = {}
        for path in cs_files:
            content = self._read_file(path) or ""
            for m in _CTRL_CLASS_RE.finditer(content):
                index[m.group(1)] = path
        return index

    def _build_service_index_3(self, cs_files: List[str]) -> Dict[str, str]:
        # FIX 1+2: also index Repository classes -- SQL lives there via IBaseRepository
        _SVC_CLASS_RE = re.compile(
            r'\bclass\s+(\w+(?:Service|Repository))\b', re.IGNORECASE
        )
        index: Dict[str, str] = {}
        for path in cs_files:
            content = self._read_file(path) or ""
            for m in _SVC_CLASS_RE.finditer(content):
                index[m.group(1)] = path
        return index

    def _find_controller_for_url(
        self, url: str, controller_index: Dict[str, str]
    ):
        # Heuristic: strip /api/ prefix, take first path segment, compare to
        # the controller's base name (class name minus 'Controller').
        # Handles plurals by checking prefix overlap (e.g. 'customers'→'customer').
        seg = url.lstrip("/")
        if seg.lower().startswith("api/"):
            seg = seg[4:]
        seg = seg.split("/")[0].lower()  # e.g. "customers"
        for ctrl_name, ctrl_file in controller_index.items():
            base = ctrl_name.lower().replace("controller", "")  # e.g. "customer"
            if seg.startswith(base) or base.startswith(seg):
                return ctrl_name, ctrl_file
        return "", ""

    def _extract_service_calls_from_controller(
        self,
        ctrl_file: str,
        service_index: Dict[str, str],
    ) -> List[tuple]:
        """Return list of (service_name, service_file, [sqls]) tuples.

        Looks for field declarations like:
            private CustomerService _customerService;
            private readonly ICustomerService _svc;
        and matches the declared type against the service index.
        """
        content = self._read_file(ctrl_file) or ""
        # Match field declarations: optional 'readonly', then type, then field name
        # FIX 1+2: also capture Repository types (IBaseRepository pattern)
        _FIELD_DECL_RE = re.compile(
            r'\b(?:private|protected|public)\s+(?:readonly\s+)?'
            r'(\w+(?:Service|Repository))\b',
            re.IGNORECASE,
        )
        results = []
        seen: set = set()
        for m in _FIELD_DECL_RE.finditer(content):
            svc_type = m.group(1)  # e.g. "CustomerService" or "ICustomerService"
            if svc_type in seen:
                continue
            # Match against service index: exact or strip leading 'I' for interfaces
            matched_name = None
            matched_file = None
            candidates = [svc_type.lower()]
            if svc_type.lower().startswith("i") and len(svc_type) > 1:
                candidates.append(svc_type[1:].lower())  # ICustomerService → customerservice
            for svc_name, svc_file in service_index.items():
                if svc_name.lower() in candidates:
                    matched_name, matched_file = svc_name, svc_file
                    break
            if not matched_name:
                continue
            seen.add(svc_type)
            svc_content = self._read_file(matched_file) or ""
            sqls = _extract_dapper_sqls(svc_content)
            if sqls:
                results.append((matched_name, matched_file, sqls))
        return results

    def _build_api_routes_index(self) -> Dict[str, str]:
        """Parse ApiRoutes.ts and return {dotpath: resolved_url_string}.

        Handles patterns like:
            private static benchmarkEndpoint = ApiRoutes.api + "Benchmark/";
            public static benchmarkRoutes = { get: { getBenchmarks: ApiRoutes.benchmarkEndpoint + "GetBenchmarks" } }
        """
        # Locate ApiRoutes.ts
        api_routes_file: str = ""
        try:
            files = SolutionScanner().scan(self.solution_root)
        except OSError:
            files = []
        for fp in files:
            if os.path.basename(fp).lower() == "apiroutes.ts":
                api_routes_file = fp
                break
        if not api_routes_file:
            return {}

        content = self._read_file(api_routes_file) or ""
        # Step 1: resolve flat static string variables (private static X = "...")
        flat_re = re.compile(
            r'(?:private|public|protected)\s+static\s+(\w+)\s*=\s*'
            r'((?:ApiRoutes\.\w+\s*\+\s*)?[\'"]([^\'"]+)[\'"])',
        )
        flat_vars: Dict[str, str] = {}
        for m in flat_re.finditer(content):
            name = m.group(1)
            val_expr = m.group(2).strip()
            # Resolve concatenations like ApiRoutes.api + "Benchmark/"
            val = self._eval_api_routes_concat(val_expr, flat_vars)
            flat_vars[name] = val

        # Step 2: build flat dotpath→url from nested objects
        # public static routeGroup = { get: { method: ApiRoutes.ep + "path", ... }, post: {...} }
        result: Dict[str, str] = {}
        group_re = re.compile(
            r'(?:public|private)\s+static\s+(\w+)\s*=\s*\{',
        )
        for gm in group_re.finditer(content):
            group_name = gm.group(1)
            block_start = gm.end() - 1  # position of '{'
            block_end = _find_block_end(content, block_start)
            if block_end == -1:
                continue
            block = content[block_start + 1: block_end]
            # Parse nested { verb: { method: expr }, ... } OR { method: expr, ... }
            self._parse_api_routes_block(
                block, f"ApiRoutes.{group_name}", flat_vars, result
            )

        return result

    def _eval_api_routes_concat(self, expr: str, flat_vars: Dict[str, str]) -> str:
        """Evaluate a simple ApiRoutes.X + "suffix" concatenation."""
        parts = [p.strip() for p in expr.split("+")]
        resolved = []
        for part in parts:
            part = part.strip("'\"")
            if part.startswith("ApiRoutes."):
                key = part[len("ApiRoutes."):]
                resolved.append(flat_vars.get(key, part))
            else:
                resolved.append(part)
        return "".join(resolved)

    def _parse_api_routes_block(
        self,
        block: str,
        prefix: str,
        flat_vars: Dict[str, str],
        result: Dict[str, str],
    ) -> None:
        """Recursively parse an ApiRoutes object block and populate *result*."""
        # Entry pattern: key: value (where value is string, concat, or nested block)
        entry_re = re.compile(r'(\w+)\s*:\s*')
        i = 0
        while i < len(block):
            m = entry_re.search(block, i)
            if not m:
                break
            key = m.group(1)
            val_start = m.end()
            if val_start >= len(block):
                break
            ch = block[val_start:].lstrip()
            i = val_start + (len(block[val_start:]) - len(ch))
            if not ch:
                break
            if ch[0] == "{":
                brace_pos = block.index("{", i)
                brace_end = _find_block_end(block, brace_pos)
                if brace_end == -1:
                    i = brace_pos + 1
                    continue
                sub_block = block[brace_pos + 1: brace_end]
                self._parse_api_routes_block(sub_block, f"{prefix}.{key}", flat_vars, result)
                i = brace_end + 1
            elif ch[0] in ("'", '"', "`") or ch.startswith("ApiRoutes."):
                # Find end of value expression (until comma, or end)
                val_end = self._find_value_end(block, i)
                val_expr = block[i:val_end].strip().rstrip(",").strip()
                url = self._eval_api_routes_concat(val_expr, flat_vars)
                result[f"{prefix}.{key}"] = url
                i = val_end
            else:
                i += 1

    @staticmethod
    def _find_value_end(text: str, start: int) -> int:
        """Return end index of a value expression ending at comma or next key."""
        depth = 0
        i = start
        while i < len(text):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                if depth == 0:
                    return i
                depth -= 1
            elif ch == "," and depth == 0:
                return i + 1
            i += 1
        return i

    def _build_controller_route_index(self, cs_files: List[str]) -> Dict[str, Dict]:
        """Return route metadata keyed by controller class name.

        Structure::

            {ctrl_name: {"file": str, "class_route": str,
                         "actions": [{"verb": str, "suffix": str, "method_name": str}]}}
        """
        _CTRL_CLASS_RE = re.compile(r'\bclass\s+(\w+Controller)\b', re.IGNORECASE)
        index: Dict[str, Dict] = {}
        for path in cs_files:
            content = self._read_file(path) or ""
            for cm in _CTRL_CLASS_RE.finditer(content):
                ctrl_name = cm.group(1)
                class_route_m = _CTRL_CLASS_ROUTE_RE.search(content)
                class_route_raw = class_route_m.group(1).strip("/") if class_route_m else ""
                # FIX 3: resolve ASP.NET [controller] token to actual controller base name
                ctrl_base_name = ctrl_name.lower().replace("controller", "")
                class_route = re.sub(r'\[controller\]', ctrl_base_name, class_route_raw, flags=re.IGNORECASE)
                actions: List[Dict] = []
                for am in _CTRL_HTTP_ATTR_RE.finditer(content):
                    verb = am.group(1).upper()
                    suffix = (am.group(2) or "").strip("/")
                    method_name = _parse_action_name_after_attr(content, am.end())
                    if method_name:
                        actions.append({"verb": verb, "suffix": suffix, "method_name": method_name})
                index[ctrl_name] = {"file": path, "class_route": class_route, "actions": actions}
        return index

    def _find_controller_and_action(
        self,
        url: str,
        route_index: Dict[str, Dict],
        controller_index: Dict[str, str],
    ) -> tuple:
        """Return (ctrl_name, ctrl_file, action_method_name).

        Tries route-attribute matching first, then falls back to the name heuristic.
        FIX 3: normalize url; add relaxed first-segment match as secondary fallback.
        """
        url_norm = url.lstrip("/").lower().rstrip("/")
        # FIX 3: stripped segment without api/ prefix for relaxed matching
        url_stripped = url_norm[4:] if url_norm.startswith("api/") else url_norm
        url_first_seg = url_stripped.split("/")[0]

        for ctrl_name, info in route_index.items():
            class_route = info["class_route"].lower()
            ctrl_base = ctrl_name.lower().replace("controller", "")
            # Per-action matching
            for action in info["actions"]:
                suffix = action["suffix"].lower()
                full = f"{class_route}/{suffix}".strip("/") if suffix else class_route
                full_clean = re.sub(r'/?\.?\{[^}]+\}', '', full).rstrip("/")
                if full_clean and (
                    url_norm == full_clean
                    or url_norm.startswith(full_clean + "/")
                    or url_norm.startswith(full_clean)
                ):
                    return ctrl_name, info["file"], action["method_name"]
            # Class-route-only match (action has no suffix or actions list is empty)
            if class_route:
                class_clean = re.sub(r'/?\.?\{[^}]+\}', '', class_route).rstrip("/")
                if class_clean and (
                    url_norm == class_clean or url_norm.startswith(class_clean + "/")
                ):
                    first = info["actions"][0]["method_name"] if info["actions"] else ""
                    return ctrl_name, info["file"], first
            # FIX 3: relaxed fallback -- first URL segment vs controller base name
            if url_first_seg and ctrl_base and (
                url_first_seg == ctrl_base
                or url_first_seg.startswith(ctrl_base)
                or ctrl_base.startswith(url_first_seg)
            ):
                first = info["actions"][0]["method_name"] if info["actions"] else ""
                return ctrl_name, info["file"], first
        # Heuristic fallback
        ctrl_name, ctrl_file = self._find_controller_for_url(url, controller_index)
        return ctrl_name, ctrl_file, ""

    def _extract_service_method_call(
        self,
        action_body: str,
        service_index: Dict[str, str],
        ctrl_content: str,
    ) -> List[tuple]:
        """Return [(svc_name, svc_file, svc_method, sqls)] from service calls in *action_body*.

        Field-to-type resolution uses *ctrl_content* for the controller field declarations.
        Handles both concrete types (``CustomerService``) and interfaces (``ICustomerService``).
        """
        field_to_type: Dict[str, str] = {}
        for m in _CS_FIELD_DECL_RE.finditer(ctrl_content):
            field_to_type[m.group(2).lower()] = m.group(1)

        results: List[tuple] = []
        seen: set = set()
        for m in _CS_SVC_CALL_RE.finditer(action_body):
            raw_field = m.group(1)
            svc_method = m.group(2)
            svc_type = field_to_type.get(raw_field.lower())
            if not svc_type:
                continue
            # Resolve interface to implementation (ICustomerService → CustomerService)
            candidates = [svc_type.lower()]
            if svc_type.lower().startswith("i") and len(svc_type) > 1:
                candidates.append(svc_type[1:].lower())
            matched_name = matched_file = ""
            for svc_name, svc_file in service_index.items():
                if svc_name.lower() in candidates:
                    matched_name, matched_file = svc_name, svc_file
                    break
            if not matched_name:
                continue
            key = (matched_name, svc_method)
            if key in seen:
                continue
            seen.add(key)
            sqls = self._dapper_sqls_for_method(matched_file, svc_method)
            if sqls:
                results.append((matched_name, matched_file, svc_method, sqls))
        return results

    def _dapper_sqls_for_method(self, svc_file: str, method_name: str) -> List[str]:
        """Return Dapper SQL literals from *method_name* in *svc_file*.

        Falls back to scanning the entire file when the method cannot be isolated.
        """
        content = self._read_file(svc_file) or ""
        if method_name:
            bodies = _extract_method_bodies(content)
            if method_name in bodies:
                return _extract_dapper_sqls(bodies[method_name])
        return _extract_dapper_sqls(content)

    # ------------------------------------------------------------------
    # SLICE_3b -- Webhook controllers (inbound from external systems)
    # ------------------------------------------------------------------

    def _run_slice_3b(self) -> Dict:
        """Detect webhook controllers that receive inbound payloads from 3rd parties.

        Writes data/webhook_map.json.
        """
        errors: List[str] = []
        webhooks: List[Dict] = []

        # Keyword sets for detection
        _SOURCE_MAP = {
            "gatewayapi":    "GatewayAPI",
            "infobip":       "Infobip",
            "sendgrid":      "SendGrid",
            "nineteennineteen": "NineteenNineteen",
            "1919":          "NineteenNineteen",
            "strex":         "Strex",
            "trimble":       "Trimble",
        }
        _INBOUND_KEYWORDS = re.compile(
            r'\b(webhook|inbound|parse|dlr|receipt|callback|incoming)\b',
            re.IGNORECASE
        )

        # Walk the solution tree for controllers
        for dirpath, _dirs, filenames in os.walk(self.solution_root):
            # Skip obj/bin/test folders
            rel = os.path.relpath(dirpath, self.solution_root).replace("\\", "/").lower()
            if any(seg in rel for seg in ("obj/", "/obj", "bin/", "/bin", ".test", "test/")):
                continue
            # Exclude Razor MVC apps (ServiceAlert.Web) -- those are not REST webhook receivers
            # Only scan ServiceAlert.Api and ServiceAlert.Worker.* projects
            rel_parts = rel.split("/")
            project_root = rel_parts[0] if rel_parts else ""
            _RAZOR_PROJECTS = {"servicealert.web", "smsservicewebapi", "balarmwebapp"}
            if project_root in _RAZOR_PROJECTS:
                continue
            for fname in filenames:
                if not fname.endswith("Controller.cs"):
                    continue
                fpath = os.path.join(dirpath, fname)
                content = self._read_file(fpath)
                if not content:
                    continue

                rel_file = os.path.relpath(fpath, self.solution_root).replace("\\", "/")

                # Include if in a Webhooks/ subfolder (primary signal)
                in_webhooks_dir = "webhook" in rel_file.lower().split("/").__repr__()
                in_webhooks_dir = any(
                    seg == "webhooks" for seg in rel_file.lower().split("/")
                )

                # OR if content contains inbound webhook keywords
                has_keywords = _INBOUND_KEYWORDS.search(content) is not None

                if not (in_webhooks_dir or has_keywords):
                    continue

                controller_name = fname.replace(".cs", "")

                # Detect source system from filename / content
                name_lower = controller_name.lower()
                source = "Unknown"
                for key, label in _SOURCE_MAP.items():
                    if key in name_lower or key in content.lower():
                        source = label
                        break

                # Extract HTTP action methods
                actions = []
                for m in re.finditer(
                    r'\[Http(?:Post|Get|Put|Delete)\]\s*(?:\[.*?\]\s*)?'
                    r'public\s+\S+\s+(\w+)\s*\(',
                    content
                ):
                    actions.append(m.group(1))
                if not actions:
                    # Fallback: any public method
                    for m in re.finditer(
                        r'public\s+(?:async\s+)?Task[<\[]\s*\S+\s*[>\]]\s+(\w+)\s*\(',
                        content
                    ):
                        actions.append(m.group(1))

                # Detect published MediatR events
                published_events = []
                for m in re.finditer(
                    r'mediator\.Publish\(\s*new\s+(\w+)\(',
                    content, re.IGNORECASE
                ):
                    published_events.append(m.group(1))

                webhooks.append({
                    "controller": controller_name,
                    "source": source,
                    "actions": sorted(set(actions)),
                    "publishes": published_events,
                    "type": "inbound",
                    "file": os.path.relpath(fpath, self.solution_root).replace("\\", "/"),
                })

        path = self._write_json("webhook_map.json", {"webhooks": webhooks})
        return {
            "slice": "SLICE_3b",
            "status": "OK",
            "files_written": [path],
            "items_found": len(webhooks),
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # SLICE_12 -- Background services (hosted / queue consumers)
    # ------------------------------------------------------------------

    def _run_slice_12(self) -> Dict:
        """Scan for BackgroundService / IHostedService implementations.

        Writes data/background_services.json.
        """
        errors: List[str] = []
        services: List[Dict] = []

        _CLASS_PATTERN = re.compile(
            r'public\s+class\s+(\w+)\s*(?::\s*([\w<>, \n]+))?',
            re.MULTILINE
        )
        _CTOR_INJECT_PATTERN = re.compile(
            r'public\s+\w+\s*\(([^)]+)\)'
        )

        def _detect_type(name: str, content: str) -> str:
            n = name.lower()
            if "queue" in n or "consumer" in n or "worker" in n:
                return "queue_consumer"
            if "sync" in n or "syncro" in n:
                return "sync_worker"
            if "send" in n or "dispatcher" in n:
                return "dispatcher"
            if "poll" in n or "watch" in n or "monitor" in n:
                return "poller"
            if "log" in n or "logger" in n:
                return "logger"
            if "cache" in n or "caching" in n:
                return "cache_worker"
            return "worker"

        _BASE_SIGNALS = {
            "BackgroundService", "IHostedService",
            "ISmsBackgroundService", "IEmailBackgroundService",
            "IVoiceBackgroundService", "ISendGridBackgroundService",
            "IClientEventSyncroBackgroundService", "IScopedProcessingService",
        }

        for dirpath, _dirs, filenames in os.walk(self.solution_root):
            rel = os.path.relpath(dirpath, self.solution_root).replace("\\", "/").lower()
            if any(seg in rel for seg in ("obj/", "/obj", "bin/", "/bin")):
                continue
            for fname in filenames:
                if not fname.endswith(".cs"):
                    continue
                fpath = os.path.join(dirpath, fname)
                content = self._read_file(fpath)
                if not content:
                    continue

                for m in _CLASS_PATTERN.finditer(content):
                    class_name = m.group(1)
                    bases_raw = m.group(2) or ""
                    bases = {b.strip().split("<")[0] for b in bases_raw.split(",") if b.strip()}
                    if not (bases & _BASE_SIGNALS):
                        # Also check if "BackgroundService" appears anywhere as base
                        if "BackgroundService" not in bases_raw and "IHostedService" not in bases_raw:
                            continue

                    # Extract constructor-injected dependencies
                    deps = []
                    ctor_m = _CTOR_INJECT_PATTERN.search(content)
                    if ctor_m:
                        for param in ctor_m.group(1).split(","):
                            param = param.strip()
                            type_match = re.match(r'I?(\w+)', param.split()[-2]) if len(param.split()) >= 2 else None
                            if type_match and not type_match.group(1).startswith("Cancellation"):
                                deps.append(param.split()[-1].lstrip("_"))

                    # Detect host project
                    rel_file = os.path.relpath(fpath, self.solution_root).replace("\\", "/")
                    host = rel_file.split("/")[0] if "/" in rel_file else "unknown"

                    services.append({
                        "name": class_name,
                        "type": _detect_type(class_name, content),
                        "host": host,
                        "dependencies": deps,
                        "bases": sorted(bases & _BASE_SIGNALS) or sorted(bases),
                        "file": rel_file,
                    })

        path = self._write_json("background_services.json", {"services": services})
        return {
            "slice": "SLICE_12",
            "status": "OK",
            "files_written": [path],
            "items_found": len(services),
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # SLICE_13 -- Batch jobs (CLI actions from ServiceAlertBatchAction enum)
    # ------------------------------------------------------------------

    def _run_slice_13(self) -> Dict:
        """Extract all batch job names from the ServiceAlertBatchAction enum.

        Also scans for the shared import infrastructure (base importers).
        Writes data/batch_jobs.json.
        """
        errors: List[str] = []
        jobs: List[Dict] = []

        _CATEGORY_RULES: List[tuple] = [
            (re.compile(r'^import_|^poslist_ftp_import|^export_|^import_fi_|^import_se_|^import_no_|^import_dk_'),                                               "import"),
            (re.compile(r'^gateway_|^send_emails_|^send_test_'),                                                                                                   "delivery"),
            (re.compile(r'^cleanup_'),                                                                                                                             "cleanup"),
            (re.compile(r'^monitoring|^watchdog_|^send_error_|^send_system_|^check_certificate'),                                                                 "monitoring"),
            (re.compile(r'^statistics_|^archive_|^snapshot_|^calculate_'),                                                                                        "statistics"),
            (re.compile(r'^update_|^stage_|^swap_|^fix_|^recheck_|^recalculate_|^coded_lookup|^document_lookup|^data_import_'),                                  "maintenance"),
            (re.compile(r'^prelookup|^lookup$'),                                                                                                                   "lookup"),
            (re.compile(r'^subscription_|^import_ftp_subscriptions|^import_ftp_enrollments|^import_standard_receivers|^import_robinsons'),                        "subscription"),
            (re.compile(r'^economic_|^import_economic_|^import_balance_|^import_budget|^import_framweb_|^import_salesforce'),                                     "finance"),
            (re.compile(r'^update_benchmark_|^snapshot_benchmark|^push_infoportal|^autoclose_infoportal'),                                                        "benchmark"),
            (re.compile(r'^create_scheduled|^create_schedules|^Weather_|^process_warnings|^email_norecipient'),                                                   "scheduled_broadcast"),
            (re.compile(r'^ready_'),                                                                                                                               "ready"),
            (re.compile(r'^azure_sql_|^update_database_'),                                                                                                        "database_maintenance"),
            (re.compile(r'^export_translations|^import_translations|^update_templates'),                                                                          "localization"),
            (re.compile(r'^import_no_people_'),                                                                                                                    "people_registry"),
            (re.compile(r'^trimble_|^fof_'),                                                                                                                      "converter"),
            (re.compile(r'^webhook_messages|^import_company_|^update_smslogs|^monitor_sso'),                                                                      "operations"),
        ]

        def _categorize(job_name: str) -> str:
            name_lower = job_name.lower()
            for pattern, category in _CATEGORY_RULES:
                if pattern.match(name_lower):
                    return category
            return "other"

        # --- Primary source: enum file ---
        enum_files = []
        for dirpath, _dirs, filenames in os.walk(self.solution_root):
            rel = os.path.relpath(dirpath, self.solution_root).lower()
            if "obj" in rel or "bin" in rel:
                continue
            for fname in filenames:
                if fname == "ServiceAlertBatchAction.cs":
                    enum_files.append(os.path.join(dirpath, fname))

        # Known non-job identifiers that appear in enum files
        _NON_JOB = {
            "namespace", "public", "enum", "class", "pragma", "warning",
            "disable", "undefined", "identifiers", "underscores", "contain",
            "import", "return", "using", "private", "static", "void",
            "bool", "true", "false", "null", "await", "async",
        }

        for enum_path in enum_files:
            content = self._read_file(enum_path)
            if not content:
                continue
            # Only match enum member lines: leading whitespace + snake_case id + comma or comment
            for m in re.finditer(
                r'^[ \t]{4,}([a-z][a-z0-9_]{3,})[ \t]*(?:,|//)',
                content, re.MULTILINE
            ):
                name = m.group(1)
                if name in _NON_JOB:
                    continue
                jobs.append({
                    "job": name,
                    "category": _categorize(name),
                    "source": "ServiceAlertBatchAction",
                })

        # --- Secondary source: Program.cs switch-cases (fallback / extra) ---
        batch_programs = []
        for dirpath, _dirs, filenames in os.walk(self.solution_root):
            rel = os.path.relpath(dirpath, self.solution_root).lower()
            if "obj" in rel or "bin" in rel:
                continue
            if "batch" in rel and "Program.cs" in filenames:
                batch_programs.append(os.path.join(dirpath, "Program.cs"))

        existing_jobs = {j["job"] for j in jobs}
        for prog_path in batch_programs:
            content = self._read_file(prog_path)
            if not content:
                continue
            for m in re.finditer(r'case\s+"([a-z][a-z0-9_]{3,})"', content):
                name = m.group(1)
                if name not in existing_jobs:
                    jobs.append({
                        "job": name,
                        "category": _categorize(name),
                        "source": "Program.cs",
                    })
                    existing_jobs.add(name)

        # --- Discover shared import infrastructure ---
        importer_bases: List[Dict] = []
        for dirpath, _dirs, filenames in os.walk(self.solution_root):
            rel = os.path.relpath(dirpath, self.solution_root).replace("\\", "/").lower()
            if "obj" in rel or "bin" in rel or ".test" in rel:
                continue
            for fname in filenames:
                if not fname.endswith(".cs"):
                    continue
                if not re.search(r'[Ii]mport|[Ii]mporter|[Ii]mporterBase', fname):
                    continue
                fpath = os.path.join(dirpath, fname)
                content = self._read_file(fpath)
                if not content:
                    continue
                # Only include abstract/interface importer base classes
                if re.search(r'public\s+(abstract\s+class|interface)\s+\w*(Import|Importer)\w*', content):
                    class_m = re.search(r'public\s+(?:abstract\s+)?(?:class|interface)\s+(\w+)', content)
                    if class_m:
                        rel_file = os.path.relpath(fpath, self.solution_root).replace("\\", "/")
                        importer_bases.append({
                            "name": class_m.group(1),
                            "file": rel_file,
                        })

        path = self._write_json("batch_jobs.json", {
            "jobs": jobs,
            "importer_infrastructure": importer_bases,
        })
        return {
            "slice": "SLICE_13",
            "status": "OK",
            "files_written": [path],
            "items_found": len(jobs),
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # SLICE_14 -- MediatR events (internal pub/sub)
    # ------------------------------------------------------------------

    def _run_slice_14(self) -> Dict:
        """Extract all INotification classes and their INotificationHandlers.

        For each event, find where it is published (mediator.Publish call sites).
        Writes data/event_map.json.
        """
        errors: List[str] = []

        _NOTIFICATION_DECL = re.compile(
            r'public\s+(?:sealed\s+|partial\s+)?class\s+(\w+)\s*[:(][^{]*INotification\b'
        )
        _HANDLER_DECL = re.compile(
            r'public\s+(?:partial\s+)?class\s+(\w+)\s*[:(][^{]*INotificationHandler\s*<\s*(\w+)\s*>'
        )
        _PUBLISH_CALL = re.compile(
            r'(?:await\s+)?_?mediator(?:Service)?\.Publish\s*\(\s*new\s+(\w+)\s*\('
        )

        # Pass 1: collect all event declarations
        event_files: Dict[str, str] = {}   # class_name -> relative_path
        handler_map: Dict[str, List[str]] = {}  # event_name -> handler classes
        publish_map: Dict[str, List[str]] = {}  # event_name -> list of publisher files

        _SKIP = re.compile(r'[\\/](obj|bin|\.test|Test[\./])[\\/]', re.IGNORECASE)

        for dirpath, _dirs, filenames in os.walk(self.solution_root):
            rel_dir = os.path.relpath(dirpath, self.solution_root)
            for fname in filenames:
                if not fname.endswith(".cs"):
                    continue
                fpath = os.path.join(dirpath, fname)
                rel_file = os.path.relpath(fpath, self.solution_root).replace("\\", "/")
                if _SKIP.search(rel_file):
                    continue
                content = self._read_file(fpath)
                if not content:
                    continue

                # Event declarations
                for m in _NOTIFICATION_DECL.finditer(content):
                    event_files[m.group(1)] = rel_file

                # Handler declarations
                for m in _HANDLER_DECL.finditer(content):
                    handler_cls = m.group(1)
                    event_name = m.group(2)
                    handler_map.setdefault(event_name, []).append(handler_cls)

                # Publish call sites
                for m in _PUBLISH_CALL.finditer(content):
                    event_name = m.group(1)
                    publish_map.setdefault(event_name, []).append(rel_file)

        # Build output -- only for events with an actual INotification declaration
        events: List[Dict] = []
        for event_name in sorted(event_files.keys()):
            publishers = sorted(set(publish_map.get(event_name, [])))
            handlers = sorted(set(handler_map.get(event_name, [])))
            events.append({
                "event": event_name,
                "declaration_file": event_files[event_name],
                "publishers": publishers,
                "handlers": handlers,
            })

        # Also include handlers for events not found as INotification (e.g. commands)
        for event_name, handlers in sorted(handler_map.items()):
            if event_name not in event_files:
                publishers = sorted(set(publish_map.get(event_name, [])))
                events.append({
                    "event": event_name,
                    "declaration_file": None,
                    "publishers": publishers,
                    "handlers": sorted(set(handlers)),
                })

        path = self._write_json("event_map.json", {"events": events})
        return {
            "slice": "SLICE_14",
            "status": "OK",
            "files_written": [path],
            "items_found": len(events),
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # SLICE_16 -- SSE / Realtime streams
    # ------------------------------------------------------------------

    def _run_slice_16(self) -> Dict:
        """Detect Server-Sent Events streams, group names, event types, and consumers.

        Writes data/realtime_map.json.
        """
        errors: List[str] = []
        streams: List[Dict] = []

        _SKIP = re.compile(r'[\\/](obj|bin)[\\/]', re.IGNORECASE)

        # Known SSE event types from the enum (extracted from codebase scan)
        _KNOWN_EVENT_TYPES = {
            "CONVERSATIONUNREADSTATUS":  "conversation_unread_status",
            "CONVERSATIONCREATED":       "conversation_created",
            "CONVERSATIONMESSAGESENT":   "conversation_message_sent",
            "LOOKUPPROGRESS":            "lookup_progress",
            "PROGRESSWATCHERINFO":       "progress_watcher_info",
            "ACTIVEJOBS":                "active_jobs",
        }

        # Scan C# for: MapServerSentEvents, SendEventAsync group names, SSE service class
        _MAP_SSE_RE = re.compile(
            r'MapServerSentEvents\s*<\s*(\w+)\s*>\s*\(\s*"([^"]+)"',
        )
        _SEND_GROUP_RE = re.compile(
            r'SendEventAsync\s*\(\s*(?:clientEvent\.GroupName|"([^"]+)")',
        )

        endpoints: List[Dict] = []
        send_groups: List[str] = []

        for dirpath, _dirs, filenames in os.walk(self.solution_root):
            for fname in filenames:
                if not fname.endswith(".cs"):
                    continue
                fpath = os.path.join(dirpath, fname)
                rel_file = os.path.relpath(fpath, self.solution_root).replace("\\", "/")
                if _SKIP.search(rel_file):
                    continue
                content = self._read_file(fpath)
                if not content:
                    continue

                for m in _MAP_SSE_RE.finditer(content):
                    endpoints.append({
                        "service_class": m.group(1),
                        "endpoint_path": m.group(2),
                        "file": rel_file,
                    })
                for m in _SEND_GROUP_RE.finditer(content):
                    if m.group(1):
                        send_groups.append(m.group(1))

        # Scan TypeScript for EventSource / serverSentEventsService usage
        _TS_SSE_RE = re.compile(
            r'new\s+EventSource\s*\(\s*["\']([^"\']+)["\']|'
            r'serverSentEventsService|'
            r'\.subscribe\([^)]*ServerSentEvent'
        )
        ts_consumers: List[str] = []
        for dirpath, _dirs, filenames in os.walk(self.solution_root):
            rel_dir = os.path.relpath(dirpath, self.solution_root).replace("\\", "/").lower()
            if "obj" in rel_dir or "bin" in rel_dir or "node_modules" in rel_dir:
                continue
            for fname in filenames:
                if not fname.endswith(".ts"):
                    continue
                fpath = os.path.join(dirpath, fname)
                content = self._read_file(fpath)
                if not content:
                    continue
                if _TS_SSE_RE.search(content):
                    ts_consumers.append(
                        os.path.relpath(fpath, self.solution_root).replace("\\", "/")
                    )

        # Build streams from known event types + discovered endpoints
        for et_key, et_slug in _KNOWN_EVENT_TYPES.items():
            streams.append({
                "stream": et_slug,
                "event_type_enum": et_key,
                "group_pattern": f"{et_key.title().replace('_', '')}/" + "{id}",
                "trigger": et_slug.replace("_", " "),
                "consumer": "Angular",
                "endpoint": endpoints[0]["endpoint_path"] if endpoints else "/sse",
                "service_class": endpoints[0]["service_class"] if endpoints else "ClientEventServerSentEventsService",
            })

        path = self._write_json("realtime_map.json", {
            "streams": streams,
            "endpoints": endpoints,
            "ts_consumers": sorted(ts_consumers),
        })
        return {
            "slice": "SLICE_16",
            "status": "OK",
            "files_written": [path],
            "items_found": len(streams),
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # SLICE_17 -- RabbitMQ topology
    # ------------------------------------------------------------------

    def _run_slice_17(self) -> Dict:
        """Scan all C# source for RabbitMQ exchanges, queues, bindings, publishers and consumers."""
        errors: List[str] = []

        _exchange_re = re.compile(
            r'ExchangeDeclareAsync\(\s*"([^"]+)"\s*,\s*(?:ExchangeType\.)?(\w+)',
            re.IGNORECASE,
        )
        _queue_re = re.compile(
            r'QueueDeclareAsync\(\s*"([^"]+)"\s*,\s*durable:\s*(true|false)',
            re.IGNORECASE,
        )
        _bind_re = re.compile(
            r'QueueBindAsync\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*routingKey:\s*"([^"]*)"',
            re.IGNORECASE,
        )
        _publish_re = re.compile(
            r'BasicPublishAsync\(\s*"([^"]+)"\s*,\s*"([^"]+)"',
            re.IGNORECASE,
        )
        _consume_re = re.compile(
            r'BasicConsumeAsync\(\s*queue:\s*"([^"]+)"',
            re.IGNORECASE,
        )
        _aspire_re = re.compile(
            r'(?:AddRabbitMQ|AddRabbitMQClient)\(\s*"([^"]+)"',
        )
        _consumer_class_re = re.compile(
            r'class\s+(\w+)\s*:\s*(?:AsyncDefaultBasicConsumer|DefaultBasicConsumer|IBasicConsumer)',
        )
        _skip_dirs = {"obj", "bin", "node_modules", ".git"}
        _skip_rel = (".test", "tests/", "/tests", "clientapp")

        # Aggregation dicts keyed by name
        exchanges: dict = {}   # name -> {type, durable, declared_in:[]}
        queues: dict = {}       # name -> {durable, declared_in:[]}
        bindings: list = []
        publishers: list = []
        consumers: list = []
        connections: list = []
        seen_bindings: set = set()
        seen_connections: set = set()

        # Two-pass: first collect consumer classes + BasicConsumeAsync calls separately,
        # then link them by project.
        consumer_classes: list = []   # {class, project, source_file}
        consume_calls: list = []      # {queue, project, source_file}

        for dirpath, dirs, filenames in os.walk(self.solution_root):
            dirs[:] = [d for d in dirs if d.lower() not in _skip_dirs]
            rel_dir = os.path.relpath(dirpath, self.solution_root).replace("\\", "/").lower()
            if any(s in rel_dir for s in _skip_rel):
                dirs[:] = []
                continue

            for fname in filenames:
                if not fname.endswith(".cs"):
                    continue
                fpath = os.path.join(dirpath, fname)
                content = self._read_file(fpath)
                if content is None:
                    continue
                rel_file = os.path.relpath(fpath, self.solution_root).replace("\\", "/")
                parts = rel_file.split("/")
                project = parts[0] if parts else ""

                # Aspire connection registrations
                for m in _aspire_re.finditer(content):
                    key = (project, m.group(1))
                    if key not in seen_connections:
                        seen_connections.add(key)
                        connections.append({
                            "connection_name": m.group(1),
                            "host_project": project,
                            "source_file": rel_file,
                        })

                # Exchanges
                for m in _exchange_re.finditer(content):
                    name = m.group(1)
                    ex_type = m.group(2).lower()
                    if name not in exchanges:
                        exchanges[name] = {"name": name, "type": ex_type, "durable": True, "declared_in": []}
                    if rel_file not in exchanges[name]["declared_in"]:
                        exchanges[name]["declared_in"].append(rel_file)

                # Queues
                for m in _queue_re.finditer(content):
                    name = m.group(1)
                    durable = m.group(2).lower() == "true"
                    if name not in queues:
                        queues[name] = {"name": name, "durable": durable, "declared_in": []}
                    if rel_file not in queues[name]["declared_in"]:
                        queues[name]["declared_in"].append(rel_file)

                # Bindings
                for m in _bind_re.finditer(content):
                    queue_name, exchange_name, routing_key = m.group(1), m.group(2), m.group(3)
                    key = (queue_name, exchange_name, routing_key)
                    if key not in seen_bindings:
                        seen_bindings.add(key)
                        bindings.append({
                            "queue": queue_name,
                            "exchange": exchange_name,
                            "routing_key": routing_key,
                            "declared_in": rel_file,
                        })

                # Publishers
                for m in _publish_re.finditer(content):
                    class_m = re.search(r'class\s+(\w+)', content)
                    class_name = class_m.group(1) if class_m else os.path.splitext(fname)[0]
                    publishers.append({
                        "class": class_name,
                        "exchange": m.group(1),
                        "routing_key": m.group(2),
                        "host_project": project,
                        "source_file": rel_file,
                    })

                # Consumer class declarations
                for m in _consumer_class_re.finditer(content):
                    consumer_classes.append({
                        "class": m.group(1),
                        "host_project": project,
                        "source_file": rel_file,
                    })

                # BasicConsumeAsync calls (may be in a different file than the class)
                for m in _consume_re.finditer(content):
                    consume_calls.append({
                        "queue": m.group(1),
                        "host_project": project,
                        "source_file": rel_file,
                    })

        # Link consumer classes to queues via shared project
        _queues_by_project: dict = {}
        for call in consume_calls:
            _queues_by_project.setdefault(call["host_project"], []).append(call["queue"])

        for entry in consumer_classes:
            project_queues = _queues_by_project.get(entry["host_project"], [])
            consumers.append({
                "class": entry["class"],
                "queue": project_queues[0] if len(project_queues) == 1 else (project_queues if project_queues else ""),
                "host_project": entry["host_project"],
                "source_file": entry["source_file"],
            })

        output = {
            "connections": connections,
            "exchanges": sorted(exchanges.values(), key=lambda e: e["name"]),
            "queues": sorted(queues.values(), key=lambda q: q["name"]),
            "bindings": bindings,
            "publishers": publishers,
            "consumers": consumers,
        }
        path = self._write_json("rabbitmq_topology.json", output)
        total = len(exchanges) + len(queues) + len(bindings) + len(publishers) + len(consumers)
        return {
            "slice": "SLICE_17",
            "status": "OK",
            "files_written": [path],
            "items_found": total,
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # SLICE_7b -- Extended system fusion (all flows merged)
    # ------------------------------------------------------------------

    def _run_slice_7b(self) -> Dict:
        """Merge all extracted data into a single extended system model.

        Reads :  system_model.json, background_services.json, batch_jobs.json,
                 webhook_map.json, event_map.json, realtime_map.json,
                 use-cases.analysis.json, component_api_map.json, api_db_map.json
        Writes:  data/system_model_extended.json
        """
        from collections import defaultdict
        errors: List[str] = []

        # ------------------------------------------------------------------
        # Helpers
        # ------------------------------------------------------------------
        def _load(filename: str):
            path = os.path.join(self.data_root, filename)
            if not os.path.isfile(path):
                errors.append(f"Missing: {filename}")
                return None
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    return json.load(fh)
            except Exception as exc:
                errors.append(f"Failed to load {filename}: {exc}")
                return None

        _STOP_TOKENS = {
            "service", "services", "repository", "repositories",
            "controller", "controllers", "component", "components",
            "handler", "handlers", "manager", "managers",
            "helper", "background", "notification", "event", "events",
            "job", "jobs", "task", "tasks", "base", "impl",
        }

        def _tokens(name: str) -> set:
            parts = re.split(r'(?<=[a-z])(?=[A-Z])|[_\-\s\.\/\\]+', name)
            result: set = set()
            for p in parts:
                t = p.lower().strip()
                if len(t) >= 3 and t not in _STOP_TOKENS:
                    result.add(t)
            return result

        def _normalize(name: str) -> str:
            n = name.lower()
            for suf in ("services", "service", "repositories", "repository",
                        "controllers", "controller", "components", "component",
                        "handlers", "handler", "managers", "manager"):
                if n.endswith(suf):
                    n = n[: -len(suf)]
                    break
            return n.strip("_- ")

        # ------------------------------------------------------------------
        # Load all inputs
        # ------------------------------------------------------------------
        model         = _load("system_model.json")       or {"modules": []}
        bg_data       = _load("background_services.json") or {"services": []}
        batch_data    = _load("batch_jobs.json")          or {"jobs": []}
        wh_data       = _load("webhook_map.json")         or {"webhooks": []}
        ev_data       = _load("event_map.json")           or {"events": []}
        rt_data       = _load("realtime_map.json")        or {"streams": []}
        uc_data       = _load("use-cases.analysis.json")  or {"use_cases": []}

        # ------------------------------------------------------------------
        # Build rich token sets per module (name + routes + apis + controllers)
        # ------------------------------------------------------------------
        modules_raw = model.get("modules", [])
        mod_tokens: Dict[str, set] = {}
        for mod in modules_raw:
            name = mod.get("name", "")
            toks = _tokens(name)
            for r in mod.get("routes", []):
                toks |= _tokens(r)
            for a in mod.get("apis", []):
                toks |= _tokens(a)
            for c in mod.get("controllers", []):
                toks |= _tokens(c)
            for s in mod.get("services", []):
                toks |= _tokens(s)
            mod_tokens[name] = toks

        def _best_match(item_toks: set) -> str:
            best_name = ""
            best_score = 0
            for mname, mtoks in mod_tokens.items():
                score = len(item_toks & mtoks)
                if score > best_score:
                    best_score = score
                    best_name = mname
            return best_name if best_score >= 1 else ""

        # ------------------------------------------------------------------
        # Build assignment maps:  module_name → [item, ...]
        # ------------------------------------------------------------------
        bg_map:  Dict[str, List[str]] = defaultdict(list)
        for svc in bg_data.get("services", []):
            svc_name = svc.get("name", "")
            host_file = svc.get("file", "")
            toks = _tokens(svc_name) | _tokens(os.path.basename(host_file))
            match = _best_match(toks)
            if match:
                bg_map[match].append(svc_name)

        batch_map: Dict[str, List[str]] = defaultdict(list)
        for job in batch_data.get("jobs", []):
            job_name = job.get("job", "")
            category = job.get("category", "")
            toks = _tokens(job_name) | _tokens(category)
            match = _best_match(toks)
            if match:
                batch_map[match].append(job_name)

        wh_map: Dict[str, List[str]] = defaultdict(list)
        for wh in wh_data.get("webhooks", []):
            ctrl = wh.get("controller", "")
            source = wh.get("source", "")
            toks = _tokens(ctrl) | _tokens(source)
            match = _best_match(toks)
            if match:
                wh_map[match].append(ctrl)

        ev_map: Dict[str, List[str]] = defaultdict(list)
        for ev in ev_data.get("events", []):
            ev_name = ev.get("event", "")
            toks = _tokens(ev_name)
            for h in ev.get("handlers", []):
                toks |= _tokens(h)
            for pub in ev.get("publishers", []):
                toks |= _tokens(os.path.basename(pub).replace(".cs", ""))
            match = _best_match(toks)
            if match:
                ev_map[match].append(ev_name)

        rt_map: Dict[str, List[str]] = defaultdict(list)
        for stream in rt_data.get("streams", []):
            stream_name = stream.get("stream", "")
            toks = _tokens(stream_name)
            match = _best_match(toks)
            if match:
                rt_map[match].append(stream_name)

        def _conf(mod: Dict, name: str,
                  _bg: dict, _bt: dict, _wh: dict, _ev: dict) -> float:
            """Confidence 0-1 based on how many flow types are attached."""
            base = mod.get("confidence", 0.3)
            bonus = 0.0
            if mod.get("apis"):        bonus += 0.1
            if mod.get("routes"):      bonus += 0.1
            if mod.get("tables"):      bonus += 0.1
            if _bg.get(name):          bonus += 0.1
            if _bt.get(name):          bonus += 0.1
            if _wh.get(name):          bonus += 0.1
            if _ev.get(name):          bonus += 0.1
            return round(min(base + bonus, 1.0), 2)

        # ------------------------------------------------------------------
        # Build extended modules
        # ------------------------------------------------------------------
        extended_modules: List[Dict] = []
        for mod in modules_raw:
            name = mod.get("name", "")
            ext: Dict = {
                "name":                _normalize(name) or name,
                "name_raw":            name,
                "routes":              mod.get("routes", []),
                "components":          mod.get("components", []),
                "apis":                mod.get("apis", []),
                "controllers":         mod.get("controllers", []),
                "services":            mod.get("services", []),
                "tables":              mod.get("tables", []),
                "features":            mod.get("features", []),
                "signals":             mod.get("signals", []),
                "background_services": sorted(set(bg_map.get(name, []))),
                "batch_jobs":          sorted(set(batch_map.get(name, []))),
                "webhooks":            sorted(set(wh_map.get(name, []))),
                "events":              sorted(set(ev_map.get(name, []))),
                "realtime":            sorted(set(rt_map.get(name, []))),
                "confidence":          _conf(mod, name, bg_map, batch_map, wh_map, ev_map),
            }
            extended_modules.append(ext)

        # ------------------------------------------------------------------
        # Build extended use cases
        # ------------------------------------------------------------------
        extended_ucs: List[Dict] = []

        # Existing UI/API use cases
        for uc in uc_data.get("use_cases", []):
            extended_ucs.append({
                "type":   "ui",
                "id":     uc.get("id", ""),
                "name":   uc.get("name", ""),
                "module": uc.get("module", ""),
                "flow":   uc.get("flow_steps", []),
            })

        # Webhook use cases -- one per controller
        ev_by_name = {e["event"]: e for e in ev_data.get("events", [])}
        for wh in wh_data.get("webhooks", []):
            ctrl = wh.get("controller", "")
            source = wh.get("source", "Unknown")
            publishes = wh.get("publishes", [])
            actions = wh.get("actions", [])
            flow: List[str] = [source, ctrl]
            if publishes:
                for ev_name in publishes[:2]:
                    flow.append(f"event:{ev_name}")
                    ev = ev_by_name.get(ev_name, {})
                    for h in ev.get("handlers", [])[:1]:
                        flow.append(h)
            elif actions:
                flow.extend(actions[:2])
            extended_ucs.append({
                "type":   "webhook",
                "name":   f"Receive inbound payload from {source}",
                "module": _best_match(_tokens(ctrl) | _tokens(source)),
                "flow":   flow,
            })

        # Batch use cases -- grouped by category
        by_cat: Dict[str, List[str]] = defaultdict(list)
        for job in batch_data.get("jobs", []):
            by_cat[job.get("category", "other")].append(job.get("job", ""))
        for category, jobs in sorted(by_cat.items()):
            rep = jobs[0] if jobs else category
            extended_ucs.append({
                "type":      "batch",
                "name":      f"Batch: {category} ({len(jobs)} jobs)",
                "module":    _best_match(_tokens(rep) | _tokens(category)),
                "flow":      ["AzureScheduler", "ServiceAlert.Batch",
                              f"{category} ({len(jobs)})", "Database"],
                "job_count": len(jobs),
            })

        # Background service use cases
        _bg_flow_map = {
            "queue_consumer": ["SqlQueue", "{name}", "Gateway", "Database"],
            "dispatcher":     ["Queue",    "{name}", "ExternalGateway", "Database"],
            "sync_worker":    ["Timer",    "{name}", "ExternalService", "Database"],
            "poller":         ["Timer",    "{name}", "ExternalAPI", "Database"],
            "logger":         ["Request",  "{name}", "Database"],
            "cache_worker":   ["Timer",    "{name}", "Cache"],
            "worker":         ["Timer",    "{name}", "Service", "Database"],
        }
        for svc in bg_data.get("services", []):
            svc_name = svc.get("name", "")
            svc_type = svc.get("type", "worker")
            template = _bg_flow_map.get(svc_type, _bg_flow_map["worker"])
            flow = [s.replace("{name}", svc_name) for s in template]
            extended_ucs.append({
                "type":   "async",
                "name":   f"Background: {svc_name}",
                "module": _best_match(_tokens(svc_name) | _tokens(svc.get("file", ""))),
                "flow":   flow,
            })

        # Realtime use cases
        for stream in rt_data.get("streams", []):
            stream_name = stream.get("stream", "")
            endpoint = stream.get("endpoint", "/sse")
            extended_ucs.append({
                "type":   "realtime",
                "name":   f"SSE: {stream_name}",
                "module": _best_match(_tokens(stream_name)),
                "flow":   ["BackendService", f"SSE {endpoint}", "Angular"],
            })

        # Event use cases (non-trivial: has publisher OR handler)
        for ev in ev_data.get("events", []):
            ev_name = ev.get("event", "")
            publishers = ev.get("publishers", [])
            handlers = ev.get("handlers", [])
            if not publishers and not handlers:
                continue
            flow: List[str] = []
            if publishers:
                flow.append(os.path.basename(publishers[0]).replace(".cs", ""))
            flow.append(f"event:{ev_name}")
            if handlers:
                flow.append(handlers[0])
            extended_ucs.append({
                "type":   "event",
                "name":   f"Event: {ev_name}",
                "module": _best_match(_tokens(ev_name)),
                "flow":   [f for f in flow if f],
            })

        # ------------------------------------------------------------------
        # Coverage statistics (STEP 7)
        # ------------------------------------------------------------------
        bg_total    = len(bg_data.get("services", []))
        batch_total = len(batch_data.get("jobs", []))
        wh_total    = len(wh_data.get("webhooks", []))
        ev_total    = len(ev_data.get("events", []))
        rt_total    = len(rt_data.get("streams", []))

        bg_linked    = sum(len(v) for v in bg_map.values())
        batch_linked = sum(len(v) for v in batch_map.values())
        wh_linked    = sum(len(v) for v in wh_map.values())
        ev_linked    = sum(len(v) for v in ev_map.values())
        rt_linked    = sum(len(v) for v in rt_map.values())

        total_items  = bg_total + batch_total + wh_total + ev_total + rt_total
        total_linked = bg_linked + batch_linked + wh_linked + ev_linked + rt_linked
        cov_pct      = total_linked / total_items if total_items else 0
        coverage     = "HIGH" if cov_pct >= 0.75 else ("MEDIUM" if cov_pct >= 0.40 else "LOW")

        stats = {
            "modules":                     len(extended_modules),
            "batch_jobs_linked":           batch_linked,
            "webhooks_linked":             wh_linked,
            "events_linked":               ev_linked,
            "background_services_linked":  bg_linked,
            "realtime_linked":             rt_linked,
            "total_use_cases":             len(extended_ucs),
            "coverage_pct":                round(cov_pct, 3),
            "coverage":                    coverage,
        }

        # ------------------------------------------------------------------
        # Write output
        # ------------------------------------------------------------------
        output = {
            "modules":        extended_modules,
            "use_cases":      extended_ucs,
            "coverage_stats": stats,
        }
        path = self._write_json("system_model_extended.json", output)
        return {
            "slice":         "SLICE_7b",
            "status":        "OK",
            "files_written": [path],
            "items_found":   len(extended_modules),
            "errors":        errors,
        }

    # ------------------------------------------------------------------
    # SLICE_1b -- iFrame / sub Angular apps
    # ------------------------------------------------------------------

    def _run_slice_1b(self) -> Dict:
        """Scan SubscriptionApp, iFrameModules, QuickResponse Angular sub-projects."""
        errors: List[str] = []
        apps: List[Dict] = []

        # Augmented anchor: also matches `export default [` and `provideRouter([`
        _sub_anchor_re = re.compile(
            r'(?:=|forRoot\s*\(|forChild\s*\(|export\s+default|provideRouter\s*\()\s*\['
        )
        # Bare loadComponent without .then() — derive name from import path
        _lc_bare_import_re = re.compile(
            r'''loadComponent\s*:\s*\(\s*\)\s*=>\s*import\s*\(\s*["']([^"']+)["']\s*\)'''
        )

        def _component_from_import(import_path: str) -> str:
            stem = re.sub(r'\.component$', '', import_path.rsplit('/', 1)[-1], flags=re.IGNORECASE)
            return "".join(w.capitalize() for w in re.split(r'[-_]', stem)) + "Component"

        # Locate angular.json (skip node_modules / obj / bin)
        angular_json_path = None
        for dirpath, dirs, filenames in os.walk(self.solution_root):
            dirs[:] = [d for d in dirs if d not in ("node_modules", "obj", "bin")]
            if "angular.json" in filenames:
                angular_json_path = os.path.join(dirpath, "angular.json")
                break

        if not angular_json_path:
            errors.append("angular.json not found under solution root")
            out = self._write_json("angular_apps.json", {"apps": []})
            return {"slice": "SLICE_1b", "status": "WARN", "files_written": [out],
                    "items_found": 0, "errors": errors}

        try:
            with open(angular_json_path, "r", encoding="utf-8") as fh:
                angular_config = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"Failed to parse angular.json: {exc}")
            out = self._write_json("angular_apps.json", {"apps": []})
            return {"slice": "SLICE_1b", "status": "WARN", "files_written": [out],
                    "items_found": 0, "errors": errors}

        client_app_dir = os.path.dirname(angular_json_path)
        projects = angular_config.get("projects", {})

        for project_name, project_cfg in projects.items():
            project_root = project_cfg.get("root", "")
            if not project_root.startswith("side-projects/"):
                continue

            source_root = project_cfg.get("sourceRoot", project_root + "/src")

            port = None
            try:
                port = project_cfg["architect"]["serve"]["options"]["port"]
            except (KeyError, TypeError):
                pass

            source_root_abs = os.path.join(client_app_dir, source_root)
            if not os.path.isdir(source_root_abs):
                errors.append(f"Source root not found: {source_root_abs}")
                continue

            seen_ids: set = set()
            routes: List[Dict] = []

            for dirpath, dirs, filenames in os.walk(source_root_abs):
                dirs[:] = [d for d in dirs if d != "node_modules"]
                for fname in filenames:
                    # Include routing files AND app.config.ts (inline routes)
                    if not (_ROUTING_FILE_RE.search(fname) or fname == "app.config.ts"):
                        continue
                    fpath = os.path.join(dirpath, fname)
                    content = self._read_file(fpath)
                    if content is None:
                        errors.append(f"Unreadable: {fpath}")
                        continue
                    rel_file = os.path.relpath(fpath, self.solution_root).replace("\\", "/")
                    covered: List[tuple] = []
                    for m in _sub_anchor_re.finditer(content):
                        bracket_pos = m.end() - 1
                        if any(s <= bracket_pos <= e for s, e in covered):
                            continue
                        bracket_end = _find_array_end(content, bracket_pos)
                        if bracket_end == -1:
                            continue
                        if not _ROUTE_PATH_RE.search(content[bracket_pos: bracket_end + 1]):
                            continue
                        covered.append((bracket_pos, bracket_end))
                        entries = _extract_routes_from_array(
                            content, rel_file,
                            bracket_pos + 1, bracket_end,
                            "", "",
                        )
                        # Fix UNKNOWN components from bare import() calls
                        segment = content[bracket_pos + 1: bracket_end]
                        bare_imports = _lc_bare_import_re.findall(segment)
                        unknown_entries = [e for e in entries if e["component"] == "UNKNOWN"]
                        if len(bare_imports) == len(unknown_entries):
                            for entry, imp in zip(unknown_entries, bare_imports):
                                entry["component"] = _component_from_import(imp)
                                entry["type"] = "lazy-component"
                                entry["id"] = _make_route_id(entry["path"], entry["component"])
                        for entry in entries:
                            if entry["id"] not in seen_ids:
                                seen_ids.add(entry["id"])
                                routes.append(entry)

            routes.sort(key=lambda r: r.get("path", ""))
            app_entry: Dict = {
                "name": project_name,
                "source_root": project_root,
                "routes": routes,
            }
            if port is not None:
                app_entry["port"] = port
            apps.append(app_entry)

        apps.sort(key=lambda a: a["name"])
        output_path = self._write_json("angular_apps.json", {"apps": apps})
        total_routes = sum(len(a["routes"]) for a in apps)
        return {
            "slice": "SLICE_1b",
            "status": "OK",
            "files_written": [output_path],
            "items_found": total_routes,
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # SLICE_1c -- ServiceAlert.Web REST API controllers
    # ------------------------------------------------------------------

    def _run_slice_1c(self) -> Dict:
        """Scan ServiceAlert.Web/Controllers for REST API controllers."""
        errors: List[str] = []
        controllers: List[Dict] = []

        web_controllers_dir = os.path.join(
            self.solution_root, "ServiceAlert.Web", "Controllers"
        )
        if not os.path.isdir(web_controllers_dir):
            errors.append(f"Controllers directory not found: {web_controllers_dir}")
            out = self._write_json("mvc_routes.json", {"mvc_routes": []})
            return {"slice": "SLICE_1c", "status": "WARN", "files_written": [out],
                    "items_found": 0, "errors": errors}

        _route_attr_re = re.compile(r'\[Route\("([^"]+)"\)\]')
        _namespace_re = re.compile(r'\bnamespace\s+([\w.]+)')
        _action_re = re.compile(
            r'public\s+(?:async\s+)?(?:Task<[^>]+>|IActionResult|'
            r'ActionResult(?:<[^>]+>)?|\w+)\s+(\w+)\s*\('
        )
        _class_re = re.compile(r'\bclass\s+(\w+Controller)\b')
        _skip_actions = {"ToString", "GetHashCode", "Equals", "GetType"}

        for dirpath, _dirs, filenames in os.walk(web_controllers_dir):
            rel_dir = os.path.relpath(dirpath, self.solution_root).replace("\\", "/")
            if any(seg in rel_dir for seg in ("/obj", "/bin", "obj/", "bin/")):
                continue
            for fname in filenames:
                if not fname.endswith("Controller.cs") or fname == "BaseController.cs":
                    continue
                fpath = os.path.join(dirpath, fname)
                content = self._read_file(fpath)
                if content is None:
                    errors.append(f"Unreadable: {fpath}")
                    continue

                rel_file = os.path.relpath(fpath, self.solution_root).replace("\\", "/")

                class_m = _class_re.search(content)
                controller_name = class_m.group(1) if class_m else fname.replace(".cs", "")

                route_m = _route_attr_re.search(content)
                route_prefix = route_m.group(1) if route_m else "api/[controller]"

                ns_m = _namespace_re.search(content)
                namespace = ns_m.group(1) if ns_m else ""

                seen_actions: set = set()
                actions: List[str] = []
                for m in _action_re.finditer(content):
                    action = m.group(1)
                    if action not in seen_actions and action not in _skip_actions:
                        seen_actions.add(action)
                        actions.append(action)

                controllers.append({
                    "controller": controller_name,
                    "route_prefix": route_prefix,
                    "namespace": namespace,
                    "file": rel_file,
                    "actions": actions,
                })

        controllers.sort(key=lambda c: c["controller"])
        output_path = self._write_json("mvc_routes.json", {"mvc_routes": controllers})
        return {
            "slice": "SLICE_1c",
            "status": "OK",
            "files_written": [output_path],
            "items_found": len(controllers),
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # SLICE_15 -- External HTTP integrations
    # ------------------------------------------------------------------

    def _run_slice_15(self) -> Dict:
        """Scan AddHttpClient<I, C> registrations across all C# projects."""
        errors: List[str] = []
        integrations: List[Dict] = []

        _http_client_re = re.compile(r'services\.AddHttpClient<(\w+),\s*(\w+)>')
        _skip_dirs = {"obj", "bin", "node_modules", ".git"}
        _skip_rel_fragments = (".test", "tests/", "/tests", "clientapp")
        seen: set = set()

        for dirpath, dirs, filenames in os.walk(self.solution_root):
            dirs[:] = [d for d in dirs if d.lower() not in _skip_dirs]
            rel_dir = (
                os.path.relpath(dirpath, self.solution_root)
                .replace("\\", "/")
                .lower()
            )
            if any(s in rel_dir for s in _skip_rel_fragments):
                dirs[:] = []
                continue

            for fname in filenames:
                if not fname.endswith(".cs"):
                    continue
                fpath = os.path.join(dirpath, fname)
                content = self._read_file(fpath)
                if content is None:
                    continue

                rel_file = os.path.relpath(fpath, self.solution_root).replace("\\", "/")
                parts = rel_file.split("/")
                project_name = parts[0] if parts else ""
                source_file = "/".join(parts[1:]) if len(parts) > 1 else rel_file

                for m in _http_client_re.finditer(content):
                    interface_name = m.group(1)
                    impl_name = m.group(2)
                    key = (project_name, interface_name, impl_name)
                    if key in seen:
                        continue
                    seen.add(key)
                    integrations.append({
                        "interface": interface_name,
                        "implementation": impl_name,
                        "host_project": project_name,
                        "source_file": source_file,
                    })

        integrations.sort(key=lambda i: (i["host_project"], i["interface"]))
        output_path = self._write_json("integrations.json", {"integrations": integrations})
        return {
            "slice": "SLICE_15",
            "status": "OK",
            "files_written": [output_path],
            "items_found": len(integrations),
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # I/O helpers
    # ------------------------------------------------------------------

    def _read_file(self, path: str):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                return fh.read()
        except OSError:
            return None

    def _write_json(self, filename: str, data: Any) -> str:
        os.makedirs(self.data_root, exist_ok=True)
        path = os.path.join(self.data_root, filename)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        print(f"[WRITE] {path}")
        return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m core.execution_engine <solution_root>")
        return 1
    solution_root = sys.argv[1]
    engine = ExecutionEngine(solution_root=solution_root)
    summary = engine.execute_next_slice()
    print(f"Slice: {summary['slice']}  Status: {summary['status']}  "
          f"Items: {summary['items_found']}  Errors: {len(summary['errors'])}")
    for err in summary["errors"]:
        print(f"  ERROR: {err}")
    return 0 if summary["status"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
