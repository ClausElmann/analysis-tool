"""
Rebuild Integrity Gate (RIG) — core checker.

Usage:
    from analysis_tool.integrity.checker import run_integrity_check

    report = run_integrity_check(
        greenai_folder="c:/Udvikling/green-ai/src/GreenAi.Api/Features",
        legacy_folder="c:/Udvikling/sms-service",
        # include_sql=True is the default — SQL is PRIMARY (equal weight to .cs)
    )
"""
from __future__ import annotations

import json
from pathlib import Path

from .models import (
    FileIntegrityReport,
    IntegrityReport,
    IntegrityScores,
    RiskLevel,
)
from .analyzers.structural  import structural_similarity, naming_guard
from .analyzers.behavioral  import behavioral_similarity
from .analyzers.domain      import domain_similarity
from .analyzers.llm_layer   import llm_analyze
from .analyzers.sql_analyzer import (
    sql_behavior_signature,
    sql_structural_similarity,
    sql_naming_guard,
    sql_schema_guard,
    is_schema_file,
)


# Gate thresholds (Architect-defined)
_BEHAVIORAL_FAIL_THRESHOLD = 0.75
_DOMAIN_FAIL_THRESHOLD     = 0.50


def _load_whitelist() -> list[str]:
    """Load whitelist patterns from config.json. Returns list of glob-style patterns."""
    import json as _json
    config_path = Path(__file__).parent / "config.json"
    try:
        cfg = _json.loads(config_path.read_text(encoding="utf-8"))
        return [p.lower() for p in cfg.get("whitelist", [])]
    except Exception:
        return []


def _is_whitelisted(file_path: Path, patterns: list[str]) -> bool:
    """Return True if the file name matches any whitelist pattern."""
    from fnmatch import fnmatch
    name = file_path.name.lower()
    return any(fnmatch(name, p) for p in patterns)


