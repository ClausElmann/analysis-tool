"""
semantic_analyzer.py — Stage: semantic_analysis

Wraps the AI processor with semantic-analysis-specific prompt loading.
Selects the correct prompt file based on asset type.

Prompt files:
  prompts/code_semantic.txt       → code_file
  prompts/sql_semantic.txt        → (future: sql_file)
  prompts/wiki_semantic.txt       → wiki_section, pdf_section
  prompts/workitem_semantic.txt   → work_items_batch, git_insights_batch
"""

from pathlib import Path



STAGE = "semantic_analysis"

_PROMPT_MAP = {
    "code_file":          "code_semantic.txt",
    "wiki_section":       "wiki_semantic.txt",
    "pdf_section":        "wiki_semantic.txt",
    "work_items_batch":   "workitem_semantic.txt",
    "git_insights_batch": "workitem_semantic.txt",
    "labels_namespace":   "workitem_semantic.txt",
}

_DEFAULT_PROMPT = "code_semantic.txt"


def _load_prompt(prompts_root: Path, asset_type: str) -> str:
    filename = _PROMPT_MAP.get(asset_type, _DEFAULT_PROMPT)
    path = prompts_root / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


class SemanticAnalyzer:
    """

    # Lokal LLM (Copilot chat) bruges altid — ekstern LLM ikke understøttet
    def __init__(self, ai_processor, prompts_root: str):
        self._ai = ai_processor  # Skal være lokal LLM (Copilot chat)
        self._prompts_root = Path(prompts_root)

    def analyze(self, asset: dict, content: str) -> dict:
        """
        Run semantic analysis on an asset.

        Args:
            asset:   Asset dict (id, type, content_hash, …)
            content: Pre-loaded text content for this asset

        Returns:
            Domain output dict with all DOMAIN_OUTPUT_KEYS.
        """
        system_prompt = _load_prompt(self._prompts_root, asset["type"])
        user_prompt = self._build_user_prompt(asset, content)
        full_prompt = f"{system_prompt}\n\n[CONTENT]\n{user_prompt}" if system_prompt else user_prompt
        return self._ai.process(asset, STAGE, full_prompt)

    def _build_user_prompt(self, asset: dict, content: str) -> str:
        cap = 8_000
        return (
            f"Asset: {asset['id']}\n"
            f"Type: {asset['type']}\n"
            f"Group size: {asset.get('group_size', '?')}\n\n"
            f"{content[:cap]}"
        )
