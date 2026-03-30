"""
ai_processor.py — Abstract AI processor interface, stub, and Copilot implementation.

All AI processors must:
  - Return strict JSON (dict)
  - NEVER copy source code — extract intent and responsibility only
  - Normalize naming to system-wide domain terms
  - Populate all DOMAIN_OUTPUT_KEYS in every response

CopilotAIProcessor uses GitHub Copilot via the OpenAI-compatible
GitHub Copilot API endpoint:  https://api.githubcopilot.com

Requires:
  pip install openai
  GITHUB_TOKEN env var  (a GitHub PAT or Copilot token)

Default model:
  gpt-4.1  — free with GitHub Copilot subscription
"""

import json
import os
import re
from abc import ABC, abstractmethod

# Canonical domain output keys — every AI response must include all of these.
DOMAIN_OUTPUT_KEYS = (
    "entities",
    "behaviors",
    "flows",
    "events",
    "batch_jobs",
    "integrations",
    "rules",
    "pseudocode",
    "rebuild_requirements",
)


class AIProcessor(ABC):
    """
    Abstract interface for AI-powered domain extraction.

    Implementations are responsible for calling an LLM and parsing its output
    into the canonical domain format.  The base class provides validate_output()
    to guarantee all required keys are present even if the model omits some.
    """

    @abstractmethod
    def process(self, asset: dict, stage: str, prompt: str) -> dict:
        """
        Process a single asset at the given stage.

        Args:
            asset:  Asset dict from AssetScanner (id, type, content_hash, …)
            stage:  One of STAGES from stage_state.py
            prompt: Pre-built prompt string from PromptBuilder

        Returns:
            Dict with all DOMAIN_OUTPUT_KEYS populated.
            Must NOT contain raw source code.
        """
        ...

    def validate_output(self, result: dict) -> dict:
        """Ensure all domain output keys are present, defaulting to empty list."""
        for key in DOMAIN_OUTPUT_KEYS:
            result.setdefault(key, [])
        return result


class StubAIProcessor(AIProcessor):
    """
    No-op processor for testing and dry runs.

    Returns the domain skeleton with empty lists and a _stub marker.
    Useful for verifying pipeline wiring without consuming AI tokens.
    """

    def process(self, asset: dict, stage: str, prompt: str) -> dict:
        return self.validate_output(
            {
                "_stub": True,
                "asset_id": asset["id"],
                "stage": stage,
            }
        )


class CopilotAIProcessor(AIProcessor):
    """
    Uses GitHub Copilot (gpt-4.1) via the OpenAI-compatible Copilot API.

    Args:
        model:        Copilot model name (default: "gpt-4.1")
        temperature:  Sampling temperature (default: 0.2 for deterministic extraction)
        max_retries:  Retry count on rate-limit or transient errors (default: 3)
        github_token: GitHub PAT/Copilot token — falls back to GITHUB_TOKEN env var

    Usage:
        processor = CopilotAIProcessor()          # uses gpt-4.1 by default
        pipeline = DomainPipeline(scanner, stage_state, processor, "data/domain_output")
        pipeline.run(max_assets=50)
    """

    ENDPOINT = "https://api.githubcopilot.com"

    def __init__(
        self,
        model: str = "gpt-4.1",
        temperature: float = 0.2,
        max_retries: int = 3,
        github_token: str | None = None,
    ):
        token = github_token or os.environ.get("GITHUB_TOKEN")
        if not token:
            raise ValueError(
                "GitHub token required. Set GITHUB_TOKEN env var or pass github_token=."
            )

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError("pip install openai") from exc

        self._client = OpenAI(base_url=self.ENDPOINT, api_key=token)
        self._model = model
        self._temperature = temperature
        self._max_retries = max_retries

    def process(self, asset: dict, stage: str, prompt: str) -> dict:
        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    temperature=self._temperature,
                    response_format={"type": "json_object"},
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a domain knowledge extraction engine. "
                                "You NEVER copy source code. "
                                "You ALWAYS extract intent and responsibility. "
                                "You ALWAYS use normalized domain naming. "
                                "You ALWAYS return strict JSON with the requested keys."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                )
                raw = response.choices[0].message.content or "{}"
                result = self._parse(raw)
                return self.validate_output(result)

            except Exception as exc:
                last_error = exc
                # Retry on rate-limit (429) or transient server errors (5xx)
                msg = str(exc).lower()
                if not any(x in msg for x in ("429", "rate", "500", "502", "503", "timeout")):
                    raise

        raise RuntimeError(
            f"Copilot call failed after {self._max_retries} attempts: {last_error}"
        )

    def _parse(self, raw: str) -> dict:
        raw = raw.strip()
        # Strip markdown code fences if model wraps output despite json_object mode
        match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL)
        if match:
            raw = match.group(1)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Best-effort: extract first {...} block
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                return json.loads(m.group())
            raise
