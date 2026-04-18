"""
Structural similarity: class names, method names, file names.
Compares extracted identifiers between two C# files using sequence matching.
"""
import re
from difflib import SequenceMatcher


def _extract_identifiers(source: str) -> list[str]:
    """
    Extract class names, method names and property names from C# source.
    Returns a normalised (lowercase) list for comparison.
    """
    patterns = [
        r'\bclass\s+(\w+)',
        r'\binterface\s+(\w+)',
        r'\b(?:public|private|protected|internal|static)\s+(?:\w[\w<>, \[\]?*]*\s+)+(\w+)\s*\(',
        r'\b(?:public|private|protected|internal)\s+(?:readonly\s+)?(?:\w[\w<>?, \[\]]*\s+)(\w+)\s*[{;=]',
    ]
    names: list[str] = []
    for pattern in patterns:
        names.extend(re.findall(pattern, source))
    return [n.lower() for n in names if len(n) > 2]


def _extract_parameter_names(source: str) -> list[str]:
    """
    Extract parameter names from method signatures in C# source.
    E.g. 'void Handle(CreateWarningCommand command, ...)' → ['command', ...]
    Returns normalised (lowercase) list.
    """
    # Match method parameter lists: type paramName (with optional default)
    param_pattern = re.compile(
        r'\b(?:[\w<>\[\]?,\s]+)\s+(\w+)\s*(?:[,)])' ,
        re.MULTILINE,
    )
    # Extract from inside method signatures only (rough: lines with '(')
    names: list[str] = []
    for line in source.splitlines():
        if '(' in line and ('public' in line or 'private' in line or 'protected' in line):
            names.extend(param_pattern.findall(line))
    # Filter out C# keywords and type-like names (start with upper)
    keywords = {'string', 'int', 'bool', 'void', 'task', 'list', 'result', 'cancellationtoken',
                'cancellation', 'token', 'async', 'override', 'sealed', 'readonly'}
    return [n.lower() for n in names if len(n) > 2 and n.lower() not in keywords and n[0].islower()]


def structural_similarity(greenai_source: str, legacy_source: str) -> tuple[float, list[str]]:
    """
    Returns (score, flags).
    score: 0.0–1.0 — fraction of GreenAI identifiers that closely match a legacy identifier.
    flags: list of matched name pairs that are identical or near-identical.
    """
    greenai_ids = _extract_identifiers(greenai_source)
    legacy_ids  = _extract_identifiers(legacy_source)

    if not greenai_ids:
        return 0.0, []

    legacy_set = set(legacy_ids)
    exact_matches: list[str] = []
    fuzzy_matches: int = 0

    for name in greenai_ids:
        if name in legacy_set:
            exact_matches.append(name)
        else:
            # fuzzy: check if any legacy name is >0.85 similar
            for leg in legacy_ids:
                ratio = SequenceMatcher(None, name, leg).ratio()
                if ratio > 0.85:
                    fuzzy_matches += 1
                    break

    matched = len(exact_matches) + fuzzy_matches
    score   = min(matched / len(greenai_ids), 1.0)

    flags: list[str] = []
    for name in sorted(set(exact_matches))[:5]:
        flags.append(f"Identifier '{name}' is identical in both codebases")

    return round(score, 3), flags


def naming_guard(greenai_source: str, legacy_source: str) -> list[str]:
    """
    Naming guard: flag identical method names AND parameter names between GreenAI and legacy.
    This catches 'Copilot sneaking legacy in via naming' — same method + same params = risk signal.
    Returns list of flag strings.
    """
    flags: list[str] = []

    ga_ids  = set(_extract_identifiers(greenai_source))
    leg_ids = set(_extract_identifiers(legacy_source))
    shared_ids = ga_ids & leg_ids

    ga_params  = set(_extract_parameter_names(greenai_source))
    leg_params = set(_extract_parameter_names(legacy_source))
    shared_params = ga_params & leg_params

    # Only flag parameter overlap when there is also method-name overlap (combined signal)
    if shared_ids and shared_params:
        flags.append(
            f"Naming risk: method identifiers {sorted(shared_ids)[:3]} AND "
            f"parameter names {sorted(shared_params)[:3]} both overlap with legacy — "
            "verify these reflect GreenAI domain intent, not copy."
        )
    elif len(shared_params) > 3:
        # Many parameter names shared even without method overlap
        flags.append(
            f"Parameter names overlap with legacy: {sorted(shared_params)[:5]} — "
            "low risk alone, but monitor."
        )

    return flags
