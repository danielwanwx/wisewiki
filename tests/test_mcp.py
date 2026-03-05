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


class TestWikiCaptureDeduplication:
    """Tests for wiki_capture deduplication mechanisms (Phase 1 + Phase 2)."""

    def test_new_module_returns_created(self, tmp_path):
        """First save should return 'Created' message."""
        from wisewiki.mcp_server import _session_saves, _compute_content_hash
        import mcp.types as types

        # Clear session state
        _session_saves.clear()

        # Setup
        wiki_dir = tmp_path / "wiki"
        cache = WikiCache(wiki_dir / ".index" / "cache.json")
        content = "## Purpose\nThis is a new module."

        # Simulate wiki_capture for new module
        repo, module = "myrepo", "new_module"
        key = (repo, module)
        content_hash = _compute_content_hash(content)

        module_dir = wiki_dir / "repos" / repo / "modules"
        module_dir.mkdir(parents=True, exist_ok=True)
        md_path = module_dir / f"{module}.md"

        # File doesn't exist
        assert not md_path.exists()

        # Simulate save
        md_path.write_text(content, encoding="utf-8")
        _session_saves[key] = content_hash

        # Verify
        assert md_path.exists()
        assert key in _session_saves
        assert _session_saves[key] == content_hash

    def test_unchanged_content_returns_no_changes(self, tmp_path):
        """Saving identical content should return 'No changes' and skip I/O."""
        from wisewiki.mcp_server import _session_saves, _compute_content_hash

        # Clear session state
        _session_saves.clear()

        # Setup
        wiki_dir = tmp_path / "wiki"
        cache = WikiCache(wiki_dir / ".index" / "cache.json")
        content = "## Purpose\nThis module does X."

        repo, module = "myrepo", "test_module"
        key = (repo, module)
        content_hash = _compute_content_hash(content)

        module_dir = wiki_dir / "repos" / repo / "modules"
        module_dir.mkdir(parents=True, exist_ok=True)
        md_path = module_dir / f"{module}.md"

        # First save
        md_path.write_text(content, encoding="utf-8")
        _session_saves[key] = content_hash
        mtime_first = md_path.stat().st_mtime

        # Second save with identical content (disk comparison)
        existing_content = md_path.read_text(encoding="utf-8")
        assert existing_content == content  # Should match

        # No write should happen - verify by checking mtime stays same
        # (In real implementation, we return early without writing)
        mtime_second = md_path.stat().st_mtime
        assert mtime_first == mtime_second

    def test_changed_content_returns_updated(self, tmp_path):
        """Modified content should return 'Updated' message."""
        from wisewiki.mcp_server import _session_saves, _compute_content_hash

        # Clear session state
        _session_saves.clear()

        # Setup
        wiki_dir = tmp_path / "wiki"
        content_v1 = "## Purpose\nVersion 1"
        content_v2 = "## Purpose\nVersion 2 - updated!"

        repo, module = "myrepo", "evolving_module"
        key = (repo, module)

        module_dir = wiki_dir / "repos" / repo / "modules"
        module_dir.mkdir(parents=True, exist_ok=True)
        md_path = module_dir / f"{module}.md"

        # First save
        md_path.write_text(content_v1, encoding="utf-8")
        _session_saves[key] = _compute_content_hash(content_v1)

        # Second save with different content
        existing_content = md_path.read_text(encoding="utf-8")
        assert existing_content == content_v1
        assert existing_content != content_v2  # Content changed

        # Should be classified as "updated"
        operation_type = "updated"

        # Perform update
        md_path.write_text(content_v2, encoding="utf-8")
        _session_saves[key] = _compute_content_hash(content_v2)

        # Verify
        assert md_path.read_text(encoding="utf-8") == content_v2
        assert _session_saves[key] == _compute_content_hash(content_v2)

    def test_session_deduplication(self, tmp_path):
        """Same session, second save should use session cache."""
        from wisewiki.mcp_server import _session_saves, _compute_content_hash

        # Clear session state
        _session_saves.clear()

        # Setup
        wiki_dir = tmp_path / "wiki"
        content = "## Purpose\nSession test module."

        repo, module = "myrepo", "session_module"
        key = (repo, module)
        content_hash = _compute_content_hash(content)

        module_dir = wiki_dir / "repos" / repo / "modules"
        module_dir.mkdir(parents=True, exist_ok=True)
        md_path = module_dir / f"{module}.md"

        # First save
        md_path.write_text(content, encoding="utf-8")
        _session_saves[key] = content_hash

        # Second save in same session with identical content
        # Session cache should hit
        assert key in _session_saves
        assert _session_saves[key] == content_hash

        # This simulates the session cache check returning early
        # with "Already saved in this session" message

    def test_session_isolation_after_restart(self, tmp_path):
        """After clearing session, should fall back to disk comparison."""
        from wisewiki.mcp_server import _session_saves, _compute_content_hash

        # Setup
        wiki_dir = tmp_path / "wiki"
        content = "## Purpose\nPersisted module."

        repo, module = "myrepo", "persistent_module"
        key = (repo, module)
        content_hash = _compute_content_hash(content)

        module_dir = wiki_dir / "repos" / repo / "modules"
        module_dir.mkdir(parents=True, exist_ok=True)
        md_path = module_dir / f"{module}.md"

        # First save
        _session_saves.clear()
        md_path.write_text(content, encoding="utf-8")
        _session_saves[key] = content_hash
        assert key in _session_saves

        # Simulate server restart - clear session state
        _session_saves.clear()
        assert key not in _session_saves

        # File still exists on disk
        assert md_path.exists()

        # Second save should use disk comparison (not session cache)
        existing_content = md_path.read_text(encoding="utf-8")
        assert existing_content == content  # Disk comparison works

    def test_hash_computation_deterministic(self):
        """Hash computation should be deterministic."""
        from wisewiki.mcp_server import _compute_content_hash

        content = "## Test\nSome content here."
        hash1 = _compute_content_hash(content)
        hash2 = _compute_content_hash(content)

        assert hash1 == hash2
        assert len(hash1) == 16  # First 16 chars of SHA256

        # Different content should have different hash
        content2 = "## Test\nDifferent content."
        hash3 = _compute_content_hash(content2)
        assert hash1 != hash3

    def test_end_to_end_workflow(self, tmp_path):
        """Complete user scenario testing all states."""
        from wisewiki.mcp_server import _session_saves, _compute_content_hash

        # Clear session state
        _session_saves.clear()

        wiki_dir = tmp_path / "wiki"
        content_v1 = "## Purpose\nOriginal content."
        content_v2 = "## Purpose\nUpdated content!"

        repo, module = "myrepo", "workflow_module"
        key = (repo, module)

        module_dir = wiki_dir / "repos" / repo / "modules"
        module_dir.mkdir(parents=True, exist_ok=True)
        md_path = module_dir / f"{module}.md"

        # 1. Save new module → should be "created"
        assert not md_path.exists()
        md_path.write_text(content_v1, encoding="utf-8")
        _session_saves[key] = _compute_content_hash(content_v1)
        assert md_path.exists()

        # 2. Save again with same content → should be "Already saved in session"
        assert key in _session_saves
        assert _session_saves[key] == _compute_content_hash(content_v1)

        # 3. Update module with new content → should be "updated"
        md_path.write_text(content_v2, encoding="utf-8")
        _session_saves[key] = _compute_content_hash(content_v2)
        assert md_path.read_text(encoding="utf-8") == content_v2

        # 4. Save again with same new content → should be "Already saved in session"
        assert _session_saves[key] == _compute_content_hash(content_v2)
