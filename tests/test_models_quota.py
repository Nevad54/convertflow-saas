"""Regression test: ``count_conversions_today`` must filter by UTC date.

``record_conversion`` stamps ``created_at`` in UTC, so the today-window filter
must also be UTC. Pre-fix the filter used ``date.today()`` (local TZ), which
silently undercounts whenever the host's local date has rolled past the UTC
date — e.g. server in Asia/Manila (UTC+8) during local morning hours: every
fresh UTC-stamped row falls on "yesterday UTC" relative to local, so the
quota window sees 0 rows and the per-day cap effectively disables itself.
"""
from __future__ import annotations

from datetime import datetime as _real_datetime, timezone as _tz

import pytest


@pytest.fixture()
def models_with_frozen_utc(tmp_path, monkeypatch):
    """Route auth.models at a tmp sqlite db with a freezable UTC clock.

    Same monkeypatch-only pattern as test_models_postgres.py — no module
    reload, so other tests holding a reference to auth.models keep seeing
    the same module instance.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)

    import auth.models as m

    monkeypatch.setattr(m, "DB_PATH", tmp_path / "cf.db")

    state: dict = {"utc": None}

    class _FrozenDatetime(_real_datetime):
        @classmethod
        def now(cls, tz=None):
            utc = state["utc"]
            return utc.astimezone(tz) if tz is not None else utc.replace(tzinfo=None)

    monkeypatch.setattr(m, "datetime", _FrozenDatetime)

    assert m._is_pg() is False  # sanity: hitting the sqlite path

    m.init_db()

    def set_utc(utc_dt):
        state["utc"] = utc_dt

    return m, set_utc


def test_quota_count_uses_utc_near_midnight(models_with_frozen_utc):
    """Two conversions stamped at 22:00 UTC (≈ 06:00 next day in UTC+8).

    Both rows carry UTC date 2026-04-16. The today-count must return 2 —
    a local-TZ filter (``date.today()`` on a UTC+8 host) would resolve to
    "2026-04-17" and lexicographically miss both rows. Regression for the
    pre-fix bug where the per-day quota silently disabled itself during
    local-morning hours on hosts east of UTC.
    """
    m, set_utc = models_with_frozen_utc
    set_utc(_real_datetime(2026, 4, 16, 22, 0, 0, tzinfo=_tz.utc))

    user = m.create_user("east@example.com", "hash")
    m.record_conversion(user["id"], "pdf_to_docx")
    m.record_conversion(user["id"], "pdf_to_docx")

    assert m.count_conversions_today(user["id"]) == 2
