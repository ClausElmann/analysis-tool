"""analysis_tool/idle/targeted_extractor.py

Targeted Extractor Bridge — Idle Harvest v1

Takes structured JSON responses from Copilot harvest prompts and maps
them to CodeFact-compatible entries that can be merged into the domain's
existing GA fact file.

Governance rules:
  - APPEND-ONLY — never overwrite existing facts
  - Every extracted fact is tagged with:
      source = "idle_harvest"
      capability_id = <from which gap this came>
  - Returns count of NEW facts added (0 means nothing new)
  - Input validation: reject empty or invalid JSON responses
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Fact model — aligns with dfep_v3 CodeFact structure
# ---------------------------------------------------------------------------

@dataclass
class HarvestedFact:
    """
    A single code fact extracted from a Copilot harvest response.

    Tagged with source="idle_harvest" + capability_id for traceability.
    Compatible with CodeFact used by DFEP v3 extractors.
    """
    file: str               # "path/to/File.cs:line" or "path/to/File.sql:1"
    class_name: str         # controller, service, repository, SQL
    method: str             # method name or SQL operation type
    description: str        # what this fact proves
    capability_id: str      # which gap this fact came from
    source: str = "idle_harvest"
    harvest_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    params: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    sql_ops: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Targeted Extractor
# ---------------------------------------------------------------------------


class TargetedExtractor:
    """
    Processes Copilot harvest JSON responses into HarvestedFact entries.

    Storage: appends to analysis/dfep/idle_facts/{domain_lower}_idle_facts.json
    The file is a JSON array of HarvestedFact dicts.

    Deduplication: a fact is skipped if an identical (file, method) pair
    already exists in the stored facts.
    """

    def __init__(
        self,
        domain: str,
        facts_dir: str | None = None,
    ):
        self.domain = domain
        _tool_root = Path(__file__).parent.parent.parent
        self.facts_dir = facts_dir or str(_tool_root / "analysis" / "dfep" / "idle_facts")
        os.makedirs(self.facts_dir, exist_ok=True)
        self._facts_path = os.path.join(self.facts_dir, f"{domain.lower()}_idle_facts.json")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_response(
        self,
        response_path: str,
        capability_id: str,
    ) -> int:
        """
        Parse a Copilot harvest response JSON file.
        Extracts facts, deduplicates, and appends new ones to storage.

        Returns the number of NEW facts added.
        """
        # Safety: reject missing / empty files
        if not os.path.exists(response_path):
            raise FileNotFoundError(f"Response file not found: {response_path}")
        if os.path.getsize(response_path) < 10:
            raise ValueError(f"Response file appears empty: {response_path}")

        with open(response_path, encoding="utf-8") as f:
            raw = f.read().strip()

        data = self._parse_json(raw)
        if not data:
            raise ValueError(f"Could not parse JSON from: {response_path}")

        # Safety: reject responses where "found" is explicitly False
        if data.get("found") is False:
            print(f"      [SKIP] {capability_id}: capability not found in response (found=false)")
            return 0

        new_facts = self._extract_facts(data, capability_id)
        if not new_facts:
            return 0

        return self._append_facts(new_facts)

    def load_all_facts(self) -> list[HarvestedFact]:
        """Load all previously harvested facts for this domain."""
        if not os.path.exists(self._facts_path):
            return []
        with open(self._facts_path, encoding="utf-8") as f:
            raw = json.load(f)
        return [
            HarvestedFact(**{k: v for k, v in item.items() if k in HarvestedFact.__dataclass_fields__})
            for item in raw
        ]

    # ------------------------------------------------------------------
    # Extraction logic
    # ------------------------------------------------------------------

    def _extract_facts(self, data: dict, capability_id: str) -> list[HarvestedFact]:
        facts: list[HarvestedFact] = []

        # Entry point
        ep = data.get("entry_point")
        if ep and ep.get("file"):
            facts.append(HarvestedFact(
                file=ep["file"],
                class_name=ep.get("controller", "Controller"),
                method=ep.get("method", "unknown"),
                description=f"Entry point: {ep.get('http_verb', 'HTTP')} {ep.get('route', '')}",
                capability_id=capability_id,
            ))

        # Service calls
        for sc in data.get("service_calls", []):
            if sc.get("file"):
                facts.append(HarvestedFact(
                    file=sc["file"],
                    class_name=sc.get("class", "Service"),
                    method=sc.get("method", "unknown"),
                    description=f"Service call for {capability_id}",
                    capability_id=capability_id,
                ))

        # Repository calls
        for rc in data.get("repository_calls", []):
            if rc.get("file"):
                facts.append(HarvestedFact(
                    file=rc["file"],
                    class_name=rc.get("class", "Repository"),
                    method=rc.get("method", "unknown"),
                    description=f"Repository call for {capability_id}",
                    capability_id=capability_id,
                ))

        # SQL operations
        for sql in data.get("sql_operations", []):
            if sql.get("file"):
                facts.append(HarvestedFact(
                    file=sql["file"],
                    class_name="SQL",
                    method=f"{sql.get('type', 'SQL')}_{sql.get('table', 'unknown')}",
                    description=f"SQL {sql.get('type', '')} on {sql.get('table', '')}",
                    capability_id=capability_id,
                    sql_ops=[sql.get("type", "")],
                    tables=[sql.get("table", "")],
                ))

        # Additional evidence (from LOW_CONFIDENCE prompts)
        for ev in data.get("additional_evidence", []):
            if ev.get("file"):
                facts.append(HarvestedFact(
                    file=ev["file"],
                    class_name=ev.get("type", "evidence").title(),
                    method=ev.get("description", "")[:60],
                    description=ev.get("description", ""),
                    capability_id=capability_id,
                ))

        # Execution flow (from UNKNOWN_FLOW prompts)
        for step in data.get("execution_flow", []):
            if step.get("file"):
                facts.append(HarvestedFact(
                    file=step["file"],
                    class_name=step.get("layer", "unknown"),
                    method=step.get("description", "")[:60],
                    description=step.get("description", ""),
                    capability_id=capability_id,
                ))

        return facts

    # ------------------------------------------------------------------
    # Storage — append-only
    # ------------------------------------------------------------------

    def _append_facts(self, new_facts: list[HarvestedFact]) -> int:
        existing = self.load_all_facts()
        existing_keys = {(f.file, f.method) for f in existing}

        truly_new = [
            f for f in new_facts
            if (f.file, f.method) not in existing_keys
        ]

        if truly_new:
            combined = existing + truly_new
            with open(self._facts_path, "w", encoding="utf-8") as out:
                json.dump(
                    [f.to_dict() for f in combined],
                    out,
                    indent=2,
                    ensure_ascii=False,
                )

        return len(truly_new)

    # ------------------------------------------------------------------
    # JSON parsing helper
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json(raw: str) -> dict | None:
        import re
        # Strip markdown fences if present
        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if fence:
            raw = fence.group(1)
        else:
            # Find first { ... } block
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1:
                raw = raw[start:end + 1]

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
