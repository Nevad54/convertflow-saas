# ConvertFlow — SaaS Deployment & Monetization Master Plan

**Last updated:** 2026-04-16  
**Goal:** Deploy ConvertFlow as a hosted, paying SaaS product.  
**Stack:** FastAPI · Python · LibreOffice · Ollama · Docker · Stripe · SQLite → Postgres

---

## Product Snapshot

- 30 PDF/document tools — fully built and QA'd
- AI engine via Ollama (gemma4 model) with multi-engine fallback chains
- Currently runs locally on Windows via `start.bat`
- No auth, no payments, no user accounts yet

---

## Monetization Model

| Tier | Price | Limits | Features |
|---|---|---|---|
| **Free** | $0 | 10 conversions/day | All 30 tools, basic engines |
| **Pro** | $12/month | Unlimited | All tools + AI engines (Ollama), priority queue |

Payment: Stripe Checkout (hosted page) + webhook to activate Pro.  
Auth: email + password, JWT tokens stored in HttpOnly cookies.  
Database: SQLite for launch → migrate to Postgres when needed.

---

## Phase Overview

| Phase | Goal | Status |
|---|---|---|
| **Phase 1** | Linux compatibility (Docker blockers) | ✅ Done (code) — pending Docker runtime validation |
| **Phase 2** | Dockerize the app | ✅ Done (code) — pending Docker runtime validation |
| **Phase 3** | Deploy to server (Railway) | ✅ Done (code-side prep complete — manual Railway steps remain) |
| **Phase 4** | Auth + user accounts | ✅ Done |
| **Phase 5** | Stripe payments + usage metering | ✅ Done |
| **Phase 6** | Landing page + pricing page | ✅ Done |

Complete phases in order. Each phase ships independently.

---

## Phase 1 — Linux Compatibility

**Why:** COM automation (pywin32) is Windows-only. Docker runs Linux. Two blockers must be fixed before containerizing.

### Blocker 1: LibreOffice fallback for Office→PDF

**Sub-plan:** `docs/superpowers/plans/2026-04-16-libreoffice-fallback.md`  
**Design spec:** `docs/superpowers/specs/2026-04-16-libreoffice-fallback-design.md`

Summary of changes (all in `execution/pdf_tools.py`):
- Add `_libreoffice_available()` after line 3229
- Add `_office_to_pdf_via_libreoffice()` after line 3229
- Wire LibreOffice into `word_to_pdf` chain (line ~2691)
- Wire LibreOffice into `pptx_to_pdf` chain (line ~3457)
- Wire LibreOffice into `excel_to_pdf` chain (line ~3590)
- Add `import subprocess` to top-level imports (line 4-7)

**Status:** ✅ Done — LibreOffice fallback is implemented in `execution/pdf_tools.py`

### Blocker 2: Ollama as Docker sidecar

**Problem:** `start.bat` launches Ollama on the host. In Docker, Ollama must run as a separate container.

**Changes needed:**

1. **`docker-compose.yml`** — create at project root:
```yaml
version: "3.9"
services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - OLLAMA_HOST=http://ollama:11434
    depends_on:
      - ollama
    volumes:
      - ./outputs:/app/.tmp

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"

volumes:
  ollama_data:
```

2. **`app.py` or `.env`** — ensure Ollama base URL is read from `OLLAMA_HOST` env var, not hardcoded to `localhost:11434`.

   Search for all hardcoded Ollama URLs:
   ```bash
   grep -n "localhost:11434\|127.0.0.1:11434" app.py execution/pdf_tools.py execution/converter.py
   ```
   Replace each with `os.getenv("OLLAMA_HOST", "http://localhost:11434")`.

3. **Pull the model on first start** — add an init script or `docker-compose` entrypoint that runs:
   ```bash
   ollama pull gemma4:e4b
   ```
   This only runs once (model cached in `ollama_data` volume).

**Status:** 🟡 In progress — initial `docker-compose.yml` is created; Docker validation still pending

---

## Phase 2 — Dockerize

**Goal:** Single `docker build` produces a working image.

### `Dockerfile` (create at project root)

