"""Shared data model used by the analysis pipeline."""

from dataclasses import asdict, dataclass, field
from typing import Dict, List


@dataclass
class FileAnalysis:
    """Represents a normalized analysis result for a single file."""

    project: str = ""
    path: str = ""
    type: str = ""
    technology: str = ""
    summary: str = ""
    key_elements: Dict[str, List[str]] = field(default_factory=dict)
    domain_signals: Dict[str, List[str]] = field(default_factory=dict)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    inputs_outputs: Dict[str, List[str]] = field(default_factory=dict)
    risks_notes: List[str] = field(default_factory=list)
    raw_extract: str = ""

    def __post_init__(self):
        # Guarantee no null values for any field
        if self.project is None:
            self.project = ""
        if self.path is None:
            self.path = ""
        if self.type is None:
            self.type = ""
        if self.technology is None:
            self.technology = ""
        if self.summary is None:
            self.summary = ""
        if self.raw_extract is None:
            self.raw_extract = ""
        if self.key_elements is None:
            self.key_elements = {}
        if self.domain_signals is None:
            self.domain_signals = {}
        if self.dependencies is None:
            self.dependencies = {}
        if self.inputs_outputs is None:
            self.inputs_outputs = {}
        if self.risks_notes is None:
            self.risks_notes = []

    def to_dict(self) -> dict:
        raw = asdict(self)
        # Ensure deterministic key ordering in all nested dicts
        raw["key_elements"] = {k: sorted(v) if isinstance(v, list) else v for k, v in sorted(raw["key_elements"].items())}
        raw["domain_signals"] = {k: sorted(v) if isinstance(v, list) else v for k, v in sorted(raw["domain_signals"].items())}
        raw["dependencies"] = {k: sorted(v) if isinstance(v, list) else v for k, v in sorted(raw["dependencies"].items())}
        raw["inputs_outputs"] = {k: sorted(v) if isinstance(v, list) else v for k, v in sorted(raw["inputs_outputs"].items())}
        raw["risks_notes"] = raw["risks_notes"] if isinstance(raw["risks_notes"], list) else []
        return raw