def _load_llm_overrides(greenai_folder: Path) -> dict:
    """
    Indlæs llm_scores_<domain>.json override-fil hvis den eksisterer.

    Workflow (Copilot Chat som officiel LLM):
      1. Kør heuristik: python -m analysis_tool.integrity.run_rig ... --copilot-batch batch.md
      2. Indsæt batch.md i VS Code Copilot Chat
      3. Gem Copilot-svar som: analysis/integrity/llm_scores_<domain>.json
      4. Kør RIG igen — override anvendes automatisk på matchende filer

    Format af llm_scores_<domain>.json:
      {
        "<Filename.cs>": {
          "structural_similarity": 0.0,
          "behavioral_similarity": 0.0,
          "domain_similarity": 0.0,
          "flags": [...],
          "recommendations": [...]
        }
      }

    Domain-hint: lowercase af greenai_folder.name (e.g. CustomerAdmin -> customeradmin).
    """
    domain_hint = greenai_folder.name.lower()
    # Look in analysis/integrity/ relative to tool root:
    # analysis_tool/integrity/checker.py -> analysis_tool/integrity/ -> analysis_tool/ -> root
    tool_root  = Path(__file__).parent.parent.parent
    score_file = tool_root / "analysis" / "integrity" / f"llm_scores_{domain_hint}.json"
    if score_file.exists():
        try:
            return json.loads(score_file.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


# RIG scope: backend/API only.
# .razor / .html / .ts EXCLUDED — GreenAI uses Blazor, legacy uses Angular → no frontend duplication risk.
# Test files EXCLUDED — if SQL/API/backend is GreenAI-native, tests are non-duplicate by definition.
# Focus: .cs (handlers, repositories, validators, endpoints) + .sql (primary, equal weight).
_EXCLUDED_SUFFIXES = frozenset({".razor", ".cshtml", ".html", ".ts", ".js", ".css", ".scss"})
_EXCLUDED_PATH_PARTS = frozenset({"test", "tests", "spec", "specs"})


def _collect_files(folder: Path, extensions: tuple[str, ...]) -> list[Path]:
    return [
        p for p in folder.rglob("*")
        if p.suffix.lower() in extensions
        and p.suffix.lower() not in _EXCLUDED_SUFFIXES
        and not any(part.lower() in _EXCLUDED_PATH_PARTS for part in p.parts)
    ]


def _find_best_legacy_match(
    greenai_path: Path,
    greenai_source: str,
    legacy_files: list[Path],
) -> tuple[Path, str]:
    """
    Find the legacy file whose name is most similar to the GreenAI file.
    Falls back to the legacy file with the highest structural similarity.
    """
    from difflib import SequenceMatcher

    ga_name = greenai_path.stem.lower()
    best_path   = legacy_files[0]
    best_score  = -1.0

    for lp in legacy_files:
        name_score = SequenceMatcher(None, ga_name, lp.stem.lower()).ratio()
        if name_score > best_score:
            best_score = name_score
            best_path  = lp

    legacy_source = best_path.read_text(encoding="utf-8", errors="replace")
    return best_path, legacy_source


def _risk_level(scores: IntegrityScores, gate_failed: bool) -> RiskLevel:
    if gate_failed:
        return RiskLevel.HIGH
    if scores.behavior > 0.60 or scores.structure > 0.70:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _recommendations(
    scores: IntegrityScores,
    struct_flags: list[str],
    behav_flags: list[str],
    domain_flags: list[str],
) -> list[str]:
    recs: list[str] = []
    if scores.structure > 0.60:
        recs.append(
            "Rename classes/methods to use GreenAI-native vocabulary "
            "(e.g. 'IngestWarning' instead of 'CreateWarning' if it matches legacy)."
        )
    if scores.behavior > 0.75:
        recs.append(
            "Refactor method flow: split into distinct steps (ingest / validate / persist) "
            "rather than a single sequential method matching legacy shape."
        )
    if scores.domain < 0.50:
        recs.append(
            "Increase GreenAI-native patterns: ensure Result<T>, ICurrentUser, "
            "IDbSession, and vertical-slice namespace are used."
        )
    for f in domain_flags:
        recs.append(f"Fix: {f}")
    return recs


def _analyze_file(
    greenai_path: Path,
    legacy_files: list[Path],
    use_llm: bool = False,  # Ignoreres — ekstern LLM ikke tilgængelig. Brug --copilot-batch for manuel analyse.
    overrides: dict | None = None,  # llm_scores_<domain>.json override — Copilot Chat scores
) -> FileIntegrityReport | None:
    try:
        greenai_source = greenai_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    if not legacy_files:
        return None

    legacy_path, legacy_source = _find_best_legacy_match(
        greenai_path, greenai_source, legacy_files
    )

    is_sql = greenai_path.suffix.lower() == ".sql"

    # --- Heuristic scores (always computed as baseline) ---
    if is_sql:
        if is_schema_file(greenai_source):
            # DDL/migration: schema guard is primary — table/column/constraint names are highest risk
            schema_score, schema_flags     = sql_schema_guard(greenai_source, legacy_source)
            struct_score, struct_flags     = sql_structural_similarity(greenai_source, legacy_source)
            naming_flags                   = sql_naming_guard(greenai_source, legacy_source)
            # Use schema score as behavioral proxy for gate evaluation
            behav_score                    = schema_score
            behav_flags: list[str]         = schema_flags
            behavior_sig                   = sql_behavior_signature(greenai_source)
            dom_score                      = 0.5
            dom_flags: list[str]           = []
            struct_flags                   = struct_flags + schema_flags  # merge for reporting
        else:
            struct_score, struct_flags     = sql_structural_similarity(greenai_source, legacy_source)
            naming_flags                   = sql_naming_guard(greenai_source, legacy_source)
            behav_score                    = 0.0
            behav_flags: list[str]         = []
            behavior_sig                   = sql_behavior_signature(greenai_source)
            dom_score                      = 0.5
            dom_flags: list[str]           = []
    else:
        struct_score, struct_flags                 = structural_similarity(greenai_source, legacy_source)
        behav_score,  behav_flags, behavior_sig    = behavioral_similarity(greenai_source, legacy_source)
        dom_score,    dom_flags                    = domain_similarity(greenai_source)
        naming_flags                               = naming_guard(greenai_source, legacy_source)

    all_flags = struct_flags + behav_flags + dom_flags + naming_flags
    recs_heuristic = _recommendations(
        IntegrityScores(struct_score, behav_score, dom_score),
        struct_flags, behav_flags, dom_flags,
    )

    # --- LLM override (Copilot Chat — officiel LLM metode) ---
    # Indlæs llm_scores_<domain>.json hvis den eksisterer (Copilot Chat resultater).
    # Workflow: --copilot-batch → Copilot Chat → gem JSON → kør RIG igen → override aktiv.
    llm_result = None
    source_label = "heuristic"

    if overrides:
        file_key = greenai_path.name
        if file_key in overrides:
            llm_result = overrides[file_key]
            source_label = "copilot"

    if llm_result:
        struct_score = llm_result["structural_similarity"]
        behav_score  = llm_result["behavioral_similarity"]
        dom_score    = llm_result["domain_similarity"]
        all_flags    = llm_result["flags"] or all_flags
        recs         = llm_result["recommendations"] or recs_heuristic
        source_label = "llm"
    else:
        recs = recs_heuristic

    scores      = IntegrityScores(struct_score, behav_score, dom_score)
    gate_failed = (behav_score > _BEHAVIORAL_FAIL_THRESHOLD) and (dom_score < _DOMAIN_FAIL_THRESHOLD)
    risk        = _risk_level(scores, gate_failed)

    return FileIntegrityReport(
        greenai_file       = str(greenai_path),
        legacy_file        = str(legacy_path),
        risk_level         = risk,
        scores             = scores,
        flags              = all_flags,
        recommendations    = recs,
        gate_failed        = gate_failed,
        behavior_signature = behavior_sig,
    )


def run_integrity_check(
    greenai_folder: str | Path,
    legacy_folder:  str | Path,
    include_sql:    bool = True,
    output_json:    str | Path | None = None,
    use_llm:        bool = False,
) -> IntegrityReport:
    """
    Run the full 3-layer integrity check.

    Scope: backend/API only.
    - .cs  PRIMARY — handlers, repositories, validators, endpoints (NOT tests)
    - .sql PRIMARY — equal weight to .cs (Dapper = SQL = behavior)
    - .razor / .html / .ts EXCLUDED — GreenAI uses Blazor, legacy uses Angular → no frontend risk.
    - tests/ EXCLUDED — if SQL/API/backend is GreenAI-native, tests are non-duplicate by definition.

    Args:
        greenai_folder: Root of the GreenAI feature folder to analyse.
        legacy_folder:  Root of the legacy codebase.
        include_sql:    Include .sql files — PRIMARY (equal weight to .cs). Default: True.
        output_json:    If given, write the report to this path as JSON.
        use_llm:        Ignoreres — ekstern LLM er ikke tilgængelig.
                        Brug run_rig.py --copilot-batch for manuel Copilot-analyse.

    Returns:
        IntegrityReport with gate_status PASS or FAIL.
    """
    extensions = (".cs", ".sql") if include_sql else (".cs",)
    # NOTE: include_sql=True is the default — SQL is PRIMARY (equal weight to .cs)

    greenai_files = _collect_files(Path(greenai_folder), extensions)
    legacy_files  = _collect_files(Path(legacy_folder),  extensions)

    if not greenai_files:
        raise FileNotFoundError(f"No {extensions} files found in: {greenai_folder}")
    if not legacy_files:
        raise FileNotFoundError(f"No {extensions} files found in: {legacy_folder}")

    whitelist = _load_whitelist()

    file_reports: list[FileIntegrityReport] = []
    overrides = _load_llm_overrides(Path(greenai_folder))

    for gf in greenai_files:
        if _is_whitelisted(gf, whitelist):
            continue  # Explicitly whitelisted — skip gate evaluation
        report = _analyze_file(gf, legacy_files, use_llm=use_llm, overrides=overrides)
        if report:
            file_reports.append(report)

    failed = [r for r in file_reports if r.gate_failed]
    gate   = "FAIL" if failed else "PASS"

    report = IntegrityReport(
        gate_status  = gate,
        failed_files = len(failed),
        total_files  = len(file_reports),
        files        = file_reports,
    )

    if output_json:
        _write_json(report, Path(output_json))

    return report


def _write_json(report: IntegrityReport, path: Path) -> None:
    def _serialise(obj):
        # Primitives first — avoids __instancecheck__ recursion with str+Enum
        if obj is None or isinstance(obj, (bool, int, float)):
            return obj
        if type(obj) is str:
            return obj
        if isinstance(obj, RiskLevel):
            return obj.value
        if isinstance(obj, list):
            return [_serialise(i) for i in obj]
        if hasattr(obj, "__dict__"):
            return {k: _serialise(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
        return str(obj)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_serialise(report), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report written to: {path}")