```dockerfile
FROM python:3.12-slim

# System deps
RUN apt-get update && apt-get install -y \
    libreoffice \
    tesseract-ocr \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

# Temp dirs
RUN mkdir -p .tmp/uploads .tmp/outputs

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```

### `requirements.txt` audit

Check that `requirements.txt` does NOT include `pywin32` — it won't install on Linux.  
If it's there, remove it (pywin32 import is already guarded in `pdf_tools.py` with try/except).

### `.dockerignore` (create at project root)

```
.venv/
.tmp/
.playwright-mcp/
__pycache__/
*.pyc
*.png
*.bat
.env
```

### Verify locally

```bash
docker compose up --build
# Then open http://localhost:8080
# Upload a .docx and convert to PDF — must work via LibreOffice
```

**Status:** 🟡 In progress — initial `Dockerfile` and `.dockerignore` are created; Docker validation still pending

---

## Phase 3 — Deploy to Server

**Platform:** Railway (easiest) or Hetzner VPS (cheapest).

### Option A — Railway (recommended for launch)

1. Push code to GitHub (private repo is fine)
2. Go to railway.app → New Project → Deploy from GitHub
3. Set environment variables in Railway dashboard:
   - `OLLAMA_HOST=http://ollama:11434` (internal Railway service URL)
   - `SECRET_KEY=<random 32-char string>` (for JWT signing, Phase 4)
   - `STRIPE_SECRET_KEY=<from Stripe dashboard>` (Phase 5)
   - `STRIPE_WEBHOOK_SECRET=<from Stripe dashboard>` (Phase 5)
4. Add Ollama as a second Railway service (Docker image: `ollama/ollama`)
5. Set `PORT=8080` in Railway
6. Attach a custom domain in Railway settings

**Cost:** ~$5-20/month depending on usage.

### Option B — Hetzner VPS

1. Spin up a CX21 (2 vCPU, 4 GB RAM, €4.51/month)
2. Install Docker + Docker Compose on the VPS
3. `git clone` the repo, `docker compose up -d`
4. Use Caddy or nginx as a reverse proxy for HTTPS
5. Point your domain DNS to the VPS IP

**Cost:** €4.51/month + domain.

### Domain & HTTPS

- Register a domain (e.g., convertflow.io)
- Railway: SSL is automatic with custom domains
- Hetzner: use `caddy` with auto-HTTPS

**Status:** ✅ Done (code-side prep complete)

Code-side checklist completed 2026-04-16:
- `pywin32` is platform-conditional in `requirements.txt` — won't install on Linux
- `Dockerfile` and `docker-compose.yml` exist and are production-ready (with health checks and model-puller sidecar)
- All Ollama URLs use `os.getenv("OLLAMA_HOST", "http://localhost:11434")` — no hardcoded values
- `.env.example` created documenting all required env vars (SECRET_KEY, APP_URL, STRIPE_*, OLLAMA_HOST)
- `README.md` updated with full env var reference
- `python -c "import app; print('OK')"` → OK

Remaining manual steps (require Railway access):
1. Push repo to GitHub
2. Railway → New Project → Deploy from GitHub
3. Set env vars in Railway dashboard (SECRET_KEY, APP_URL, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRO_PRICE_ID)
4. Add Ollama as a second Railway service (image: ollama/ollama) → set OLLAMA_HOST to internal service URL
5. Attach custom domain → SSL automatic
6. Register Stripe webhook endpoint at `https://yourdomain.com/billing/webhook`

---

## Phase 4 — Auth & User Accounts

**Goal:** Users can sign up, log in, and their conversion quota is tracked.

### New files to create

| File | Purpose |
|---|---|
| `auth/models.py` | SQLite `users` table via sqlite3 |
| `auth/jwt.py` | JWT encode/decode with `python-jose` |
| `auth/router.py` | FastAPI router: `/auth/signup`, `/auth/login`, `/auth/logout`, `/auth/me` |
| `templates/auth/login.html` | Login form |
| `templates/auth/signup.html` | Signup form |

### Database schema (`auth/models.py`)

