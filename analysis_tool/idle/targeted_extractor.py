"""analysis_tool/idle/targeted_extractor.py

Targeted Extractor Bridge — Idle Harvest v1

Takes structured JSON responses from Copilot harvest prompts and merges
the extracted facts DIRECTLY into the domain GA facts file
(analysis/dfep/responses/{domain}_ga.json).

This is the ONLY correct storage target — idle facts in a separate file
are invisible to DFEP v3, so the match score never changes.

Governance rules:
  - APPEND-ONLY — never overwrite existing GA capabilities
  - Every new capability entry is tagged: "source": "idle_harvest"
  - Existing capabilities: evidence list is extended (no overwrite)
  - Deduplication on evidence file:line strings
  - Returns ExtractionResult with per-target metrics
  - Input validation: reject empty or invalid JSON responses
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Result model — per-target metrics
# ---------------------------------------------------------------------------

@dataclass
class ExtractionResult:
    """
    Metrics for a single capability extraction.
    Used by the runner to detect STOP_NO_NEW_FILES and report per-target progress.
    """
    capability_id: str
    files_found: int            # unique files added/referenced in this extraction
    evidence_before: int        # evidence items in GA before merge
    evidence_after: int         # evidence items in GA after merge
    new_evidence: int           # = evidence_after - evidence_before
    is_new_capability: bool     # True if capability was added fresh to GA


# ---------------------------------------------------------------------------
# Targeted Extractor
# ---------------------------------------------------------------------------


class TargetedExtractor:
    """
    Processes Copilot harvest JSON responses and merges extracted facts
    DIRECTLY into the domain's GA facts file:

        analysis/dfep/responses/{domain_lower}_ga.json

    This makes the facts immediately visible to DFEP v3 on the next run.

    Merge rules:
      - If capability_id already in GA → append new evidence (dedup)
      - If capability_id missing from GA → add new capability entry
      - Never remove or overwrite existing entries
      - All new/modified entries tagged: "source": "idle_harvest"
    """

    def __init__(
        self,
        domain: str,
        responses_dir: str | None = None,
    ):
        self.domain = domain
        _tool_root = Path(__file__).parent.parent.parent
        _responses_dir = responses_dir or str(
            _tool_root / "analysis" / "dfep" / "responses"
        )
        self._ga_path = os.path.join(_responses_dir, f"{domain.lower()}_ga.json")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_response(
        self,
        response_path: str,
        capability_id: str,
        capability_intent: str = "",
    ) -> ExtractionResult:
        """
        Parse a Copilot harvest response JSON file and merge facts into GA.

        Returns ExtractionResult with per-target metrics.
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

        # Safety: reject responses where "found" / "flow_reconstructed" is explicitly False
        if data.get("found") is False:
            print(f"      [SKIP] {capability_id}: found=false in response")
            ga = self._load_ga()
            existing = self._find_capability(ga, capability_id)
            ev_count = len(existing.get("evidence", [])) if existing else 0
            return ExtractionResult(
                capability_id=capability_id,
                files_found=0,
                evidence_before=ev_count,
                evidence_after=ev_count,
                new_evidence=0,
                is_new_capability=False,
            )

        return self._merge_into_ga(data, capability_id, capability_intent)

    # ------------------------------------------------------------------
    # GA merge logic
    # ------------------------------------------------------------------

    def _merge_into_ga(
        self, data: dict, capability_id: str, capability_intent: str
    ) -> ExtractionResult:
        ga = self._load_ga()
        caps = ga.setdefault("capabilities", [])

        existing = self._find_capability(ga, capability_id)
        evidence_before = len(existing.get("evidence", [])) if existing else 0
        is_new = existing is None

        # Build evidence list from all response sections
        new_evidence = self._extract_evidence(data, capability_id)
        new_flow_steps = self._extract_flow_steps(data)
        new_files = {self._file_only(e) for e in new_evidence}

        if is_new:
            # Create a fresh capability entry
            intent = (
                data.get("notes", "")[:120]
                or capability_intent
                or capability_id
            )
            entry = {
                "id": capability_id,
                "intent": capability_intent or intent,
                "business_value": f"Discovered via idle harvest on {datetime.now().strftime('%Y-%m-%d')}",
                "flow": new_flow_steps,
                "constraints": [],
                "rules": [],
                "evidence": new_evidence,
                "confidence": float(data.get("confidence", 0.6)),
                "source": "idle_harvest",
                "harvest_date": datetime.now().strftime("%Y-%m-%d"),
            }
            caps.append(entry)
            existing_after = entry
        else:
            # Extend existing — append-only, deduplicate evidence strings
            old_evidence = existing.get("evidence", [])
            merged_evidence = old_evidence + [e for e in new_evidence if e not in old_evidence]
            existing["evidence"] = merged_evidence

            old_flow = existing.get("flow", [])
            existing["flow"] = old_flow + [s for s in new_flow_steps if s not in old_flow]

            # Only update source tag if not already set
            if "source" not in existing:
                existing["source"] = "idle_harvest"

            existing_after = existing

        evidence_after = len(existing_after.get("evidence", []))
        self._write_ga(ga)

        return ExtractionResult(
            capability_id=capability_id,
            files_found=len(new_files),
            evidence_before=evidence_before,
            evidence_after=evidence_after,
            new_evidence=evidence_after - evidence_before,
            is_new_capability=is_new,
        )

    # ------------------------------------------------------------------
    # Evidence extraction — one flat list of "file:line" strings
    # ------------------------------------------------------------------

    def _extract_evidence(self, data: dict, capability_id: str) -> list[str]:
        evidence: list[str] = []

        def _add(file_str: str) -> None:
            if file_str and file_str not in evidence:
                evidence.append(file_str)

        # Entry point
        ep = data.get("entry_point", {})
        if ep.get("file"):
            _add(ep["file"])

        # Request model
        rm = data.get("request_model", {})
        if rm.get("file"):
            _add(rm["file"])

        # Service, repository, additional_evidence
        for section in ("service_calls", "repository_calls", "additional_evidence"):
            for item in data.get(section, []):
                if item.get("file"):
                    _add(item["file"])

        # SQL
        for sql in data.get("sql_operations", []):
            if sql.get("file"):
                _add(sql["file"])

        # Execution flow steps
        for step in data.get("execution_flow", []):
            if step.get("file"):
                _add(step["file"])

        # Validations / side effects / error paths — extract inline file:line
        import re
        file_ref = re.compile(r"[\w./\\-]+\.(cs|sql|razor|ts|js):\d+")
        for section in ("validations", "side_effects", "error_paths"):
            for item in data.get(section, []):
                for match in file_ref.findall(str(item)):
                    _add(match)

        return evidence

    def _extract_flow_steps(self, data: dict) -> list[str]:
        """Build human-readable flow strings (for the GA 'flow' list).

        NOTE: Evidence markers (file:line refs) are intentionally OMITTED from
        flow steps. Flow steps in GA capabilities are validated against the
        green-ai codebase — not the L0 (sms-service) codebase. Including
        L0 file refs would cause DFEP v3 phantom-ref rejection on unimplemented
        domains. Uncited steps produce WARNINGs (accepted), not errors.
        """
        steps: list[str] = []

        ep = data.get("entry_point", {})
        if ep.get("file"):
            verb = ep.get("http_verb", "HTTP")
            route = ep.get("route", "")
            method = ep.get("method", "")
            steps.append(
                f"{verb} {route} → {ep.get('controller', '')}::{method}"
            )

        for sc in data.get("service_calls", []):
            steps.append(
                f"Service: {sc.get('class', '')}::{sc.get('method', '')}"
            )

        for rc in data.get("repository_calls", []):
            steps.append(
                f"Repository: {rc.get('class', '')}::{rc.get('method', '')}"
            )

        for sql in data.get("sql_operations", []):
            steps.append(
                f"SQL {sql.get('type', '')} {sql.get('table', '')}"
            )

        # FLOW_STITCH responses
        for step in data.get("execution_flow", []):
            steps.append(
                f"[step {step.get('step', '?')}] {step.get('layer', '')}:"
                f" {step.get('description', '')}"
            )

        return steps

    # ------------------------------------------------------------------
    # GA file I/O
    # ------------------------------------------------------------------

    def _load_ga(self) -> dict:
        if not os.path.exists(self._ga_path):
            raise FileNotFoundError(
                f"GA facts file not found: {self._ga_path}\n"
                "Run DFEP v3 phase2 for this domain first to create the GA response file."
            )
        with open(self._ga_path, encoding="utf-8") as f:
            return json.load(f)

    def _write_ga(self, ga: dict) -> None:
        with open(self._ga_path, "w", encoding="utf-8") as f:
            json.dump(ga, f, indent=2, ensure_ascii=False)

    def _find_capability(self, ga: dict, capability_id: str) -> dict | None:
        for cap in ga.get("capabilities", []):
            if cap.get("id") == capability_id:
                return cap
        return None

    @staticmethod
    def _file_only(evidence_str: str) -> str:
        """Strip :line number to get bare file path."""
        return evidence_str.split(":")[0] if ":" in evidence_str else evidence_str

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
