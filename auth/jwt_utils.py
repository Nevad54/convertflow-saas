"""JWT encode/decode helpers for ConvertFlow auth."""
from __future__ import annotations

import os
import secrets
import sys
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

_env_secret = os.environ.get("SECRET_KEY")
if _env_secret:
    _SECRET_KEY: str = _env_secret
else:
    _SECRET_KEY = secrets.token_hex(32)
    # Missing SECRET_KEY in production means every restart invalidates all sessions.
    # Warn loudly in SaaS mode; stay quiet in local mode.
    if os.environ.get("APP_MODE", "saas").lower() != "local":
        print(
            "[auth] WARNING: SECRET_KEY is not set — using a random per-process key. "
            "All JWT sessions will break on restart. Set SECRET_KEY in your host env.",
            file=sys.stderr,
            flush=True,
        )
_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_DAYS = 30
COOKIE_NAME = "cf_token"


def create_token(user_id: str, plan: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=_ACCESS_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": user_id, "plan": plan, "exp": exp},
        _SECRET_KEY,
        algorithm=_ALGORITHM,
    )


def decode_token(token: str) -> dict | None:
    """Return payload dict or None if invalid/expired."""
    try:
        payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
        return payload
    except JWTError:
        return None
