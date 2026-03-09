"""End-to-end tests for the session distillation pipeline."""

import json
import sqlite3
from pathlib import Path

from click.testing import CliRunner

from wisewiki.cache import WikiCache
from wisewiki.mcp_server import capture_wiki_page
from wisewiki.cli import cli


def test_capture_pipeline_publishes_session_memory(tmp_path):
    wiki_dir = tmp_path / "wiki"
    cache = WikiCache(wiki_dir / ".index" / "cache.json")
    cache.load()

    session_id = "session-alpha"
    content_one = """## Purpose
Capture wiki pages and publish human-visible session memory.

## Source Files
- `src/wisewiki/mcp_server.py`

## Key Functions
- `capture_wiki_page()`: persists pages and triggers publishing

## Design Decisions
- Keep HTML as the human-visible output layer.

## Gotchas
- Session dedupe does not replace visible noise filtering.

## Open Questions
- Should future claim extraction use a stronger LLM-backed pipeline?
"""
    content_two = """## Purpose
Render human-visible HTML pages for captures, sessions, and graphs.

## Source Files
- `src/wisewiki/html_writer.py`

## Key Functions
- `generate_index(repo)`: builds the session-centric home page

## Architecture
`HtmlWriter` renders module pages, session recap pages, and graph views from published memory data.

## Validation
- New pages include visible filters for trust and provenance.
"""

    first = capture_wiki_page(
        wiki_dir=wiki_dir,
        cache=cache,
        repo="wisewiki",
        module="mcp_server",
        content=content_one,
        session_id=session_id,
    )
    second = capture_wiki_page(
        wiki_dir=wiki_dir,
        cache=cache,
        repo="wisewiki",
        module="html_writer",
        content=content_two,
        session_id=session_id,
    )

    assert first["ok"] is True
    assert second["ok"] is True

    session_html = wiki_dir / "repos" / "wisewiki" / "sessions" / f"{session_id}.html"
    index_html = wiki_dir / "repos" / "wisewiki" / "index.html"
    graph_html = wiki_dir / "repos" / "wisewiki" / "graph.html"
    graph_json = wiki_dir / "repos" / "wisewiki" / "graph.json"
    db_path = wiki_dir / ".index" / "wisewiki.db"

    assert session_html.exists()
    assert index_html.exists()
    assert graph_html.exists()
    assert graph_json.exists()
    assert db_path.exists()

    session_text = session_html.read_text(encoding="utf-8")
    assert "Key Takeaways" in session_text
    assert "mcp_server" in session_text
    assert "html_writer" in session_text
    assert session_id in session_text

    index_text = index_html.read_text(encoding="utf-8")
    assert "Recent Sessions" in index_text
    assert "Your AI Session Wiki" in index_text
    assert "Latest Session" in index_text
    assert 'class="home-graph-preview"' in index_text
    assert "Trusted Modules" in index_text

    graph_data = json.loads(graph_json.read_text(encoding="utf-8"))
    assert len(graph_data["nodes"]) >= 2
    assert len(graph_data["edges"]) >= 1

    conn = sqlite3.connect(db_path)
    sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    captures = conn.execute("SELECT COUNT(*) FROM captures").fetchone()[0]
    claims = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    edges = conn.execute("SELECT COUNT(*) FROM graph_edges").fetchone()[0]
    conn.close()

    assert sessions == 1
    assert captures == 2
    assert claims >= 3
    assert edges >= 1


def test_capture_pipeline_uses_session_events_for_freeform_content(tmp_path):
    wiki_dir = tmp_path / "wiki"
    cache = WikiCache(wiki_dir / ".index" / "cache.json")
    cache.load()

    result = capture_wiki_page(
        wiki_dir=wiki_dir,
        cache=cache,
        repo="wisewiki",
        module="html_writer",
        content="We investigated html navigation behavior and captured the outcome.",
        session_id="session-events",
        session_events=[
            {
                "id": "ev1",
                "event_type": "error_observed",
                "payload": {"message": "overview sidebar links broken"},
            },
            {
                "id": "ev2",
                "event_type": "code_edit",
                "payload": {"path": "src/wisewiki/html_writer.py", "summary": "split relative links by page location"},
            },
            {
                "id": "ev3",
                "event_type": "test_result",
                "payload": {"command": "uv run pytest tests/test_html_writer.py -v", "summary": "1 passed", "exit_code": 0},
            },
            {
                "id": "ev4",
                "event_type": "assistant_message",
                "payload": {"text": "HtmlWriter needs different relative link logic because overview and module pages live in different directories."},
            },
        ],
        source_files=["src/wisewiki/html_writer.py"],
    )

    assert result["ok"] is True

    session_html = wiki_dir / "repos" / "wisewiki" / "sessions" / "session-events.html"
    recap_text = session_html.read_text(encoding="utf-8")
    assert "overview sidebar links broken" in recap_text
    assert "different directories" in recap_text

    conn = sqlite3.connect(wiki_dir / ".index" / "wisewiki.db")
    events = conn.execute("SELECT COUNT(*) FROM session_events").fetchone()[0]
    claims = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    conn.close()

    assert events >= 4
    assert claims >= 2


