from __future__ import annotations

import io
import os
import shutil
import threading
import time
import uuid
import zipfile
from pathlib import Path
import re

from dotenv import load_dotenv
import base64
import json as _json

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from execution.converter import (
    MissingDependencyError,
    SUPPORTED_DOC_STYLES,
    SUPPORTED_OCR_ENGINES,
    SUPPORTED_OUTPUTS,
    convert_images_to_document,
)
import execution.pdf_tools as pdf_tools

from auth import router as auth_router
from auth.models import init_db
from auth.quota import get_current_user, record_usage, require_quota
from billing import router as billing_router


BASE_DIR = Path(__file__).resolve().parent
SHARED_3D_DIR = BASE_DIR.parent / "shared-3d-assets"
TMP_DIR = BASE_DIR / ".tmp"
UPLOAD_DIR = TMP_DIR / "uploads"
OUTPUT_DIR = TMP_DIR / "outputs"

load_dotenv(BASE_DIR / ".env")

# APP_MODE controls whether auth/billing features are active.
# "saas"  → auth, quota enforcement, Stripe payments (default for Railway/Docker)
# "local" → no auth, no quota, no payments (for self-hosted / desktop use)
_SAAS = os.getenv("APP_MODE", "saas").lower() != "local"

for directory in (UPLOAD_DIR, OUTPUT_DIR):
    directory.mkdir(parents=True, exist_ok=True)

_MAX_TMP_AGE_SECONDS = 3 * 3600  # 3 hours
_MAX_UPLOAD_BYTES = 200 * 1024 * 1024  # 200 MB
_BATCH_ID_RE = re.compile(r"^[0-9a-f]{32}$")


def _cleanup_tmp() -> None:
    cutoff = time.time() - _MAX_TMP_AGE_SECONDS
    for d in UPLOAD_DIR.iterdir():
        if d.is_dir() and d.stat().st_mtime < cutoff:
            shutil.rmtree(d, ignore_errors=True)
    for f in OUTPUT_DIR.iterdir():
        if f.is_file() and f.stat().st_mtime < cutoff:
            f.unlink(missing_ok=True)
        elif f.is_dir() and f.stat().st_mtime < cutoff:
            shutil.rmtree(f, ignore_errors=True)


def _start_cleanup_thread() -> None:
    """Run _cleanup_tmp once per hour in a background daemon thread."""
    def _loop() -> None:
        while True:
            time.sleep(3600)
            try:
                _cleanup_tmp()
            except Exception:
                pass
    t = threading.Thread(target=_loop, daemon=True, name="tmp-cleanup")
    t.start()


_cleanup_tmp()
_start_cleanup_thread()
if _SAAS:
    init_db()


def _validated_batch_id(value: str) -> str:
    batch_id = str(value or "").strip().lower()
    if not batch_id:
        raise HTTPException(status_code=400, detail="batch_id is required.")
    if not _BATCH_ID_RE.fullmatch(batch_id):
        raise HTTPException(status_code=400, detail="Invalid batch_id.")
    return batch_id

app = FastAPI(title="ConvertFlow - Local-First Document Workspace")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
if SHARED_3D_DIR.exists():
    app.mount("/shared-3d-assets", StaticFiles(directory=SHARED_3D_DIR), name="shared-3d-assets")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals["saas_mode"] = _SAAS  # available in every template as {{ saas_mode }}

if _SAAS:
    app.include_router(auth_router.router)
    app.include_router(billing_router.router)


# ── Auth + quota middleware ────────────────────────────────────────────────────

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as _StarletteResponse


class _AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if _SAAS:
            request.state.current_user = get_current_user(request)
        else:
            request.state.current_user = None

        # Enforce + record quota on every POST to /convert/* (SaaS only)
        if _SAAS and request.method == "POST" and request.url.path.startswith("/convert/"):
            try:
                user = require_quota(request)
            except HTTPException as exc:
                return JSONResponse(
                    {"detail": exc.detail},
                    status_code=exc.status_code,
                )
            response = await call_next(request)
            # Record usage only on success (2xx)
            if response.status_code < 300:
                tool = request.url.path.removeprefix("/convert/")
                record_usage(user, tool)
            return response

        return await call_next(request)


