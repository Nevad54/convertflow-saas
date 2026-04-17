"""Usage quota enforcement for ConvertFlow.

Limits:
  Anonymous (no account): 3 conversions / day, tracked by IP
  Free tier:              10 conversions / day, tracked in DB
  Pro tier:               unlimited
"""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request

from .jwt_utils import COOKIE_NAME, decode_token
from .models import count_conversions_today, get_user_by_id, record_conversion

_FREE_DAILY_LIMIT = 10
_ANON_DAILY_LIMIT = 3

# In-memory anonymous IP counter — resets each calendar day
# Structure: { "YYYY-MM-DD": { ip: count } }
_anon_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
_anon_lock = Lock()


def _today_str() -> str:
    from datetime import date
    return date.today().isoformat()


def get_current_user(request: Request) -> dict | None:
    """Return user dict from JWT cookie, or None if not logged in / invalid token."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    return get_user_by_id(payload["sub"])


def require_quota(request: Request) -> dict | None:
    """FastAPI dependency — enforces per-user or per-IP daily quota.

    Returns the current user dict (or None for anonymous).
    Raises HTTP 429 if quota exceeded.
    """
    user = get_current_user(request)

    if user is None:
        # Anonymous — check IP
        ip = request.client.host if request.client else "unknown"
        today = _today_str()
        with _anon_lock:
            count = _anon_counts[today].get(ip, 0)
            if count >= _ANON_DAILY_LIMIT:
                raise HTTPException(
                    status_code=429,
                    detail=(
                        f"You've used your {_ANON_DAILY_LIMIT} free conversions for today. "
                        "Sign up for a free account to get 10/day, or upgrade to Pro for unlimited."
                    ),
                )
            _anon_counts[today][ip] = count + 1
        return None

    if user["plan"] == "pro":
        return user  # unlimited

    # Free user — check DB count
    count = count_conversions_today(user["id"])
    if count >= _FREE_DAILY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=(
                f"You've reached your {_FREE_DAILY_LIMIT} daily conversions. "
                "Upgrade to Pro for unlimited conversions."
            ),
        )
    return user


def record_usage(user: dict | None, tool: str) -> None:
    """Record a completed conversion for quota accounting.

    Call this after a successful conversion, not before.
    Anonymous usage is already counted in require_quota().
    """
    if user is not None:
        record_conversion(user["id"], tool)
