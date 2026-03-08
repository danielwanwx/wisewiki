from __future__ import annotations

import json
from pathlib import Path

from wisewiki.claims import extract_candidate_claims, promote_candidate_claims
from wisewiki.html_writer import HtmlWriter
from wisewiki.models import CacheEntry, SessionEvent
from wisewiki.session_store import SessionStore


class WikiPublisher:
    def __init__(self, wiki_dir: Path) -> None:
        self.wiki_dir = wiki_dir
        self.store = SessionStore(wiki_dir)
        self.html_writer = HtmlWriter(wiki_dir)

    def publish_capture(
        self,
        *,
        repo: str,
        module: str,
        content: str,
        md_path: Path,
        entry: CacheEntry,
        session_events: list[SessionEvent] | None = None,
    ) -> dict[str, str]:
        claims = extract_candidate_claims(repo, module, content, entry, session_events=session_events)
        promoted = promote_candidate_claims(
            claims,
            existing_summaries=self._existing_claim_summaries(repo, module),
            staleness_state=entry.staleness_state,
        )
        html_path = self.html_writer.write_module_page(repo, module, content, md_path, entry=entry)
        self.store.record_capture(
            repo=repo,
            session_id=entry.session_id,
            module=module,
            entry=entry,
            html_path=str(html_path),
            promoted_claims=promoted,
            session_events=session_events,
        )
        recap = self.store.build_session_recap(repo, entry.session_id)
        recap_path = self.html_writer.write_session_page(repo, recap)
        graph_data = self.store.get_graph_data(repo)
        graph_json_path = self.html_writer.write_graph_data(repo, graph_data)
        graph_html_path = self.html_writer.write_graph_page(repo, graph_data)
        index_path = self.html_writer.generate_index(repo)
        return {
            "module_html_path": str(html_path),
            "session_html_path": str(recap_path),
            "graph_html_path": str(graph_html_path),
            "graph_json_path": str(graph_json_path),
            "index_path": str(index_path),
        }

    def _existing_claim_summaries(self, repo: str, module: str) -> list[str]:
        rows = self.store.conn.execute(
            """
            SELECT summary
            FROM claims
            WHERE repo = ? AND module = ?
            ORDER BY created_at DESC
            """,
            (repo, module),
        ).fetchall()
        return [row["summary"] for row in rows]