app.add_middleware(_AuthMiddleware)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _batch() -> tuple[str, Path]:
    batch_id = uuid.uuid4().hex
    batch_dir = UPLOAD_DIR / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    return batch_id, batch_dir


def _save_upload(upload: UploadFile, dest_dir: Path) -> Path:
    safe_name = Path(upload.filename or "upload").name
    safe_name = safe_name or "upload"
    dest = dest_dir / safe_name
    written = 0
    chunk_size = 65536
    with dest.open("wb") as buf:
        while True:
            chunk = upload.file.read(chunk_size)
            if not chunk:
                break
            written += len(chunk)
            if written > _MAX_UPLOAD_BYTES:
                buf.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail="File too large. Maximum upload size is 200 MB.",
                )
            buf.write(chunk)
    return dest


def _save_uploads(uploads: list[UploadFile], dest_dir: Path) -> list[Path]:
    paths = [_save_upload(u, dest_dir) for u in uploads]
    paths.sort(key=lambda p: natural_sort_key(p))
    return paths


def _out(batch_id: str, name: str) -> Path:
    return OUTPUT_DIR / f"{batch_id}_{name}"


def slugify(value: str) -> str:
    cleaned = "".join(c.lower() if c.isalnum() else "_" for c in value.strip())
    return "_".join(p for p in cleaned.split("_") if p)


def natural_sort_key(path: Path) -> list[object]:
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", path.name)]


def _file_response(path: Path, filename: str) -> FileResponse:
    return FileResponse(path=path, filename=filename, media_type="application/octet-stream")


def _zip_response(paths: list[Path], zip_name: str) -> StreamingResponse:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in paths:
            zf.write(p, p.name)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
    )


# ─────────────────────────────────────────────
# Pages
# ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    from fastapi.responses import RedirectResponse as _RR
    if not _SAAS:
        return _RR(url="/", status_code=303)
    user = request.state.current_user
    if not user:
        return _RR(url="/auth/login", status_code=303)
    from auth.models import count_conversions_today
    from auth.quota import _FREE_DAILY_LIMIT
    today_count = count_conversions_today(user["id"]) if user["plan"] != "pro" else None
    limit = _FREE_DAILY_LIMIT if user["plan"] == "free" else None
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "today_count": today_count,
            "limit": limit,
        },
    )


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "app": "convertflow",
            "tmp": {
                "uploads": str(UPLOAD_DIR),
                "outputs": str(OUTPUT_DIR),
            },
        }
    )


@app.get("/tool/{tool}", response_class=HTMLResponse)
async def tool_page(request: Request, tool: str) -> HTMLResponse:
    ctx = {
        "request": request,
        "tool": tool,
        "formats": sorted(SUPPORTED_OUTPUTS),
        "ocr_engines": sorted(SUPPORTED_OCR_ENGINES),
        "document_styles": sorted(SUPPORTED_DOC_STYLES),
    }
    try:
        return templates.TemplateResponse(request, f"tools/{tool}.html", ctx)
    except Exception:
        raise HTTPException(status_code=404, detail="Tool not found.")


# ─────────────────────────────────────────────
# OCR / Image-to-Document  (existing)
# ─────────────────────────────────────────────

@app.post("/convert/image-to-doc")
async def convert_image_to_doc(
    files: list[UploadFile] = File(...),
    output_format: str = Form(...),
    title: str = Form(""),
    ocr_engine: str = Form("auto"),
    document_style: str = Form("auto"),
    pdf_page_numbers: bool = Form(False),
    pdf_watermark: str = Form(""),
) -> FileResponse:
    if output_format not in SUPPORTED_OUTPUTS:
        raise HTTPException(status_code=400, detail="Unsupported output format.")
    if not files:
        raise HTTPException(status_code=400, detail="Please upload at least one image.")

    batch_id, batch_dir = _batch()
    saved = _save_uploads(files, batch_dir)

    output_name = f"{slugify(title) or 'converted_document'}.{output_format}"
    output_path = _out(batch_id, output_name)

    try:
        convert_images_to_document(
            saved, output_format, output_path,
            title=title or None,
            ocr_engine=ocr_engine,
            document_style=document_style,
            pdf_page_numbers=pdf_page_numbers,
            pdf_watermark=pdf_watermark or None,
        )
    except MissingDependencyError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {exc}") from exc

    return _file_response(output_path, output_name)