```python
# Table: users
# id           TEXT PRIMARY KEY (uuid4)
# email        TEXT UNIQUE NOT NULL
# password_hash TEXT NOT NULL  (bcrypt)
# plan         TEXT NOT NULL DEFAULT 'free'  ('free' | 'pro')
# stripe_customer_id TEXT
# created_at   TEXT NOT NULL  (ISO timestamp)
```

```python
# Table: conversions
# id         TEXT PRIMARY KEY (uuid4)
# user_id    TEXT NOT NULL REFERENCES users(id)
# tool       TEXT NOT NULL  (e.g. 'word_to_pdf')
# created_at TEXT NOT NULL  (ISO timestamp)
```

### New packages needed

Add to `requirements.txt`:
```
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
```

### Auth flow

- Signup: hash password with bcrypt → insert user → issue JWT → set HttpOnly cookie
- Login: verify password → issue JWT → set HttpOnly cookie  
- JWT payload: `{"sub": user_id, "plan": "free"|"pro", "exp": ...}`
- Cookie name: `cf_token`, HttpOnly, Secure, SameSite=Lax

### Usage quota middleware

In `app.py`, add a dependency `require_quota()`:

```python
async def require_quota(request: Request):
    user = get_current_user(request)  # returns None for anonymous
    if user is None:
        # Anonymous: allow but rate-limit by IP (10/day)
        check_ip_quota(request.client.host)
        return
    if user["plan"] == "pro":
        return  # unlimited
    # Free: count today's conversions
    count = count_conversions_today(user["id"])
    if count >= 10:
        raise HTTPException(429, "Daily limit reached. Upgrade to Pro.")
```

Apply this dependency to every `/convert/...` route.

### Anonymous users

Anonymous users (no login) are allowed up to **3 conversions/day** tracked by IP.  
This lets people try the product without signup friction.