def test_full_v1_workflow_acceptance(tmp_path):
    wiki_dir = tmp_path / "wiki"
    cache = WikiCache(wiki_dir / ".index" / "cache.json")
    cache.load()

    capture_wiki_page(
        wiki_dir=wiki_dir,
        cache=cache,
        repo="wisewiki",
        module="mcp_server",
        content="Quick capture for server behavior.",
        session_id="acceptance-session",
        session_events=[
            {"id": "e1", "event_type": "error_observed", "payload": {"message": "duplicate save confusion"}},
            {"id": "e2", "event_type": "code_edit", "payload": {"path": "src/wisewiki/mcp_server.py", "summary": "added session metadata and recap publishing"}},
            {"id": "e3", "event_type": "test_result", "payload": {"command": "uv run pytest tests/test_pipeline.py -v", "summary": "1 passed", "exit_code": 0}},
            {"id": "e4", "event_type": "assistant_message", "payload": {"text": "mcp_server now routes capture into a full publish pipeline because session memory should be human-visible."}},
        ],
        source_files=["src/wisewiki/mcp_server.py"],
    )
    capture_wiki_page(
        wiki_dir=wiki_dir,
        cache=cache,
        repo="wisewiki",
        module="html_writer",
        content="Quick capture for rendering behavior.",
        session_id="acceptance-session",
        session_events=[
            {"id": "e5", "event_type": "assistant_message", "payload": {"text": "HtmlWriter now renders a session-centric home because users should see recent trusted captures first."}},
            {"id": "e6", "event_type": "code_edit", "payload": {"path": "src/wisewiki/html_writer.py", "summary": "added session home, recap page, and graph page"}},
            {"id": "e7", "event_type": "test_result", "payload": {"command": "uv run pytest tests/test_html_writer.py -v", "summary": "1 passed", "exit_code": 0}},
        ],
        source_files=["src/wisewiki/html_writer.py"],
    )

    runner = CliRunner()
    sessions = runner.invoke(cli, ["sessions", "wisewiki", "--wiki-dir", str(wiki_dir)])
    recap = runner.invoke(cli, ["recap", "wisewiki", "acceptance-session", "--wiki-dir", str(wiki_dir)])
    graph = runner.invoke(cli, ["graph", "wisewiki", "--wiki-dir", str(wiki_dir)])

    assert sessions.exit_code == 0
    assert recap.exit_code == 0
    assert graph.exit_code == 0
    assert "acceptance-session" in sessions.output
    assert "Key takeaways" in recap.output
    assert "graph.html" in graph.output

    index_html = (wiki_dir / "repos" / "wisewiki" / "index.html").read_text(encoding="utf-8")
    session_html = (wiki_dir / "repos" / "wisewiki" / "sessions" / "acceptance-session.html").read_text(encoding="utf-8")
    graph_html = (wiki_dir / "repos" / "wisewiki" / "graph.html").read_text(encoding="utf-8")
    graph_json = json.loads((wiki_dir / "repos" / "wisewiki" / "graph.json").read_text(encoding="utf-8"))

    assert "Your AI Session Wiki" in index_html
    assert "Latest Session" in index_html
    assert "Trusted Modules" in index_html
    assert 'class="home-graph-preview"' in index_html
    assert "acceptance-session" in session_html
    assert "human-visible" in session_html
    assert "Evidence Highlights" in session_html
    assert "Session Health" in session_html
    assert "Kind Filters" in graph_html
    assert "Focus neighbors" not in graph_html
    assert len(graph_json["nodes"]) >= 2