# ─────────────────────────────────────────────
# PDF Organize
# ─────────────────────────────────────────────

@app.post("/convert/merge-pdf")
async def api_merge_pdf(files: list[UploadFile] = File(...)) -> FileResponse:
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Upload at least 2 PDF files to merge.")
    batch_id, batch_dir = _batch()
    saved = _save_uploads(files, batch_dir)
    out = _out(batch_id, "merged.pdf")
    try:
        pdf_tools.merge_pdfs(saved, out)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, "merged.pdf")


@app.post("/convert/split-pdf")
async def api_split_pdf(file: UploadFile = File(...)) -> StreamingResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out_dir = OUTPUT_DIR / batch_id
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        pages = pdf_tools.split_pdf(src, out_dir)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if len(pages) == 1:
        return _file_response(pages[0], pages[0].name)
    return _zip_response(pages, "split_pages.zip")


@app.post("/convert/extract-pages")
async def api_extract_pages(
    file: UploadFile = File(...),
    pages: str = Form(...),
) -> FileResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out = _out(batch_id, "extracted.pdf")
    try:
        pdf_tools.extract_pages(src, pages, out)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, "extracted.pdf")


@app.post("/convert/remove-pages")
async def api_remove_pages(
    file: UploadFile = File(...),
    pages: str = Form(...),
) -> FileResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out = _out(batch_id, "removed_pages.pdf")
    try:
        pdf_tools.remove_pages(src, pages, out)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, "removed_pages.pdf")


@app.post("/convert/rotate-pdf")
async def api_rotate_pdf(
    file: UploadFile = File(...),
    degrees: int = Form(90),
) -> FileResponse:
    if degrees not in (90, 180, 270):
        raise HTTPException(status_code=400, detail="Degrees must be 90, 180, or 270.")
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out = _out(batch_id, "rotated.pdf")
    try:
        pdf_tools.rotate_pdf(src, degrees, out)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, "rotated.pdf")


# ─────────────────────────────────────────────
# PDF Optimize
# ─────────────────────────────────────────────

@app.post("/convert/compress-pdf")
async def api_compress_pdf(file: UploadFile = File(...)) -> FileResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out = _out(batch_id, "compressed.pdf")
    try:
        pdf_tools.compress_pdf(src, out)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, "compressed.pdf")


@app.post("/convert/repair-pdf")
async def api_repair_pdf(file: UploadFile = File(...)) -> FileResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out = _out(batch_id, "repaired.pdf")
    try:
        pdf_tools.repair_pdf(src, out)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, "repaired.pdf")


# ─────────────────────────────────────────────
# PDF Edit
# ─────────────────────────────────────────────

@app.post("/convert/add-page-numbers")
async def api_add_page_numbers(
    file: UploadFile = File(...),
    position: str = Form("bottom-center"),
) -> FileResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out = _out(batch_id, "numbered.pdf")
    try:
        pdf_tools.add_page_numbers(src, out, position=position)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, "numbered.pdf")


@app.post("/convert/watermark-pdf")
async def api_watermark_pdf(
    file: UploadFile = File(...),
    watermark: str = Form(...),
    position: str = Form("center"),
    font_size: int = Form(40),
) -> FileResponse:
    if not watermark.strip():
        raise HTTPException(status_code=400, detail="Watermark text is required.")
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out = _out(batch_id, "watermarked.pdf")
    try:
        pdf_tools.add_watermark(src, watermark.strip(), out, position=position, font_size=font_size)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, "watermarked.pdf")


# ─────────────────────────────────────────────
# PDF Security
# ─────────────────────────────────────────────

@app.post("/convert/protect-pdf")
async def api_protect_pdf(
    file: UploadFile = File(...),
    password: str = Form(...),
) -> FileResponse:
    if not password.strip():
        raise HTTPException(status_code=400, detail="Password is required.")
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out = _out(batch_id, "protected.pdf")
    try:
        pdf_tools.protect_pdf(src, password.strip(), out)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, "protected.pdf")


