"""
LLM integrity analysis layer — VS Code Copilot (built-in) ONLY.

IMPORTANT — ADGANGSBEGRÆNSNING:
  Den eneste LLM vi har adgang til er VS Code Copilot (built-in chat).
  Eksterne LLM API'er (api.githubcopilot.com, OpenAI, Azure OpenAI) er IKKE
  tilgængelige fra Python-kode — OAuth tokens (gh auth token) giver ikke
  API-adgang til disse endpoints og returnerer PermissionDeniedError.

HVORDAN MAN BRUGER LLM-ANALYSE:

  Automatisk (heuristik) — kør altid:
    python -m analysis_tool.integrity.run_rig --greenai <mappe> --legacy <mappe>
    Heuristics scaner alle filer uden LLM.

  Manuel LLM (Copilot) — for HIGH/MEDIUM-risk filer:
    1. Brug generate_copilot_prompt(greenai_path, greenai_src, legacy_path, legacy_src)
       til at generere en analyse-prompt.
    2. Indsæt prompten i VS Code Copilot Chat.
    3. Copilot returnerer JSON-scores som kan valideres manuelt.

  Batch Copilot — ved Wave-checkpoints:
    python -m analysis_tool.integrity.run_rig --greenai <mappe> --legacy <mappe>
           --copilot-batch <output.md>
    Genererer en .md-fil med alle fil-par og prompts klar til Copilot Chat.

DERAF FØLGER: --no-llm-flaget er fjernet. Heuristik er DEFAULT.
LLM-analyse sker KUN via VS Code Copilot (manuel eller batch-prompt).
"""
from __future__ import annotations

import json

_SYSTEM_PROMPT = """\
You are a code architecture integrity auditor.

Your task: compare two C# code files — one from a NEW system (GreenAI) and one from a LEGACY system.
Determine whether the GreenAI file is an independent implementation or a structural copy of the legacy file.

You evaluate three dimensions:

1. STRUCTURAL (0.0–1.0):
   How similar are the names? (classes, methods, properties, variables)
   1.0 = identical names throughout. 0.0 = completely different naming.

2. BEHAVIORAL (0.0–1.0):
   How similar is the control flow SHAPE?
   Not whether the code compiles the same — but whether the sequence of operations matches:
   (null-guard → existence-check → insert → return) in both = high behavioral similarity.
   1.0 = identical flow shape. 0.0 = completely different flow.

3. DOMAIN (0.0–1.0):
   How GreenAI-native is the new file?
   High score = uses GreenAI patterns (Result<T>, ICurrentUser, vertical-slice namespace, sealed record, IDbSession).
   Low score = uses legacy-style patterns (Manager/Helper suffix, static factory, ConnectionFactory, void handlers).
   1.0 = fully GreenAI-native. 0.0 = completely legacy-style.

GATE RULE:
   FAIL = behavioral > 0.75 AND domain < 0.50

Return ONLY a JSON object with this exact structure:
{
  "structural_similarity": <float>,
  "behavioral_similarity": <float>,
  "domain_similarity": <float>,
  "flags": [<string>, ...],
  "recommendations": [<string>, ...]
}

flags: List the specific risk observations (max 5). Be concrete — name the actual identifiers or patterns.
recommendations: List actionable fixes (max 5). Be specific about what to rename or restructure.

Do NOT include any explanation outside the JSON.
Do NOT copy source code in your response.
"""


def _truncate(text: str, max_lines: int = 150) -> str:
    lines = text.splitlines()
    if len(lines) > max_lines:
        return "\n".join(lines[:max_lines]) + f"\n... [{len(lines) - max_lines} lines truncated]"
    return text


def generate_copilot_prompt(greenai_path: str, greenai_source: str, legacy_path: str, legacy_source: str) -> str:
    """
    Generer en analyse-prompt klar til at indsætte i VS Code Copilot Chat.

    Workflow:
      1. Kald denne funktion for det fil-par du vil analysere.
      2. Indsæt outputtet i Copilot Chat.
      3. Copilot svarer med et JSON-objekt med scores.

    Returnerer den fulde prompt som string.
    """
    return (
        f"{_SYSTEM_PROMPT}\n\n"
        f"=== GreenAI file: {greenai_path} ===\n"
        f"{_truncate(greenai_source)}\n\n"
        f"=== Legacy file: {legacy_path} ===\n"
        f"{_truncate(legacy_source)}\n"
    )


def llm_analyze(
    greenai_path: str,
    greenai_source: str,
    legacy_path: str,
    legacy_source: str,
) -> dict | None:
    """
    LLM-analyse er KUN tilgængelig via VS Code Copilot (built-in chat).

    Denne funktion returnerer altid None — heuristik bruges som fallback.
    For manuel LLM-analyse: brug generate_copilot_prompt() og indsæt i Copilot Chat.
    For batch-analyse: brug run_rig.py --copilot-batch <output.md>.

    BAGGRUND: api.githubcopilot.com og andre eksterne LLM endpoints er ikke
    tilgængelige fra Python via OAuth tokens. VS Code Copilot (built-in) er
    den eneste LLM vi har adgang til i dette projekt.
    """
    # Ekstern LLM ikke tilgængelig — returner None → checker falder tilbage til heuristik.
    # Se generate_copilot_prompt() for manuel Copilot-analyse.
    return None
