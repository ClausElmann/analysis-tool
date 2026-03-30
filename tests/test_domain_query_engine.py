"""Tests for core.domain.domain_query_engine.

Covers:
* _score_asset indirectly via ranking — unprocessed bonus, type priority,
  gap-term keyword hits, path/id overlap
* rank_assets_for_domain — ordering, determinism
* select_assets_for_iteration — unprocessed first, max_assets cap
* expand_search_terms — domain tokens + gap terms, sorted + deduped
"""

import pytest

from core.domain.domain_query_engine import DomainQueryEngine


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def _asset(asset_id: str, asset_type: str = "code_file", path: str = "", content: str = "") -> dict:
    return {
        "id": asset_id,
        "type": asset_type,
        "path": path or f"src/{asset_id}.cs",
        "content": content,
    }


def _gap(gap_id: str, terms: list) -> dict:
    return {
        "id": gap_id,
        "type": "missing_entity",
        "priority": 1.0,
        "suggested_terms": terms,
    }


class _FakeMemory:
    """Stub memory for rank_assets_for_domain tests."""

    def __init__(self, gaps=None):
        self._gaps = gaps or []

    def get_latest_gaps(self, domain):
        return self._gaps


# ---------------------------------------------------------------------------
# expand_search_terms
# ---------------------------------------------------------------------------


class TestExpandSearchTerms:
    def test_domain_tokens_always_included(self):
        qe = DomainQueryEngine()
        terms = qe.expand_search_terms("identity_access", [])
        assert "identity" in terms
        assert "access" in terms

    def test_gap_suggested_terms_included(self):
        qe = DomainQueryEngine()
        gaps = [_gap("gap:id:missing_entity:user", ["user", "account"])]
        terms = qe.expand_search_terms("identity_access", gaps)
        assert "user" in terms
        assert "account" in terms

    def test_output_is_sorted(self):
        qe = DomainQueryEngine()
        gaps = [_gap("gap:id:missing_flow:flow", ["zebra", "alpha"])]
        terms = qe.expand_search_terms("messaging", gaps)
        assert terms == sorted(terms)

    def test_no_duplicates(self):
        qe = DomainQueryEngine()
        gaps = [_gap("gap:id:missing_entity:msg", ["messaging", "messaging"])]
        terms = qe.expand_search_terms("messaging", gaps)
        assert len(terms) == len(set(terms))

    def test_empty_gaps_returns_domain_tokens(self):
        qe = DomainQueryEngine()
        terms = qe.expand_search_terms("customer_administration", [])
        assert "customer" in terms
        assert "administration" in terms

    def test_whitespace_terms_stripped(self):
        qe = DomainQueryEngine()
        gaps = [_gap("gap:id:x:y", ["  spaces  ", ""])]
        terms = qe.expand_search_terms("messaging", gaps)
        assert "" not in terms
        assert "spaces" in terms or "  spaces  " not in terms


# ---------------------------------------------------------------------------
# rank_assets_for_domain
# ---------------------------------------------------------------------------


