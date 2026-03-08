"""Tests for wisewiki.cli."""

from pathlib import Path

from click.testing import CliRunner

from wisewiki.cli import cli
from wisewiki.cache import WikiCache
from wisewiki.mcp_server import capture_wiki_page


def test_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "wisewiki" in result.output
    assert "serve" in result.output
    assert "setup" in result.output
    assert "status" in result.output
    assert "view" in result.output


def test_status_no_wiki_dir(tmp_path):
    runner = CliRunner()
    nonexistent = str(tmp_path / "nonexistent")
    result = runner.invoke(cli, ["status", "--wiki-dir", nonexistent])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_status_empty(tmp_path):
    runner = CliRunner()
    # Create the wiki dir but no repos
    result = runner.invoke(cli, ["status", "--wiki-dir", str(tmp_path)])
    assert "No repos found" in result.output


def test_status_with_repos(tmp_path):
    # Create a repo with a module
    module_dir = tmp_path / "repos" / "test-repo" / "modules"
    module_dir.mkdir(parents=True)
    (module_dir / "my_module.md").write_text("## Purpose\nTest")

    runner = CliRunner()
    result = runner.invoke(cli, ["status", "--wiki-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "test-repo" in result.output
    assert "1 pages" in result.output


def test_view_nonexistent_repo(tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, ["view", "nonexistent", "--wiki-dir", str(tmp_path)])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_view_no_index(tmp_path):
    repo_dir = tmp_path / "repos" / "myrepo"
    repo_dir.mkdir(parents=True)
    runner = CliRunner()
    result = runner.invoke(cli, ["view", "myrepo", "--wiki-dir", str(tmp_path)])
    assert result.exit_code == 1
    assert "No index.html" in result.output


def test_st_alias():
    runner = CliRunner()
    result = runner.invoke(cli, ["st", "--help"])
    assert result.exit_code == 0
    assert "Show wiki repos" in result.output


def test_reindex(tmp_path):
    module_dir = tmp_path / "repos" / "test-repo" / "modules"
    module_dir.mkdir(parents=True)
    (module_dir / "my_module.md").write_text("## Purpose\nTest")

    runner = CliRunner()
    result = runner.invoke(cli, ["reindex", "test-repo", "--wiki-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "Regenerated" in result.output

    index_html = tmp_path / "repos" / "test-repo" / "index.html"
    assert index_html.exists()


def test_reindex_nonexistent_repo(tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, ["reindex", "nonexistent", "--wiki-dir", str(tmp_path)])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_sessions_lists_recent_sessions(tmp_path):
    cache = WikiCache(tmp_path / ".index" / "cache.json")
    cache.load()
    capture_wiki_page(
        wiki_dir=tmp_path,
        cache=cache,
        repo="demo",
        module="html_writer",
        content="## Purpose\nRender pages.\n\n## Source Files\n- `src/wisewiki/html_writer.py`\n",
        session_id="session-demo",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["sessions", "demo", "--wiki-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "session-demo" in result.output
    assert "captures" in result.output


def test_recap_shows_session_summary(tmp_path):
    cache = WikiCache(tmp_path / ".index" / "cache.json")
    cache.load()
    capture_wiki_page(
        wiki_dir=tmp_path,
        cache=cache,
        repo="demo",
        module="html_writer",
        content="## Purpose\nRender pages.\n\n## Source Files\n- `src/wisewiki/html_writer.py`\n",
        session_id="session-demo",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["recap", "demo", "session-demo", "--wiki-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "session-demo" in result.output
    assert "Key takeaways" in result.output


def test_graph_command_outputs_graph_location(tmp_path):
    cache = WikiCache(tmp_path / ".index" / "cache.json")
    cache.load()
    capture_wiki_page(
        wiki_dir=tmp_path,
        cache=cache,
        repo="demo",
        module="html_writer",
        content="## Purpose\nRender pages.\n\n## Source Files\n- `src/wisewiki/html_writer.py`\n",
        session_id="session-demo",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["graph", "demo", "--wiki-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "graph.html" in result.output
