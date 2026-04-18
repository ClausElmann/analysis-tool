"""
Domain intent: measures how much the GreenAI code uses its own architecture
versus generic or legacy-style patterns.

A high domain score means the file is clearly "GreenAI-native".
A low domain score means the file borrows legacy structure/vocabulary.

Scoring:
  +1 for each GreenAI-marker found (vertical slice patterns, Result<T>, ICurrentUser, etc.)
  -1 for each legacy-risk marker (Manager/Service/Helper suffix, static factory, etc.)
  Normalised to 0.0–1.0 (clamped).
"""
import re

# Patterns that indicate GreenAI-native architecture
_GREENAI_MARKERS: list[tuple[str, str]] = [
    ("Result<",           r'\bResult<'),
    ("ICurrentUser",      r'\bICurrentUser\b'),
    ("ProfileId",         r'\bProfileId\b'),
    ("CustomerId",        r'\bCustomerId\b'),
    ("IDbSession",        r'\bIDbSession\b'),
    ("SqlLoader",         r'\bSqlLoader\b'),
    ("IRequest<Result",   r'\bIRequest<Result'),
    ("AbstractValidator", r'\bAbstractValidator<'),
    ("IEndpointRouteBuilder", r'\bIEndpointRouteBuilder\b'),
    ("MapPost|MapGet|MapPut|MapDelete", r'\b(?:MapPost|MapGet|MapPut|MapDelete)\b'),
    ("RequireAuthorization",r'\bRequireAuthorization\(\)'),
    ("VerticalSlice namespace", r'namespace GreenAi\.Api\.Features\.'),
    ("sealed record/class",r'\bsealed\s+(?:record|class)\b'),
]

# Patterns that indicate legacy-style / non-GreenAI design
_LEGACY_RISK_MARKERS: list[tuple[str, str]] = [
    ("static helper class",   r'\bpublic\s+static\s+class\b'),
    ("Manager suffix",        r'\b\w+Manager\b'),
    ("Helper suffix",         r'\b\w+Helper\b'),
    ("Util suffix",           r'\b\w+Util(?:s|ity)?\b'),
    ("ConnectionFactory",     r'\bConnectionFactory\b'),
    ("new SqlConnection",     r'\bnew\s+SqlConnection\b'),
    ("void return on handler",r'\bpublic\s+(?:void|async void)\s+\w+\s*\('),
    ("Direct exception throw without Result",
                              r'\bthrow\s+new\s+Exception\b'),
]


def domain_similarity(greenai_source: str) -> tuple[float, list[str]]:
    """
    Returns (score, flags).
    score: 0.0–1.0 — how GreenAI-native the file is (higher = safer).
    flags: legacy-risk markers found in the file.
    """
    greenai_hits = sum(
        1 for _, pattern in _GREENAI_MARKERS
        if re.search(pattern, greenai_source)
    )
    legacy_hits = 0
    flags: list[str] = []

    for label, pattern in _LEGACY_RISK_MARKERS:
        if re.search(pattern, greenai_source):
            legacy_hits += 1
            flags.append(f"Legacy-risk pattern detected: {label}")

    total = greenai_hits + legacy_hits
    if total == 0:
        # No markers either way — neutral
        return 0.5, []

    score = greenai_hits / total
    return round(score, 3), flags
