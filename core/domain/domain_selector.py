"""Domain selector — picks the next domain to process.

Priority:
1. A domain already ``in_progress`` (resume crashed run).
2. First domain with status ``pending`` (set to ``in_progress``).
3. Highest-completeness ``blocked`` domain eligible for retry (SLICE-03).
4. ``None`` when all domains are exhausted or at retry cap.
"""

from __future__ import annotations

from typing import List, Optional

from core.domain.domain_state import (
    DomainProgress,
    DomainState,
    STATUS_BLOCKED,
    STATUS_IN_PROGRESS,
    STATUS_PENDING,
)

# SLICE-03: maximum number of times a blocked domain may be re-queued.
# A domain with retry_count >= MAX_RETRY_COUNT is permanently skipped.
MAX_RETRY_COUNT: int = 3


def pick_next(state: DomainState) -> Optional[DomainProgress]:
    """Return the next domain to process.

    Mutates the domain's ``status`` to ``in_progress`` when picking
    a pending domain.  Mutates ``status`` and ``retry_count`` when
    re-queuing a blocked domain.  The caller must call ``state.save()``
    to persist the change.

    Returns ``None`` when all domains are exhausted (nothing left to do).
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

    # 3. SLICE-03: re-queue the highest-completeness blocked domain that
    #    has not yet exhausted its retry budget.
    eligible: List[DomainProgress] = [
        d for d in domains
        if d.status == STATUS_BLOCKED and d.retry_count < MAX_RETRY_COUNT
    ]
    if eligible:
        # Prefer the domain closest to the completion threshold.
        # Use a stable secondary sort (name) for determinism.
        candidate = max(
            eligible,
            key=lambda d: (d.completeness_score, d.name),
        )
        candidate.retry_count += 1
        candidate.status = STATUS_PENDING
        return candidate

    # 4. Nothing left to do
    return None
