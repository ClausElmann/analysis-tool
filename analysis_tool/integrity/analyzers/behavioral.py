"""
Behavioral similarity: control-flow shape of methods.

Each method is fingerprinted as a sequence of statement-type tokens:
  NULL  = null guard / null check
  EARLY = early return / throw
  LOOP  = for / foreach / while
  TRY   = try/catch block
  IF    = conditional branch
  DB    = database call (Execute, Query, Insert, BulkInsert, etc.)
  CALL  = generic method call
  RET   = return statement

The shape of a method is the ordered list of these tokens.
Two methods with the same token sequence are considered behaviorally similar.
"""
import re
from difflib import SequenceMatcher


# Token patterns — order matters (more specific first)
_PATTERNS: list[tuple[str, str]] = [
    ("NULL",  r'\b(?:if\s*\(.*==\s*null|if\s*\(.*is\s+null|ArgumentNullException|NullOrWhiteSpace|NullOrEmpty)\b'),
    ("EARLY", r'\b(?:throw\s+new|return\s+Result|return\s+false|return\s+null)\b'),
    ("DB",    r'\b(?:BulkInsert|BulkUpdate|ExecuteAsync|QueryAsync|QuerySingleOrDefault|ExecuteInTransaction|Execute|Query)\b'),
    ("LOOP",  r'\b(?:foreach|for\s*\(|while\s*\()\b'),
    ("TRY",   r'\btry\s*\{'),
    ("IF",    r'\bif\s*\('),
    ("CALL",  r'\bawait\s+\w+'),
    ("RET",   r'\breturn\b'),
]


def _extract_methods(source: str) -> dict[str, list[str]]:
    """
    Extract method bodies from C# source.
    Returns {method_name: [token, token, ...]} for each method found.
    """
    # Find method signatures and their bodies (heuristic brace-counting)
    method_pattern = re.compile(
        r'(?:public|private|protected|internal|static|async|override|virtual)\s+'
        r'(?:[\w<>\[\]?,\s]+)\s+(\w+)\s*\([^)]*\)\s*\{',
        re.MULTILINE
    )
    methods: dict[str, list[str]] = {}

    for m in method_pattern.finditer(source):
        name      = m.group(1).lower()
        start     = m.end() - 1   # position of opening brace
        depth     = 0
        body_end  = start
        for i, ch in enumerate(source[start:], start):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    body_end = i
                    break
        body = source[start:body_end]
        tokens = _tokenise_body(body)
        if tokens:
            methods[name] = tokens

    return methods


def _tokenise_body(body: str) -> list[str]:
    tokens: list[str] = []
    for line in body.splitlines():
        for token, pattern in _PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                tokens.append(token)
                break
    return tokens


def _method_similarity(tokens_a: list[str], tokens_b: list[str]) -> float:
    if not tokens_a or not tokens_b:
        return 0.0
    return SequenceMatcher(None, tokens_a, tokens_b).ratio()


def _get_main_signature(methods: dict[str, list[str]]) -> list[str]:
    """
    Return the token sequence of the most significant method (longest token list).
    Prefers 'handle' if present (MediatR handler pattern).
    """
    if not methods:
        return []
    if "handle" in methods:
        return methods["handle"]
    # Fall back to the method with the most tokens
    return max(methods.values(), key=len)


def behavioral_similarity(greenai_source: str, legacy_source: str) -> tuple[float, list[str], list[str]]:
    """
    Returns (score, flags, behavior_signature).
    score: 0.0–1.0 — average similarity of matched method pairs.
    flags: method pairs whose behavioral shape exceeds 0.75.
    behavior_signature: token sequence of the main GreenAI method (flow fingerprint).
    """
    greenai_methods = _extract_methods(greenai_source)
    legacy_methods  = _extract_methods(legacy_source)

    behavior_signature = _get_main_signature(greenai_methods)

    if not greenai_methods or not legacy_methods:
        return 0.0, [], behavior_signature

    scores: list[float] = []
    flags:  list[str]   = []

    for ga_name, ga_tokens in greenai_methods.items():
        best_score  = 0.0
        best_legacy = ""
        for leg_name, leg_tokens in legacy_methods.items():
            s = _method_similarity(ga_tokens, leg_tokens)
            if s > best_score:
                best_score  = s
                best_legacy = leg_name
        scores.append(best_score)
        if best_score > 0.75:
            flags.append(
                f"Method '{ga_name}' has behavioral shape similarity {best_score:.2f} "
                f"with legacy '{best_legacy}'"
            )

    avg = sum(scores) / len(scores) if scores else 0.0
    return round(avg, 3), flags, behavior_signature
