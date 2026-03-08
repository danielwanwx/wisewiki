from __future__ import annotations

import sqlite3
from pathlib import Path


def connect_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            repo TEXT NOT NULL,
            title TEXT,
            summary TEXT,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS captures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            module TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            html_path TEXT NOT NULL,
            captured_at REAL NOT NULL,
            quality_score REAL NOT NULL DEFAULT 0.0,
            source_files_json TEXT NOT NULL DEFAULT '[]',
            staleness_state TEXT NOT NULL DEFAULT 'unknown',
            UNIQUE(session_id, module),
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS session_events (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            created_at REAL NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            module TEXT NOT NULL,
            kind TEXT NOT NULL,
            summary TEXT NOT NULL,
            why_it_matters TEXT NOT NULL DEFAULT '',
            confidence REAL NOT NULL DEFAULT 0.0,
            reusability REAL NOT NULL DEFAULT 0.0,
            specificity REAL NOT NULL DEFAULT 0.0,
            novelty_score REAL NOT NULL DEFAULT 0.0,
            evidence_score REAL NOT NULL DEFAULT 0.0,
            final_score REAL NOT NULL DEFAULT 0.0,
            evidence_refs_json TEXT NOT NULL DEFAULT '[]',
            staleness_state TEXT NOT NULL DEFAULT 'unknown',
            status TEXT NOT NULL DEFAULT 'promoted',
            created_at REAL NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS graph_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo TEXT NOT NULL,
            session_id TEXT NOT NULL,
            source_key TEXT NOT NULL,
            target_key TEXT NOT NULL,
            edge_type TEXT NOT NULL,
            weight REAL NOT NULL DEFAULT 1.0,
            created_at REAL NOT NULL
        );
        """
    )
    conn.commit()
