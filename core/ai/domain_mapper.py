"""
domain_mapper.py — Stage: domain_mapping

Takes the semantic_analysis result for an asset and maps it to system-wide
domain concepts: bounded contexts, aggregate roots, domain roles.

Uses code_domain.txt prompt which instructs the AI to classify by domain,
not just describe responsibility.
"""

from pathlib import Path



STAGE = "domain_mapping"

_PROMPT_FILE = "code_domain.txt"


def _load_prompt(prompts_root: Path) -> str:
    path = prompts_root / _PROMPT_FILE
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


class DomainMapper:
    """
    Runs domain_mapping for a single asset.

    The domain mapping stage receives:
    - The original asset (id, type, content_hash)
    - The semantic_analysis result from the previous stage

    It returns a domain-classified version of the knowledge.


    # Lokal LLM (Copilot chat) bruges altid — ekstern LLM ikke understøttet
    def __init__(self, ai_processor, prompts_root: str):
        self._ai = ai_processor  # Skal være lokal LLM (Copilot chat)
        self._prompts_root = Path(prompts_root)

    def map(self, asset: dict, semantic_result: dict) -> dict:
        """
        Run domain mapping on the semantic analysis result.

        Args:
            asset:           Asset dict
            semantic_result: Output from SemanticAnalyzer.analyze()

        Returns:
            Domain-mapped output dict with all DOMAIN_OUTPUT_KEYS.
        """
        import json

        system_prompt = _load_prompt(self._prompts_root)
        previous_json = json.dumps(semantic_result, ensure_ascii=False, indent=2)
        user_prompt = (
            f"Asset: {asset['id']}\n"
            f"Type: {asset['type']}\n\n"
            f"[SEMANTIC ANALYSIS RESULT]\n{previous_json[:6_000]}"
        )
        full_prompt = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt
        return self._ai.process(asset, STAGE, full_prompt)
