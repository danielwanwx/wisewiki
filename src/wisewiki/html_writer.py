# src/wisewiki/html_writer.py

import json
import math
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
    .layout.no-nav {{ display: block; }}
    nav {{ width: 250px; background: #fbfbfc; border-right: 1px solid #e5e7eb; padding: 1.4rem 1rem; box-sizing: border-box; }}
    nav h3 {{ margin: 0; }}
    .nav-shell {{ position: sticky; top: 1rem; }}
    .nav-brand {{ margin-bottom: 1.4rem; padding: 0 0.35rem; font-size: 0.95rem; font-weight: 800; letter-spacing: 0.08em; color: #6b7280; text-transform: uppercase; }}
    .nav-group {{ margin-top: 1rem; }}
    .nav-section-title {{ margin: 0 0 0.45rem; padding: 0 0.35rem; font-size: 0.78rem; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; color: #6b7280; }}
    .nav-links {{ display: grid; gap: 0.2rem; }}
    .nav-link {{ display: flex; align-items: center; gap: 0.55rem; min-height: 38px; padding: 0.5rem 0.7rem; border-radius: 10px; color: #374151; text-decoration: none; transition: background 120ms ease, color 120ms ease; }}
    .nav-link::before {{ content: ""; width: 0.5rem; height: 0.5rem; border-radius: 999px; background: #cbd5e1; flex: 0 0 auto; }}
    .nav-link:hover {{ background: #f3f4f6; color: #111827; }}
    .nav-link.is-active {{ background: #eef2ff; color: #2563eb; font-weight: 700; }}
    .nav-link.is-active::before {{ background: #2563eb; }}
    .nav-link-home::before {{ background: #94a3b8; }}
    .nav-link-graph::before {{ background: #a78bfa; }}
    .nav-link-session::before {{ background: #60a5fa; }}
    .nav-link-module::before {{ background: #86efac; }}
    main {{ flex: 1; padding: 2rem; max-width: 980px; }}
    main.main-full {{ max-width: 1280px; margin: 0 auto; padding: 2.5rem 2rem 4rem; }}
    h1, h2, h3 {{ color: #111827; }}
    h2 {{ margin-top: 2rem; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.35rem; }}
    .hero {{ margin-bottom: 1.5rem; }}
    .hero p {{ color: #4b5563; line-height: 1.6; }}
    .meta, .filters, .card-grid {{ display: grid; gap: 0.75rem; }}
    .meta {{ grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); margin: 1rem 0 1.5rem; }}
    .meta-card, .card, .filter-card, .graph-shell {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 1rem; }}
    .card-grid {{ grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }}
    .hero-panel {{ background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%); border: 1px solid #e5e7eb; border-radius: 16px; padding: 1.4rem; }}
    .hero-panel h1 {{ margin-top: 0; margin-bottom: 0.75rem; font-size: 2.2rem; line-height: 1.1; }}
    .hero-panel.compact h1 {{ font-size: 1.75rem; }}
    .dashboard-grid {{ display: grid; gap: 1rem; grid-template-columns: minmax(0, 1.45fr) minmax(280px, 0.9fr); align-items: start; }}
    .dashboard-side {{ display: grid; gap: 0.75rem; }}
    .insight-stack {{ display: grid; gap: 0.65rem; }}
    .insight-mini {{ padding: 0.8rem 0.95rem; border-radius: 12px; background: #fff; border: 1px solid #e5e7eb; }}
    .insight-mini strong {{ display: block; margin-bottom: 0.3rem; }}
    .insight-list {{ display: grid; gap: 0.75rem; margin-top: 1rem; }}
    .insight-item {{ display: grid; grid-template-columns: 28px minmax(0, 1fr); gap: 0.75rem; align-items: start; padding: 0.9rem 1rem; border-radius: 12px; background: #fff; border: 1px solid #e5e7eb; }}
    .insight-rank {{ display: grid; place-items: center; width: 28px; height: 28px; border-radius: 999px; background: #111827; color: #fff; font-size: 0.8rem; font-weight: 700; }}
    .split-grid {{ display: grid; gap: 0.75rem; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }}
    .compare-card {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 1rem; }}
    .compare-card.before {{ border-color: #fecaca; background: #fffafa; }}
    .compare-card.after {{ border-color: #bfdbfe; background: #f8fbff; }}
    .signal-strip {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 1rem; }}
    .signal-pill {{ display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.35rem 0.65rem; border-radius: 999px; background: #eef2ff; color: #3730a3; font-size: 0.78rem; font-weight: 600; }}
    .kind-filter-list {{ display: flex; flex-wrap: wrap; gap: 0.45rem; margin-top: 0.75rem; }}
    .kind-filter {{ display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.35rem 0.6rem; border-radius: 999px; background: #0b1020; border: 1px solid #1f2937; color: #e5eefc; font-size: 0.75rem; }}
    .kind-filter input {{ accent-color: #60a5fa; }}
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
    .graph-shell {{ display: grid; gap: 1rem; }}
    .graph-shell-dark {{ grid-template-columns: minmax(0, 1fr) 280px; background: #0f172a; border-color: #1e293b; }}
    .graph-toolbar {{ display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center; margin-bottom: 1rem; }}
    .graph-toolbar input[type="search"] {{ flex: 1 1 240px; padding: 0.65rem 0.8rem; border-radius: 8px; border: 1px solid #334155; background: #0b1020; color: #e5eefc; }}
    .graph-toolbar button {{ padding: 0.65rem 0.9rem; border-radius: 8px; border: 1px solid #334155; background: #111827; color: #e5eefc; cursor: pointer; }}
    .graph-toolbar .filter-card {{ background: #111827; border-color: #1f2937; color: #e5eefc; min-width: 180px; }}
    .graph-stage {{ position: relative; min-height: 620px; border-radius: 12px; overflow: hidden; background:
      radial-gradient(circle at top, rgba(59, 130, 246, 0.14), transparent 34%),
      radial-gradient(circle at 20% 80%, rgba(168, 85, 247, 0.18), transparent 26%),
      linear-gradient(180deg, #0b1020 0%, #111827 100%); }}
    #graph-canvas {{ width: 100%; height: 620px; display: block; cursor: grab; }}
    .graph-shell-dark aside {{ background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 1rem; color: #e5eefc; }}
    .graph-shell-dark h3, .graph-shell-dark p, .graph-shell-dark li, .graph-shell-dark strong {{ color: #e5eefc; }}
    .graph-shell-dark .muted {{ color: #94a3b8; }}
    #graph-details p {{ margin: 0.45rem 0; }}
    .graph-detail-copy {{ font-size: 0.92rem; line-height: 1.55; color: #cbd5e1; }}
    .graph-detail-links {{ display: flex; flex-direction: column; gap: 0.45rem; margin-top: 0.8rem; }}
    .graph-detail-links a {{ color: #93c5fd; font-size: 0.88rem; text-decoration: none; }}
    .graph-detail-links a:hover {{ text-decoration: underline; }}
    .graph-legend {{ display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 0.8rem; }}
    .legend-dot {{ display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.2rem 0.5rem; border-radius: 999px; background: #0b1020; border: 1px solid #1f2937; font-size: 0.75rem; }}
    .legend-dot::before {{ content: ""; width: 0.65rem; height: 0.65rem; border-radius: 999px; background: var(--dot); }}
    .graph-empty {{ position: absolute; inset: 0; display: grid; place-items: center; color: #cbd5e1; font-size: 0.95rem; pointer-events: none; }}
    .graph-empty[hidden] {{ display: none; }}
    .knowledge-grid {{ display: grid; gap: 0.75rem; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); margin-top: 1rem; }}
    .claim-card {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 1rem; }}
    .claim-card p {{ margin: 0.35rem 0; }}
    .session-mini-list {{ display: grid; gap: 0.6rem; }}
    .session-mini {{ padding: 0.8rem; border-radius: 8px; background: #f8fafc; border: 1px solid #e5e7eb; }}
    .catalog-hero {{ margin: 0 0 2.2rem; max-width: none; }}
    .catalog-hero h1 {{ margin: 0 0 0.9rem; font-size: clamp(2.6rem, 6vw, 4.5rem); line-height: 0.98; letter-spacing: -0.03em; }}
    .catalog-hero p {{ margin: 0; font-size: 1.15rem; color: #4b5563; line-height: 1.6; }}
    .catalog-grid {{ display: grid; gap: 1rem; grid-template-columns: 1.4fr 1fr; margin-top: 2rem; }}
    .catalog-stack {{ display: grid; gap: 1rem; }}
    .catalog-card {{ display: block; padding: 1.5rem; border-radius: 24px; background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%); border: 1px solid #e5e7eb; text-decoration: none; color: inherit; min-height: 220px; box-shadow: 0 1px 0 rgba(15, 23, 42, 0.02); transition: transform 120ms ease, box-shadow 120ms ease, border-color 120ms ease; }}
    .catalog-card:hover {{ transform: translateY(-2px); box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08); border-color: #dbe3f0; }}
    .catalog-card.featured {{ min-height: 460px; display: flex; flex-direction: column; justify-content: space-between; }}
    .catalog-card.featured.is-clickable {{ cursor: pointer; }}
    .catalog-card h2, .catalog-card h3 {{ margin: 0; border: 0; padding: 0; }}
    .catalog-card h2 {{ font-size: clamp(2rem, 4vw, 3rem); line-height: 1.04; letter-spacing: -0.03em; max-width: 12ch; }}
    .catalog-card h3 {{ font-size: 1.45rem; line-height: 1.15; letter-spacing: -0.02em; max-width: 14ch; }}
    .catalog-card p {{ margin: 0.5rem 0 0; color: #4b5563; line-height: 1.5; max-width: 34ch; }}
    .catalog-meta {{ color: #6b7280; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; }}
    .catalog-footer {{ display: flex; justify-content: space-between; align-items: end; gap: 1rem; margin-top: 1.3rem; }}
    .catalog-stat {{ font-size: 0.95rem; color: #111827; font-weight: 600; }}
    .catalog-pills {{ display: flex; flex-wrap: wrap; gap: 0.45rem; margin-top: 1rem; }}
    .catalog-pill {{ display: inline-flex; align-items: center; padding: 0.35rem 0.65rem; border-radius: 999px; background: #fff; border: 1px solid #e5e7eb; color: #374151; font-size: 0.82rem; }}
    .home-graph-preview {{ position: relative; margin-top: 1.4rem; min-height: 260px; border-radius: 20px; overflow: hidden; border: 1px solid #e5e7eb; background: linear-gradient(180deg, #071226 0%, #0f172a 100%); }}
    .home-graph-preview svg {{ width: 100%; height: 100%; display: block; }}
    .home-graph-edge {{ stroke: rgba(148, 163, 184, 0.28); stroke-width: 1.2; }}
    .home-graph-node {{ cursor: grab; }}
    .home-graph-node circle {{ stroke: rgba(226, 232, 240, 0.85); stroke-width: 1.2; }}
    .home-graph-node text {{ fill: #e2e8f0; font-size: 11px; font-weight: 600; paint-order: stroke; stroke: rgba(15, 23, 42, 0.92); stroke-width: 3px; pointer-events: none; }}
    .catalog-actions {{ display: flex; justify-content: space-between; align-items: end; gap: 1rem; margin-top: 1.3rem; }}
    .catalog-action-link {{ color: #111827; font-size: 0.95rem; font-weight: 600; text-decoration: none; }}
    .catalog-action-link:hover {{ text-decoration: underline; }}
    .home-strip {{ margin-top: 2.4rem; }}
    .strip-row {{ display: grid; gap: 0.8rem; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }}
    .strip-card {{ padding: 1rem 1.1rem; border-radius: 16px; background: #fff; border: 1px solid #e5e7eb; text-decoration: none; color: inherit; }}
    .strip-card strong {{ display: block; font-size: 1rem; line-height: 1.25; }}
    .strip-card p {{ margin: 0.35rem 0 0; color: #6b7280; font-size: 0.92rem; }}
    @media (max-width: 960px) {{
      .catalog-grid {{ grid-template-columns: 1fr; }}
      .catalog-card.featured {{ min-height: 340px; }}
    }}
    .footer {{ margin-top: 2rem; color: #6b7280; font-size: 0.82rem; }}
  </style>
</head>
<body>
  <div class="layout{layout_class}">
    {nav_html}
    <main class="{main_class}">
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

    def _render_page(
        self,
        *,
        title: str,
        repo: str,
        body: str,
        footer: str,
        sidebar: str | None = None,
        main_class: str = "",
        layout_class: str = "",
    ) -> str:
        nav_html = ""
        if sidebar is not None:
            nav_html = f"<nav>{sidebar}</nav>"
        return BASE_TEMPLATE.format(
            title=title,
            repo=repo,
            nav_html=nav_html,
            main_class=main_class,
            layout_class=layout_class,
            body=body,
            footer=footer,
        )

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
        sidebar = self._build_sidebar(repo, current=module, location="modules")
        title = self._extract_title(md_content, module)
        meta_html = self._module_meta(entry)
        knowledge_html = self._module_knowledge_panels(repo, module)
        body = f"{meta_html}{knowledge_html}{html_content}"
        page = self._render_page(
            title=title,
            repo=repo,
            sidebar=sidebar,
            body=body,
            footer=f"{repo}/{module}",
        )
        html_path = md_path.with_suffix(".html")
        self._atomic_write(html_path, page)
        return html_path

    def rebuild_repo(self, repo: str) -> None:
        repo_dir = self.wiki_dir / "repos" / repo
        module_dir = repo_dir / "modules"
        store = SessionStore(self.wiki_dir)
        cache_data = self._load_cache_data()

        for md_path in sorted(module_dir.glob("*.md")) if module_dir.exists() else []:
            entry_dict = cache_data.get(f"{repo}/{md_path.stem}")
            entry = CacheEntry.from_dict(entry_dict) if entry_dict else None
            self.write_module_page(
                repo,
                md_path.stem,
                md_path.read_text(encoding="utf-8"),
                md_path,
                entry=entry,
            )

        session_rows = store.get_recent_sessions(repo, limit=1000)
        for row in session_rows:
            self.write_session_page(repo, store.build_session_recap(repo, row["id"]))

        graph_data = store.get_graph_data(repo)
        self.write_graph_data(repo, graph_data)
        self.write_graph_page(repo, graph_data)
        self.generate_index(repo)

    def write_session_page(self, repo: str, recap: SessionRecap) -> Path:
        session_dir = self.wiki_dir / "repos" / repo / "sessions"
        session_dir.mkdir(parents=True, exist_ok=True)
        body = self._render_session_recap(recap)
        page = self._render_page(
            title=recap.title,
            repo=repo,
            sidebar=self._build_sidebar(repo, current=f"session:{recap.session_id}", location="sessions"),
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
        sidebar = self._build_sidebar(repo, current="graph", location="root")
        nodes_json = self._json_for_script(graph_data.get("nodes", []))
        edges_json = self._json_for_script(graph_data.get("edges", []))
        nodes = graph_data.get("nodes", [])
        kind_counts: dict[str, int] = {}
        for node in nodes:
            kind = str(node.get("type", "default"))
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
        kind_filters = "\n".join(
            f'<label class="kind-filter"><input type="checkbox" class="graph-kind-filter" value="{escape(kind)}" checked> {escape(kind.replace("_", " "))} ({count})</label>'
            for kind, count in sorted(kind_counts.items())
        )
        body = f"""
        <section class="hero">
          <h1>Session Graph</h1>
          <p>obsidian-style knowledge graph for recent modules and distilled session claims.</p>
        </section>
        <div class="graph-toolbar">
          <input type="search" id="graph-search" placeholder="Search modules or claims">
          <button type="button" id="graph-reset">Reset view</button>
        </div>
        <p class="muted" id="graph-filter-summary">Showing {len(nodes)} of {len(nodes)} nodes.</p>
        <section class="graph-shell graph-shell-dark">
          <div class="graph-stage" id="graph-stage">
            <canvas id="graph-canvas"></canvas>
            <div class="graph-empty" id="graph-empty" hidden>No visible nodes for the current filters.</div>
          </div>
          <aside>
            <div class="graph-legend">
              <span class="legend-dot" style="--dot:#7dd3fc">module</span>
              <span class="legend-dot" style="--dot:#a78bfa">decision</span>
              <span class="legend-dot" style="--dot:#86efac">architecture</span>
              <span class="legend-dot" style="--dot:#fca5a5">gotcha</span>
              <span class="legend-dot" style="--dot:#fcd34d">open question</span>
            </div>
            <p class="eyebrow">Kind Filters</p>
            <div class="kind-filter-list">{kind_filters}</div>
            <h3>Selection</h3>
            <div id="graph-details">
              <p class="graph-detail-copy">Select a node to see what it represents, why it matters in this graph, and where to open the related page.</p>
            </div>
          </aside>
        </section>
        <script id="graph-nodes-data" type="application/json">{nodes_json}</script>
        <script id="graph-edges-data" type="application/json">{edges_json}</script>
        <script>
        const nodes = JSON.parse(document.getElementById("graph-nodes-data").textContent);
        const edges = JSON.parse(document.getElementById("graph-edges-data").textContent);
        const stage = document.getElementById("graph-stage");
        const canvas = document.getElementById("graph-canvas");
        const empty = document.getElementById("graph-empty");
        const details = document.getElementById("graph-details");
        const searchInput = document.getElementById("graph-search");
        const filterSummary = document.getElementById("graph-filter-summary");
        const kindFilterInputs = Array.from(document.querySelectorAll(".graph-kind-filter"));
        const ctx = canvas.getContext("2d");
        const palette = {{
          module: "#7dd3fc",
          decision: "#a78bfa",
          architecture: "#86efac",
          gotcha: "#fca5a5",
          open_question: "#fcd34d",
          debug_outcome: "#c4b5fd",
          default: "#94a3b8",
        }};
        const state = {{
          width: 0,
          height: 0,
          scale: 1,
          offsetX: 0,
          offsetY: 0,
          hovered: null,
          selected: null,
          draggingNode: null,
          panning: false,
          lastX: 0,
          lastY: 0,
        }};

        nodes.forEach((node, index) => {{
          const angle = (Math.PI * 2 * index) / Math.max(nodes.length, 1);
          const ring = 120 + (index % 5) * 28;
          node.x = Math.cos(angle) * ring;
          node.y = Math.sin(angle) * ring;
          node.vx = 0;
          node.vy = 0;
          node.radius = node.type === "module" ? 12 + (node.confidence || 0) * 8 : 6 + (node.confidence || 0) * 6;
          node.labelShort = node.label.length > 42 ? node.label.slice(0, 39) + "..." : node.label;
        }});

        const resizeCanvas = () => {{
          const rect = stage.getBoundingClientRect();
          const ratio = window.devicePixelRatio || 1;
          state.width = Math.max(640, Math.floor(rect.width));
          state.height = Math.max(620, Math.floor(rect.height));
          canvas.width = state.width * ratio;
          canvas.height = state.height * ratio;
          canvas.style.width = state.width + "px";
          canvas.style.height = state.height + "px";
          ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
          if (!state.offsetX && !state.offsetY) {{
            state.offsetX = state.width / 2;
            state.offsetY = state.height / 2;
          }}
        }};

        const visibleNodes = () => nodes.filter((node) => {{
          const query = searchInput.value.trim().toLowerCase();
          const enabledKinds = new Set(kindFilterInputs.filter((input) => input.checked).map((input) => input.value));
          if (!enabledKinds.has(node.type)) return false;
          if (query && !node.label.toLowerCase().includes(query)) return false;
          return true;
        }});

        const activeGraph = () => {{
          const activeNodes = visibleNodes();
          const activeIds = new Set(activeNodes.map((node) => node.id));
          const activeEdges = edges.filter((edge) => activeIds.has(edge.source_key) && activeIds.has(edge.target_key));
          return {{ activeNodes, activeEdges }};
        }};

        const worldToScreen = (x, y) => ({{
          x: x * state.scale + state.offsetX,
          y: y * state.scale + state.offsetY,
        }});

        const screenToWorld = (x, y) => ({{
          x: (x - state.offsetX) / state.scale,
          y: (y - state.offsetY) / state.scale,
        }});

        const getNodeAt = (screenX, screenY) => {{
          const point = screenToWorld(screenX, screenY);
          const {{ activeNodes }} = activeGraph();
          for (let i = activeNodes.length - 1; i >= 0; i -= 1) {{
            const node = activeNodes[i];
            const dx = point.x - node.x;
            const dy = point.y - node.y;
            if (Math.hypot(dx, dy) <= node.radius + 6 / state.scale) {{
              return node;
            }}
          }}
          return null;
        }};

        const updateDetails = (node) => {{
          if (!node) {{
            details.innerHTML = `
              <p class="graph-detail-copy">Select a node to see what it represents, why it matters in this graph, and where to open the related page.</p>
            `;
            return;
          }}
          const trust = (node.confidence || 0).toFixed(2);
          details.innerHTML = `
            <p class="eyebrow">${{node.type.replace("_", " ")}}</p>
            <h3>${{node.label}}</h3>
            <p class="graph-detail-copy">${{nodeExplanation(node)}}</p>
            <p class="graph-detail-copy"><strong>Trust:</strong> ${{trust}} · <strong>Session:</strong> ${{node.session_id || "unknown"}} · <strong>Freshness:</strong> ${{node.staleness_state || "unknown"}}</p>
            <div class="graph-detail-links">${{nodeLinks(node)}}</div>
          `;
        }};

        const drawLabel = (node, screenX, screenY) => {{
          const label = node.labelShort;
          ctx.font = "12px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
          const width = ctx.measureText(label).width + 16;
          const x = screenX - width / 2;
          const y = screenY + node.radius * state.scale + 12;
          ctx.fillStyle = "rgba(15, 23, 42, 0.92)";
          ctx.strokeStyle = "rgba(148, 163, 184, 0.45)";
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.roundRect(x, y, width, 24, 12);
          ctx.fill();
          ctx.stroke();
          ctx.fillStyle = "#e5eefc";
          ctx.fillText(label, x + 8, y + 16);
        }};

        const nodeExplanation = (node) => {{
          if (node.type === "module") {{
            return "Module node representing a distilled page in Wisewiki. Connected claim nodes are reusable insights attached to this module.";
          }}
          return "Distilled claim from this session. It captures a reusable insight connected back to a module page and its originating session recap.";
        }};

        const nodeLinks = (node) => {{
          const links = [];
          const moduleName = node.module || (node.type === "module" ? node.label : "");
          if (moduleName) {{
            links.push(`<a href="modules/${{moduleName}}.html">Open module page</a>`);
          }}
          if (node.session_id) {{
            links.push(`<a href="sessions/${{node.session_id}}.html">Open session recap</a>`);
          }}
          return links.join("");
        }};

        const stepLayout = () => {{
          const {{ activeNodes, activeEdges }} = activeGraph();
          const visibleIds = new Set(activeNodes.map((node) => node.id));
          for (const node of nodes) {{
            if (!visibleIds.has(node.id)) continue;
            node.vx *= 0.92;
            node.vy *= 0.92;
          }}
          for (let i = 0; i < activeNodes.length; i += 1) {{
            const a = activeNodes[i];
            for (let j = i + 1; j < activeNodes.length; j += 1) {{
              const b = activeNodes[j];
              let dx = b.x - a.x;
              let dy = b.y - a.y;
              let dist = Math.hypot(dx, dy) || 0.001;
              const repel = 2200 / (dist * dist);
              dx /= dist;
              dy /= dist;
              a.vx -= dx * repel;
              a.vy -= dy * repel;
              b.vx += dx * repel;
              b.vy += dy * repel;
            }}
          }}
          for (const edge of activeEdges) {{
            const source = activeNodes.find((node) => node.id === edge.source_key);
            const target = activeNodes.find((node) => node.id === edge.target_key);
            if (!source || !target) continue;
            let dx = target.x - source.x;
            let dy = target.y - source.y;
            const dist = Math.hypot(dx, dy) || 0.001;
            const targetDistance = edge.edge_type === "claim_support" ? 90 : 150;
            const spring = (dist - targetDistance) * 0.0025 * (edge.weight || 1);
            dx /= dist;
            dy /= dist;
            source.vx += dx * spring;
            source.vy += dy * spring;
            target.vx -= dx * spring;
            target.vy -= dy * spring;
          }}
          for (const node of activeNodes) {{
            if (state.draggingNode && state.draggingNode.id === node.id) continue;
            node.vx += (-node.x) * 0.0018;
            node.vy += (-node.y) * 0.0018;
            node.x += node.vx;
            node.y += node.vy;
          }}
          return {{ activeNodes, activeEdges }};
        }};

        const render = () => {{
          const {{ activeNodes, activeEdges }} = stepLayout();
          ctx.clearRect(0, 0, state.width, state.height);
          ctx.fillStyle = "#0b1020";
          ctx.fillRect(0, 0, state.width, state.height);
          empty.hidden = activeNodes.length > 0;
          filterSummary.textContent = `Showing ${{activeNodes.length}} of ${{nodes.length}} nodes.`;
          if (!activeNodes.length) return;

          for (const edge of activeEdges) {{
            const source = activeNodes.find((node) => node.id === edge.source_key);
            const target = activeNodes.find((node) => node.id === edge.target_key);
            if (!source || !target) continue;
            const start = worldToScreen(source.x, source.y);
            const end = worldToScreen(target.x, target.y);
            ctx.strokeStyle = edge.edge_type === "claim_support"
              ? "rgba(125, 211, 252, 0.24)"
              : "rgba(148, 163, 184, 0.18)";
            ctx.lineWidth = edge.edge_type === "claim_support" ? 1.4 : 1.0;
            ctx.beginPath();
            ctx.moveTo(start.x, start.y);
            ctx.lineTo(end.x, end.y);
            ctx.stroke();
          }}

          for (const node of activeNodes) {{
            const point = worldToScreen(node.x, node.y);
            const radius = Math.max(4, node.radius * state.scale);
            ctx.beginPath();
            ctx.fillStyle = palette[node.type] || palette.default;
            ctx.globalAlpha = 0.92;
            ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
            ctx.fill();
            ctx.globalAlpha = 1;
            ctx.lineWidth = state.selected && state.selected.id === node.id ? 2.8 : 1.2;
            ctx.strokeStyle = node.staleness_state === "stale" ? "#f87171" : "rgba(226, 232, 240, 0.8)";
            ctx.stroke();
            if (node.type === "module") {{
              ctx.fillStyle = "#dbeafe";
              ctx.font = "12px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
              ctx.fillText(node.labelShort, point.x + radius + 8, point.y + 4);
            }}
          }}

          if (state.hovered) {{
            const hoveredPoint = worldToScreen(state.hovered.x, state.hovered.y);
            drawLabel(state.hovered, hoveredPoint.x, hoveredPoint.y);
          }} else if (state.selected) {{
            const selectedPoint = worldToScreen(state.selected.x, state.selected.y);
            drawLabel(state.selected, selectedPoint.x, selectedPoint.y);
          }}
        }};

        const loop = () => {{
          render();
          window.requestAnimationFrame(loop);
        }};

        const pointerPosition = (event) => {{
          const rect = canvas.getBoundingClientRect();
          return {{
            x: event.clientX - rect.left,
            y: event.clientY - rect.top,
          }};
        }};

        canvas.addEventListener("mousedown", (event) => {{
          const point = pointerPosition(event);
          const hit = getNodeAt(point.x, point.y);
          state.lastX = point.x;
          state.lastY = point.y;
          if (hit) {{
            state.draggingNode = hit;
            state.selected = hit;
            updateDetails(hit);
            canvas.style.cursor = "grabbing";
          }} else {{
            state.panning = true;
            canvas.style.cursor = "grabbing";
          }}
        }});

        canvas.addEventListener("mousemove", (event) => {{
          const point = pointerPosition(event);
          if (state.draggingNode) {{
            const world = screenToWorld(point.x, point.y);
            state.draggingNode.x = world.x;
            state.draggingNode.y = world.y;
            state.draggingNode.vx = 0;
            state.draggingNode.vy = 0;
          }} else if (state.panning) {{
            state.offsetX += point.x - state.lastX;
            state.offsetY += point.y - state.lastY;
          }} else {{
            state.hovered = getNodeAt(point.x, point.y);
            updateDetails(state.hovered || state.selected);
            canvas.style.cursor = state.hovered ? "pointer" : "grab";
          }}
          state.lastX = point.x;
          state.lastY = point.y;
        }});

        const releasePointer = () => {{
          state.draggingNode = null;
          state.panning = false;
          canvas.style.cursor = state.hovered ? "pointer" : "grab";
        }};
        canvas.addEventListener("mouseup", releasePointer);
        canvas.addEventListener("mouseleave", releasePointer);

        canvas.addEventListener("wheel", (event) => {{
          event.preventDefault();
          const point = pointerPosition(event);
          const before = screenToWorld(point.x, point.y);
          const zoomFactor = event.deltaY < 0 ? 1.08 : 0.92;
          state.scale = Math.max(0.45, Math.min(2.8, state.scale * zoomFactor));
          state.offsetX = point.x - before.x * state.scale;
          state.offsetY = point.y - before.y * state.scale;
        }}, {{ passive: false }});

        document.getElementById("graph-reset").addEventListener("click", () => {{
          state.scale = 1;
          state.offsetX = state.width / 2;
          state.offsetY = state.height / 2;
        }});

        kindFilterInputs.forEach((input) => input.addEventListener("change", () => {{
          state.hovered = null;
          updateDetails(state.selected);
        }}));
        searchInput.addEventListener("input", () => {{
          state.hovered = null;
          updateDetails(state.selected);
        }});

        window.addEventListener("resize", resizeCanvas);
        resizeCanvas();
        updateDetails(null);
        loop();
        </script>
        """
        page = self._render_page(
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
        sidebar = self._build_sidebar(repo, current="overview", location="root")
        title = self._extract_title(md_content, repo)
        page = self._render_page(
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
        latest_recap = None
        if recent_sessions and store.get_recent_sessions(repo):
            latest_recap = store.build_session_recap(repo, recent_sessions[0]["id"])
        elif recent_captures:
            latest_recap = self._fallback_latest_recap(repo, recent_captures)
        graph_data = store.get_graph_data(repo) if store.get_recent_sessions(repo) else self._fallback_graph_data(recent_captures)
        body = self._render_index_body(repo, recent_sessions, recent_captures, trusted, open_questions, latest_recap, graph_data)
        page = self._render_page(
            title=f"{repo} home",
            repo=repo,
            sidebar=None,
            main_class="main-full",
            layout_class=" no-nav",
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
        latest_recap: SessionRecap | None,
        graph_data: dict,
    ) -> str:
        latest_session_panel = self._home_featured_card(latest_recap, graph_data)
        modules_card = self._home_modules_card(recent_captures)
        questions_card = self._home_questions_card(open_questions, latest_recap)
        recent_strip = self._home_recent_sessions_strip(recent_sessions)
        return f"""
        <section class="catalog-hero">
          <p class="eyebrow">Wisewiki 1.0</p>
          <h1>Your AI Session Wiki</h1>
          <p>Wisewiki turns useful AI conversations into clear session recaps, linked module pages, and a graph you can revisit later.</p>
        </section>
        <section class="catalog-grid">
          {latest_session_panel}
          <div class="catalog-stack">
            {modules_card}
            {questions_card}
          </div>
        </section>
        <section class="home-strip">
          <h2>Recent Sessions</h2>
          <div class="strip-row">{recent_strip}</div>
        </section>
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

    def _home_featured_card(self, recap: SessionRecap | None, graph_data: dict) -> str:
        if recap is None:
            return """
            <div class="catalog-card featured">
              <div>
                <div class="catalog-meta">Latest Session</div>
                <h2>No session memory yet.</h2>
                <p>Capture one conversation to turn this front page into a clean, clickable knowledge catalog.</p>
              </div>
            </div>
            """
        title = recap.title or f"Session {recap.session_id}"
        kicker = title if len(title) < 80 else title[:77] + "..."
        graph_preview = self._home_graph_preview(graph_data)
        session_href = f"sessions/{escape(recap.session_id)}.html"
        return f"""
        <article class="catalog-card featured is-clickable" data-card-href="{session_href}">
          <div>
            <div class="catalog-meta">Latest Session</div>
            <h2>{escape(kicker)}</h2>
            <p>Open the newest distilled recap and continue from the clearest version of what this session figured out.</p>
            <div class="home-graph-preview">{graph_preview}</div>
          </div>
          <script>
          (() => {{
            const card = document.currentScript.closest(".catalog-card.featured");
            if (!card || card.dataset.cardBound === "1") return;
            card.dataset.cardBound = "1";
            card.addEventListener("click", (event) => {{
              if (event.target.closest("a")) return;
              if (event.target.closest(".home-graph-preview")) return;
              if (card.dataset.cardHref) window.location.href = card.dataset.cardHref;
            }});
          }})();
          </script>
        </article>
        """

    def _home_modules_card(self, captures: list[dict]) -> str:
        top_modules = [capture["module"] for capture in captures[:3]]
        href = f"modules/{escape(captures[0]['module'])}.html" if captures else "graph.html"
        pills = "".join(
            f"<a class='catalog-pill' href='modules/{escape(module)}.html'>{escape(module)}</a>"
            for module in top_modules
        ) or "<span class='catalog-pill'>No modules yet</span>"
        return f"""
        <article class="catalog-card is-clickable" data-card-href="{href}">
          <div>
            <div class="catalog-meta">Trusted Modules</div>
            <h3>Jump into the modules worth revisiting.</h3>
            <p>Start from the most credible module pages instead of browsing the whole repository tree.</p>
            <div class="catalog-pills">{pills}</div>
          </div>
          <script>
          (() => {{
            const card = document.currentScript.closest(".catalog-card");
            if (!card || card.dataset.cardBound === "1") return;
            card.dataset.cardBound = "1";
            card.addEventListener("click", (event) => {{
              if (event.target.closest("a")) return;
              if (card.dataset.cardHref) window.location.href = card.dataset.cardHref;
            }});
          }})();
          </script>
        </article>
        """

    def _home_questions_card(self, open_questions: list[str], recap: SessionRecap | None) -> str:
        href = f"sessions/{escape(recap.session_id)}.html" if recap is not None else "graph.html"
        description = "Review what is still unresolved before you dive deeper." if open_questions else "Nothing urgent is unresolved right now; use this as a quick confidence check."
        return f"""
        <a class="catalog-card" href="{href}">
          <div>
            <div class="catalog-meta">Open Questions</div>
            <h3>Know what still needs attention.</h3>
            <p>{escape(description)}</p>
          </div>
        </a>
        """

    def _home_recent_sessions_strip(self, recent_sessions: list[dict]) -> str:
        if not recent_sessions:
            return '<div class="strip-card"><strong>No recent sessions.</strong><p>Capture one to get started.</p></div>'
        cards = []
        for session in recent_sessions[:4]:
            cards.append(
                f"""
                <a class="strip-card" href="sessions/{escape(session['id'])}.html">
                  <div class="catalog-meta">Session</div>
                  <strong>{escape(session['title'] or session['id'])}</strong>
                  <p>{escape(session['summary'] or 'Open the recap.')}</p>
                </a>
                """
            )
        return "\n".join(cards)

    def _capture_card(self, capture: dict) -> str:
        source_files = capture.get("source_files", [])
        badge_class = "badge low" if capture["quality_score"] < 0.6 else "badge"
        stale_class = "badge stale" if capture["staleness_state"] == "stale" else "badge"
        href = Path(capture["html_path"]).name
        capture_kind = capture.get("capture_kind", "session")
        return f"""
        <article class="card" data-capture-kind="{escape(capture_kind)}" data-has-provenance="{1 if source_files else 0}" data-quality="{capture['quality_score']}">
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
                    "capture_kind": entry.get("capture_kind", "session"),
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

    def _fallback_latest_recap(self, repo: str, captures: list[dict]) -> SessionRecap | None:
        if not captures:
            return None
        primary = captures[0]
        takeaways = [capture["summary"] for capture in captures[:3] if capture.get("summary")]
        modules = [capture["module"] for capture in captures[:3]]
        source_files: list[str] = []
        for capture in captures[:3]:
            for path in capture.get("source_files", []):
                if path not in source_files:
                    source_files.append(path)
        return SessionRecap(
            session_id=primary.get("session_id", "legacy-session"),
            repo=repo,
            title=f"Recovered session for {primary.get('module', repo)}",
            summary=primary.get("summary", "Recovered latest session memory."),
            key_takeaways=takeaways,
            modules_touched=modules,
            source_files=source_files,
            created_at=primary.get("captured_at", 0),
        )

    def _fallback_graph_data(self, captures: list[dict]) -> dict:
        nodes = []
        for capture in captures[:6]:
            nodes.append(
                {
                    "id": f"module:{capture['module']}",
                    "label": capture["module"],
                    "type": "module",
                    "module": capture["module"],
                    "session_id": capture.get("session_id", "legacy-session"),
                    "confidence": capture.get("quality_score", 0.0),
                    "staleness_state": capture.get("staleness_state", "unknown"),
                }
            )
        edges = []
        for idx in range(max(0, len(nodes) - 1)):
            edges.append(
                {
                    "source_key": nodes[idx]["id"],
                    "target_key": nodes[idx + 1]["id"],
                    "edge_type": "same_session",
                    "weight": 1.0,
                }
            )
        return {"nodes": nodes, "edges": edges}

    def _home_graph_preview(self, graph_data: dict) -> str:
        nodes = graph_data.get("nodes", [])[:8]
        if not nodes:
            return (
                '<svg id="home-graph-preview-svg" data-graph-href="graph.html" viewBox="0 0 520 260" aria-label="Graph preview">'
                '<rect width="520" height="260" fill="#0f172a" />'
                "</svg>"
            )
        preview_nodes = []
        for index, node in enumerate(nodes):
            angle = (2 * math.pi * index) / max(len(nodes), 1)
            ring = 64 + (index % 3) * 28
            preview_nodes.append(
                {
                    "id": node["id"],
                    "label": str(node.get("label", node["id"]))[:28],
                    "type": node.get("type", "module"),
                    "x": round(260 + (ring * math.cos(angle)), 1),
                    "y": round(130 + (ring * math.sin(angle)), 1),
                    "r": 16 if node.get("type") == "module" else 10,
                    "fill": {
                        "module": "#7dd3fc",
                        "decision": "#a78bfa",
                        "architecture": "#86efac",
                        "gotcha": "#fca5a5",
                        "open_question": "#fcd34d",
                    }.get(str(node.get("type")), "#94a3b8"),
                }
            )
        preview_ids = {node["id"] for node in preview_nodes}
        preview_edges = [
            edge for edge in graph_data.get("edges", [])[:12]
            if edge.get("source_key") in preview_ids and edge.get("target_key") in preview_ids
        ]
        data = self._json_for_script({"nodes": preview_nodes, "edges": preview_edges})
        return f"""
        <svg id="home-graph-preview-svg" data-graph-href="graph.html" viewBox="0 0 520 260" aria-label="Graph preview"></svg>
        <script type="application/json" id="home-graph-preview-data">{data}</script>
        <script>
        (() => {{
          const svg = document.getElementById("home-graph-preview-svg");
          const dataEl = document.getElementById("home-graph-preview-data");
          if (!svg || !dataEl || svg.dataset.ready === "1") return;
          svg.dataset.ready = "1";
          const NS = "http://www.w3.org/2000/svg";
          const state = JSON.parse(dataEl.textContent);
          const nodes = state.nodes || [];
          const edges = state.edges || [];
          const byId = new Map(nodes.map((node) => [node.id, node]));
          const defs = document.createElementNS(NS, "defs");
          defs.innerHTML = '<linearGradient id="homeGraphBg" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#071226"></stop><stop offset="100%" stop-color="#0f172a"></stop></linearGradient>';
          svg.appendChild(defs);
          const bg = document.createElementNS(NS, "rect");
          bg.setAttribute("width", "520");
          bg.setAttribute("height", "260");
          bg.setAttribute("fill", "url(#homeGraphBg)");
          svg.appendChild(bg);
          const edgeLayer = document.createElementNS(NS, "g");
          const nodeLayer = document.createElementNS(NS, "g");
          svg.appendChild(edgeLayer);
          svg.appendChild(nodeLayer);
          const interaction = {{ moved: false, startX: 0, startY: 0 }};
          const edgeEls = edges.map((edge) => {{
            const line = document.createElementNS(NS, "line");
            line.setAttribute("class", "home-graph-edge");
            edgeLayer.appendChild(line);
            return {{ edge, line }};
          }});
          const nodeEls = nodes.map((node) => {{
            const group = document.createElementNS(NS, "g");
            group.setAttribute("class", "home-graph-node");
            group.dataset.nodeId = node.id;
            const circle = document.createElementNS(NS, "circle");
            circle.setAttribute("r", String(node.r || 10));
            circle.setAttribute("fill", node.fill || "#94a3b8");
            circle.setAttribute("fill-opacity", "0.95");
            const label = document.createElementNS(NS, "text");
            label.textContent = node.label;
            group.appendChild(circle);
            group.appendChild(label);
            nodeLayer.appendChild(group);
            return {{ node, group, circle, label }};
          }});
          function render() {{
            edgeEls.forEach((item) => {{
              const source = byId.get(item.edge.source_key);
              const target = byId.get(item.edge.target_key);
              if (!source || !target) return;
              item.line.setAttribute("x1", String(source.x));
              item.line.setAttribute("y1", String(source.y));
              item.line.setAttribute("x2", String(target.x));
              item.line.setAttribute("y2", String(target.y));
            }});
            nodeEls.forEach((item) => {{
              item.group.setAttribute("transform", `translate(${{item.node.x}}, ${{item.node.y}})`);
              item.label.setAttribute("x", String((item.node.r || 10) + 8));
              item.label.setAttribute("y", "4");
            }});
          }}
          let dragging = null;
          function pointFromEvent(event) {{
            const pt = svg.createSVGPoint();
            pt.x = event.clientX;
            pt.y = event.clientY;
            const mapped = pt.matrixTransform(svg.getScreenCTM().inverse());
            return {{
              x: Math.max(18, Math.min(502, mapped.x)),
              y: Math.max(18, Math.min(242, mapped.y)),
            }};
          }}
          nodeEls.forEach((item) => {{
            item.group.addEventListener("pointerdown", (event) => {{
              dragging = item.node;
              interaction.moved = false;
              interaction.startX = event.clientX;
              interaction.startY = event.clientY;
              item.group.style.cursor = "grabbing";
              item.group.setPointerCapture(event.pointerId);
              const point = pointFromEvent(event);
              item.node.x = point.x;
              item.node.y = point.y;
              render();
              event.preventDefault();
            }});
            item.group.addEventListener("pointermove", (event) => {{
              if (dragging !== item.node) return;
              if (Math.hypot(event.clientX - interaction.startX, event.clientY - interaction.startY) > 4) {{
                interaction.moved = true;
              }}
              const point = pointFromEvent(event);
              item.node.x = point.x;
              item.node.y = point.y;
              render();
            }});
            const endDrag = () => {{
              if (dragging === item.node) dragging = null;
              item.group.style.cursor = "grab";
            }};
            item.group.addEventListener("pointerup", endDrag);
            item.group.addEventListener("pointercancel", endDrag);
            item.group.addEventListener("click", (event) => {{
              event.stopPropagation();
              if (!interaction.moved && svg.dataset.graphHref) {{
                window.location.href = svg.dataset.graphHref;
              }}
            }});
          }});
          svg.addEventListener("click", (event) => {{
            if (event.target.closest(".home-graph-node")) return;
            if (svg.dataset.graphHref) window.location.href = svg.dataset.graphHref;
          }});
          render();
        }})();
        </script>
        """

    def _render_session_recap(self, recap: SessionRecap) -> str:
        top_insights = self._session_top_insights(recap)
        insight_cards = "\n".join(
            f"""
            <div class="insight-item">
              <div class="insight-rank">{idx}</div>
              <div><strong>{escape(item)}</strong></div>
            </div>
            """
            for idx, item in enumerate(top_insights, start=1)
        ) or '<p class="muted">No distilled insights yet.</p>'
        takeaways = "\n".join(f"<li>{escape(item)}</li>" for item in recap.key_takeaways) or "<li>No takeaways yet.</li>"
        decisions = "\n".join(f"<li>{escape(item)}</li>" for item in recap.decisions) or "<li>No explicit decisions captured.</li>"
        gotchas = "\n".join(f"<li>{escape(item)}</li>" for item in recap.gotchas) or "<li>No gotchas captured.</li>"
        questions = "\n".join(f"<li>{escape(item)}</li>" for item in recap.open_questions) or "<li>No open questions captured.</li>"
        modules = "\n".join(f"<span class='badge'>{escape(module)}</span>" for module in recap.modules_touched) or "<span class='badge low'>No modules</span>"
        sources = "\n".join(f"<li><code>{escape(path)}</code></li>" for path in recap.source_files) or "<li>No provenance recorded.</li>"
        evidence_cards = "\n".join(self._session_claim_card(claim) for claim in recap.related_claims[:4]) or "<p class='muted'>No promoted claims yet.</p>"
        before_points = "\n".join(f"<li>{escape(item)}</li>" for item in (recap.gotchas[:2] + recap.open_questions[:1])) or "<li>No explicit confusion captured.</li>"
        after_points = "\n".join(f"<li>{escape(item)}</li>" for item in (recap.decisions[:2] + recap.key_takeaways[:2])) or "<li>No resolved insights captured yet.</li>"
        session_health = self._session_health_metrics(recap)
        meta_cards = f"""
          <div class="meta">
            <div class="meta-card"><p class="eyebrow">Signal Quality</p><strong>{session_health['quality']}</strong></div>
            <div class="meta-card"><p class="eyebrow">Promoted Claims</p><strong>{len(recap.related_claims)}</strong></div>
            <div class="meta-card"><p class="eyebrow">Modules Touched</p><strong>{len(recap.modules_touched)}</strong></div>
            <div class="meta-card"><p class="eyebrow">Captured</p><strong>{_format_ts(recap.created_at)}</strong></div>
          </div>
        """
        return f"""
        <section class="hero">
          <div class="hero-panel">
            <p class="eyebrow">Session recap</p>
            <h1>{escape(recap.summary)}</h1>
            <p>{escape(recap.title)}</p>
            <div class="signal-strip">
              <span class="signal-pill">{escape(recap.session_id)}</span>
              <span class="signal-pill">{len(recap.modules_touched)} modules</span>
              <span class="signal-pill">{len(top_insights)} core insights</span>
            </div>
          </div>
        </section>
        <h2>Core Insights</h2>
        <div class="insight-list">{insight_cards}</div>
        <h2>What Became Clear</h2>
        <div class="split-grid">
          <div class="compare-card before">
            <p class="eyebrow">Before</p>
            <ul>{before_points}</ul>
          </div>
          <div class="compare-card after">
            <p class="eyebrow">After</p>
            <ul>{after_points}</ul>
          </div>
        </div>
        <h2>Evidence Highlights</h2>
        <div class="knowledge-grid">{evidence_cards}</div>
        <h2>Key Takeaways</h2>
        <div class="card"><ul>{takeaways}</ul></div>
        <h2>Modules Touched</h2>
        <div class="card">{modules}</div>
        <div class="split-grid">
          <div>
            <h2>Decisions</h2>
            <div class="card"><ul>{decisions}</ul></div>
          </div>
          <div>
            <h2>Open Questions</h2>
            <div class="card"><ul>{questions}</ul></div>
          </div>
        </div>
        <h2>Session Health</h2>
        {meta_cards}
        <div class="card"><ul>{gotchas}</ul></div>
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

    def _module_knowledge_panels(self, repo: str, module: str) -> str:
        store = SessionStore(self.wiki_dir)
        claims = store.get_module_claims(repo, module)
        sessions = store.get_module_sessions(repo, module)
        if not claims and not sessions:
            return ""
        claim_cards = "\n".join(self._claim_card(claim) for claim in claims) or "<p class='muted'>No promoted knowledge yet.</p>"
        session_cards = "\n".join(self._module_session_card(session) for session in sessions) or "<p class='muted'>No recent sessions yet.</p>"
        return f"""
        <h2>Promoted Knowledge</h2>
        <div class="knowledge-grid">{claim_cards}</div>
        <h2>Recent Sessions</h2>
        <div class="card"><div class="session-mini-list">{session_cards}</div></div>
        """

    def _claim_card(self, claim: dict) -> str:
        evidence = ", ".join(escape(item) for item in claim["evidence_refs"][:3]) or "No evidence refs"
        return f"""
        <article class="claim-card">
          <p class="eyebrow">{escape(claim['kind'].replace('_', ' '))}</p>
          <p><strong>{escape(claim['summary'])}</strong></p>
          <p class="muted">{escape(claim['why_it_matters'] or 'Distilled from session evidence.')}</p>
          <span class="badge">trust {claim['final_score']:.2f}</span>
          <span class="badge">{escape(claim['staleness_state'])}</span>
          <p class="muted">Evidence: {evidence}</p>
        </article>
        """

    def _module_session_card(self, session: dict) -> str:
        return f"""
        <div class="session-mini">
          <strong>{escape(session['id'])}</strong>
          <p>{escape(session['summary'] or 'Module captured in this session.')}</p>
          <p class="muted">Captured {_format_ts(session['captured_at'])} · quality {session['quality_score']:.2f}</p>
        </div>
        """

    def _session_claim_card(self, claim: PromotedClaim) -> str:
        evidence = ", ".join(escape(item) for item in claim.evidence_refs[:2]) or "No evidence refs"
        return f"""
        <article class="claim-card">
          <p class="eyebrow">{escape(claim.kind.replace('_', ' '))}</p>
          <p><strong>{escape(claim.summary)}</strong></p>
          <p class="muted">{escape(claim.why_it_matters or 'Distilled from session evidence.')}</p>
          <span class="badge">trust {claim.final_score:.2f}</span>
          <span class="badge">{escape(claim.staleness_state)}</span>
          <p class="muted">Evidence: {evidence}</p>
        </article>
        """

    def _session_top_insights(self, recap: SessionRecap) -> list[str]:
        insights: list[str] = []
        for claim in recap.related_claims:
            if claim.summary not in insights:
                insights.append(claim.summary)
            if len(insights) == 3:
                return insights
        for takeaway in recap.key_takeaways:
            if takeaway not in insights:
                insights.append(takeaway)
            if len(insights) == 3:
                break
        return insights

    def _session_health_metrics(self, recap: SessionRecap) -> dict[str, str]:
        if recap.related_claims:
            average = sum(claim.final_score for claim in recap.related_claims) / len(recap.related_claims)
        else:
            average = 0.0
        return {"quality": f"{average:.2f}"}

    def _build_sidebar(self, repo: str, current: str = "", *, location: str = "modules") -> str:
        repo_dir = self.wiki_dir / "repos" / repo
        sessions_dir = repo_dir / "sessions"
        modules = self._list_modules(repo)
        href_prefix = {
            "root": "",
            "modules": "../",
            "sessions": "../",
        }[location]
        items = [
            ("index.html", "home", current == "home", "nav-link-home"),
            ("graph.html", "graph", current == "graph", "nav-link-graph"),
        ]
        if (repo_dir / "overview.html").exists():
            items.append(("overview.html", "overview", current == "overview", "nav-link-home"))
        primary_links = []
        for href, label, active, class_name in items:
            active_class = " is-active" if active else ""
            primary_links.append(
                f'<a href="{href_prefix}{href}" class="nav-link {class_name}{active_class}">{label}</a>'
            )
        groups = [
            '<div class="nav-group"><div class="nav-links">' + "\n".join(primary_links) + "</div></div>"
        ]
        if sessions_dir.exists():
            session_links = []
            for page in sorted(sessions_dir.glob("*.html"), reverse=True)[:5]:
                href = f"{href_prefix}sessions/{page.name}" if location != "sessions" else page.name
                session_id = page.stem
                active_class = " is-active" if current == f"session:{session_id}" else ""
                session_links.append(
                    f'<a href="{href}" class="nav-link nav-link-session{active_class}">{session_id}</a>'
                )
            if session_links:
                groups.append(
                    '<div class="nav-group"><div class="nav-section-title">Sessions</div><div class="nav-links">'
                    + "\n".join(session_links)
                    + "</div></div>"
                )
        module_links = []
        for module in modules:
            active_class = " is-active" if module == current else ""
            href = f"{href_prefix}modules/{module}.html" if location != "modules" else f"{module}.html"
            module_links.append(
                f'<a href="{href}" class="nav-link nav-link-module{active_class}">{module}</a>'
            )
        groups.append(
            '<div class="nav-group"><div class="nav-section-title">Modules</div><div class="nav-links">'
            + "\n".join(module_links)
            + "</div></div>"
        )
        return '<div class="nav-shell"><div class="nav-brand">' + escape(repo) + "</div>" + "\n".join(groups) + "</div>"

    def _load_cache_data(self) -> dict[str, dict]:
        cache_path = self.wiki_dir / ".index" / "cache.json"
        if not cache_path.exists():
            return {}
        return json.loads(cache_path.read_text(encoding="utf-8"))

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
    def _json_for_script(value: object) -> str:
        return json.dumps(value).replace("</", "<\\/")

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
