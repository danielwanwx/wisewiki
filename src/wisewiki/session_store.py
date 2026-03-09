from __future__ import annotations

import json
import time
from pathlib import Path

from wisewiki.db import connect_db, init_db
from wisewiki.models import CacheEntry, PromotedClaim, SessionEvent, SessionRecap


class SessionStore:
    def __init__(self, wiki_dir: Path) -> None:
        self.wiki_dir = wiki_dir
        self.db_path = wiki_dir / ".index" / "wisewiki.db"
        self.conn = connect_db(self.db_path)
        init_db(self.conn)

    def ensure_session(self, repo: str, session_id: str, *, created_at: float | None = None) -> None:
        now = created_at if created_at is not None else time.time()
        self.conn.execute(
            """
            INSERT INTO sessions (id, repo, title, summary, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET updated_at = excluded.updated_at
            """,
            (
                session_id,
                repo,
                f"Session {session_id}",
                "",
                now,
                now,
            ),
        )
        self.conn.commit()

    def record_capture(
        self,
        *,
        repo: str,
        session_id: str,
        module: str,
        entry: CacheEntry,
        html_path: str,
        promoted_claims: list[PromotedClaim],
        session_events: list[SessionEvent] | None = None,
    ) -> None:
        now = entry.captured_at or time.time()
        self.ensure_session(repo, session_id, created_at=now)
        if session_events:
            self._record_events(session_id, session_events)
        self.conn.execute(
            """
            INSERT INTO captures (
                session_id, repo, module, title, summary, html_path,
                captured_at, quality_score, source_files_json, staleness_state
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id, module) DO UPDATE SET
                title = excluded.title,
                summary = excluded.summary,
                html_path = excluded.html_path,
                captured_at = excluded.captured_at,
                quality_score = excluded.quality_score,
                source_files_json = excluded.source_files_json,
                staleness_state = excluded.staleness_state
            """,
            (
                session_id,
                repo,
                module,
                entry.title,
                entry.summary,
                html_path,
                now,
                entry.quality_score,
                json.dumps(entry.source_files),
                entry.staleness_state,
            ),
        )
        self.conn.execute(
            "DELETE FROM claims WHERE session_id = ? AND module = ?",
            (session_id, module),
        )
        self.conn.execute(
            "DELETE FROM graph_edges WHERE session_id = ? AND (source_key = ? OR target_key = ?)",
            (session_id, f"module:{module}", f"module:{module}"),
        )
        for claim in promoted_claims:
            self.conn.execute(
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
                    session_id,
                    repo,
                    module,
                    claim.kind,
                    claim.summary,
                    claim.why_it_matters,
                    claim.confidence,
                    claim.reusability,
                    claim.specificity,
                    claim.novelty_score,
                    claim.evidence_score,
                    claim.final_score,
                    json.dumps(claim.evidence_refs),
                    claim.staleness_state,
                    claim.status,
                    now,
                ),
            )
        self._rebuild_same_session_edges(repo, session_id, now)
        self._update_session_rollup(repo, session_id)
        self.conn.commit()

    def _record_events(self, session_id: str, session_events: list[SessionEvent]) -> None:
        for event in session_events:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO session_events (id, session_id, event_type, created_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    session_id,
                    event.event_type,
                    event.created_at,
                    json.dumps(event.payload),
                ),
            )

    def _rebuild_same_session_edges(self, repo: str, session_id: str, created_at: float) -> None:
        modules = [
            row["module"]
            for row in self.conn.execute(
                "SELECT module FROM captures WHERE session_id = ? ORDER BY module",
                (session_id,),
            )
        ]
        self.conn.execute("DELETE FROM graph_edges WHERE repo = ? AND session_id = ?", (repo, session_id))
        for i, source in enumerate(modules):
            for target in modules[i + 1 :]:
                self.conn.execute(
                    """
                    INSERT INTO graph_edges (repo, session_id, source_key, target_key, edge_type, weight, created_at)
                    VALUES (?, ?, ?, ?, 'same_session', 1.0, ?)
                    """,
                    (repo, session_id, f"module:{source}", f"module:{target}", created_at),
                )

    def _update_session_rollup(self, repo: str, session_id: str) -> None:
        recap = self.build_session_recap(repo, session_id)
        self.conn.execute(
            "UPDATE sessions SET title = ?, summary = ?, updated_at = ? WHERE id = ?",
            (recap.title, recap.summary, recap.created_at, session_id),
        )

    def build_session_recap(self, repo: str, session_id: str) -> SessionRecap:
        session_row = self.conn.execute(
            "SELECT * FROM sessions WHERE id = ? AND repo = ?",
            (session_id, repo),
        ).fetchone()
        capture_rows = self.conn.execute(
            """
            SELECT * FROM captures
            WHERE session_id = ? AND repo = ?
            ORDER BY captured_at DESC, module
            """,
            (session_id, repo),
        ).fetchall()
        claim_rows = self.conn.execute(
            """
            SELECT * FROM claims
            WHERE session_id = ? AND repo = ?
            ORDER BY final_score DESC, created_at DESC
            """,
            (session_id, repo),
        ).fetchall()

        related_claims = [
            PromotedClaim(
                kind=row["kind"],
                module=row["module"],
                summary=row["summary"],
                why_it_matters=row["why_it_matters"],
                confidence=row["confidence"],
                reusability=row["reusability"],
                specificity=row["specificity"],
                novelty_score=row["novelty_score"],
                evidence_score=row["evidence_score"],
                final_score=row["final_score"],
                evidence_refs=json.loads(row["evidence_refs_json"]),
                staleness_state=row["staleness_state"],
                status=row["status"],
            )
            for row in claim_rows
        ]

        key_takeaways = [claim.summary for claim in related_claims[:5]]
        decisions = [claim.summary for claim in related_claims if claim.kind == "decision"][:5]
        gotchas = [claim.summary for claim in related_claims if claim.kind == "gotcha"][:5]
        open_questions = [claim.summary for claim in related_claims if claim.kind == "open_question"][:5]
        modules_touched = [row["module"] for row in capture_rows]
        source_files: list[str] = []
        for row in capture_rows:
            for path in json.loads(row["source_files_json"]):
                if path not in source_files:
                    source_files.append(path)

        summary = (
            session_row["summary"]
            if session_row and session_row["summary"]
            else _build_recap_summary(modules_touched, key_takeaways)
        )
        title = (
            session_row["title"]
            if session_row and session_row["title"] and session_row["title"] != f"Session {session_id}"
            else _build_recap_title(modules_touched, session_id)
        )
        created_at = session_row["updated_at"] if session_row else time.time()
        return SessionRecap(
            session_id=session_id,
            repo=repo,
            title=title,
            summary=summary,
            key_takeaways=key_takeaways,
            decisions=decisions,
            gotchas=gotchas,
            open_questions=open_questions,
            modules_touched=modules_touched,
            source_files=source_files,
            commands_run=[],
            tests_run=[],
            related_claims=related_claims,
            created_at=created_at,
        )

    def get_recent_sessions(self, repo: str, limit: int = 5) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT s.id, s.title, s.summary, s.updated_at,
                   COUNT(c.id) AS capture_count
            FROM sessions s
            LEFT JOIN captures c ON c.session_id = s.id
            WHERE s.repo = ?
            GROUP BY s.id, s.title, s.summary, s.updated_at
            ORDER BY s.updated_at DESC
            LIMIT ?
            """,
            (repo, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_recent_captures(self, repo: str, limit: int = 8) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT session_id, module, title, summary, html_path, captured_at,
                   quality_score, source_files_json, staleness_state
            FROM captures
            WHERE repo = ?
            ORDER BY captured_at DESC
            LIMIT ?
            """,
            (repo, limit),
        ).fetchall()
        captures = []
        for row in rows:
            item = dict(row)
            item["source_files"] = json.loads(item.pop("source_files_json"))
            captures.append(item)
        return captures

    def get_module_claims(self, repo: str, module: str, limit: int = 6) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT session_id, kind, summary, why_it_matters, final_score,
                   evidence_refs_json, staleness_state, created_at
            FROM claims
            WHERE repo = ? AND module = ? AND status = 'promoted'
            ORDER BY final_score DESC, created_at DESC
            LIMIT ?
            """,
            (repo, module, limit),
        ).fetchall()
        claims = []
        for row in rows:
            item = dict(row)
            item["evidence_refs"] = json.loads(item.pop("evidence_refs_json"))
            claims.append(item)
        return claims

    def get_module_sessions(self, repo: str, module: str, limit: int = 4) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT session_id AS id, summary, captured_at, quality_score
            FROM captures
            WHERE repo = ? AND module = ?
            ORDER BY captured_at DESC
            LIMIT ?
            """,
            (repo, module, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_graph_data(self, repo: str) -> dict:
        capture_rows = self.conn.execute(
            """
            SELECT module, quality_score, staleness_state, session_id
            FROM captures
            WHERE repo = ?
            ORDER BY captured_at DESC
            """,
            (repo,),
        ).fetchall()
        claim_rows = self.conn.execute(
            """
            SELECT session_id, kind, module, summary, final_score, staleness_state
            FROM claims
            WHERE repo = ? AND final_score >= 0.7
            ORDER BY created_at DESC
            LIMIT 24
            """,
            (repo,),
        ).fetchall()
        edge_rows = self.conn.execute(
            """
            SELECT source_key, target_key, edge_type, weight
            FROM graph_edges
            WHERE repo = ?
            ORDER BY created_at DESC
            """,
            (repo,),
        ).fetchall()

        nodes: list[dict] = []
        seen_nodes: set[str] = set()
        for row in capture_rows:
            node_id = f"module:{row['module']}"
            if node_id in seen_nodes:
                continue
            seen_nodes.add(node_id)
            nodes.append(
                {
                    "id": node_id,
                    "label": row["module"],
                    "type": "module",
                    "module": row["module"],
                    "session_id": row["session_id"],
                    "confidence": row["quality_score"],
                    "staleness_state": row["staleness_state"],
                }
            )
        for row in claim_rows:
            node_id = f"{row['kind']}:{row['module']}:{abs(hash(row['summary'])) % 100000}"
            if node_id in seen_nodes:
                continue
            seen_nodes.add(node_id)
            nodes.append(
                {
                    "id": node_id,
                    "label": row["summary"],
                    "type": row["kind"],
                    "module": row["module"],
                    "session_id": row["session_id"],
                    "confidence": row["final_score"],
                    "staleness_state": row["staleness_state"],
                }
            )
        edges = [dict(row) for row in edge_rows]
        for row in claim_rows:
            claim_node_id = f"{row['kind']}:{row['module']}:{abs(hash(row['summary'])) % 100000}"
            edges.append(
                {
                    "source_key": f"module:{row['module']}",
                    "target_key": claim_node_id,
                    "edge_type": "claim_support",
                    "weight": max(0.6, row["final_score"]),
                }
            )
        return {"nodes": nodes, "edges": edges}


def _build_recap_title(modules_touched: list[str], session_id: str) -> str:
    if modules_touched:
        primary = ", ".join(modules_touched[:2])
        return f"Session recap for {primary}"
    return f"Session recap {session_id}"


def _build_recap_summary(modules_touched: list[str], takeaways: list[str]) -> str:
    if modules_touched and takeaways:
        return (
            f"This session touched {', '.join(modules_touched[:3])} and produced "
            f"{len(takeaways)} promoted takeaways."
        )
    if modules_touched:
        return f"This session touched {', '.join(modules_touched[:3])}."
    return "This session captured reusable coding knowledge."
