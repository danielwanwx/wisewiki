"""Tests for wisewiki.setup_wizard."""

from wisewiki.setup_wizard import WIKI_SAVE_SKILL_CONTENT, _install_skill


def test_install_skill_creates_directory_with_skill_md(tmp_path):
    skills_dir = tmp_path / "skills"

    skill_path = _install_skill(skills_dir)

    assert skill_path == skills_dir / "wiki-save" / "SKILL.md"
    assert skill_path.exists()
    assert skill_path.read_text(encoding="utf-8") == WIKI_SAVE_SKILL_CONTENT


def test_install_skill_migrates_legacy_flat_file(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir(parents=True)
    legacy_path = skills_dir / "wiki-save.md"
    legacy_path.write_text("legacy content", encoding="utf-8")

    skill_path = _install_skill(skills_dir)

    assert skill_path == skills_dir / "wiki-save" / "SKILL.md"
    assert skill_path.exists()
    assert skill_path.read_text(encoding="utf-8") == WIKI_SAVE_SKILL_CONTENT
    assert not legacy_path.exists()


def test_wiki_save_skill_limits_scope_and_reports_html_entry_points():
    assert "Save only the 1-2 highest-signal modules" in WIKI_SAVE_SKILL_CONTENT
    assert "Do not save every file or topic mentioned" in WIKI_SAVE_SKILL_CONTENT
    assert "Keep each `content` payload concise" in WIKI_SAVE_SKILL_CONTENT
    assert "First report these entry points" in WIKI_SAVE_SKILL_CONTENT
    assert "index.html" in WIKI_SAVE_SKILL_CONTENT
    assert "graph.html" in WIKI_SAVE_SKILL_CONTENT
    assert "session recap" in WIKI_SAVE_SKILL_CONTENT
