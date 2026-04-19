"""Exercise auth.models' Postgres code path using a sqlite-backed fake psycopg.

Why a fake: a real Postgres isn't available in CI/dev. But the failure modes
the PG path can introduce are all at the SQL-translation layer:
  - ``?`` → ``%s`` placeholder rewriting
  - row access via key (``row["n"]``) instead of index
  - connection context-manager semantics (commit on success, rollback on error)
All three are backend-agnostic and observable with a sqlite-backed fake that
accepts the translated SQL.

If ``psycopg`` is not installed this file is skipped cleanly so the base test
suite stays green in minimal dev envs without the optional dep.
"""
from __future__ import annotations

import sqlite3

import pytest


# Skip the whole module unless psycopg is importable. auth.models imports it
# lazily, so local dev without psycopg still works — the test honors that.
pytest.importorskip("psycopg")


class _FakePgConn:
    """Wrap a sqlite3.Connection behind a psycopg3-Connection-shaped facade.

    auth.models authors SQL with ``?`` placeholders and rewrites to ``%s`` for
    Postgres. This fake translates back so the rewritten SQL runs on sqlite,
    which is enough to exercise the PG code path end-to-end.
    """

    def __init__(self, path: str) -> None:
        self._c = sqlite3.connect(path)
        self._c.row_factory = sqlite3.Row

    def execute(self, sql, params=None):
        sql = sql.replace("%s", "?")
        if params is None:
            return self._c.execute(sql)
        return self._c.execute(sql, params)

    def commit(self) -> None:
        self._c.commit()

    def rollback(self) -> None:
        self._c.rollback()

    def close(self) -> None:
        self._c.close()


@pytest.fixture()
def pg_models(tmp_path, monkeypatch):
    """Route auth.models' PG path through a sqlite-backed fake connection.

    Uses env + attribute monkeypatching only (no module reload) so other tests
    that hold references into auth.models keep seeing the same module instance.
    """
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake:fake@localhost/fake")

    import auth.models as m

    db_file = tmp_path / "pg_fake.db"
    monkeypatch.setattr(m, "_pg_connect", lambda: _FakePgConn(str(db_file)))

    # Sanity: confirm the module sees itself as running against Postgres now.
    assert m._is_pg() is True

    m.init_db()
    return m


def test_postgres_path_roundtrip(pg_models):
    m = pg_models

    # create + lookup by email / id (exercises INSERT and two SELECTs)
    u = m.create_user("pg@example.com", "hashed_pw")
    assert u["plan"] == "free"

    by_email = m.get_user_by_email("pg@example.com")
    assert by_email is not None
    assert by_email["email"] == "pg@example.com"
    assert by_email["password_hash"] == "hashed_pw"

    by_id = m.get_user_by_id(u["id"])
    assert by_id is not None
    assert by_id["plan"] == "free"
    assert by_id["stripe_customer_id"] is None

    # plan transitions (exercises COALESCE + placeholder rewrite in UPDATE)
    m.set_user_plan(u["id"], "pro", stripe_customer_id="cus_TEST")
    upgraded = m.get_user_by_id(u["id"])
    assert upgraded["plan"] == "pro"
    assert upgraded["stripe_customer_id"] == "cus_TEST"

    m.set_plan_by_stripe_customer("cus_TEST", "free")
    downgraded = m.get_user_by_id(u["id"])
    assert downgraded["plan"] == "free"
    assert downgraded["stripe_customer_id"] == "cus_TEST"

    # conversion counting (exercises COUNT(*) AS n alias + date-range filter)
    assert m.count_conversions_today(u["id"]) == 0
    m.record_conversion(u["id"], "pdf_to_docx")
    m.record_conversion(u["id"], "pdf_to_docx")
    assert m.count_conversions_today(u["id"]) == 2
