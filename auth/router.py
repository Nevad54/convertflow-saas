"""FastAPI auth router — signup, login, logout, /me."""
from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext

from .jwt_utils import COOKIE_NAME, create_token, decode_token
from .models import create_user, get_user_by_email, get_user_by_id

router = APIRouter(prefix="/auth")
templates = Jinja2Templates(directory="templates")
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _cookie_secure() -> bool:
    """Secure cookies when the app is served over HTTPS.

    Resolution order:
      1. COOKIE_SECURE env var ("true"/"false") — explicit override.
      2. APP_URL starts with https:// — auto-detect for Koyeb/Railway/etc.
      3. Default False (local http://localhost dev).
    """
    import os

    override = os.getenv("COOKIE_SECURE", "").strip().lower()
    if override in ("true", "1", "yes"):
        return True
    if override in ("false", "0", "no"):
        return False
    return os.getenv("APP_URL", "").lower().startswith("https://")


_COOKIE_OPTS: dict = {
    "key": COOKIE_NAME,
    "httponly": True,
    "samesite": "lax",
    "secure": _cookie_secure(),
    "max_age": 30 * 24 * 3600,
}


# ── Pages ─────────────────────────────────────────────────────────────────────

@router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "auth/signup.html", {"request": request})


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "auth/login.html", {"request": request})


# ── Actions ───────────────────────────────────────────────────────────────────

@router.post("/signup")
async def signup(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
) -> RedirectResponse:
    email = email.lower().strip()

    if len(password) < 8:
        return templates.TemplateResponse(
            request,
            "auth/signup.html",
            {"request": request, "error": "Password must be at least 8 characters."},
            status_code=422,
        )

    if get_user_by_email(email):
        return templates.TemplateResponse(
            request,
            "auth/signup.html",
            {"request": request, "error": "An account with that email already exists."},
            status_code=409,
        )

    hashed = _pwd.hash(password)
    user = create_user(email, hashed)
    token = create_token(user["id"], user["plan"])

    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(**_COOKIE_OPTS, value=token)
    return response


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
) -> RedirectResponse:
    user = get_user_by_email(email)
    if not user or not _pwd.verify(password, user["password_hash"]):
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {"request": request, "error": "Incorrect email or password."},
            status_code=401,
        )

    token = create_token(user["id"], user["plan"])
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(**_COOKIE_OPTS, value=token)
    return response


@router.post("/logout")
async def logout() -> RedirectResponse:
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response


# ── API ───────────────────────────────────────────────────────────────────────

@router.get("/me")
async def me(request: Request) -> JSONResponse:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Session expired.")
    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    return JSONResponse({"id": user["id"], "email": user["email"], "plan": user["plan"]})
