"""Tests for wisewiki.cli."""

from pathlib import Path

from click.testing import CliRunner

from wisewiki.cli import cli


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
