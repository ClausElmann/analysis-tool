"""
Data models for the Rebuild Integrity Gate (RIG).
"""
from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(str, Enum):
    LOW    = "LOW"
    MEDIUM = "MEDIUM"
    HIGH   = "HIGH"


@dataclass
class IntegrityScores:
    structure: float   # 0.0–1.0  name/file-level similarity
    behavior:  float   # 0.0–1.0  control-flow shape similarity
    domain:    float   # 0.0–1.0  GreenAI-native vocabulary ratio (higher = more own)


@dataclass
class FileIntegrityReport:
    greenai_file:       str
    legacy_file:        str                    # best-matching legacy file
    risk_level:         RiskLevel
    scores:             IntegrityScores
    flags:              list[str] = field(default_factory=list)
    recommendations:    list[str] = field(default_factory=list)
    gate_failed:        bool = False           # True if behavioral > 0.75 AND domain < 0.5
    behavior_signature: list[str] = field(default_factory=list)  # ordered step labels of main GreenAI method


@dataclass
class IntegrityReport:
    gate_status:  str                       # "PASS" or "FAIL"
    failed_files: int
    total_files:  int
    files:        list[FileIntegrityReport] = field(default_factory=list)
