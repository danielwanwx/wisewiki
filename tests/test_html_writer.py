"""Tests for wisewiki.html_writer."""

import json

from wisewiki.html_writer import HtmlWriter
from wisewiki.models import CacheEntry, PromotedClaim, SessionRecap
from wisewiki.session_store import SessionStore


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

    assert "Your AI Session Wiki" in html
    assert "Wisewiki turns useful AI conversations into clear session recaps, linked module pages, and a graph you can revisit later." in html
    assert "Latest Session" in html
    assert "Trusted Modules" in html
    assert "Open Questions" in html
    assert 'class="home-graph-preview"' in html
    assert 'data-card-href="sessions/session-abc.html"' in html
    assert 'data-graph-href="graph.html"' in html
    assert 'id="home-graph-preview-svg"' in html
    assert "Drag nodes" not in html
    assert "home-graph-preview-data" in html
    assert "Open full graph" not in html
    assert "Open full session recap" not in html
    assert "executor" in html
    assert "cache" in html
    assert "modules/executor.html" in html
    assert "modules/cache.html" in html
    assert "highlighted" not in html
    assert "Inspect" not in html
    assert "unresolved items" not in html
    assert "Review" not in html
    assert "Recent Sessions" in html
    assert 'class="layout no-nav"' in html
    assert "<nav>" not in html


def test_write_graph_page_builds_obsidian_style_graph(tmp_path):
    writer = HtmlWriter(tmp_path)
    graph_data = {
        "nodes": [
            {"id": "module:cache", "label": "cache", "type": "module", "session_id": "session-1", "confidence": 0.55, "staleness_state": "fresh"},
            {"id": "decision:cache:1", "label": "Prefer local cache reads", "type": "decision", "session_id": "session-1", "confidence": 0.9, "staleness_state": "fresh"},
        ],
        "edges": [
            {"source_key": "module:cache", "target_key": "decision:cache:1", "edge_type": "supports", "weight": 1.0}
        ],
    }

    path = writer.write_graph_page("demo", graph_data)
    html = path.read_text(encoding="utf-8")

    assert "obsidian-style knowledge graph" in html
    assert "graph-canvas" in html
    assert "graph-detail-copy" in html
    assert "#0b1020" in html
    assert ".graph-empty[hidden] { display: none; }" in html
    assert 'id="graph-filter-summary"' in html
    assert "Only latest session" not in html
    assert "Hide stale" not in html
    assert "Hide low signal" not in html
    assert "Focus neighbors" not in html