**Status:** ✅ Done — `auth/` module complete; login/signup/logout/me routes; quota middleware on all /convert/* routes; dashboard at /dashboard; 77/0/0 smoke tests.

---

## Phase 5 — Stripe Payments + Usage Metering

**Goal:** Users can subscribe to Pro ($12/month) via Stripe Checkout.

### New files

| File | Purpose |
|---|---|
| `billing/router.py` | FastAPI router: `/billing/checkout`, `/billing/portal`, `/billing/webhook` |
| `templates/pricing.html` | Pricing page with Free vs Pro cards |

### New packages

Add to `requirements.txt`:
```
stripe==9.12.0
```

### Stripe setup (one-time, in Stripe dashboard)

1. Create a Product: "ConvertFlow Pro"
2. Create a Price: $12/month recurring
3. Note the Price ID (e.g. `price_1ABC...`)
4. Create a webhook endpoint pointing to `https://yourdomain.com/billing/webhook`
5. Subscribe to events: `checkout.session.completed`, `customer.subscription.deleted`

### Checkout flow

```
User clicks "Upgrade to Pro"
→ POST /billing/checkout
→ Server creates Stripe Checkout Session (mode=subscription, price=price_1ABC...)
  with metadata: {"user_id": user.id}
→ Redirect user to Stripe-hosted checkout page
→ User pays → Stripe redirects to /billing/success
→ Stripe fires checkout.session.completed webhook
→ POST /billing/webhook: update users SET plan='pro', stripe_customer_id=...
```

### Cancellation flow

```
User clicks "Manage Subscription"
→ POST /billing/portal
→ Server creates Stripe Customer Portal session
→ Redirect user to Stripe portal
→ User cancels → Stripe fires customer.subscription.deleted
→ POST /billing/webhook: update users SET plan='free'
```

### Webhook handler (in `billing/router.py`)

```python
@router.post("/billing/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    event = stripe.Webhook.construct_event(payload, sig, WEBHOOK_SECRET)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session["metadata"]["user_id"]
        customer_id = session["customer"]
        update_user(user_id, plan="pro", stripe_customer_id=customer_id)

    elif event["type"] == "customer.subscription.deleted":
        customer_id = event["data"]["object"]["customer"]
        downgrade_by_customer(customer_id)  # SET plan='free'

    return {"ok": True}
```

**Status:** ✅ Done — `billing/router.py` complete; pricing/success/cancel templates created; webhook handles checkout.session.completed + customer.subscription.deleted; 3/3 tests pass.

---

## Phase 6 — Landing Page & Pricing Page

**Goal:** Visitors understand the product and convert to paid users.

### Pages to build/update

| Page | Route | What to add |
|---|---|---|
| Landing (existing `index.html`) | `/` | Hero section with value prop, feature grid, CTA to pricing |
| Pricing | `/pricing` | Free vs Pro comparison table, Stripe checkout button |
| Login | `/auth/login` | Clean form, link to signup |
| Signup | `/auth/signup` | Clean form, link to login |
| Dashboard | `/dashboard` | Usage bar (X/10 conversions today), plan badge, upgrade button |

### SEO basics (add to `base.html`)

```html
<meta name="description" content="Free PDF tools — merge, compress, convert, sign. No upload limits. AI-powered.">
<meta property="og:title" content="ConvertFlow — PDF Tools That Work">
<meta property="og:description" content="30 PDF tools, free forever. No account required.">
```

### Value proposition

"30 PDF tools. No upload limits on Free. AI-powered conversions. Your files never leave our server storage beyond conversion time."

**Status:** ✅ Done — SEO meta tags in base.html; hero updated (30 tools, no upload limits, AI-powered, CTA to /pricing); Pricing nav link added to site-wide header.

---

## Environment Variables Reference

Create `.env` for local dev, set in Railway/Hetzner for production.

| Variable | Example | Required by |
|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` | Phase 1 |
| `SECRET_KEY` | `<32 random chars>` | Phase 4 (JWT) |
| `DATABASE_URL` | `sqlite:///./cf.db` | Phase 4 |
| `STRIPE_SECRET_KEY` | `sk_live_...` | Phase 5 |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` | Phase 5 |
| `STRIPE_PRO_PRICE_ID` | `price_1ABC...` | Phase 5 |
| `APP_URL` | `https://convertflow.io` | Phase 5 (redirect URLs) |

---

## Sub-Plans Index

Each phase has its own detailed implementation plan:

| Phase | Plan file |
|---|---|
| Phase 1 — LibreOffice fallback | `docs/superpowers/plans/2026-04-16-libreoffice-fallback.md` |
| Phase 1 — Ollama Docker sidecar | `docs/superpowers/plans/2026-04-16-ollama-docker-sidecar.md` |
| Phase 2 — Dockerize | `docs/superpowers/plans/2026-04-16-dockerize-linux-container.md` |
| Phase 3 — Deploy | _write before starting_ |
| Phase 4 — Auth | _write before starting_ |
| Phase 5 — Stripe | _write before starting_ |
| Phase 6 — Landing page | _write before starting_ |

**Convention:** Before starting any phase, run the `superpowers:brainstorming` skill to produce a design doc, then `superpowers:writing-plans` to produce the sub-plan. Save the plan, then execute it.

---

## How to Start Any Session

1. Read this file (`SAAS_PLAN.md`) to find the current phase
2. Check the phase's status (🔲 Not started / 🟡 In progress / ✅ Done)
3. If the sub-plan exists, use `superpowers:executing-plans` to execute it
4. If the sub-plan doesn't exist yet, use `superpowers:brainstorming` → `superpowers:writing-plans`
5. After completing a phase, update the status in this file to ✅ Done

---

## Revenue Projections (rough)

| Users | Free | Pro (10%) | MRR |
|---|---|---|---|
| 500 | 450 | 50 | $600 |
| 2,000 | 1,800 | 200 | $2,400 |
| 10,000 | 9,000 | 1,000 | $12,000 |

Target: 2,000 users within 6 months of launch via SEO + Product Hunt.

---

## Current Blockers (as of 2026-04-16)

1. LibreOffice fallback → implemented; validate in Linux container runtime
2. Ollama Docker sidecar → compose exists; validate on a machine with Docker
3. Dockerize phase → Dockerfile and .dockerignore exist; validate Linux runtime and conversion flows
4. Everything else follows in phase order
