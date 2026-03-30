"""
refiner.py — Stage: refinement

Takes accumulated domain knowledge for a domain cluster and refines it:
  - Merge duplicates
  - Normalize naming
  - Add pseudocode for complex behaviors
  - Produce ordered rebuild requirements
  - Add confidence scores

Uses prompts/refinement.txt.
"""

import json
from pathlib import Path

from core.ai_processor import AIProcessor

STAGE = "refinement"

_PROMPT_FILE = "refinement.txt"


def _load_prompt(prompts_root: Path) -> str:
    path = prompts_root / _PROMPT_FILE
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


class Refiner:
    """
    Runs refinement for a single asset.

    The refinement stage receives the domain_mapping result and improves it.
    It is also used by the DomainBuilder to refine aggregated domain clusters.

    Args:
        ai_processor: Any AIProcessor implementation
        prompts_root: Path to the /prompts/ directory
    """

    def __init__(self, ai_processor: AIProcessor, prompts_root: str):
        self._ai = ai_processor
        self._prompts_root = Path(prompts_root)

    def refine(self, asset: dict, domain_result: dict) -> dict:
        """
        Run refinement on the domain mapping result.

        Args:
            asset:         Asset dict
            domain_result: Output from DomainMapper.map()

        Returns:
            Refined output dict with confidence scores added.
        """
        system_prompt = _load_prompt(self._prompts_root)
        previous_json = json.dumps(domain_result, ensure_ascii=False, indent=2)
        user_prompt = (
            f"Asset: {asset['id']}\n"
            f"Type: {asset['type']}\n\n"
            f"[DOMAIN MAPPING RESULT TO REFINE]\n{previous_json[:6_000]}"
        )
        full_prompt = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt
        return self._ai.process(asset, STAGE, full_prompt)

    def refine_cluster(self, domain_name: str, accumulated: dict) -> dict:
        """
        Refine an entire aggregated domain cluster (used by DomainBuilder).

        Args:
            domain_name:  The domain label (e.g. "Messaging")
            accumulated:  Merged dict with all DOMAIN_OUTPUT_KEYS

        Returns:
            Refined and deduplicated domain dict with confidence scores.
        """
        # Use a synthetic asset dict to reuse the same AI interface
        synthetic_asset = {
            "id": f"domain:{domain_name}",
            "type": "domain_cluster",
            "content_hash": "",
            "group_size": 0,
        }
        system_prompt = _load_prompt(self._prompts_root)
        previous_json = json.dumps(accumulated, ensure_ascii=False, indent=2)
        user_prompt = (
            f"Domain: {domain_name}\n\n"
            f"[ACCUMULATED DOMAIN KNOWLEDGE TO REFINE]\n{previous_json[:8_000]}"
        )
        full_prompt = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt
        return self._ai.process(synthetic_asset, STAGE, full_prompt)
