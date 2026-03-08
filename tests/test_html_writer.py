"""Tests for wisewiki.html_writer."""

import json

from wisewiki.html_writer import HtmlWriter


def test_generate_index_builds_session_centric_home(tmp_path):
    wiki_dir = tmp_path
    repo = "demo-repo"
    repo_dir = wiki_dir / "repos" / repo
    module_dir = repo_dir / "modules"
    module_dir.mkdir(parents=True)
    (wiki_dir / ".index").mkdir(parents=True)

    (module_dir / "executor.md").write_text("## Purpose\nRuns tasks.\n")
    (module_dir / "cache.md").write_text("## Purpose\nStores entries.\n")

    cache_path = wiki_dir / ".index" / "cache.json"
    cache_path.write_text(
        json.dumps(
            {
                f"{repo}/executor": {
                    "title": "Executor",
                    "summary": "Runs task execution.",
                    "sections": ["Purpose", "Key Functions"],
                    "key_facts": [],
                    "tables": [],
                    "decisions": [],
                    "code_sigs": ["run()"],
                    "metrics": [],
                    "abs_path": str((module_dir / "executor.md").resolve()),
                    "generator": "wiki_capture",
                    "wiki_generated": 200.0,
                    "captured_at": 200.0,
                    "capture_kind": "session",
                    "session_id": "session-abc",
                    "source_files": ["src/wisewiki/mcp_server.py"],
                    "staleness_state": "fresh",
                    "quality_score": 0.9,
                    "tokens_est_l1": 50,
                    "tokens_est_l2": 100,
                },
                f"{repo}/cache": {
                    "title": "Cache",
                    "summary": "Caches entries.",
                    "sections": ["Purpose"],
                    "key_facts": [],
                    "tables": [],
                    "decisions": [],
                    "code_sigs": [],
                    "metrics": [],
                    "abs_path": str((module_dir / "cache.md").resolve()),
                    "generator": "wiki_capture",
                    "wiki_generated": 100.0,
                    "captured_at": 100.0,
                    "capture_kind": "session",
                    "session_id": "session-abc",
                    "source_files": [],
                    "staleness_state": "unknown",
                    "quality_score": 0.2,
                    "tokens_est_l1": 50,
                    "tokens_est_l2": 100,
                },
            }
        ),
        encoding="utf-8",
    )

    writer = HtmlWriter(wiki_dir)
    index_path = writer.generate_index(repo)
    html = index_path.read_text(encoding="utf-8")

    assert "Recent Sessions" in html
    assert "Recent Captures" in html
    assert "session-abc" in html
    assert "Session captures only" in html
    assert "Hide low signal" in html
    assert "Only with provenance" in html
    assert "executor" in html
    assert "cache" in html