@app.post("/convert/unlock-pdf")
async def api_unlock_pdf(
    file: UploadFile = File(...),
    password: str = Form(""),
) -> FileResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out = _out(batch_id, "unlocked.pdf")
    try:
        pdf_tools.unlock_pdf(src, password.strip(), out)
    except Exception as exc:
        msg = str(exc).lower()
        if "password" in msg or "decrypt" in msg or "encrypted" in msg:
            raise HTTPException(status_code=422, detail="Incorrect password. Please check the password and try again.")
        raise HTTPException(status_code=500, detail="Could not unlock PDF. The file may be corrupted or in an unsupported format.")
    return _file_response(out, "unlocked.pdf")


# ─────────────────────────────────────────────
# Convert FROM PDF
# ─────────────────────────────────────────────

@app.post("/convert/pdf-to-word")
async def api_pdf_to_word(
    file: UploadFile = File(...),
    engine: str = Form("fidelity"),
    auto_pair_small_pages: bool = Form(True),
) -> FileResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out = _out(batch_id, "converted.docx")
    try:
        pdf_tools.pdf_to_word(src, out, engine=engine, auto_pair_small_pages=auto_pair_small_pages)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, "converted.docx")


@app.post("/convert/pdf-to-text")
async def api_pdf_to_text(
    file: UploadFile = File(...),
    engine: str = Form("basic"),
) -> FileResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out = _out(batch_id, "converted.txt")
    try:
        pdf_tools.pdf_to_text(src, out, engine=engine)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, "converted.txt")


@app.post("/convert/pdf-to-word/plan")
async def api_pdf_to_word_plan(
    file: UploadFile = File(...),
    auto_pair_small_pages: bool = Form(True),
) -> JSONResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    try:
        plan = pdf_tools.pdf_fidelity_plan(
            src,
            target="word",
            auto_pair_small_pages=auto_pair_small_pages,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return JSONResponse(plan)


@app.post("/convert/pdf-to-excel")
async def api_pdf_to_excel(
    file: UploadFile = File(...),
    engine: str = Form("fidelity"),
) -> FileResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out = _out(batch_id, "converted.xlsx")
    try:
        pdf_tools.pdf_to_excel(src, out, engine=engine)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, "converted.xlsx")


@app.post("/convert/pdf-to-excel/plan")
async def api_pdf_to_excel_plan(
    file: UploadFile = File(...),
) -> JSONResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    try:
        plan = pdf_tools.pdf_to_excel_plan(src)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return JSONResponse(plan)


@app.post("/convert/pdf/profile")
async def api_pdf_profile(file: UploadFile = File(...)) -> JSONResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    try:
        profile = pdf_tools.pdf_document_profile(src)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return JSONResponse(profile)


@app.post("/convert/pdf-to-images")
async def api_pdf_to_images(
    file: UploadFile = File(...),
    fmt: str = Form("jpg"),
) -> StreamingResponse:
    if fmt not in ("jpg", "png"):
        raise HTTPException(status_code=400, detail="Format must be jpg or png.")
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out_dir = OUTPUT_DIR / batch_id
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        imgs = pdf_tools.pdf_to_images(src, out_dir, fmt)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if len(imgs) == 1:
        return _file_response(imgs[0], imgs[0].name)
    return _zip_response(imgs, "pdf_images.zip")


@app.post("/convert/pdf-to-svg")
async def api_pdf_to_svg(
    file: UploadFile = File(...),
    export_mode: str = Form("single"),
    page: int = Form(1),
    text_as_path: bool = Form(False),
    auto_pair_small_pages: bool = Form(True),
):
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out_dir = OUTPUT_DIR / batch_id
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        outputs = pdf_tools.pdf_to_svg(
            src,
            out_dir,
            export_mode=export_mode,
            page_number=page - 1,
            text_as_path=text_as_path,
            auto_pair_small_pages=auto_pair_small_pages,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if len(outputs) == 1:
        return _file_response(outputs[0], outputs[0].name)
    return _zip_response(outputs, "pdf_svg_exports.zip")


@app.post("/convert/pdf-to-svg/plan")
async def api_pdf_to_svg_plan(
    file: UploadFile = File(...),
    export_mode: str = Form("single"),
    page: int = Form(1),
    auto_pair_small_pages: bool = Form(True),
) -> JSONResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    try:
        plan = pdf_tools.pdf_to_svg_plan(
            src,
            export_mode=export_mode,
            page_number=page - 1,
            auto_pair_small_pages=auto_pair_small_pages,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return JSONResponse(plan)


# ─────────────────────────────────────────────
# Convert TO PDF
# ─────────────────────────────────────────────

@app.post("/convert/images-to-pdf")
async def api_images_to_pdf(files: list[UploadFile] = File(...)) -> FileResponse:
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one image.")
    batch_id, batch_dir = _batch()
    saved = _save_uploads(files, batch_dir)
    out = _out(batch_id, "images.pdf")
    try:
        pdf_tools.images_to_pdf(saved, out)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, "images.pdf")


@app.post("/convert/word-to-pdf")
async def api_word_to_pdf(file: UploadFile = File(...)) -> FileResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out = _out(batch_id, "converted.pdf")
    try:
        pdf_tools.word_to_pdf(src, out)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, "converted.pdf")


