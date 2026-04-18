"""
LLM-based integrity analysis layer.

Sends GreenAI + legacy code to the LLM and asks for:
  - structural_similarity  (0.0–1.0)
  - behavioral_similarity  (0.0–1.0)
  - domain_similarity      (0.0–1.0, higher = more GreenAI-native)
  - flags                  (list of concrete risk observations)
  - recommendations        (list of actionable fix suggestions)

The LLM layer supersedes heuristic scores when available.
Falls back to heuristic-only if LLM is unavailable (no token, quota exceeded, etc.).
"""
from __future__ import annotations

import json
import os
import re
import subprocess

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


def _build_prompt(greenai_path: str, greenai_source: str, legacy_path: str, legacy_source: str) -> str:
    # Truncate to avoid context overflow — keep first 150 lines of each file
    def _truncate(text: str, max_lines: int = 150) -> str:
        lines = text.splitlines()
        if len(lines) > max_lines:
            return "\n".join(lines[:max_lines]) + f"\n... [{len(lines) - max_lines} lines truncated]"
        return text

    return (
        f"=== GreenAI file: {greenai_path} ===\n"
        f"{_truncate(greenai_source)}\n\n"
        f"=== Legacy file: {legacy_path} ===\n"
        f"{_truncate(legacy_source)}\n"
    )


def _get_token() -> str | None:
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    try:
        result = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, timeout=5
        )
        t = result.stdout.strip()
        if t and result.returncode == 0:
            return t
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _call_llm(prompt: str) -> dict:
    from openai import OpenAI

    token = _get_token()
    if not token:
        raise RuntimeError("No GitHub token available for LLM call.")

    client = OpenAI(base_url="https://api.githubcopilot.com", api_key=token)
    response = client.chat.completions.create(
        model="gpt-4.1",
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
    )
    raw = response.choices[0].message.content or "{}"
    raw = raw.strip()
    # Strip markdown fences if present
    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL)
    if match:
        raw = match.group(1)
    return json.loads(raw)


def llm_analyze(
    greenai_path: str,
    greenai_source: str,
    legacy_path: str,
    legacy_source: str,
) -> dict | None:
    """
    Call the LLM to assess architectural integrity.

    Returns a dict with keys:
      structural_similarity, behavioral_similarity, domain_similarity, flags, recommendations
    Or None if LLM is unavailable (caller falls back to heuristics).
    """
    try:
        prompt = _build_prompt(greenai_path, greenai_source, legacy_path, legacy_source)
        result = _call_llm(prompt)

        # Validate and sanitise response
        return {
            "structural_similarity": float(result.get("structural_similarity", 0.5)),
            "behavioral_similarity": float(result.get("behavioral_similarity", 0.5)),
            "domain_similarity":     float(result.get("domain_similarity", 0.5)),
            "flags":                 list(result.get("flags", [])),
            "recommendations":       list(result.get("recommendations", [])),
        }
    except Exception as exc:
        print(f"  [WARN] LLM analysis unavailable ({type(exc).__name__}: {exc}) — using heuristics only.")
        return None