def test_write_module_page_includes_promoted_knowledge(tmp_path):
    wiki_dir = tmp_path
    repo = "demo"
    module = "cache"
    module_dir = wiki_dir / "repos" / repo / "modules"
    module_dir.mkdir(parents=True)
    md_path = module_dir / f"{module}.md"
    md_path.write_text("## Purpose\nCache values for later use.\n", encoding="utf-8")

    store = SessionStore(wiki_dir)
    store.ensure_session(repo, "session-one", created_at=100)
    store.conn.execute(
        """
        INSERT INTO claims (
            session_id, repo, module, kind, summary, why_it_matters,
            confidence, reusability, specificity, novelty_score,
            evidence_score, final_score, evidence_refs_json,
            staleness_state, status, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "session-one",
            repo,
            module,
            "decision",
            "Prefer local-first cache reads before recomputing results.",
            "Reduces repeated work across sessions.",
            0.85,
            0.9,
            0.8,
            0.9,
            0.8,
            0.86,
            json.dumps(["src/wisewiki/cache.py"]),
            "fresh",
            "promoted",
            100.0,
        ),
    )
    store.conn.commit()

    writer = HtmlWriter(wiki_dir)
    html_path = writer.write_module_page(
        repo,
        module,
        "## Purpose\nCache values for later use.\n",
        md_path,
        entry=CacheEntry(
            title="Cache",
            summary="Cache values for later use.",
            capture_kind="session",
            session_id="session-one",
            source_files=["src/wisewiki/cache.py"],
            quality_score=0.8,
            staleness_state="fresh",
        ),
    )
    html = html_path.read_text(encoding="utf-8")

    assert "Promoted Knowledge" in html
    assert "Recent Sessions" in html
    assert "Prefer local-first cache reads" in html


def test_write_session_page_prioritizes_core_insights_before_metadata(tmp_path):
    writer = HtmlWriter(tmp_path)
    recap = SessionRecap(
        session_id="session-wow",
        repo="demo",
        title="Wisewiki session recap",
        summary="This session clarified how Wisewiki should turn noisy coding chats into a trusted knowledge product.",
        key_takeaways=[
            "Lead with distilled insights instead of metadata.",
            "Move trust and freshness metrics below the main knowledge narrative.",
            "Use before and after framing to show why the session mattered.",
        ],
        decisions=[
            "The session hero should show one sentence plus three core insights.",
        ],
        gotchas=[
            "Pages felt noisy because users had to scan cards before seeing the main takeaway.",
        ],
        open_questions=[
            "Should future sessions cluster related insights automatically?",
        ],
        modules_touched=["html_writer", "session_store"],
        source_files=["src/wisewiki/html_writer.py"],
        related_claims=[
            PromotedClaim(
                kind="decision",
                module="html_writer",
                summary="Hero should present one sentence plus three core insights.",
                why_it_matters="Users should understand the value of the session instantly.",
                confidence=0.9,
                reusability=0.9,
                specificity=0.8,
                novelty_score=0.8,
                evidence_score=0.8,
                final_score=0.88,
                evidence_refs=["src/wisewiki/html_writer.py"],
                staleness_state="fresh",
            ),
            PromotedClaim(
                kind="architecture",
                module="session_store",
                summary="Before and after framing makes the distilled learning feel transformative.",
                why_it_matters="It creates the wow moment instead of a plain archive page.",
                confidence=0.85,
                reusability=0.8,
                specificity=0.75,
                novelty_score=0.75,
                evidence_score=0.8,
                final_score=0.82,
                evidence_refs=["src/wisewiki/session_store.py"],
                staleness_state="fresh",
            ),
        ],
        created_at=100.0,
    )

    html_path = writer.write_session_page("demo", recap)
    html = html_path.read_text(encoding="utf-8")

    assert "Core Insights" in html
    assert "What Became Clear" in html
    assert "Session Health" in html
    assert html.index("Core Insights") < html.index("Session Health")
    assert html.index("Lead with distilled insights instead of metadata.") < html.index("Session Health")
    assert "Users should understand the value of the session instantly." in html
    assert "Evidence Highlights" in html


def test_sidebar_renders_grouped_navigation_shell(tmp_path):
    wiki_dir = tmp_path
    repo = "demo"
    repo_dir = wiki_dir / "repos" / repo
    module_dir = repo_dir / "modules"
    session_dir = repo_dir / "sessions"
    module_dir.mkdir(parents=True)
    session_dir.mkdir(parents=True)

    (module_dir / "claims.md").write_text("## Claims\n", encoding="utf-8")
    (module_dir / "html_writer.md").write_text("## Html Writer\n", encoding="utf-8")
    (session_dir / "clarity-session.html").write_text("<html></html>", encoding="utf-8")

    writer = HtmlWriter(wiki_dir)
    html = writer._build_sidebar(repo, current="session:clarity-session", location="root")

    assert 'class="nav-link nav-link-home"' in html
    assert 'class="nav-section-title"' in html
    assert 'class="nav-link nav-link-session is-active"' in html
    assert 'class="nav-link nav-link-module"' in html
    assert "<h3>" not in html


def test_session_page_sidebar_uses_parent_relative_links(tmp_path):
    wiki_dir = tmp_path
    repo = "demo"
    repo_dir = wiki_dir / "repos" / repo
    module_dir = repo_dir / "modules"
    session_dir = repo_dir / "sessions"
    module_dir.mkdir(parents=True)
    session_dir.mkdir(parents=True)

    (module_dir / "claims.md").write_text("## Claims\n", encoding="utf-8")

    writer = HtmlWriter(wiki_dir)
    recap = SessionRecap(
        session_id="session-links",
        repo=repo,
        title="Recap",
        summary="Summary",
        created_at=100.0,
    )
    html_path = writer.write_session_page(repo, recap)
    html = html_path.read_text(encoding="utf-8")

    assert 'href="../index.html"' in html
    assert 'href="../graph.html"' in html
    assert 'href="../modules/claims.html"' in html
    assert "<nav><h3>" not in html


def test_graph_page_keeps_kind_filters_but_removes_redundant_top_filters(tmp_path):
    writer = HtmlWriter(tmp_path)
    graph_data = {
        "nodes": [
            {"id": "module:cache", "label": "cache", "type": "module", "session_id": "session-1", "confidence": 0.55, "staleness_state": "fresh"},
            {"id": "decision:cache:1", "label": "Prefer local cache reads", "type": "decision", "session_id": "session-1", "confidence": 0.9, "staleness_state": "fresh"},
            {"id": "gotcha:cache:2", "label": "Cache invalidation remains tricky", "type": "gotcha", "session_id": "session-2", "confidence": 0.85, "staleness_state": "stale"},
        ],
        "edges": [
            {"source_key": "module:cache", "target_key": "decision:cache:1", "edge_type": "supports", "weight": 1.0},
            {"source_key": "module:cache", "target_key": "gotcha:cache:2", "edge_type": "supports", "weight": 1.0},
        ],
    }

    path = writer.write_graph_page("demo", graph_data)
    html = path.read_text(encoding="utf-8")

    assert "Kind Filters" in html
    assert "decision (1)" in html
    assert "gotcha (1)" in html
    assert "Only latest session" not in html
    assert "Hide stale" not in html
    assert "Hide low signal" not in html
    assert "Focus neighbors" not in html


def test_graph_page_details_include_explanations_and_links(tmp_path):
    writer = HtmlWriter(tmp_path)
    graph_data = {
        "nodes": [
            {
                "id": "module:cache",
                "label": "cache",
                "type": "module",
                "module": "cache",
                "session_id": "session-1",
                "confidence": 0.75,
                "staleness_state": "fresh",
            },
            {
                "id": "decision:cache:1",
                "label": "Prefer local cache reads",
                "type": "decision",
                "module": "cache",
                "session_id": "session-1",
                "confidence": 0.9,
                "staleness_state": "fresh",
            },
        ],
        "edges": [
            {"source_key": "module:cache", "target_key": "decision:cache:1", "edge_type": "supports", "weight": 1.0}
        ],
    }

    path = writer.write_graph_page("demo", graph_data)
    html = path.read_text(encoding="utf-8")

    assert "graph-detail-copy" in html
    assert "graph-detail-links" in html
    assert "Open module page" in html
    assert "Open session recap" in html
    assert "Distilled claim from this session" in html