@app.post("/convert/pptx-to-pdf")
async def api_pptx_to_pdf(
    file: UploadFile = File(...),
    engine: str = Form("powerpoint"),
    paper_size: str = Form("a4"),
    orientation: str = Form("portrait"),
    margin_mm: str = Form("15"),
    slides_per_page: str = Form("1"),
) -> FileResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out = _out(batch_id, "converted.pdf")
    try:
        pdf_tools.pptx_to_pdf(
            src, out,
            engine=engine,
            paper_size=paper_size,
            orientation=orientation,
            margin_mm=int(margin_mm),
            slides_per_page=int(slides_per_page),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, "converted.pdf")


@app.post("/convert/excel-to-pdf")
async def api_excel_to_pdf(
    file: UploadFile = File(...),
    engine: str = Form("excel"),
    paper_size: str = Form("a4"),
    orientation: str = Form("landscape"),
    margin_mm: str = Form("10"),
    fit_columns: str = Form("0"),
    fit_pages_wide: str = Form("0"),
) -> FileResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out = _out(batch_id, "converted.pdf")
    try:
        pdf_tools.excel_to_pdf(
            src, out,
            engine=engine,
            paper_size=paper_size,
            orientation=orientation,
            margin_mm=int(margin_mm),
            fit_columns=(fit_columns == "1"),
            fit_pages_wide=int(fit_pages_wide),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, "converted.pdf")


@app.post("/convert/html-to-pdf")
async def api_html_to_pdf(file: UploadFile = File(...)) -> FileResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out = _out(batch_id, "converted.pdf")
    try:
        pdf_tools.html_to_pdf(src, out)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, "converted.pdf")


@app.post("/convert/summarize-pdf")
async def api_summarize_pdf(
    file: UploadFile = File(...),
    engine: str = Form("auto"),
    length: str = Form("standard"),
    output_format: str = Form("txt"),
) -> FileResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    ext = "pdf" if output_format == "pdf" else ("docx" if output_format == "docx" else "txt")
    out = _out(batch_id, f"summary.{ext}")
    try:
        pdf_tools.summarize_pdf(src, out, engine=engine, length=length, output_format=output_format)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, f"summary.{ext}")


@app.post("/convert/translate-pdf")
async def api_translate_pdf(
    file: UploadFile = File(...),
    engine: str = Form("auto"),
    language: str = Form("Spanish"),
    output_format: str = Form("docx"),
) -> FileResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    ext = "pdf" if output_format == "pdf" else "docx"
    out = _out(batch_id, f"translated.{ext}")
    try:
        pdf_tools.translate_pdf(src, out, engine=engine, language=language, output_format=output_format)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, f"translated.{ext}")


@app.post("/convert/pdf-to-pptx")
async def api_pdf_to_pptx(
    file: UploadFile = File(...),
    engine: str = Form("fidelity"),
    auto_pair_small_pages: bool = Form(True),
) -> FileResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out = _out(batch_id, "converted.pptx")
    try:
        pdf_tools.pdf_to_pptx(src, out, engine=engine, auto_pair_small_pages=auto_pair_small_pages)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, "converted.pptx")


@app.post("/convert/pdf-to-pptx/plan")
async def api_pdf_to_pptx_plan(
    file: UploadFile = File(...),
    auto_pair_small_pages: bool = Form(True),
) -> JSONResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    try:
        plan = pdf_tools.pdf_fidelity_plan(
            src,
            target="pptx",
            auto_pair_small_pages=auto_pair_small_pages,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return JSONResponse(plan)


@app.post("/convert/crop-pdf")
async def api_crop_pdf(
    file: UploadFile = File(...),
    left_mm: float = Form(0),
    top_mm: float = Form(0),
    right_mm: float = Form(0),
    bottom_mm: float = Form(0),
) -> FileResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out = _out(batch_id, "cropped.pdf")
    try:
        pdf_tools.crop_pdf(src, out, left_mm=left_mm, top_mm=top_mm, right_mm=right_mm, bottom_mm=bottom_mm)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, "cropped.pdf")


