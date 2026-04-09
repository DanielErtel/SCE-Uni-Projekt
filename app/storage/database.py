"""SQLite-Wissensdatenbank fuer alle verarbeiteten Inhalte."""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

from app.config import DB_PATH


def get_db(db_path: Path = None) -> sqlite3.Connection:
    """Datenbankverbindung holen und Schema sicherstellen."""
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection):
    """Datenbank-Schema erstellen."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL,  -- 'file', 'url', 'fileshare'
            source_path TEXT NOT NULL,
            file_type TEXT,             -- 'pdf', 'docx', 'xlsx', 'url', etc.
            file_size INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            metadata JSON,
            UNIQUE(source_path)
        );

        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            content_type TEXT NOT NULL,  -- 'text', 'table', 'image_desc', 'summary'
            content TEXT NOT NULL,
            page_number INTEGER,
            section TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            metadata JSON,
            FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER,
            analysis_type TEXT NOT NULL,  -- 'summary', 'extraction', 'qa', 'custom'
            prompt TEXT,
            result TEXT NOT NULL,
            model TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE SET NULL
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS content_fts USING fts5(
            content,
            content_id UNINDEXED,
            source_path UNINDEXED
        );

        CREATE INDEX IF NOT EXISTS idx_sources_type ON sources(source_type);
        CREATE INDEX IF NOT EXISTS idx_content_source ON content(source_id);
        CREATE INDEX IF NOT EXISTS idx_analyses_source ON analyses(source_id);
    """)
    conn.commit()


def add_source(conn: sqlite3.Connection, source_type: str, source_path: str,
               file_type: str = None, file_size: int = None,
               metadata: dict = None) -> int:
    """Neue Quelle registrieren. Gibt source_id zurueck."""
    cur = conn.execute("""
        INSERT INTO sources (source_type, source_path, file_type, file_size, metadata)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(source_path) DO UPDATE SET
            updated_at = datetime('now'),
            metadata = excluded.metadata
    """, (source_type, source_path, file_type, file_size,
          json.dumps(metadata) if metadata else None))
    conn.commit()

    if cur.lastrowid:
        return cur.lastrowid
    row = conn.execute("SELECT id FROM sources WHERE source_path = ?",
                       (source_path,)).fetchone()
    return row["id"]


def add_content(conn: sqlite3.Connection, source_id: int, content_type: str,
                content: str, page_number: int = None, section: str = None,
                metadata: dict = None) -> int:
    """Inhalt zu einer Quelle hinzufuegen."""
    cur = conn.execute("""
        INSERT INTO content (source_id, content_type, content, page_number, section, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (source_id, content_type, content, page_number, section,
          json.dumps(metadata) if metadata else None))

    # Volltextindex aktualisieren
    source = conn.execute("SELECT source_path FROM sources WHERE id = ?",
                          (source_id,)).fetchone()
    conn.execute("""
        INSERT INTO content_fts (content, content_id, source_path)
        VALUES (?, ?, ?)
    """, (content, cur.lastrowid, source["source_path"] if source else ""))

    conn.commit()
    return cur.lastrowid


def add_analysis(conn: sqlite3.Connection, source_id: int, analysis_type: str,
                 result: str, prompt: str = None, model: str = None) -> int:
    """KI-Analyse-Ergebnis speichern."""
    cur = conn.execute("""
        INSERT INTO analyses (source_id, analysis_type, prompt, result, model)
        VALUES (?, ?, ?, ?, ?)
    """, (source_id, analysis_type, prompt, result, model))
    conn.commit()
    return cur.lastrowid


def search(conn: sqlite3.Connection, query: str, limit: int = 20) -> list[dict]:
    """Volltextsuche ueber alle Inhalte."""
    rows = conn.execute("""
        SELECT
            f.content_id,
            f.source_path,
            snippet(content_fts, 0, '>>>', '<<<', '...', 64) as snippet,
            rank
        FROM content_fts f
        WHERE content_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """, (query, limit)).fetchall()
    return [dict(r) for r in rows]


def get_sources(conn: sqlite3.Connection, source_type: str = None) -> list[dict]:
    """Alle Quellen auflisten."""
    if source_type:
        rows = conn.execute(
            "SELECT * FROM sources WHERE source_type = ? ORDER BY updated_at DESC",
            (source_type,)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM sources ORDER BY updated_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_stats(conn: sqlite3.Connection) -> dict:
    """Statistiken ueber die Wissensdatenbank."""
    sources = conn.execute("SELECT COUNT(*) as n FROM sources").fetchone()["n"]
    contents = conn.execute("SELECT COUNT(*) as n FROM content").fetchone()["n"]
    analyses = conn.execute("SELECT COUNT(*) as n FROM analyses").fetchone()["n"]
    types = conn.execute(
        "SELECT file_type, COUNT(*) as n FROM sources GROUP BY file_type"
    ).fetchall()
    return {
        "quellen": sources,
        "inhalte": contents,
        "analysen": analyses,
        "typen": {r["file_type"]: r["n"] for r in types},
    }
