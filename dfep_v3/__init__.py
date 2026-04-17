# dfep_v3 — Copilot-Native Domain Feature Extraction Pipeline
# 
# Architecture: two-phase, Copilot-driven (NO external LLM)
#
# Phase 1: --generate-prompts
#   Deterministic extractor → structured prompt files
#   Copilot reads prompts → produces structured JSON response
#
# Phase 2: --parse-response
#   Copilot's JSON → parse → validate → report → temp.md