@app.post("/convert/redact-pdf")
async def api_redact_pdf(
    file: UploadFile = File(...),
    phrases: str = Form(...),
) -> FileResponse:
    phrase_list = [p for p in phrases.splitlines() if p.strip()]
    if not phrase_list:
        raise HTTPException(status_code=400, detail="Provide at least one word or phrase to redact.")
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out = _out(batch_id, "redacted.pdf")
    try:
        count = pdf_tools.redact_pdf(src, out, phrase_list)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if count == 0:
        raise HTTPException(status_code=400, detail="None of the phrases were found in the PDF.")
    return _file_response(out, "redacted.pdf")


@app.post("/convert/compare-pdf")
async def api_compare_pdf(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
) -> FileResponse:
    batch_id, batch_dir = _batch()
    src_a = _save_upload(file_a, batch_dir)
    src_b = _save_upload(file_b, batch_dir)
    out = _out(batch_id, "comparison.html")
    try:
        pdf_tools.compare_pdfs(src_a, src_b, out)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, "comparison.html")


@app.post("/convert/pdf-to-pdfa")
async def api_pdf_to_pdfa(file: UploadFile = File(...)) -> FileResponse:
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out = _out(batch_id, "converted_pdfa.pdf")
    try:
        pdf_tools.pdf_to_pdfa(src, out)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, "converted_pdfa.pdf")


# ─────────────────────────────────────────────
# Organize PDF  (thumbnail upload + reorder)
# ─────────────────────────────────────────────

@app.post("/convert/edit-pdf/upload")
async def api_edit_pdf_upload(file: UploadFile = File(...)) -> JSONResponse:
    batch_id, batch_dir = _batch()
    orig = batch_dir / "original.pdf"
    with orig.open("wb") as buf:
        shutil.copyfileobj(file.file, buf)
    try:
        previews = pdf_tools.render_pdf_edit_previews(orig, batch_dir, dpi=96)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not prepare edit previews: {exc}")

    pages = []
    for page in previews:
        thumb_path = Path(page["thumb_path"])
        b64 = base64.b64encode(thumb_path.read_bytes()).decode()
        pages.append(
            {
                "index": page["index"],
                "page_number": page["page_number"],
                "thumb": f"data:image/png;base64,{b64}",
                "page_width_pt": page["page_width_pt"],
                "page_height_pt": page["page_height_pt"],
                "thumb_width_px": page["thumb_width_px"],
                "thumb_height_px": page["thumb_height_px"],
                "text_blocks": page.get("text_blocks", []),
            }
        )
        thumb_path.unlink(missing_ok=True)
    return JSONResponse({"batch_id": batch_id, "pages": pages})


@app.get("/convert/edit-pdf/session/{batch_id}")
async def api_edit_pdf_session(batch_id: str) -> JSONResponse:
    batch_id = _validated_batch_id(batch_id)
    orig = UPLOAD_DIR / batch_id / "original.pdf"
    if not orig.exists():
        raise HTTPException(status_code=410, detail="Session expired. Please re-upload your PDF.")
    try:
        previews = pdf_tools.render_pdf_edit_previews(orig, orig.parent, dpi=96)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not restore edit previews: {exc}")

    pages = []
    for page in previews:
        thumb_path = Path(page["thumb_path"])
        b64 = base64.b64encode(thumb_path.read_bytes()).decode()
        pages.append(
            {
                "index": page["index"],
                "page_number": page["page_number"],
                "thumb": f"data:image/png;base64,{b64}",
                "page_width_pt": page["page_width_pt"],
                "page_height_pt": page["page_height_pt"],
                "thumb_width_px": page["thumb_width_px"],
                "thumb_height_px": page["thumb_height_px"],
                "text_blocks": page.get("text_blocks", []),
            }
        )
        thumb_path.unlink(missing_ok=True)
    return JSONResponse({"batch_id": batch_id, "pages": pages})


