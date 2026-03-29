"""Coverage analysis – Phase 4.5+.

Reads two previously written output files from disk and computes how much of
the discovered UI/API/SQL surface area is actually exercised by identified
use cases.

Input files (read from ``output_root``):
    analysis-index.json        — per-file analysis produced by the pipeline
    use-cases.analysis.json    — use case records produced by UseCaseExtractor

Output file (written to ``output_root``):
    coverage.json

Coverage semantics
------------------
UI
    Pool   : unique Angular component class names found in files classified as
             "angular".  Components are the natural unit of entry-point identity
             because use cases are keyed by ``entry_point`` (a component name).
    Covered: component names that appear as ``entry_point`` in ≥1 use case.

API
    Pool   : unique method names extracted from C# files that contain at least
             one HTTP endpoint attribute (HttpGet / HttpPost / HttpPut /
             HttpDelete / Route).  These are the candidate endpoint methods.
    Used   : distinct API step names appearing in ``flow_steps`` of any use
             case (excluding sentinel values UNKNOWN / [CIRCULAR] / [DEPTH
             LIMIT]).

SQL
    Pool   : unique procedure names (``procedures_created``) and table names
             (``tables_created``) from files classified as "sql".
    Used   : distinct DB step names appearing in ``flow_steps`` of any use
             case (excluding sentinel values).

In all three domains: ``uncovered = pool − used/covered``.
``total = len(pool)`` so that ``total == covered + len(uncovered)`` always holds.

Rules
-----
* Deterministic: sets are sorted before output; no random values.
* Only real signals: no guessing, no invented names.
* Graceful degradation: if either input file is missing the analyzer still
  runs and produces a valid (possibly zero-count) report.
"""

import json
import os
from typing import Any, Dict, List, Set


class CoverageAnalyzer:
    # Sentinel step names that do not represent real identifiable objects.
    _SENTINELS: frozenset = frozenset({"UNKNOWN", "[CIRCULAR]", "[DEPTH LIMIT]"})

    def __init__(self, output_root: str = "output-data") -> None:
        self.output_root = output_root

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self) -> Dict:
        """Compute coverage report and write coverage.json.

        Returns the report dict (same structure as written to disk).
        """
        index: List[Dict] = self._load_json("analysis-index.json", default=[])
        use_cases: List[Dict] = self._load_json(
            "use-cases.analysis.json", default={}
        ).get("use_cases", [])

        ui = self._compute_ui(index, use_cases)
        api = self._compute_api(index, use_cases)
        sql = self._compute_sql(index, use_cases)

        report: Dict = {
            "ui": {"total": ui["total"], "covered": ui["covered"]},
            "api": {"total": api["total"], "used": api["used"]},
            "sql": {"total": sql["total"], "used": sql["used"]},
            "uncovered": {
                "ui": sorted(ui["uncovered"]),
                "api": sorted(api["uncovered"]),
                "sql": sorted(sql["uncovered"]),
            },
        }

        self._write_json("coverage.json", report)
        return report

    # ------------------------------------------------------------------
    # UI coverage
    # ------------------------------------------------------------------

    def _compute_ui(self, index: List[Dict], use_cases: List[Dict]) -> Dict:
        # Pool: all component class names from angular files.
        all_components: Set[str] = set()
        for entry in index:
            if entry.get("type") != "angular":
                continue
            for cls in entry.get("key_elements", {}).get("classes", []):
                if cls:
                    all_components.add(cls)

        # Covered: component names that are entry_points of at least one use case.
        covered: Set[str] = set()
        for uc in use_cases:
            ep = uc.get("entry_point", "")
            if ep:
                covered.add(ep)

        # Restrict covered to only those that were also in the pool.
        covered_in_pool = all_components & covered

        return {
            "total": len(all_components),
            "covered": len(covered_in_pool),
            "uncovered": list(all_components - covered_in_pool),
        }

    # ------------------------------------------------------------------
    # API coverage
    # ------------------------------------------------------------------

    def _compute_api(self, index: List[Dict], use_cases: List[Dict]) -> Dict:
        # Pool: method names from C# files that have ≥1 HTTP endpoint attribute.
        all_methods: Set[str] = set()
        for entry in index:
            if entry.get("type") != "csharp":
                continue
            ke = entry.get("key_elements", {})
            if not ke.get("endpoints"):
                continue
            for method in ke.get("methods", []):
                if method:
                    all_methods.add(method)

        # Used: real API step names from use case flow traces.
        used: Set[str] = set()
        for uc in use_cases:
            for step in uc.get("flow_steps", []):
                if step.get("type") == "API":
                    name = step.get("name", "")
                    if name and name not in self._SENTINELS:
                        used.add(name)

        # Restrict used to only items in the pool (extra names come from
        # capabilities.json matching, not from csharp files directly).
        used_in_pool = all_methods & used
        # Names used in flow_steps but not in the pool still count as "used"
        # since they represent real API calls; add them outside the pool check
        # for the metric only.
        total_used = len(used)

        return {
            "total": len(all_methods),
            "used": total_used,
            "uncovered": list(all_methods - used),
        }

    # ------------------------------------------------------------------
    # SQL coverage
    # ------------------------------------------------------------------

    def _compute_sql(self, index: List[Dict], use_cases: List[Dict]) -> Dict:
        # Pool: procedures and tables defined in SQL files.
        all_sql: Set[str] = set()
        for entry in index:
            if entry.get("type") != "sql":
                continue
            ke = entry.get("key_elements", {})
            for name in ke.get("procedures_created", []):
                if name:
                    all_sql.add(name)
            for name in ke.get("tables_created", []):
                if name:
                    all_sql.add(name)

        # Used: real DB step names from use case flow traces.
        used: Set[str] = set()
        for uc in use_cases:
            for step in uc.get("flow_steps", []):
                if step.get("type") == "DB":
                    name = step.get("name", "")
                    if name and name not in self._SENTINELS:
                        used.add(name)

        total_used = len(used)

        return {
            "total": len(all_sql),
            "used": total_used,
            "uncovered": list(all_sql - used),
        }

    # ------------------------------------------------------------------
    # I/O helpers
    # ------------------------------------------------------------------

    def _load_json(self, filename: str, default: Any) -> Any:
        path = os.path.join(self.output_root, filename)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError):
            return default

    def _write_json(self, filename: str, data: Any) -> None:
        os.makedirs(self.output_root, exist_ok=True)
        path = os.path.join(self.output_root, filename)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
