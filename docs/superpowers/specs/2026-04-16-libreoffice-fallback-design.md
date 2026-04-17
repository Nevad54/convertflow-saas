# Design: LibreOffice Fallback for Office→PDF Conversion

**Date:** 2026-04-16  
**Status:** Approved  
**Scope:** `execution/pdf_tools.py` only — no new files, no package changes

---

## Problem

ConvertFlow uses Windows COM automation (`pywin32`) to convert Word, Excel, and PowerPoint files to PDF with full fidelity. COM is Windows-only. Linux deployment (Docker on Railway/Hetzner) has no COM layer, so these three tools silently fall back to low-quality Basic engines.

**Goal:** Insert LibreOffice as a high-fidelity fallback that works on Linux, keeping COM as primary on Windows.

---

## Approach

Approach 1 — thin subprocess wrapper. A single reusable helper shells out to  
`soffice --headless --convert-to pdf <input> --outdir <tmpdir>`.  
No new packages. No new files. ~40 lines of code total.

---

## New Functions to Add

Both functions go near `_powerpoint_available()` (~line 3220 in `pdf_tools.py`).

### `_libreoffice_available() -> bool`

```python
import shutil

def _libreoffice_available() -> bool:
    """Return True if LibreOffice (soffice) is on PATH."""
    return shutil.which("soffice") is not None or shutil.which("libreoffice") is not None
```

### `_office_to_pdf_via_libreoffice(input_path: Path, output_path: Path) -> None`

```python
import shutil, subprocess, tempfile

def _office_to_pdf_via_libreoffice(input_path: Path, output_path: Path) -> None:
    """Convert any Office file → PDF using LibreOffice headless.

    Works on Linux, macOS, and Windows (wherever soffice is on PATH).
    Does NOT honour slides_per_page, paper_size, or orientation —
    uses whatever the document has set. The _conversion_pipeline QA
    check will fall through to the AI engine if layout is wrong.
    """
    with tempfile.TemporaryDirectory(prefix="cf_libre_") as tmp:
        tmp_path = Path(tmp)
        # Copy input so LibreOffice writes output next to it in our tmp dir
        src = tmp_path / input_path.name
        shutil.copy2(str(input_path), str(src))

        bin_name = "soffice" if shutil.which("soffice") else "libreoffice"
        result = subprocess.run(
            [bin_name, "--headless", "--convert-to", "pdf",
             str(src), "--outdir", str(tmp_path)],
            capture_output=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"LibreOffice conversion failed: {result.stderr.decode(errors='replace')[:200]}"
            )

        out_pdf = tmp_path / (src.stem + ".pdf")
        if not out_pdf.exists() or out_pdf.stat().st_size == 0:
            raise RuntimeError("LibreOffice produced no output.")

        shutil.copy2(str(out_pdf), str(output_path))
```

**Security notes:**
- subprocess called with a list, never `shell=True`
- `timeout=120` prevents hung processes
- Input is copied to a temp dir — source files are never modified

---

## Engine Chain Changes

All changes are inside the three public functions. No other code is touched.

### `word_to_pdf` (~line 2688)

**Before:**
```python
engines = []
if _powerpoint_available():
    engines.append(("word_com", lambda o: _word_to_pdf_via_com(input_path, o)))
engines.append(("basic", lambda o: _word_to_pdf_basic(input_path, o)))
```

**After:**
```python
engines = []
if _powerpoint_available():
    engines.append(("word_com", lambda o: _word_to_pdf_via_com(input_path, o)))
if _libreoffice_available():
    engines.append(("libreoffice", lambda o: _office_to_pdf_via_libreoffice(input_path, o)))
engines.append(("basic", lambda o: _word_to_pdf_basic(input_path, o)))
```

**Resulting chain:**
1. `word_com` — Windows + Office installed
2. `libreoffice` — Linux/Mac or Windows with LibreOffice
3. `basic` — always available

---

### `pptx_to_pdf` (~line 3453)