@app.get("/convert/edit-pdf/original/{batch_id}")
async def api_edit_pdf_original(batch_id: str):
    """Return the raw original PDF so the client can load it into pdf.js (Phase 1)."""
    from fastapi.responses import FileResponse as _FileResponse
    batch_id = _validated_batch_id(batch_id)
    orig = UPLOAD_DIR / batch_id / "original.pdf"
    if not orig.exists():
        raise HTTPException(status_code=410, detail="Session expired. Please re-upload your PDF.")
    return _FileResponse(str(orig), media_type="application/pdf")


@app.post("/convert/edit-pdf/ai-fix")
async def api_edit_pdf_ai_fix(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Expected JSON body.")
    text   = str(body.get("text", "")).strip()
    action = str(body.get("action", "")).strip()
    engine = str(body.get("engine", "auto")).strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required.")
    if not action:
        raise HTTPException(status_code=400, detail="action is required.")
    try:
        result = pdf_tools.ai_fix_text(text, action, engine)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return JSONResponse({"result": result})


@app.post("/convert/edit-pdf/ai-stamp")
async def api_edit_pdf_ai_stamp(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Expected JSON body.")
    batch_id = _validated_batch_id(body.get("batch_id", ""))
    engine   = str(body.get("engine", "auto")).strip()
    orig = UPLOAD_DIR / batch_id / "original.pdf"
    if not orig.exists():
        raise HTTPException(status_code=410, detail="Session expired. Please re-upload your PDF.")
    try:
        import fitz  # type: ignore
        doc  = fitz.open(str(orig))
        text = doc[0].get_text().strip()[:3000] if len(doc) else ""
        doc.close()
        stamp = pdf_tools.ai_suggest_stamp(text, engine)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return JSONResponse({"stamp": stamp})


@app.post("/convert/organize-pdf/upload")
async def api_organize_upload(file: UploadFile = File(...)) -> JSONResponse:
    batch_id, batch_dir = _batch()
    orig = batch_dir / "original.pdf"
    with orig.open("wb") as buf:
        shutil.copyfileobj(file.file, buf)
    try:
        thumbs = pdf_tools.render_pdf_thumbnails(orig, batch_dir, dpi=72)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not render pages: {exc}")
    pages = []
    for i, p in enumerate(thumbs):
        b64 = base64.b64encode(p.read_bytes()).decode()
        pages.append({"index": i, "thumb": f"data:image/png;base64,{b64}"})
        p.unlink()
    return JSONResponse({"batch_id": batch_id, "pages": pages})


@app.post("/convert/organize-pdf")
async def api_organize_reorder(request: Request) -> FileResponse:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Expected JSON body.")
    batch_id = _validated_batch_id(body.get("batch_id", ""))
    page_order = body.get("page_order", [])
    if not isinstance(page_order, list) or not page_order:
        raise HTTPException(status_code=400, detail="page_order is required.")
    orig = UPLOAD_DIR / batch_id / "original.pdf"
    if not orig.exists():
        raise HTTPException(status_code=410, detail="Session expired. Please re-upload your PDF.")
    out = _out(batch_id, "organized.pdf")
    try:
        pdf_tools.organize_pdf(orig, out, [int(i) for i in page_order])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, "organized.pdf")


# ─────────────────────────────────────────────
# Sign PDF
# ─────────────────────────────────────────────

@app.post("/convert/sign-pdf")
async def api_sign_pdf(
    file: UploadFile = File(...),
    signature_data: str = Form(...),
    position: str = Form("bottom-right"),
    page_number: int = Form(-1),
    sig_width_mm: float = Form(60),
) -> FileResponse:
    if not signature_data.startswith("data:image/png;base64,"):
        raise HTTPException(status_code=400, detail="Invalid signature data.")
    try:
        png_bytes = base64.b64decode(signature_data.split(",", 1)[1])
    except Exception:
        raise HTTPException(status_code=400, detail="Could not decode signature image.")
    batch_id, batch_dir = _batch()
    src = _save_upload(file, batch_dir)
    out = _out(batch_id, "signed.pdf")
    try:
        pdf_tools.sign_pdf(src, out, png_bytes, position=position, page_number=page_number, sig_width_mm=sig_width_mm)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _file_response(out, "signed.pdf")
