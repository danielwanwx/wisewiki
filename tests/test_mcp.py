"""Tests for wisewiki.mcp_server."""

import re
from pathlib import Path

from wisewiki.mcp_server import _entry_from_md, _route_intent, NAME_RE, _resolve
from wisewiki.cache import WikiCache


def test_entry_from_md_title_extraction(tmp_path):
    content = "## Purpose\nThis module does X.\n\n## Key Functions\n- `run()`: main entry"
    path = tmp_path / "executor.md"
    path.write_text(content)
    entry = _entry_from_md(content, path)
    assert entry["title"] == "Purpose"
    assert "Key Functions" in entry["sections"]
    assert "run()" in entry["code_sigs"]


def test_entry_from_md_fallback_title(tmp_path):
    content = "No heading here, just text."
    path = tmp_path / "my_module.md"
    path.write_text(content)
    entry = _entry_from_md(content, path)
    assert entry["title"] == "My Module"


def test_entry_from_md_summary_skips_code(tmp_path):
    content = "## Title\n```python\nskip this\n```\nActual summary here."
    path = tmp_path / "test.md"
    path.write_text(content)
    entry = _entry_from_md(content, path)
    assert entry["summary"] == "Actual summary here."


def test_entry_from_md_sections(tmp_path):
    content = "## Purpose\ntext\n## Key Functions\nmore\n## Design Decisions\nstuff"
    path = tmp_path / "test.md"
    path.write_text(content)
    entry = _entry_from_md(content, path)
    assert entry["sections"] == ["Purpose", "Key Functions", "Design Decisions"]


def test_entry_from_md_decisions(tmp_path):
    content = "## Design Decisions\n- asyncio over threading\n- flat cache format"
    path = tmp_path / "test.md"
    path.write_text(content)
    entry = _entry_from_md(content, path)
    assert "asyncio over threading" in entry["decisions"]
    assert "flat cache format" in entry["decisions"]


def test_route_intent():
    assert _route_intent("list") == "list_repos"
    assert _route_intent("repos") == "list_repos"
    assert _route_intent("repositories") == "list_repos"
    assert _route_intent("list repos") == "list_repos"
    assert _route_intent("show repos") == "list_repos"
    assert _route_intent("executor") == "explain_module"
    assert _route_intent("auth_service") == "explain_module"
    assert _route_intent("how does executor work") == "search"
    assert _route_intent("task dispatch logic") == "search"


def test_name_validation():
    assert NAME_RE.match("help-cpl")
    assert NAME_RE.match("my_module")
    assert NAME_RE.match("Module123")
    assert not NAME_RE.match("my module")
    assert not NAME_RE.match("my/module")
    assert not NAME_RE.match("")
    assert not NAME_RE.match("mod!ule")


def test_resolve_list_repos_empty(tmp_path):
    cache = WikiCache(tmp_path / "cache.json")
    cache._data = {}
    result = _resolve("list", None, "auto", cache, tmp_path)
    assert result.startswith("[REPO_NOT_FOUND]")


def test_resolve_list_repos(tmp_path):
    cache = WikiCache(tmp_path / "cache.json")
    cache._data = {
        "myrepo/mod1": {"title": "Mod1", "summary": "s"},
        "myrepo/mod2": {"title": "Mod2", "summary": "s"},
    }
    result = _resolve("list", None, "auto", cache, tmp_path)
    assert "myrepo" in result
    assert "2 pages" in result


def test_resolve_not_found(tmp_path):
    cache = WikiCache(tmp_path / "cache.json")
    cache._data = {}
    result = _resolve("nonexistent", "myrepo", "auto", cache, tmp_path)
    assert result.startswith("[REPO_NOT_FOUND]")


def test_resolve_disk_fallback(tmp_path):
    # Set up a .md file on disk without cache entry
    module_dir = tmp_path / "repos" / "myrepo" / "modules"
    module_dir.mkdir(parents=True)
    md_path = module_dir / "executor.md"
    md_path.write_text("## Purpose\nDoes things.\n\n## Key Functions\n- `run()`: entry point")

    cache = WikiCache(tmp_path / "cache.json")
    cache._data = {}
    result = _resolve("executor", "myrepo", "auto", cache, tmp_path)
    assert "Purpose" in result


def test_resolve_search(tmp_path):
    cache = WikiCache(tmp_path / "cache.json")
    cache._data = {
        "myrepo/executor": {
            "title": "Executor",
            "summary": "Runs pipeline tasks",
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
    }
    result = _resolve("pipeline tasks", None, "auto", cache, tmp_path)
    assert "Executor" in result