**Before:**
```python
engines = []
if engine in ("powerpoint", "auto") and _powerpoint_available():
    engines.append(("powerpoint_com", lambda o: _pptx_to_pdf_via_com(...)))
ai_engine = engine if engine in ("ollama", "github", "openai") else "auto"
if engine not in ("basic",):
    engines.append((f"ai_{ai_engine}", lambda o: _pptx_to_pdf_ai(...)))
engines.append(("basic", lambda o: _pptx_to_pdf_basic(...)))
```

**After:**
```python
engines = []
if engine in ("powerpoint", "auto") and _powerpoint_available():
    engines.append(("powerpoint_com", lambda o: _pptx_to_pdf_via_com(...)))
if engine in ("powerpoint", "auto") and _libreoffice_available():
    engines.append(("libreoffice", lambda o: _office_to_pdf_via_libreoffice(input_path, o)))
ai_engine = engine if engine in ("ollama", "github", "openai") else "auto"
if engine not in ("basic",):
    engines.append((f"ai_{ai_engine}", lambda o: _pptx_to_pdf_ai(...)))
engines.append(("basic", lambda o: _pptx_to_pdf_basic(...)))
```

**Resulting chain:**
1. `powerpoint_com` — Windows + PowerPoint installed
2. `libreoffice` — Linux/Mac (or Windows with LibreOffice), when engine="powerpoint" or "auto"
3. `ai_<engine>` — any platform, unless engine="basic"
4. `basic` — always available

---

### `excel_to_pdf` (~line 3581)

**Before:**
```python
engines = []
if engine in ("excel", "auto") and _powerpoint_available():
    engines.append(("excel_com", lambda o: _excel_to_pdf_via_com(...)))
ai_engine = engine if engine in ("ollama", "github", "openai") else "auto"
if engine not in ("basic",):
    engines.append((f"ai_{ai_engine}", lambda o: _excel_to_pdf_ai(...)))
engines.append(("basic", lambda o: _excel_to_pdf_basic(...)))
```

**After:**
```python
engines = []
if engine in ("excel", "auto") and _powerpoint_available():
    engines.append(("excel_com", lambda o: _excel_to_pdf_via_com(...)))
if engine in ("excel", "auto") and _libreoffice_available():
    engines.append(("libreoffice", lambda o: _office_to_pdf_via_libreoffice(input_path, o)))
ai_engine = engine if engine in ("ollama", "github", "openai") else "auto"
if engine not in ("basic",):
    engines.append((f"ai_{ai_engine}", lambda o: _excel_to_pdf_ai(...)))
engines.append(("basic", lambda o: _excel_to_pdf_basic(...)))
```

**Resulting chain:**
1. `excel_com` — Windows + Excel installed
2. `libreoffice` — Linux/Mac (or Windows with LibreOffice), when engine="excel" or "auto"
3. `ai_<engine>` — any platform, unless engine="basic"
4. `basic` — always available

---

## Known Limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| LibreOffice ignores `slides_per_page` | PPTX multi-slide layouts wrong | AI engine is #3 in chain; QA will fall through |
| LibreOffice ignores `paper_size`/`orientation` | Excel may use wrong page size | AI engine is #3 in chain; QA will fall through |
| LibreOffice cold-start ~3–5s | Slight latency on first conversion | Acceptable for SaaS async jobs |
| LibreOffice not installed | Engine silently skipped | `_libreoffice_available()` guard prevents errors |

---

## Docker / Deployment

Add to Dockerfile (no Python package changes):
```dockerfile
RUN apt-get update && apt-get install -y libreoffice --no-install-recommends && rm -rf /var/lib/apt/lists/*
```

---

## Test Coverage

`test_all_tools.py` already has `_libreoffice_available()` and skips Word/PPTX/Excel tests when LibreOffice is absent. No test changes needed — the existing skip logic validates the fallback chain correctly on both Windows and Linux.

---

## Files Changed

| File | Change |
|---|---|
| `execution/pdf_tools.py` | Add `_libreoffice_available()` + `_office_to_pdf_via_libreoffice()` near line 3220; update 3 engine chains |

**No other files change.**
