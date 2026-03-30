"""Tests for core.asset_scanner, core.asset_state, and core.asset_processor."""

import json
import os
import tempfile

import pytest

from core.asset_scanner import (
    AssetScanner,
    GIT_INSIGHTS_BATCH_SIZE,
    WORK_ITEMS_BATCH_SIZE,
    _sha256,
    _wiki_split_sections,
)
from core.asset_state import AssetState
from core.asset_processor import AssetProcessor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_data_dir(tmp_dir: str) -> str:
    data = os.path.join(tmp_dir, "data")
    os.makedirs(data, exist_ok=True)
    return data


def _make_wiki_dir(tmp_dir: str) -> str:
    wiki = os.path.join(tmp_dir, "wiki")
    os.makedirs(wiki, exist_ok=True)
    return wiki


def _write_json(directory: str, filename: str, content: dict) -> str:
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(content, fh, ensure_ascii=False)
    return path


def _write_text(directory: str, filename: str, content: str) -> str:
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


# ---------------------------------------------------------------------------
# _wiki_split_sections
# ---------------------------------------------------------------------------

class TestWikiSplitSections:
    def test_no_headings_returns_single_section(self):
        content = "Just some text\nwithout any headings."
        sections = _wiki_split_sections(content, "notes.md")
        assert len(sections) == 1
        assert sections[0]["heading"] == "notes"
        assert sections[0]["level"] == 1
        assert sections[0]["line_start"] == 0
        assert "Just some text" in sections[0]["content"]

    def test_single_heading_splits_into_preamble_and_section(self):
        content = "Preamble text\n\n## Section One\nContent here."
        sections = _wiki_split_sections(content, "doc.md")
        assert len(sections) == 2
        assert sections[0]["heading"] == "doc"
        assert sections[1]["heading"] == "Section One"
        assert sections[1]["level"] == 2

    def test_multiple_headings_no_overlap(self):
        content = (
            "## Alpha\nAlpha content\n"
            "## Beta\nBeta content\n"
            "## Gamma\nGamma content\n"
        )
        sections = _wiki_split_sections(content, "multi.md")
        headings = [s["heading"] for s in sections]
        assert headings == ["Alpha", "Beta", "Gamma"]
        # No overlap: each line appears in exactly one section
        all_lines = set()
        for s in sections:
            for line in s["content"].splitlines():
                assert line not in all_lines or not line.strip()
                if line.strip():
                    all_lines.add(line)

    def test_section_line_ranges_are_contiguous(self):
        content = "## A\nline1\n## B\nline2\n"
        sections = _wiki_split_sections(content, "f.md")
        assert len(sections) == 2
        # B starts where A ends + 1
        assert sections[1]["line_start"] == sections[0]["line_end"] + 1

    def test_level_preserved(self):
        content = "## Level 2\ntext\n### Level 3\nmore\n"
        sections = _wiki_split_sections(content, "f.md")
        levels = [s["level"] for s in sections]
        assert levels == [2, 3]

    def test_empty_content_returns_single_section(self):
        sections = _wiki_split_sections("", "empty.md")
        assert len(sections) == 1
        assert sections[0]["content"] == ""


# ---------------------------------------------------------------------------
# AssetScanner — work items
# ---------------------------------------------------------------------------

