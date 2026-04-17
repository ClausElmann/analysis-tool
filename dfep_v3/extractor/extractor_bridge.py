"""
dfep_v3/extractor/extractor_bridge.py

Exports extractors for dfep_v3.

L0Parser: unchanged from v2 — sms-service .cs extraction is stable.
GreenAIParser: upgraded to v3 (GreenAIExtractorV3) which adds .sql first-class facts.

Rationale for v3 upgrade (TASK A):
  v2 GreenAIParser walked .sql files but produced no CodeFact entries for them —
  because _extract_file only matched .cs patterns (classes, methods, endpoints).
  v3 extension adds _extract_sql_file so SQL files become evidence anchors:
    - file ref "GetTemplateById.sql:1" now maps to a real fact
    - CapabilityValidator no longer false-rejects capabilities citing SQL files
"""

from dfep_v2.extractor.l0_parser import L0Parser, CodeFact
from dfep_v3.extractor.greenai_extractor_v3 import GreenAIExtractorV3 as GreenAIParser

__all__ = ["L0Parser", "GreenAIParser", "CodeFact"]
