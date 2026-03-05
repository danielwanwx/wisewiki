"""Tests for wisewiki.cache."""

import json
from pathlib import Path

from wisewiki.cache import WikiCache, _score_entry


def _make_entry(title="Test", summary="A summary"):
    return {
        "title": title,
        "summary": summary,
        "sections": ["Purpose"],
        "key_facts": [],
        "tables": [],
        "decisions": [],
        "code_sigs": [],
        "metrics": [],
        "abs_path": "",
        "generator": "wiki_capture",
        "wiki_generated": 1000.0,
        "tokens_est_l1": 50,
        "tokens_est_l2": 100,
        "source_files": [],
    }


def test_search_exact_match(tmp_path):
    cache = WikiCache(tmp_path / "cache.json")
    cache._data = {"help-cpl/executor": _make_entry("Executor", "Runs tasks")}
    results = cache.search("executor")
    assert len(results) == 1
    assert results[0].key == "help-cpl/executor"
    assert results[0].score > 50.0


def test_search_repo_filter(tmp_path):
    cache = WikiCache(tmp_path / "cache.json")
    cache._data = {
        "help-cpl/executor": _make_entry("Executor"),
        "other/executor": _make_entry("Executor"),
    }
    results = cache.search("executor", repo_filter="help-cpl")
    assert len(results) == 1
    assert results[0].repo == "help-cpl"


def test_search_no_match(tmp_path):
    cache = WikiCache(tmp_path / "cache.json")
    cache._data = {"help-cpl/executor": _make_entry("Executor")}
    results = cache.search("nonexistent_xyz_123")
    assert len(results) == 0


def test_save_atomic(tmp_path):
    cache = WikiCache(tmp_path / "cache.json")
    cache.add_entry("test/mod", _make_entry("Mod"))
    cache.save()
    assert (tmp_path / "cache.json").exists()
    assert not (tmp_path / "cache.json.tmp").exists()

    # Verify content
    with open(tmp_path / "cache.json") as f:
        data = json.load(f)
    assert "test/mod" in data


def test_load_valid(tmp_path):
    path = tmp_path / "cache.json"
    data = {"repo/mod": _make_entry("Mod")}
    path.write_text(json.dumps(data), encoding="utf-8")

    cache = WikiCache(path)
    cache.load()
    assert "repo/mod" in cache._data


def test_load_malformed(tmp_path, capsys):
    path = tmp_path / "cache.json"
    path.write_text("not json", encoding="utf-8")
    cache = WikiCache(path)
    cache.load()
    assert cache._data == {}
    captured = capsys.readouterr()
    assert "Rebuilding" in captured.err


def test_load_nonexistent(tmp_path):
    cache = WikiCache(tmp_path / "nonexistent.json")
    cache.load()
    assert cache._data == {}


def test_get_repos_in_cache(tmp_path):
    cache = WikiCache(tmp_path / "cache.json")
    cache._data = {
        "alpha/mod1": _make_entry(),
        "alpha/mod2": _make_entry(),
        "beta/mod1": _make_entry(),
    }
    repos = cache.get_repos_in_cache()
    assert repos == ["alpha", "beta"]


def test_format_results_auto(tmp_path):
    cache = WikiCache(tmp_path / "cache.json")
    cache._data = {"repo/mod": _make_entry("My Module", "Does things")}
    results = cache.search("mod")
    text = cache.format_results(results, depth="auto")
    assert "My Module" in text
    assert "Does things" in text
    assert "**Sections:**" in text


def test_score_entry_exact_key_match():
    entry = _make_entry("Executor", "Runs tasks")
    score = _score_entry("help-cpl/executor", entry, "executor", ["executor"])
    assert score >= 100.0  # exact module name match


def test_score_entry_title_prefix():
    entry = _make_entry("Executor Module", "Runs tasks")
    score = _score_entry("help-cpl/executor", entry, "executor", ["executor"])
    assert score > 100.0  # exact key + title prefix