class TestScanWorkItemAssets:
    def test_batches_into_groups_of_100(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            features = [{"id": str(i), "title": f"Item {i}", "capability": "x", "keywords": []}
                        for i in range(250)]
            _write_json(data, "work_item_analysis.json", {"capabilities": [], "features": features})
            scanner = AssetScanner(data_root=data)
            assets = scanner._scan_work_item_assets()
            assert len(assets) == 3
            group_sizes = [a["group_size"] for a in assets]
            assert group_sizes == [100, 100, 50]

    def test_ids_are_stable_and_sequential(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            features = [{"id": str(i), "title": f"Item {i}", "capability": "x", "keywords": []}
                        for i in range(150)]
            _write_json(data, "work_item_analysis.json", {"capabilities": [], "features": features})
            scanner = AssetScanner(data_root=data)
            assets = scanner._scan_work_item_assets()
            ids = [a["id"] for a in assets]
            assert ids == ["work_items:batch:0", "work_items:batch:1"]

    def test_asset_type_is_correct(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            features = [{"id": "1", "title": "x", "capability": "c", "keywords": []}]
            _write_json(data, "work_item_analysis.json", {"capabilities": [], "features": features})
            scanner = AssetScanner(data_root=data)
            assets = scanner._scan_work_item_assets()
            assert assets[0]["type"] == "work_items_batch"

    def test_identical_batch_has_identical_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            features = [{"id": "1", "title": "x", "capability": "c", "keywords": []}]
            _write_json(data, "work_item_analysis.json", {"capabilities": [], "features": features})
            scanner = AssetScanner(data_root=data)
            assets1 = scanner._scan_work_item_assets()
            assets2 = scanner._scan_work_item_assets()
            assert assets1[0]["content_hash"] == assets2[0]["content_hash"]

    def test_changed_item_changes_batch_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            features = [{"id": "1", "title": "original", "capability": "c", "keywords": []}]
            _write_json(data, "work_item_analysis.json", {"capabilities": [], "features": features})
            scanner = AssetScanner(data_root=data)
            hash_before = scanner._scan_work_item_assets()[0]["content_hash"]

            features[0]["title"] = "changed"
            _write_json(data, "work_item_analysis.json", {"capabilities": [], "features": features})
            hash_after = scanner._scan_work_item_assets()[0]["content_hash"]
            assert hash_before != hash_after

    def test_missing_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            scanner = AssetScanner(data_root=data)
            assert scanner._scan_work_item_assets() == []

    def test_no_duplication_across_batches(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            features = [{"id": str(i), "title": f"Item {i}", "capability": "x", "keywords": []}
                        for i in range(250)]
            _write_json(data, "work_item_analysis.json", {"capabilities": [], "features": features})
            scanner = AssetScanner(data_root=data)
            assets = scanner._scan_work_item_assets()
            all_item_ids = [iid for a in assets for iid in a["item_ids"]]
            assert len(all_item_ids) == len(set(all_item_ids))


# ---------------------------------------------------------------------------
# AssetScanner — git insights
# ---------------------------------------------------------------------------

class TestScanGitInsightAssets:
    def test_batches_into_groups_of_100(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            insights = [{"id": f"git_{i:04d}", "type": "fix", "text": f"Fix {i}", "confidence": 0.8, "files": []}
                        for i in range(150)]
            _write_json(data, "git_insights.json", {"insights": insights})
            scanner = AssetScanner(data_root=data)
            assets = scanner._scan_git_insight_assets()
            assert len(assets) == 2
            assert assets[0]["group_size"] == 100
            assert assets[1]["group_size"] == 50

    def test_ids_are_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            insights = [{"id": f"git_{i:04d}", "type": "feature", "text": f"x", "confidence": 1.0, "files": []}
                        for i in range(100)]
            _write_json(data, "git_insights.json", {"insights": insights})
            scanner = AssetScanner(data_root=data)
            assets = scanner._scan_git_insight_assets()
            assert assets[0]["id"] == "git_insights:batch:0"

    def test_insight_types_aggregated(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            insights = [
                {"id": "g0", "type": "fix", "text": "a", "confidence": 1.0, "files": []},
                {"id": "g1", "type": "feature", "text": "b", "confidence": 1.0, "files": []},
                {"id": "g2", "type": "risk", "text": "c", "confidence": 1.0, "files": []},
            ]
            _write_json(data, "git_insights.json", {"insights": insights})
            scanner = AssetScanner(data_root=data)
            assets = scanner._scan_git_insight_assets()
            assert sorted(assets[0]["insight_types"]) == ["feature", "fix", "risk"]

    def test_no_duplication_across_batches(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            insights = [{"id": f"git_{i:04d}", "type": "fix", "text": f"x", "confidence": 0.8, "files": []}
                        for i in range(250)]
            _write_json(data, "git_insights.json", {"insights": insights})
            scanner = AssetScanner(data_root=data)
            assets = scanner._scan_git_insight_assets()
            all_ids = [iid for a in assets for iid in a["insight_ids"]]
            assert len(all_ids) == len(set(all_ids))


# ---------------------------------------------------------------------------
# AssetScanner — labels namespace
# ---------------------------------------------------------------------------

class TestScanLabelAssets:
    def _make_label_map(self, data_dir: str, namespaces: list) -> None:
        _write_json(data_dir, "label_map.json", {
            "namespaces": namespaces,
            "duplicate_namespaces": [],
            "total_labels": sum(n["key_count"] for n in namespaces),
            "total_namespaces": len(namespaces),
        })

    def test_one_asset_per_namespace(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            ns = [
                {"namespace": "alpha", "key_count": 5, "sample_keys": [], "matched_modules": [], "is_duplicate": False},
                {"namespace": "beta", "key_count": 10, "sample_keys": [], "matched_modules": [], "is_duplicate": False},
            ]
            self._make_label_map(data, ns)
            scanner = AssetScanner(data_root=data)
            assets = scanner._scan_label_assets()
            assert len(assets) == 2

    def test_ids_use_namespace_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            ns = [{"namespace": "myNS", "key_count": 3, "sample_keys": [], "matched_modules": [], "is_duplicate": False}]
            self._make_label_map(data, ns)
            scanner = AssetScanner(data_root=data)
            assets = scanner._scan_label_assets()
            assert assets[0]["id"] == "labels:ns:myns"

    def test_group_size_equals_key_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            ns = [{"namespace": "x", "key_count": 42, "sample_keys": [], "matched_modules": [], "is_duplicate": False}]
            self._make_label_map(data, ns)
            scanner = AssetScanner(data_root=data)
            assets = scanner._scan_label_assets()
            assert assets[0]["group_size"] == 42

    def test_sorted_by_namespace(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            ns = [
                {"namespace": "Zulu", "key_count": 1, "sample_keys": [], "matched_modules": [], "is_duplicate": False},
                {"namespace": "Alpha", "key_count": 1, "sample_keys": [], "matched_modules": [], "is_duplicate": False},
            ]
            self._make_label_map(data, ns)
            scanner = AssetScanner(data_root=data)
            assets = scanner._scan_label_assets()
            names = [a["namespace"] for a in assets]
            assert names == sorted(names, key=lambda n: n.lower())


# ---------------------------------------------------------------------------
# AssetScanner — wiki sections
# ---------------------------------------------------------------------------

class TestScanWikiAssets:
    def test_splits_on_level2_headings(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            wiki = _make_wiki_dir(tmp)
            _write_text(wiki, "Architecture.md",
                        "## Overview\nSome text.\n## Details\nMore text.\n")
            scanner = AssetScanner(data_root=data, wiki_root=wiki)
            assets = scanner._scan_wiki_assets()
            assert len(assets) == 2
            assert assets[0]["heading"] == "Overview"
            assert assets[1]["heading"] == "Details"

    def test_ids_include_section_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            wiki = _make_wiki_dir(tmp)
            _write_text(wiki, "doc.md", "## A\nx\n## B\ny\n")
            scanner = AssetScanner(data_root=data, wiki_root=wiki)
            assets = scanner._scan_wiki_assets()
            assert assets[0]["id"] == "wiki:doc.md:0"
            assert assets[1]["id"] == "wiki:doc.md:1"

    def test_group_size_is_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            wiki = _make_wiki_dir(tmp)
            _write_text(wiki, "f.md", "## Head\ncontent\n")
            scanner = AssetScanner(data_root=data, wiki_root=wiki)
            assets = scanner._scan_wiki_assets()
            assert all(a["group_size"] == 1 for a in assets)

    def test_no_overlap_between_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            wiki = _make_wiki_dir(tmp)
            _write_text(wiki, "f.md", "## Alpha\nlinea\n## Beta\nlineb\n## Gamma\nlinec\n")
            scanner = AssetScanner(data_root=data, wiki_root=wiki)
            assets = scanner._scan_wiki_assets()
            for i in range(len(assets) - 1):
                assert assets[i]["line_end"] < assets[i + 1]["line_start"]

    def test_skips_empty_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            wiki = _make_wiki_dir(tmp)
            _write_text(wiki, "empty.md", "   \n")
            _write_text(wiki, "real.md", "## Section\nText.")
            scanner = AssetScanner(data_root=data, wiki_root=wiki)
            assets = scanner._scan_wiki_assets()
            assert all(a["file"] == "real.md" for a in assets)

    def test_missing_wiki_root_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            scanner = AssetScanner(data_root=data, wiki_root="/nonexistent/path")
            assert scanner._scan_wiki_assets() == []


# ---------------------------------------------------------------------------
# AssetScanner — code files
# ---------------------------------------------------------------------------

class TestScanCodeAssets:
    def test_one_asset_per_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            src = os.path.join(tmp, "src")
            os.makedirs(src)
            _write_text(src, "MyClass.cs", "public class MyClass {}")
            _write_text(src, "app.component.ts", "export class AppComponent {}")
            scanner = AssetScanner(data_root=data, solution_root=src)
            assets = scanner._scan_code_assets()
            assert len(assets) == 2

    def test_asset_type_is_code_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            src = os.path.join(tmp, "src")
            os.makedirs(src)
            _write_text(src, "Foo.cs", "class Foo {}")
            scanner = AssetScanner(data_root=data, solution_root=src)
            assets = scanner._scan_code_assets()
            assert assets[0]["type"] == "code_file"

    def test_group_size_is_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            src = os.path.join(tmp, "src")
            os.makedirs(src)
            _write_text(src, "A.cs", "class A {}")
            scanner = AssetScanner(data_root=data, solution_root=src)
            assets = scanner._scan_code_assets()
            assert assets[0]["group_size"] == 1

    def test_node_modules_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            src = os.path.join(tmp, "src")
            nm = os.path.join(src, "node_modules", "lib")
            os.makedirs(nm)
            _write_text(nm, "index.ts", "export {};")
            _write_text(src, "app.ts", "const x = 1;")
            scanner = AssetScanner(data_root=data, solution_root=src)
            assets = scanner._scan_code_assets()
            paths = [a["path"] for a in assets]
            assert not any("node_modules" in p for p in paths)

    def test_id_uses_relative_path_with_forward_slashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            src = os.path.join(tmp, "src")
            sub = os.path.join(src, "features")
            os.makedirs(sub)
            _write_text(sub, "MyService.cs", "class MyService {}")
            scanner = AssetScanner(data_root=data, solution_root=src)
            assets = scanner._scan_code_assets()
            assert assets[0]["id"] == "code:features/MyService.cs"
            assert "\\" not in assets[0]["id"]

    def test_non_code_extensions_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            src = os.path.join(tmp, "src")
            os.makedirs(src)
            _write_text(src, "README.md", "# Readme")
            _write_text(src, "App.cs", "class App {}")
            scanner = AssetScanner(data_root=data, solution_root=src)
            assets = scanner._scan_code_assets()
            assert len(assets) == 1
            assert assets[0]["path"] == "App.cs"


# ---------------------------------------------------------------------------
# AssetState
# ---------------------------------------------------------------------------

class TestAssetState:
    def _make_asset(self, asset_id: str, content_hash: str) -> dict:
        return {"id": asset_id, "type": "wiki_section", "group_size": 1,
                "content_hash": content_hash}

    def test_new_asset_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = AssetState(tmp)
            asset = self._make_asset("wiki:doc.md:0", "abc123")
            assert state.is_stale(asset)

    def test_processed_asset_is_not_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = AssetState(tmp)
            asset = self._make_asset("wiki:doc.md:0", "abc123")
            state.mark_processed(asset)
            assert not state.is_stale(asset)

    def test_changed_hash_makes_asset_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = AssetState(tmp)
            asset = self._make_asset("wiki:doc.md:0", "abc123")
            state.mark_processed(asset)
            asset["content_hash"] = "xyz999"
            assert state.is_stale(asset)

    def test_save_and_reload_preserves_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = AssetState(tmp)
            asset = self._make_asset("wiki:doc.md:0", "abc123")
            state.mark_processed(asset)
            state.save()
            # Reload from disk
            state2 = AssetState(tmp)
            assert not state2.is_stale(asset)

    def test_reset_asset_makes_it_stale_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = AssetState(tmp)
            asset = self._make_asset("wiki:doc.md:0", "abc123")
            state.mark_processed(asset)
            state.reset_asset("wiki:doc.md:0")
            assert state.is_stale(asset)

    def test_reset_all_clears_all_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = AssetState(tmp)
            for i in range(5):
                state.mark_processed(self._make_asset(f"wiki:doc.md:{i}", f"hash_{i}"))
            state.reset_all()
            assert state.summary()["total_processed"] == 0

    def test_stale_assets_filters_correctly(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = AssetState(tmp)
            a0 = self._make_asset("wiki:doc.md:0", "h0")
            a1 = self._make_asset("wiki:doc.md:1", "h1")
            state.mark_processed(a0)
            stale = state.stale_assets([a0, a1])
            assert stale == [a1]

    def test_state_file_written_atomically(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = AssetState(tmp)
            state.mark_processed(self._make_asset("x", "h"))
            state.save()
            state_path = os.path.join(tmp, "asset_state.json")
            tmp_path = state_path + ".tmp"
            assert os.path.isfile(state_path)
            assert not os.path.isfile(tmp_path)


# ---------------------------------------------------------------------------
# AssetProcessor
# ---------------------------------------------------------------------------

class TestAssetProcessor:
    def _make_scanner_with_work_items(self, data_dir: str, count: int) -> AssetScanner:
        features = [{"id": str(i), "title": f"Item {i}", "capability": "x", "keywords": []}
                    for i in range(count)]
        _write_json(data_dir, "work_item_analysis.json", {"capabilities": [], "features": features})
        return AssetScanner(data_root=data_dir)

    def test_processes_stale_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            scanner = self._make_scanner_with_work_items(data, 50)
            state = AssetState(data)
            processor = AssetProcessor(scanner, state)
            processed = []
            processor.register_handler("work_items_batch",
                                       lambda a: processed.append(a["id"]) or {})
            processor.run()
            assert processed == ["work_items:batch:0"]

    def test_skips_unchanged_assets_on_second_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            scanner = self._make_scanner_with_work_items(data, 50)
            state = AssetState(data)
            processor = AssetProcessor(scanner, state)
            processor.register_handler("work_items_batch", lambda a: {})
            processor.run()
            # Second run — same data
            second_processed = []
            processor.register_handler("work_items_batch",
                                       lambda a: second_processed.append(a["id"]) or {})
            processor.run()
            assert second_processed == []

    def test_reprocesses_when_content_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            scanner = self._make_scanner_with_work_items(data, 10)
            state = AssetState(data)
            processor = AssetProcessor(scanner, state)
            processor.register_handler("work_items_batch", lambda a: {})
            processor.run()
            # Mutate source data
            features = [{"id": str(i), "title": f"Updated {i}", "capability": "y", "keywords": []}
                        for i in range(10)]
            _write_json(data, "work_item_analysis.json", {"capabilities": [], "features": features})
            second = []
            processor.register_handler("work_items_batch",
                                       lambda a: second.append(a["id"]) or {})
            processor.run()
            assert second == ["work_items:batch:0"]

    def test_run_report_contains_expected_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            scanner = AssetScanner(data_root=data)
            state = AssetState(data)
            processor = AssetProcessor(scanner, state)
            report = processor.run()
            for key in ("scanned", "stale", "processed", "skipped", "errors",
                        "started_at", "finished_at"):
                assert key in report

    def test_handler_exception_recorded_as_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            scanner = self._make_scanner_with_work_items(data, 10)
            state = AssetState(data)
            processor = AssetProcessor(scanner, state)

            def bad_handler(a):
                raise RuntimeError("deliberate error")

            processor.register_handler("work_items_batch", bad_handler)
            report = processor.run()
            assert len(report["errors"]) == 1
            assert "deliberate error" in report["errors"][0]["error"]

    def test_assets_without_handler_counted_as_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            scanner = self._make_scanner_with_work_items(data, 10)
            state = AssetState(data)
            processor = AssetProcessor(scanner, state)
            # No handler registered
            report = processor.run()
            assert report["processed"] == 0
            assert report["skipped"] == 1

    def test_register_handler_rejects_unknown_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            state = AssetState(data)
            processor = AssetProcessor(AssetScanner(data_root=data), state)
            with pytest.raises(ValueError, match="Unknown asset type"):
                processor.register_handler("invalid_type", lambda a: {})

    def test_dry_run_does_not_modify_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            scanner = self._make_scanner_with_work_items(data, 10)
            state = AssetState(data)
            processor = AssetProcessor(scanner, state)
            processor.dry_run()
            # State should still show 0 processed
            assert state.summary()["total_processed"] == 0

    def test_scan_all_assets_deduplicates_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            features = [{"id": str(i), "title": f"Item {i}", "capability": "x", "keywords": []}
                        for i in range(50)]
            _write_json(data, "work_item_analysis.json", {"capabilities": [], "features": features})
            scanner = AssetScanner(data_root=data)
            assets = scanner.scan_all_assets()
            ids = [a["id"] for a in assets]
            assert len(ids) == len(set(ids)), "Duplicate asset IDs found"

    def test_all_assets_have_required_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _make_data_dir(tmp)
            features = [{"id": str(i), "title": f"x", "capability": "c", "keywords": []}
                        for i in range(10)]
            _write_json(data, "work_item_analysis.json", {"capabilities": [], "features": features})
            scanner = AssetScanner(data_root=data)
            assets = scanner.scan_all_assets()
            for asset in assets:
                assert "type" in asset
                assert "id" in asset
                assert "group_size" in asset
                assert "content_hash" in asset


# ---------------------------------------------------------------------------
# _sha256 determinism
# ---------------------------------------------------------------------------

class TestSha256:
    def test_same_input_same_hash(self):
        assert _sha256("hello world") == _sha256("hello world")

    def test_different_input_different_hash(self):
        assert _sha256("foo") != _sha256("bar")

    def test_returns_hex_string(self):
        result = _sha256("test")
        assert isinstance(result, str)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)