class TestRankAssetsForDomain:
    def test_unprocessed_ranked_above_processed(self):
        qe = DomainQueryEngine()
        processed = _asset("code:msg:old", path="src/messaging/Old.cs")
        fresh = _asset("code:msg:new", path="src/messaging/New.cs")
        result = qe.rank_assets_for_domain(
            "messaging",
            [processed, fresh],
            _FakeMemory(),
            processed_ids={"code:msg:old"},
        )
        ids = [a["id"] for a in result]
        assert ids.index("code:msg:new") < ids.index("code:msg:old")

    def test_code_file_ranked_above_pdf(self):
        qe = DomainQueryEngine()
        pdf = _asset("pdf:doc:1", asset_type="pdf_section", path="docs/doc.pdf")
        code = _asset("code:msg:1", asset_type="code_file", path="src/Msg.cs")
        result = qe.rank_assets_for_domain(
            "messaging",
            [pdf, code],
            _FakeMemory(),
            processed_ids=set(),
        )
        ids = [a["id"] for a in result]
        assert ids.index("code:msg:1") < ids.index("pdf:doc:1")

    def test_gap_keyword_hit_boosts_rank(self):
        qe = DomainQueryEngine()
        hits_keyword = _asset(
            "code:msg:a",
            path="src/messaging/NotificationService.cs",
            content="notification send subscribe",
        )
        no_keyword = _asset("code:msg:b", path="src/other/File.cs", content="xyz abc")
        memory = _FakeMemory(
            gaps=[_gap("gap:msg:missing_entity:notif", ["notification", "subscribe"])]
        )
        result = qe.rank_assets_for_domain(
            "messaging",
            [no_keyword, hits_keyword],
            memory,
            processed_ids=set(),
        )
        ids = [a["id"] for a in result]
        assert ids.index("code:msg:a") < ids.index("code:msg:b")

    def test_deterministic_ordering(self):
        qe = DomainQueryEngine()
        assets = [
            _asset("code:msg:c"),
            _asset("code:msg:a"),
            _asset("code:msg:b"),
        ]
        r1 = [a["id"] for a in qe.rank_assets_for_domain("messaging", assets, _FakeMemory())]
        r2 = [a["id"] for a in qe.rank_assets_for_domain("messaging", assets, _FakeMemory())]
        assert r1 == r2

    def test_empty_assets_returns_empty(self):
        qe = DomainQueryEngine()
        result = qe.rank_assets_for_domain("messaging", [], _FakeMemory())
        assert result == []

    def test_none_processed_ids_treated_as_empty(self):
        qe = DomainQueryEngine()
        assets = [_asset("code:msg:1")]
        result = qe.rank_assets_for_domain("messaging", assets, _FakeMemory(), processed_ids=None)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# select_assets_for_iteration
# ---------------------------------------------------------------------------


class TestSelectAssetsForIteration:
    def test_max_assets_respected(self):
        qe = DomainQueryEngine()
        assets = [_asset(f"code:msg:{i}") for i in range(20)]
        result = qe.select_assets_for_iteration("messaging", assets, [], set(), max_assets=5)
        assert len(result) <= 5

    def test_max_assets_zero_returns_all(self):
        qe = DomainQueryEngine()
        assets = [_asset(f"code:msg:{i}") for i in range(20)]
        result = qe.select_assets_for_iteration("messaging", assets, [], set(), max_assets=0)
        assert len(result) == 20

    def test_unprocessed_before_processed(self):
        qe = DomainQueryEngine()
        processed_ids = {"code:msg:old1", "code:msg:old2"}
        assets = [
            _asset("code:msg:old1"),
            _asset("code:msg:old2"),
            _asset("code:msg:new1"),
        ]
        result = qe.select_assets_for_iteration(
            "messaging", assets, [], processed_ids, max_assets=10
        )
        ids = [a["id"] for a in result]
        assert ids.index("code:msg:new1") < ids.index("code:msg:old1")

    def test_gap_terms_influence_order(self):
        qe = DomainQueryEngine()
        gaps = [_gap("gap:msg:missing_entity:notif", ["notification"])]
        match_asset = _asset(
            "code:msg:notif", content="notification service handler"
        )
        no_match = _asset("code:msg:other", content="generic content here")
        result = qe.select_assets_for_iteration(
            "messaging",
            [no_match, match_asset],
            gaps,
            set(),
            max_assets=10,
        )
        ids = [a["id"] for a in result]
        assert ids.index("code:msg:notif") < ids.index("code:msg:other")

    def test_returns_list_of_dicts(self):
        qe = DomainQueryEngine()
        assets = [_asset("code:msg:1"), _asset("code:msg:2")]
        result = qe.select_assets_for_iteration("messaging", assets, [], set())
        assert isinstance(result, list)
        assert all(isinstance(a, dict) for a in result)

    def test_none_processed_ids_treated_as_empty(self):
        qe = DomainQueryEngine()
        assets = [_asset("code:msg:1")]
        result = qe.select_assets_for_iteration("messaging", assets, [], None, max_assets=5)
        assert len(result) == 1
