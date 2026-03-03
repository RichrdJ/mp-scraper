"""SQLite database layer."""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

DB_PATH = os.getenv("DB_PATH", "./data/marktplaats.db")


def init_db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS queries (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                url         TEXT UNIQUE NOT NULL,
                name        TEXT,
                enabled     INTEGER NOT NULL DEFAULT 1,
                seeded      INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_checked TEXT
            );

            CREATE TABLE IF NOT EXISTS items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                mp_id       TEXT NOT NULL,
                query_id    INTEGER NOT NULL,
                title       TEXT,
                price       TEXT,
                url         TEXT,
                image_url   TEXT,
                description TEXT,
                found_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(mp_id, query_id),
                FOREIGN KEY (query_id) REFERENCES queries(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT ''
            );
        """)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def get_queries() -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM queries ORDER BY created_at DESC"
        ).fetchall()


def add_query(url: str, name: Optional[str] = None):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO queries (url, name) VALUES (?, ?)",
            (url, name or None),
        )


def remove_query(query_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM queries WHERE id = ?", (query_id,))


def update_last_checked(query_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE queries SET last_checked = ? WHERE id = ?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), query_id),
        )


def mark_seeded(query_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE queries SET seeded = 1 WHERE id = ?", (query_id,))


def migrate():
    """Add columns introduced after initial schema creation."""
    with get_conn() as conn:
        try:
            conn.execute("ALTER TABLE queries ADD COLUMN seeded INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass  # column already exists


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------

def item_exists(mp_id: str, query_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM items WHERE mp_id = ? AND query_id = ?",
            (mp_id, query_id),
        ).fetchone()
        return row is not None


def add_item(
    mp_id: str,
    query_id: int,
    title: str,
    price: str,
    url: str,
    image_url: Optional[str],
    description: Optional[str],
):
    with get_conn() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO items
               (mp_id, query_id, title, price, url, image_url, description)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (mp_id, query_id, title, price, url, image_url, description),
        )


def get_items(limit: int = 50, query_id: Optional[int] = None) -> list:
    with get_conn() as conn:
        if query_id:
            return conn.execute(
                """SELECT i.*, q.name AS query_name
                   FROM items i JOIN queries q ON i.query_id = q.id
                   WHERE i.query_id = ?
                   ORDER BY i.found_at DESC LIMIT ?""",
                (query_id, limit),
            ).fetchall()
        return conn.execute(
            """SELECT i.*, q.name AS query_name
               FROM items i JOIN queries q ON i.query_id = q.id
               ORDER BY i.found_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()


def get_item_count() -> int:
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

def get_setting(key: str, default: str = "") -> str:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )


def get_all_settings() -> dict:
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {r["key"]: r["value"] for r in rows}
