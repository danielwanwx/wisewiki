"""Tests for wisewiki.models."""

from wisewiki.models import CacheEntry, SearchResult, WikiPage


def test_cache_entry_to_dict():
    entry = CacheEntry(title="Test", summary="A test entry")
    d = entry.to_dict()
    assert d["title"] == "Test"
    assert d["summary"] == "A test entry"
    assert d["sections"] == []
    assert d["generator"] == "wiki_capture"


def test_cache_entry_from_dict():
    d = {
        "title": "Executor",
        "summary": "Runs tasks",
        "sections": ["Purpose", "Key Functions"],
        "key_facts": ["fact1"],
        "tables": [],
        "decisions": [],
        "code_sigs": ["run()"],
        "metrics": [],
        "abs_path": "/tmp/test.md",
        "generator": "wiki_capture",
        "wiki_generated": 1000.0,
        "tokens_est_l1": 50,
        "tokens_est_l2": 200,
        "source_files": [],
    }
    entry = CacheEntry.from_dict(d)
    assert entry.title == "Executor"
    assert entry.sections == ["Purpose", "Key Functions"]
    assert entry.code_sigs == ["run()"]


def test_cache_entry_from_dict_ignores_unknown_keys():
    d = {"title": "Test", "summary": "s", "unknown_field": "ignored"}
    entry = CacheEntry.from_dict(d)
    assert entry.title == "Test"


def test_cache_entry_roundtrip():
    entry = CacheEntry(title="RT", summary="round trip", sections=["A", "B"])
    d = entry.to_dict()
    restored = CacheEntry.from_dict(d)
    assert restored.title == entry.title
    assert restored.sections == entry.sections


def test_cache_entry_metadata_roundtrip():
    entry = CacheEntry(
        title="Session Entry",
        summary="Captured from an AI session.",
        capture_kind="session",
        session_id="session-123",
        captured_at=1234.5,
        source_files=["src/wisewiki/mcp_server.py"],
        staleness_state="fresh",
        quality_score=0.85,
    )
    d = entry.to_dict()
    restored = CacheEntry.from_dict(d)
    assert restored.capture_kind == "session"
    assert restored.session_id == "session-123"
    assert restored.captured_at == 1234.5
    assert restored.source_files == ["src/wisewiki/mcp_server.py"]
    assert restored.staleness_state == "fresh"
    assert restored.quality_score == 0.85


def test_search_result_fields():
    entry = CacheEntry(title="T", summary="S")
    sr = SearchResult(key="repo/mod", repo="repo", module="mod", entry=entry, score=42.0)
    assert sr.key == "repo/mod"
    assert sr.score == 42.0


def test_wiki_page_fields():
    wp = WikiPage(repo="r", module="m", content="# hi", html_path="/a.html", md_path="/a.md")
    assert wp.repo == "r"
    assert wp.content == "# hi"
