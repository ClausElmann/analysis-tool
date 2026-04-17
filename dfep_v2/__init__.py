# dfep_v2/__init__.py
"""
DFEP v2 — Domain Functional Equivalence Protocol

Hybrid deterministic + LLM analysis engine.

Architecture:
  Layer 1 (Deterministic): extractor/ — raw code facts
  Layer 2 (Intelligence):  intelligence/ — LLM capability synthesis + comparison
  Layer 3 (Validation):    validation/ — anti-hallucination fact-binding
  Orchestration:           engine/dfep_runner.py — 9-step pipeline
  Output:                  output/report_generator.py — versioned markdown

CLI:
  cd analysis-tool
  python -m dfep_v2.engine.dfep_runner --domain Templates
  python -m dfep_v2.engine.dfep_runner --all
  python -m dfep_v2.engine.dfep_runner --domain Templates --stub   # no LLM
"""
