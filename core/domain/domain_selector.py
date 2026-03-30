"""Domain selector — picks the next domain to process.

Priority:
1. A domain already ``in_progress`` (resume crashed run).
2. First domain with status ``pending`` (set to ``in_progress``).
3. ``None`` when all domains are ``stable``.
"""

from __future__ import annotations

from typing import Optional

from core.domain.domain_state import DomainProgress, DomainState, STATUS_IN_PROGRESS, STATUS_PENDING


def pick_next(state: DomainState) -> Optional[DomainProgress]:
    """Return the next domain to process.

    Mutates the domain's ``status`` to ``in_progress`` when picking
    a pending domain.  The caller must call ``state.save()`` to persist
    the change.

    Returns ``None`` when all domains are stable (nothing left to do).
    """
    domains = state.all_domains()

    # 1. Resume any domain already in-progress (crash recovery)
    for domain in domains:
        if domain.status == STATUS_IN_PROGRESS:
            return domain

    # 2. Pick the first pending domain and mark it in-progress
    for domain in domains:
        if domain.status == STATUS_PENDING:
            domain.status = STATUS_IN_PROGRESS
            return domain

    # 3. All stable (or no domains)
    return None
