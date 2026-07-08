"""SQLite storage for MAYA: file index, memory, audit log, and runtime settings.

A single small helper — no ORM. FastAPI runs sync endpoints in a thread pool,
so writes are serialized with a lock and the connection allows cross-thread use.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS file_index (
    path        TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    ext         TEXT NOT NULL,
    folder      TEXT NOT NULL,
    mtime       REAL NOT NULL,
    size        INTEGER NOT NULL,
    sensitivity TEXT NOT NULL,
    categories  TEXT NOT NULL DEFAULT '',
    text        TEXT NOT NULL DEFAULT '',
    version     INTEGER NOT NULL DEFAULT 0,
    name_date   TEXT NOT NULL DEFAULT '',
    indexed_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS memory (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    key        TEXT NOT NULL,
    value      BLOB NOT NULL,
    category   TEXT NOT NULL DEFAULT 'preference',
    source     TEXT NOT NULL DEFAULT 'chat',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL,
    event       TEXT NOT NULL,
    target      TEXT NOT NULL DEFAULT '',
    detail      TEXT NOT NULL DEFAULT '',
    sensitivity TEXT NOT NULL DEFAULT '',
    outcome     TEXT NOT NULL DEFAULT 'ok'
);
CREATE TABLE IF NOT EXISTS kv (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def executemany(self, sql: str, rows: list[tuple]) -> None:
        with self._lock:
            self._conn.executemany(sql, rows)
            self._conn.commit()

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

    def query_one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    # -- tiny kv store for runtime-adjustable settings -------------------------
    def kv_get(self, key: str, default: str | None = None) -> str | None:
        row = self.query_one("SELECT value FROM kv WHERE key = ?", (key,))
        return row["value"] if row else default

    def kv_set(self, key: str, value: str) -> None:
        self.execute(
            "INSERT INTO kv(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    def close(self) -> None:
        with self._lock:
            self._conn.close()
