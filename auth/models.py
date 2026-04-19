"""SQLite- and Postgres-backed user/conversion models for ConvertFlow.

Backend selection (resolved per connection, reads env each call):
  - If ``DATABASE_URL`` starts with ``postgres://`` or ``postgresql://`` the
    Postgres backend is used (via ``psycopg[binary]``, imported lazily so
    local dev without psycopg installed still works).
  - Otherwise the default SQLite backend at ``CF_DB_PATH`` is used
    (defaults to ``<repo>/cf.db``).

The Postgres path exists so ephemeral-FS hosts (Koyeb free, Heroku free,
Fly free) can persist users + billing state across redeploys by pointing
``DATABASE_URL`` at a managed Postgres (Neon, Supabase, Render, etc.).
Local dev keeps SQLite as the default — ``DATABASE_URL`` is the only switch.

Public function signatures are the stable API used by auth/quota and
billing/router — they must not change when the backend changes.
"""
from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "cf.db"
DB_PATH = Path(os.environ.get("CF_DB_PATH") or _DEFAULT_DB_PATH)
_lock = Lock()


# ── Backend detection ────────────────────────────────────────────────────────

def _database_url() -> str | None:
    """Return DATABASE_URL if it points at Postgres, else None."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if url.startswith(("postgres://", "postgresql://")):
        return url
    return None


def _is_pg() -> bool:
    return _database_url() is not None


def _q(sql: str) -> str:
    """Translate SQLite ``?`` placeholders to Postgres ``%s`` when on Postgres.

    SQL in this module is authored in SQLite dialect (``?`` placeholders) and
    rewritten at execution time for Postgres. Keeps one source of truth for
    queries and avoids pulling in an ORM for a ~200-line module.
    """
    return sql.replace("?", "%s") if _is_pg() else sql


# ── Connection factories ─────────────────────────────────────────────────────

def _pg_connect():
    # Lazy import: ``psycopg`` is optional — only required when DATABASE_URL
    # actually points at Postgres. Local dev without psycopg installed still
    # imports this module fine.
    import psycopg  # noqa: WPS433  (local import is intentional)
    from psycopg.rows import dict_row

    return psycopg.connect(_database_url(), row_factory=dict_row)


def _sqlite_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def _conn():
    """Yield a connection for the active backend. Commits on success, rolls back on error.

    Both backends expose ``.execute(sql, params)`` → cursor-like with
    ``fetchone()``/``fetchall()``. Row access is by column name (``row["col"]``)
    which works for both ``sqlite3.Row`` and psycopg's ``dict_row``.
    """
    if _is_pg():
        conn = _pg_connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = _sqlite_connect()
        try:
            with conn:  # sqlite3's context manager commits on success, rolls back on error
                yield conn
        finally:
            conn.close()


# ── Schema (compatible with both SQLite and Postgres) ────────────────────────
#
# All types here are SQLite-dialect but accepted verbatim by Postgres:
#   TEXT, TEXT PRIMARY KEY, TEXT UNIQUE NOT NULL, TEXT NOT NULL DEFAULT 'free',
#   REFERENCES users(id). CREATE TABLE/INDEX IF NOT EXISTS are standard in both.

_SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS users (
        id                 TEXT PRIMARY KEY,
        email              TEXT UNIQUE NOT NULL,
        password_hash      TEXT NOT NULL,
        plan               TEXT NOT NULL DEFAULT 'free',
        stripe_customer_id TEXT,
        created_at         TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS conversions (
        id         TEXT PRIMARY KEY,
        user_id    TEXT NOT NULL REFERENCES users(id),
        tool       TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_conv_user_date
        ON conversions(user_id, created_at)
    """,
)


def init_db() -> None:
    """Create tables and indexes if they do not exist."""
    if not _is_pg():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        with _conn() as conn:
            for ddl in _SCHEMA_STATEMENTS:
                conn.execute(ddl)


# ── Users ─────────────────────────────────────────────────────────────────────

def create_user(email: str, password_hash: str) -> dict:
    user_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    email_norm = email.lower().strip()
    with _lock:
        with _conn() as conn:
            conn.execute(
                _q(
                    "INSERT INTO users (id, email, password_hash, plan, created_at) "
                    "VALUES (?, ?, ?, 'free', ?)"
                ),
                (user_id, email_norm, password_hash, now),
            )
    return {"id": user_id, "email": email_norm, "plan": "free"}


def get_user_by_email(email: str) -> dict | None:
    with _conn() as conn:
        cur = conn.execute(
            _q("SELECT id, email, password_hash, plan FROM users WHERE email = ?"),
            (email.lower().strip(),),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict | None:
    with _conn() as conn:
        cur = conn.execute(
            _q(
                "SELECT id, email, plan, stripe_customer_id "
                "FROM users WHERE id = ?"
            ),
            (user_id,),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def set_user_plan(user_id: str, plan: str, stripe_customer_id: str | None = None) -> None:
    with _lock:
        with _conn() as conn:
            conn.execute(
                _q(
                    "UPDATE users SET plan = ?, "
                    "stripe_customer_id = COALESCE(?, stripe_customer_id) "
                    "WHERE id = ?"
                ),
                (plan, stripe_customer_id, user_id),
            )


def set_plan_by_stripe_customer(stripe_customer_id: str, plan: str) -> None:
    with _lock:
        with _conn() as conn:
            conn.execute(
                _q("UPDATE users SET plan = ? WHERE stripe_customer_id = ?"),
                (plan, stripe_customer_id),
            )


# ── Conversions ────────────────────────────────────────────────────────────────

def record_conversion(user_id: str, tool: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _lock:
        with _conn() as conn:
            conn.execute(
                _q(
                    "INSERT INTO conversions (id, user_id, tool, created_at) "
                    "VALUES (?, ?, ?, ?)"
                ),
                (uuid.uuid4().hex, user_id, tool, now),
            )


def count_conversions_today(user_id: str) -> int:
    # UTC, not local: record_conversion stamps created_at in UTC, so the
    # window must be UTC too. Local date.today() near midnight UTC silently
    # misses rows whose UTC date hasn't matched the local date yet.
    today = datetime.now(timezone.utc).date().isoformat()
    with _conn() as conn:
        cur = conn.execute(
            _q(
                "SELECT COUNT(*) AS n FROM conversions "
                "WHERE user_id = ? AND created_at >= ?"
            ),
            (user_id, today),
        )
        row = cur.fetchone()
    if not row:
        return 0
    # sqlite3.Row and psycopg's dict_row both support key access.
    return row["n"]
