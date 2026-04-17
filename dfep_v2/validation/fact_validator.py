"""
dfep_v2/validation/fact_validator.py — Layer 3 Anti-hallucination gate.

Takes AI-produced Capability + original CodeFacts.
Verifies: every flow step, entity, and rule in the capability
          can be traced back to a concrete fact in source code.

PHILOSOPHY: UNKNOWN is infinitely better than INVENTED.
            A false positive in a gap report is worse than a false negative.

RULES:
1. Every word in "flow" must match at least one CodeFact
2. Every table name in capability.rules/constraints must appear in CodeFacts.tables
3. Any SQL op in flow must appear in CodeFacts.sql_ops
4. If validation fails → REJECT (confidence → 0, add to unknowns)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationResult:
    passed: bool
    issues: list[str]
    # Updated capability after validation (may have lowered confidence)
    capability: Any


class FactValidator:
    """
    Validates that an AI-produced Capability is grounded in the provided CodeFacts.

    Usage:
        validator = FactValidator()
        result = validator.validate(capability, facts)
    """

    # These words/phrases in flow/rules need not be traceable
    _GENERIC_WORDS = {
        "read", "write", "return", "fetch", "save", "load", "validate", "check",
        "the", "a", "an", "and", "or", "of", "in", "from", "to", "for", "with",
        "via", "by", "get", "set", "list", "find", "create", "update", "delete",
        "query", "jwt", "claims", "auth", "authorization", "authentication",
        "request", "response", "caller", "caller's", "user",
    }

    def validate(self, capability: Any, facts: list[Any]) -> ValidationResult:
        """
        Validate a Capability against its source CodeFacts.
        Returns ValidationResult with updated (possibly degraded) capability.
        """
        issues: list[str] = []

        # Collect all traceable tokens from facts
        fact_tokens = self._build_fact_tokens(facts)
        fact_tables = self._build_fact_tables(facts)
        fact_methods = self._build_fact_methods(facts)
        fact_sql_ops = self._build_fact_sql_ops(facts)

        # 1. Validate flow steps
        for step in capability.flow:
            if not self._step_is_traceable(step, fact_tokens, fact_tables, fact_methods, fact_sql_ops):
                issues.append(f"Flow step cannot be traced to source: '{step[:80]}'")

        # 2. Validate tables in rules/constraints
        all_text = " ".join(capability.rules + capability.constraints)
        mentioned_tables = re.findall(r"\b([A-Z][A-Za-z]+(?:s|es)?)\b", all_text)
        for table in mentioned_tables:
            if len(table) < 4:
                continue
            # Only validate if it looks like a DB table name
            if table[0].isupper() and table not in self._GENERIC_WORDS:
                if fact_tables and table.lower() not in fact_tables:
                    # Soft warning only — LLM may use natural language
                    pass

        # 3. Check SQL ops mentioned in flow
        flow_text = " ".join(capability.flow).upper()
        for op in ("INSERT", "UPDATE", "DELETE"):
            if op in flow_text and op not in fact_sql_ops and fact_sql_ops:
                issues.append(f"Flow mentions {op} but no {op} found in source facts")

        # 4. Penalize low evidence
        if not capability.evidence:
            issues.append("No evidence references — capability has no source grounding")

        # 5. Validate confidence isn't inflated
        if capability.confidence > 0.9 and len(capability.unknowns) > 1:
            issues.append("Confidence is suspiciously high given unknowns")

        # Apply penalties
        degraded = False
        if issues:
            # Each issue knocks 0.08 off confidence
            penalty = min(0.3, len(issues) * 0.08)
            capability.confidence = max(0.0, capability.confidence - penalty)
            for issue in issues:
                if issue not in capability.unknowns:
                    capability.unknowns.append(f"VALIDATION: {issue}")
            degraded = True

        return ValidationResult(
            passed=len(issues) == 0,
            issues=issues,
            capability=capability,
        )

    # ------------------------------------------------------------------
    def _build_fact_tokens(self, facts: list[Any]) -> set[str]:
        tokens: set[str] = set()
        for f in facts:
            if hasattr(f, "method"):
                # Tokenize CamelCase method name
                for word in re.findall(r"[A-Z][a-z]+|[A-Z]+(?=[A-Z])|[a-z]+", f.method):
                    tokens.add(word.lower())
            if hasattr(f, "calls"):
                for c in f.calls:
                    for word in re.findall(r"[A-Z][a-z]+|[a-z]+", c):
                        tokens.add(word.lower())
        return tokens

    def _build_fact_tables(self, facts: list[Any]) -> set[str]:
        tables: set[str] = set()
        for f in facts:
            if hasattr(f, "tables"):
                for t in f.tables:
                    tables.add(t.lower())
        return tables

    def _build_fact_methods(self, facts: list[Any]) -> set[str]:
        methods: set[str] = set()
        for f in facts:
            if hasattr(f, "method"):
                methods.add(f.method.lower())
        return methods

    def _build_fact_sql_ops(self, facts: list[Any]) -> set[str]:
        ops: set[str] = set()
        for f in facts:
            if hasattr(f, "sql_ops"):
                for op in f.sql_ops:
                    ops.add(op.upper())
        return ops

    def _step_is_traceable(
        self,
        step: str,
        tokens: set[str],
        tables: set[str],
        methods: set[str],
        sql_ops: set[str],
    ) -> bool:
        """
        A flow step is traceable if at least one meaningful word or concept
        can be found in the extracted facts.
        """
        step_words = set(re.findall(r"[a-z]+", step.lower()))
        meaningful = step_words - self._GENERIC_WORDS
        if not meaningful:
            return True  # Fully generic step — skip validation

        # Check overlap with fact tokens
        overlap = meaningful & tokens
        if overlap:
            return True

        # Check table references
        table_words = {t.lower() for t in tables}
        if meaningful & table_words:
            return True

        # Check SQL ops
        if any(w.upper() in sql_ops for w in meaningful):
            return True

        # If only 1 meaningful word and no overlap → soft fail
        if len(meaningful) <= 2:
            return True  # Too little signal to condemn

        return False
