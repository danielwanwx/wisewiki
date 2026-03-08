# src/wisewiki/html_writer.py

import json
from datetime import datetime
from html import escape
from pathlib import Path

import markdown as md_lib

from wisewiki.models import CacheEntry, SessionRecap
from wisewiki.session_store import SessionStore


BASE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — wisewiki</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; background: #fafafa; color: #1f2937; }}
    .layout {{ display: flex; min-height: 100vh; }}
    nav {{ width: 250px; background: #ffffff; border-right: 1px solid #e5e7eb; padding: 1rem; box-sizing: border-box; }}
    nav h3 {{ margin: 0 0 1rem; font-size: 0.9rem; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; }}
    nav a {{ display: block; padding: 0.35rem 0; color: #374151; text-decoration: none; }}
    nav a:hover {{ color: #2563eb; }}
    main {{ flex: 1; padding: 2rem; max-width: 980px; }}
    h1, h2, h3 {{ color: #111827; }}
    h2 {{ margin-top: 2rem; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.35rem; }}
    .hero {{ margin-bottom: 1.5rem; }}
    .hero p {{ color: #4b5563; line-height: 1.6; }}
    .meta, .filters, .card-grid {{ display: grid; gap: 0.75rem; }}
    .meta {{ grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); margin: 1rem 0 1.5rem; }}
    .meta-card, .card, .filter-card, .graph-shell {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 1rem; }}
    .card-grid {{ grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }}
    .eyebrow {{ margin: 0 0 0.35rem; color: #6b7280; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; }}
    .badge {{ display: inline-block; margin-right: 0.35rem; padding: 0.2rem 0.5rem; border-radius: 999px; background: #eff6ff; color: #1d4ed8; font-size: 0.75rem; }}
    .badge.low {{ background: #fef3c7; color: #92400e; }}
    .badge.stale {{ background: #fee2e2; color: #991b1b; }}
    ul {{ padding-left: 1.2rem; }}
    .filters {{ grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); margin-bottom: 1.2rem; }}
    .filters label {{ display: flex; gap: 0.5rem; align-items: center; font-weight: 600; }}
    .muted {{ color: #6b7280; }}
    code {{ background: #f3f4f6; padding: 0.12em 0.3em; border-radius: 4px; }}
    pre {{ background: #111827; color: #f9fafb; padding: 1rem; overflow-x: auto; border-radius: 8px; }}
    pre code {{ background: none; color: inherit; padding: 0; }}
    .graph-shell svg {{ width: 100%; height: 360px; display: block; background: linear-gradient(180deg, #ffffff 0%, #f9fafb 100%); border-radius: 8px; }}
    .footer {{ margin-top: 2rem; color: #6b7280; font-size: 0.82rem; }}
  </style>
</head>
<body>
  <div class="layout">
    <nav>
      <h3>{repo}</h3>
      {sidebar}
    </nav>
    <main>
      {body}
      <div class="footer">wisewiki · {footer}</div>
    </main>
  </div>
</body>
</html>
"""


class HtmlWriter:
    def __init__(self, wiki_dir: Path) -> None:
        self.wiki_dir = wiki_dir

    def write_module_page(
        self,
        repo: str,
        module: str,
        md_content: str,
        md_path: Path,
        *,
        entry: CacheEntry | None = None,
    ) -> Path:
        html_content = self._md_to_html(md_content)
        sidebar = self._build_sidebar(repo, current=module, in_modules=True)
        title = self._extract_title(md_content, module)
        meta_html = self._module_meta(entry)
        body = f"{meta_html}{html_content}"
        page = BASE_TEMPLATE.format(
            title=title,
            repo=repo,
            sidebar=sidebar,
            body=body,
            footer=f"{repo}/{module}",
        )
        html_path = md_path.with_suffix(".html")
        self._atomic_write(html_path, page)
        return html_path

    def write_session_page(self, repo: str, recap: SessionRecap) -> Path:
        session_dir = self.wiki_dir / "repos" / repo / "sessions"
        session_dir.mkdir(parents=True, exist_ok=True)
        body = self._render_session_recap(recap)
        page = BASE_TEMPLATE.format(
            title=recap.title,
            repo=repo,
            sidebar=self._build_sidebar(repo, current=f"session:{recap.session_id}", in_modules=False),
            body=body,
            footer=f"{repo}/sessions/{recap.session_id}",
        )
        path = session_dir / f"{recap.session_id}.html"
        self._atomic_write(path, page)
        return path

    def write_graph_data(self, repo: str, graph_data: dict) -> Path:
        graph_path = self.wiki_dir / "repos" / repo / "graph.json"
        self._atomic_write(graph_path, json.dumps(graph_data, indent=2))
        return graph_path

    def write_graph_page(self, repo: str, graph_data: dict) -> Path:
        sidebar = self._build_sidebar(repo, current="graph", in_modules=False)
        nodes_json = escape(json.dumps(graph_data.get("nodes", [])))
        edges_json = escape(json.dumps(graph_data.get("edges", [])))
        body = f"""
        <section class="hero">
          <h1>Session Graph</h1>
          <p>Lightweight project graph showing recent modules and promoted claims.</p>
        </section>
        <div class="filters">
          <div class="filter-card"><label><input type="checkbox" id="graph-session-only"> Only this session</label><div class="muted">Focus on the most recent session graph.</div></div>
          <div class="filter-card"><label><input type="checkbox" id="graph-hide-stale"> Hide stale</label><div class="muted">Hide claims or modules that need a re-check.</div></div>
          <div class="filter-card"><label><input type="checkbox" id="graph-hide-low"> Hide low signal</label><div class="muted">Hide nodes below the default trust threshold.</div></div>
        </div>
        <section class="graph-shell">
          <svg id="graph-svg" viewBox="0 0 860 360" preserveAspectRatio="xMidYMid meet"></svg>
        </section>
        <script>
        const nodes = JSON.parse("{nodes_json}");
        const edges = JSON.parse("{edges_json}");
        const svg = document.getElementById("graph-svg");
        const width = 860;
        const height = 360;
        const centerX = width / 2;
        const centerY = height / 2;
        const radius = Math.max(110, Math.min(150, nodes.length * 12));
        const latestSession = nodes.length ? nodes[0].session_id : "";
        const visibleNodes = () => nodes.filter((node) => {{
          if (document.getElementById("graph-session-only").checked && node.session_id !== latestSession) return false;
          if (document.getElementById("graph-hide-stale").checked && node.staleness_state === "stale") return false;
          if (document.getElementById("graph-hide-low").checked && (node.confidence || 0) < 0.6) return false;
          return true;
        }});
        const draw = () => {{
          const activeNodes = visibleNodes();
          const activeIds = new Set(activeNodes.map((node) => node.id));
          svg.innerHTML = "";
          const activeEdges = edges.filter((edge) => activeIds.has(edge.source_key) && activeIds.has(edge.target_key));
          activeNodes.forEach((node, index) => {{
            const angle = (Math.PI * 2 * index) / Math.max(activeNodes.length, 1);
            node._x = centerX + Math.cos(angle) * radius;
            node._y = centerY + Math.sin(angle) * radius;
          }});
          activeEdges.forEach((edge) => {{
            const source = activeNodes.find((node) => node.id === edge.source_key);
            const target = activeNodes.find((node) => node.id === edge.target_key);
            if (!source || !target) return;
            const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
            line.setAttribute("x1", source._x);
            line.setAttribute("y1", source._y);
            line.setAttribute("x2", target._x);
            line.setAttribute("y2", target._y);
            line.setAttribute("stroke", "#cbd5e1");
            line.setAttribute("stroke-width", "1.5");
            svg.appendChild(line);
          }});
          activeNodes.forEach((node) => {{
            const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            circle.setAttribute("cx", node._x);
            circle.setAttribute("cy", node._y);
            circle.setAttribute("r", node.type === "module" ? "22" : "16");
            circle.setAttribute("fill", node.type === "module" ? "#dbeafe" : "#e5e7eb");
            circle.setAttribute("stroke", node.staleness_state === "stale" ? "#dc2626" : "#2563eb");
            circle.setAttribute("stroke-width", "2");
            svg.appendChild(circle);
            const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
            text.setAttribute("x", node._x);
            text.setAttribute("y", node._y + 38);
            text.setAttribute("font-size", "11");
            text.setAttribute("text-anchor", "middle");
            text.textContent = node.label.length > 32 ? node.label.slice(0, 29) + "..." : node.label;
            svg.appendChild(text);
          }});
        }};
        document.querySelectorAll("#graph-session-only, #graph-hide-stale, #graph-hide-low").forEach((input) => input.addEventListener("change", draw));
        draw();
        </script>
        """
        page = BASE_TEMPLATE.format(
            title=f"{repo} graph",
            repo=repo,
            sidebar=sidebar,
            body=body,
            footer=f"{repo}/graph",
        )
        path = self.wiki_dir / "repos" / repo / "graph.html"
        self._atomic_write(path, page)
        return path

    def write_overview_page(self, repo: str, md_content: str) -> Path:
        html_content = self._md_to_html(md_content)
        sidebar = self._build_sidebar(repo, current="overview", in_modules=False)
        title = self._extract_title(md_content, repo)
        page = BASE_TEMPLATE.format(
            title=title,
            repo=repo,
            sidebar=sidebar,
            body=html_content,
            footer=f"{repo}/overview",
        )
        html_path = self.wiki_dir / "repos" / repo / "overview.html"
        self._atomic_write(html_path, page)
        return html_path

    def generate_index(self, repo: str) -> Path:
        repo_dir = self.wiki_dir / "repos" / repo
        store = SessionStore(self.wiki_dir)
        recent_sessions = store.get_recent_sessions(repo)
        recent_captures = store.get_recent_captures(repo)
        if not recent_captures:
            recent_captures = self._fallback_captures_from_cache(repo)
        if not recent_sessions:
            recent_sessions = self._fallback_sessions_from_captures(recent_captures)
        trusted = [item for item in recent_captures if item["quality_score"] >= 0.7]
        open_questions = [
            claim.summary
            for recap in [store.build_session_recap(repo, row["id"]) for row in recent_sessions[:1]]
            for claim in recap.related_claims
            if claim.kind == "open_question"
        ] if recent_sessions and store.get_recent_sessions(repo) else []
        body = self._render_index_body(repo, recent_sessions, recent_captures, trusted, open_questions)
        page = BASE_TEMPLATE.format(
            title=f"{repo} home",
            repo=repo,
            sidebar=self._build_sidebar(repo, current="home", in_modules=False),
            body=body,
            footer=f"{repo}/index",
        )
        index_path = repo_dir / "index.html"
        self._atomic_write(index_path, page)
        return index_path

    def _render_index_body(
        self,
        repo: str,
        recent_sessions: list[dict],
        recent_captures: list[dict],
        trusted: list[dict],
        open_questions: list[str],
    ) -> str:
        session_cards = "\n".join(
            self._session_card(repo, session)
            for session in recent_sessions
        ) or '<p class="muted">No sessions yet. Run <code>/wiki-save</code> after a coding conversation.</p>'
        capture_cards = "\n".join(
            self._capture_card(capture)
            for capture in recent_captures
        ) or '<p class="muted">No captures yet.</p>'
        trusted_cards = "\n".join(
            self._capture_card(capture)
            for capture in trusted[:4]
        ) or '<p class="muted">No trusted knowledge yet.</p>'
        open_questions_list = "\n".join(f"<li>{escape(item)}</li>" for item in open_questions[:5]) or "<li>No open questions captured.</li>"
        return f"""
        <section class="hero">
          <h1>Human-visible session memory</h1>
          <p>Review what the AI actually learned in recent coding sessions, filter the noise, and jump into trusted module knowledge.</p>
        </section>
        <section class="filters">
          <div class="filter-card"><label><input type="checkbox" id="filter-session" checked> Session captures only</label><div class="muted">Focus on captures produced during coding sessions.</div></div>
          <div class="filter-card"><label><input type="checkbox" id="filter-low"> Hide low signal</label><div class="muted">Hide captures below the trust threshold.</div></div>
          <div class="filter-card"><label><input type="checkbox" id="filter-provenance"> Only with provenance</label><div class="muted">Only show captures that link back to source files.</div></div>
        </section>
        <h2>Recent Sessions</h2>
        <div class="card-grid">{session_cards}</div>
        <h2>Recent Captures</h2>
        <div class="card-grid" id="capture-grid">{capture_cards}</div>
        <h2>Trusted Knowledge</h2>
        <div class="card-grid">{trusted_cards}</div>
        <h2>Open Questions</h2>
        <div class="card"><ul>{open_questions_list}</ul></div>
        <h2>Graph Preview</h2>
        <div class="card">
          <p>See the lightweight relation view for recent sessions and promoted module knowledge.</p>
          <a href="graph.html">Open session graph</a>
        </div>
        <script>
        const cards = Array.from(document.querySelectorAll("#capture-grid .card"));
        const refreshCards = () => {{
          cards.forEach((card) => {{
            const isSession = card.dataset.captureKind === "session";
            const hasProvenance = card.dataset.hasProvenance === "1";
            const isLowSignal = parseFloat(card.dataset.quality || "0") < 0.6;
            let visible = true;
            if (document.getElementById("filter-session").checked && !isSession) visible = false;
            if (document.getElementById("filter-low").checked && isLowSignal) visible = false;
            if (document.getElementById("filter-provenance").checked && !hasProvenance) visible = false;
            card.style.display = visible ? "block" : "none";
          }});
        }};
        document.querySelectorAll("#filter-session, #filter-low, #filter-provenance").forEach((el) => el.addEventListener("change", refreshCards));
        refreshCards();
        </script>
        """

    def _session_card(self, repo: str, session: dict) -> str:
        href = f"sessions/{escape(session['id'])}.html"
        updated = _format_ts(session["updated_at"])
        return f"""
        <article class="card">
          <p class="eyebrow">Session</p>
          <h3><a href="{href}">{escape(session['title'] or session['id'])}</a></h3>
          <p>{escape(session['summary'] or 'Session recap available.')}</p>
          <span class="badge">{escape(session['id'])}</span>
          <span class="badge">{int(session['capture_count'])} captures</span>
          <p class="muted">Updated {updated}</p>
        </article>
        """

    def _capture_card(self, capture: dict) -> str:
        source_files = capture.get("source_files", [])
        badge_class = "badge low" if capture["quality_score"] < 0.6 else "badge"
        stale_class = "badge stale" if capture["staleness_state"] == "stale" else "badge"
        href = Path(capture["html_path"]).name
        return f"""
        <article class="card" data-capture-kind="session" data-has-provenance="{1 if source_files else 0}" data-quality="{capture['quality_score']}">
          <p class="eyebrow">Module</p>
          <h3><a href="modules/{escape(href)}">{escape(capture['module'])}</a></h3>
          <p>{escape(capture['summary'])}</p>
          <span class="{badge_class}">quality {capture['quality_score']:.2f}</span>
          <span class="{stale_class}">{escape(capture['staleness_state'])}</span>
          <span class="badge">{escape(capture['session_id'])}</span>
          <p class="muted">{len(source_files)} source files · captured {_format_ts(capture['captured_at'])}</p>
        </article>
        """

    def _fallback_captures_from_cache(self, repo: str) -> list[dict]:
        cache_path = self.wiki_dir / ".index" / "cache.json"
        if not cache_path.exists():
            return []
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        captures = []
        for key, entry in data.items():
            if not key.startswith(f"{repo}/"):
                continue
            module = key.split("/", 1)[1]
            html_path = str(Path(entry.get("abs_path", "")).with_suffix(".html")) if entry.get("abs_path") else str(self.wiki_dir / "repos" / repo / "modules" / f"{module}.html")
            captures.append(
                {
                    "session_id": entry.get("session_id", "legacy-session"),
                    "module": module,
                    "title": entry.get("title", module),
                    "summary": entry.get("summary", ""),
                    "html_path": html_path,
                    "captured_at": entry.get("captured_at", entry.get("wiki_generated", 0)),
                    "quality_score": entry.get("quality_score", 0.0),
                    "source_files": entry.get("source_files", []),
                    "staleness_state": entry.get("staleness_state", "unknown"),
                }
            )
        captures.sort(key=lambda item: item["captured_at"], reverse=True)
        return captures[:8]

    def _fallback_sessions_from_captures(self, captures: list[dict]) -> list[dict]:
        sessions: dict[str, dict] = {}
        for capture in captures:
            session = sessions.setdefault(
                capture["session_id"],
                {
                    "id": capture["session_id"],
                    "title": f"Session {capture['session_id']}",
                    "summary": "Recovered from capture metadata.",
                    "updated_at": capture["captured_at"],
                    "capture_count": 0,
                },
            )
            session["capture_count"] += 1
            session["updated_at"] = max(session["updated_at"], capture["captured_at"])
        return list(sessions.values())

    def _render_session_recap(self, recap: SessionRecap) -> str:
        takeaways = "\n".join(f"<li>{escape(item)}</li>" for item in recap.key_takeaways) or "<li>No takeaways yet.</li>"
        decisions = "\n".join(f"<li>{escape(item)}</li>" for item in recap.decisions) or "<li>No explicit decisions captured.</li>"
        gotchas = "\n".join(f"<li>{escape(item)}</li>" for item in recap.gotchas) or "<li>No gotchas captured.</li>"
        questions = "\n".join(f"<li>{escape(item)}</li>" for item in recap.open_questions) or "<li>No open questions captured.</li>"
        modules = "\n".join(f"<span class='badge'>{escape(module)}</span>" for module in recap.modules_touched) or "<span class='badge low'>No modules</span>"
        sources = "\n".join(f"<li><code>{escape(path)}</code></li>" for path in recap.source_files) or "<li>No provenance recorded.</li>"
        meta_cards = f"""
          <div class="meta">
            <div class="meta-card"><p class="eyebrow">Session</p><strong>{escape(recap.session_id)}</strong></div>
            <div class="meta-card"><p class="eyebrow">Modules Touched</p><strong>{len(recap.modules_touched)}</strong></div>
            <div class="meta-card"><p class="eyebrow">Promoted Claims</p><strong>{len(recap.related_claims)}</strong></div>
            <div class="meta-card"><p class="eyebrow">Created</p><strong>{_format_ts(recap.created_at)}</strong></div>
          </div>
        """
        return f"""
        <section class="hero">
          <h1>{escape(recap.title)}</h1>
          <p>{escape(recap.summary)}</p>
        </section>
        {meta_cards}
        <h2>Key Takeaways</h2>
        <div class="card"><ul>{takeaways}</ul></div>
        <h2>Modules Touched</h2>
        <div class="card">{modules}</div>
        <h2>Decisions</h2>
        <div class="card"><ul>{decisions}</ul></div>
        <h2>Gotchas</h2>
        <div class="card"><ul>{gotchas}</ul></div>
        <h2>Open Questions</h2>
        <div class="card"><ul>{questions}</ul></div>
        <h2>Source Files</h2>
        <div class="card"><ul>{sources}</ul></div>
        <h2>Related Graph</h2>
        <div class="card"><a href="../graph.html">Open session graph</a></div>
        """

    def _module_meta(self, entry: CacheEntry | None) -> str:
        if entry is None:
            return ""
        source_list = "".join(f"<li><code>{escape(path)}</code></li>" for path in entry.source_files) or "<li>No source provenance captured.</li>"
        return f"""
        <section class="hero">
          <div class="meta">
            <div class="meta-card"><p class="eyebrow">Capture Kind</p><strong>{escape(entry.capture_kind)}</strong></div>
            <div class="meta-card"><p class="eyebrow">Session</p><strong>{escape(entry.session_id or 'n/a')}</strong></div>
            <div class="meta-card"><p class="eyebrow">Freshness</p><strong>{escape(entry.staleness_state)}</strong></div>
            <div class="meta-card"><p class="eyebrow">Quality</p><strong>{entry.quality_score:.2f}</strong></div>
          </div>
          <div class="card">
            <p class="eyebrow">Source Provenance</p>
            <ul>{source_list}</ul>
          </div>
        </section>
        """

    def _build_sidebar(self, repo: str, current: str = "", *, in_modules: bool = True) -> str:
        repo_dir = self.wiki_dir / "repos" / repo
        sessions_dir = repo_dir / "sessions"
        modules = self._list_modules(repo)
        module_prefix = "" if in_modules else "modules/"
        items = [
            ('index.html', "home", current == "home"),
            ('graph.html', "graph", current == "graph"),
        ]
        if (repo_dir / "overview.html").exists():
            items.append(('overview.html', "overview", current == "overview"))
        links = []
        for href, label, active in items:
            style = ' style="font-weight:bold;color:#2563eb"' if active else ""
            links.append(f'<a href="{href if not in_modules else "../" + href}"{style}>{label}</a>')
        if sessions_dir.exists():
            links.append('<h3>sessions</h3>')
            for page in sorted(sessions_dir.glob("*.html"), reverse=True)[:5]:
                href = f"sessions/{page.name}" if not in_modules else f"../sessions/{page.name}"
                session_id = page.stem
                style = ' style="font-weight:bold;color:#2563eb"' if current == f"session:{session_id}" else ""
                links.append(f'<a href="{href}"{style}>{session_id}</a>')
        links.append('<h3>modules</h3>')
        for module in modules:
            style = ' style="font-weight:bold;color:#2563eb"' if module == current else ""
            href = f"{module}.html" if in_modules else f"{module_prefix}{module}.html"
            links.append(f'<a href="{href}"{style}>{module}</a>')
        return "\n".join(links)

    def _list_modules(self, repo: str) -> list[str]:
        module_dir = self.wiki_dir / "repos" / repo / "modules"
        if not module_dir.exists():
            return []
        return sorted(p.stem for p in module_dir.glob("*.md"))

    def _md_to_html(self, content: str) -> str:
        return md_lib.markdown(
            content,
            extensions=["tables", "fenced_code", "nl2br"],
        )

    def _extract_title(self, content: str, fallback: str) -> str:
        for line in content.splitlines():
            if line.startswith("## "):
                return line[3:].strip()
        return fallback.replace("_", " ").replace("-", " ").title()

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)


def _format_ts(value: float | int | None) -> str:
    if not value:
        return "unknown"
    return datetime.fromtimestamp(float(value)).strftime("%Y-%m-%d %H:%M")
