# ConvertFlow

ConvertFlow is a local-first document workspace for teams that deal with real-world PDFs, Office files, scans, and mixed-format document handoffs.

Instead of treating OCR, PDF cleanup, editing, and format conversion as unrelated tools, ConvertFlow groups them into one on-device workspace built for operations-heavy document work.

## What ConvertFlow Does

### Prepare PDFs
- Merge, split, extract, remove, rotate, organize, compress, and repair PDFs
- Reorder packets and clean up files before delivery

### Convert Documents
- Convert between PDF, Word, Excel, PowerPoint, images, HTML, Markdown, and text
- Recover editable outputs from PDFs and export Office files back into PDF

### Recover Scanned Files
- Turn scans, screenshots, forms, and invoices into usable documents
- Rebuild output as Word, PDF, Excel, PowerPoint, HTML, Markdown, or plain text

### Review and Finalize
- Edit PDF overlays, redact, compare, watermark, add page numbers, protect, unlock, and sign
- Finish business-ready handoff files from the same workspace

## Local-First by Default

Core workflows run on your machine.

Optional assistive engines are available when you explicitly configure and select them:
- `tesseract`: local OCR
- `ollama`: local OCR and local AI assist
- `github`: optional cloud-backed OCR and assistive flows through GitHub Models
- `openai`: optional cloud-backed OCR

ConvertFlow does not require cloud engines for its main PDF and conversion workflows.

## Run

Recommended local startup:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app_local:app --host 0.0.0.0 --port 8080
```

Then open `http://127.0.0.1:8080`.

On Windows you can also use:

```bash
start_local.bat
```

Hosted SaaS startup:

```bash
.venv\Scripts\python.exe -m uvicorn app_saas:app --host 0.0.0.0 --port 8080
```

On Windows:

```bash
start_saas.bat
```

## Capability Matrix

| Capability | Default mode | Optional engines |
|---|---|---|
| PDF organize / edit / secure / finalize | Local | None required |
| Office to PDF / PDF to Office | Local | None required |
| Scan recovery and OCR | Local-first | `ollama`, `github`, `openai` |
| Summaries / translations / assistive extraction | Local-first with `ollama` when available | `github` for optional hosted assist |

## App Split

ConvertFlow now has two dedicated entrypoints:

- `app_local.py` - local app with no auth, no quota limits, and no billing routes
- `app_saas.py` - SaaS app with auth, pricing, quota enforcement, and Stripe billing

Both entrypoints share the same `execution/`, `templates/`, and `static/` layers so the product stays in sync.

## Environment Variables

Copy `.env.example` to `.env` for local dev. Set in Railway/VPS dashboard for production.

### Core
- `SECRET_KEY` — random 32-char string for JWT signing (`python -c "import secrets; print(secrets.token_hex(32))"`)
- `APP_URL` — e.g. `http://localhost:8080` locally, `https://convertflow.io` in production

### Ollama (AI engine)
- `OLLAMA_HOST=http://localhost:11434` — use `http://ollama:11434` in Docker / Railway
- `OLLAMA_OCR_MODEL=gemma4:e4b`

### Stripe Payments
- `STRIPE_SECRET_KEY` — from Stripe dashboard → API keys
- `STRIPE_WEBHOOK_SECRET` — from Stripe dashboard → Webhooks → Signing secret
- `STRIPE_PRO_PRICE_ID` — Price ID for the $12/month Pro plan

### Optional cloud OCR engines
- `OPENAI_API_KEY` / `OPENAI_OCR_MODEL=gpt-4.1-mini`
- `GITHUB_TOKEN` (PAT with models scope) / `GITHUB_OCR_MODEL=openai/gpt-4.1-mini`

## Repo Structure

- `app.py` - FastAPI app and route orchestration
- `templates/` - homepage and tool UI
- `static/` - shared styles and client-side behavior
- `execution/` - deterministic execution layer for OCR, conversion, editing, and PDF operations
- `directives/` - workflow-level guidance and product map
- `.tmp/` - generated intermediates and outputs

## Workflow Directives

The repo now documents the product by workflow rather than only by a single OCR flow:
- `directives/product_map.md`
- `directives/pdf_operations.md`
- `directives/office_pdf_conversion.md`
- `directives/ocr_recovery.md`
- `directives/review_finalize.md`

## Notes

- Tesseract OCR requires the Tesseract executable to be installed and available on `PATH`.
- Ollama requires a local model such as `gemma4:e4b`.
- Optional hosted engines send data off-device only when you select them.
