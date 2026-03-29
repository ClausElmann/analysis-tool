"""SLICE_0.8 — Local git history intelligence extraction.

Reads ONLY the local .git directory via ``git log``.  No network access.
Never fetches, pulls, or touches any remote.

Public API
----------
analyze_git(repo_path: str) -> dict
    Returns ``{"insights": [...]}`` ready for JSON serialisation.
"""

from __future__ import annotations

import os
import re
import subprocess
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Classification keyword tables
# ---------------------------------------------------------------------------

_BUSINESS_ACTION_KW = frozenset(
    ["send", "create", "update", "delete", "schedule", "assign", "import", "export"]
)
_RULE_KW = frozenset(
    ["prevent", "only", "must", "cannot", "ensure", "validate"]
)
_FIX_KW = frozenset(
    ["fix", "bug", "error", "issue", "duplicate", "missing", "crash"]
)
_RISK_KW = frozenset(
    ["temporary", "workaround", "hack", "quick fix"]
)
_REFACTOR_KW = frozenset(
    ["refactor", "rename", "move", "reorganize", "restructure", "cleanup", "clean up"]
)

# Exact noise messages to ignore (lowercased, stripped)
_NOISE_MESSAGES = frozenset(["fix", "update", "test", "minor"])

# Minimum useful message length
_MIN_MSG_LEN = 5

# Confidence by type
_CONFIDENCE: Dict[str, float] = {
    "rule":     0.9,
    "feature":  0.8,
    "fix":      0.7,
    "risk":     0.6,
    "refactor": 0.5,
    "unknown":  0.4,
}

# Fields separator used in the custom git log format  (safe on Windows)
_SEP = "|||GITSEP|||"

# ---------------------------------------------------------------------------
# Git helpers  (local-only — no remote calls)
# ---------------------------------------------------------------------------

_SAFE_GIT_ENV: Dict[str, str] = {}  # populated lazily to avoid import-time side effects

def _run_git(args: List[str], cwd: str) -> Tuple[str, Optional[str]]:
    """Run a git command in *cwd*.  Returns ``(stdout, error_string)``."""
    cmd = ["git"] + args
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            # Never contact any remote — git itself enforces this for log/show
        )
        if result.returncode != 0:
            return "", result.stderr.strip() or f"git exited {result.returncode}"
        return result.stdout, None
    except FileNotFoundError:
        return "", "git executable not found"
    except subprocess.TimeoutExpired:
        return "", "git log timed out after 30 s"
    except OSError as exc:
        return "", str(exc)


def _fetch_commits(repo_path: str) -> Tuple[List[Dict], Optional[str]]:
    """Return list of ``{hash, message, files}`` dicts from local git log.

    Uses two git invocations (both read-only, local-only):
    1. ``git log --no-merges`` with custom format to get hash + message per commit.
    2. ``git log --no-merges --name-only`` to map hashes to touched file paths.
    """
    # Pass 1 — messages
    fmt = f"%H{_SEP}%s"  # hash GITSEP subject
    out1, err = _run_git(
        ["log", "--no-merges", f"--format={fmt}"],
        repo_path,
    )
    if err:
        return [], err

    commits: Dict[str, Dict] = {}
    for line in out1.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(_SEP, 1)
        if len(parts) != 2:
            continue
        sha, subject = parts
        sha = sha.strip()
        subject = subject.strip()
        if sha and subject:
            commits[sha] = {"hash": sha, "message": subject, "files": []}

    if not commits:
        return [], None

    # Pass 2 — file names
    out2, err2 = _run_git(
        ["log", "--no-merges", "--name-only", f"--format=%H"],
        repo_path,
    )
    if err2:
        # Non-fatal — we still have messages; just skip file association
        return list(commits.values()), None

    current_sha: str = ""
    for line in out2.splitlines():
        line_s = line.strip()
        if not line_s:
            continue
        # git prints sha on its own line, then file names
        if re.fullmatch(r"[0-9a-f]{40}", line_s):
            current_sha = line_s
        elif current_sha and current_sha in commits:
            commits[current_sha]["files"].append(line_s)

    return list(commits.values()), None


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def _classify(message_lower: str) -> str:
    """Return one of: rule | feature | fix | risk | refactor | unknown."""
    words = set(re.findall(r"[a-z]+", message_lower))
    # Check multi-word risk phrases first
    if "quick fix" in message_lower or any(kw in message_lower for kw in _RISK_KW):
        return "risk"
    if words & _RULE_KW:
        return "rule"
    if words & _FIX_KW:
        return "fix"
    if words & _BUSINESS_ACTION_KW:
        return "feature"
    if words & _REFACTOR_KW:
        return "refactor"
    return "unknown"


def _should_ignore(message_lower: str) -> bool:
    """Return True if commit should be filtered out."""
    stripped = message_lower.strip()
    if len(stripped) < _MIN_MSG_LEN:
        return True
    if stripped in _NOISE_MESSAGES:
        return True
    cls = _classify(stripped)
    return cls == "unknown"


def _normalise(text: str) -> str:
    """Lowercase, strip, collapse internal whitespace."""
    return re.sub(r"\s+", " ", text.lower().strip())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_git(repo_path: str) -> Dict:
    """Analyse the local git history at *repo_path* and return insight dict.

    Parameters
    ----------
    repo_path:
        Path to the working tree (i.e. the directory that contains ``.git/``).
        May also be the ``.git`` directory itself — the function normalises both.

    Returns
    -------
    dict
        ``{"insights": [...], "errors": [...]}``
    """
    errors: List[str] = []

    # Normalise: if caller passes .git itself, go up one level
    if repo_path.endswith(".git") and os.path.isdir(repo_path):
        repo_path = os.path.dirname(repo_path)

    if not os.path.isdir(os.path.join(repo_path, ".git")):
        errors.append(f"No .git directory found at '{repo_path}'")
        return {"insights": [], "errors": errors}

    commits, err = _fetch_commits(repo_path)
    if err:
        errors.append(err)
        return {"insights": [], "errors": errors}

    # Build raw insights, dedup by normalised text
    seen_texts: Dict[str, Dict] = {}  # normalised_text → insight dict

    for commit in commits:
        raw_msg = commit["message"]
        norm = _normalise(raw_msg)

        if _should_ignore(norm):
            continue

        cls = _classify(norm)

        files = sorted(set(commit["files"]))[:5]

        if norm in seen_texts:
            # Merge file lists (keep best 5)
            existing_files = seen_texts[norm]["files"]
            merged = sorted(set(existing_files + files))[:5]
            seen_texts[norm]["files"] = merged
        else:
            seen_texts[norm] = {
                "_text": norm,
                "type": cls,
                "confidence": _CONFIDENCE[cls],
                "files": files,
            }

    # Sort by text (deterministic), assign sequential IDs
    sorted_items = sorted(seen_texts.values(), key=lambda x: x["_text"])
    insights: List[Dict] = []
    for idx, item in enumerate(sorted_items, start=1):
        insights.append({
            "id": f"git_{idx:04d}",
            "type": item["type"],
            "text": item["_text"],
            "confidence": item["confidence"],
            "files": item["files"],
        })

    return {"insights": insights, "errors": errors}
