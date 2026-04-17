# LibreOffice Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Insert LibreOffice headless as a high-fidelity Office→PDF fallback engine that works on Linux, where Windows COM automation is unavailable.

**Architecture:** A single shared helper `_office_to_pdf_via_libreoffice()` shells out to `soffice --headless --convert-to pdf` using a temp directory, then moves the result to the requested output path. A guard function `_libreoffice_available()` checks PATH. Both are inserted near `_powerpoint_available()`. Three public engine chains (`word_to_pdf`, `pptx_to_pdf`, `excel_to_pdf`) each get one new `if _libreoffice_available()` block inserted between the COM engine and the AI/Basic engines.

**Tech Stack:** Python stdlib only (`shutil`, `subprocess`, `tempfile`, `pathlib`). No new packages. LibreOffice must be installed as a system package (`apt-get install -y libreoffice`).

---

## File Map

| File | Action | What changes |
|---|---|---|
| `execution/pdf_tools.py` | Modify | Add 2 functions after line 3229; add 1 engine entry in `word_to_pdf` (line 2691); add 1 engine entry in `pptx_to_pdf` (after line 3456); add 1 engine entry in `excel_to_pdf` (after line 3589) |

**No other files change.**

---

## Task 1: Add `_libreoffice_available()` and `_office_to_pdf_via_libreoffice()`

**Files:**
- Modify: `execution/pdf_tools.py:3229-3230`

These two functions go immediately after `_powerpoint_available()` closes at line 3229.

- [ ] **Step 1: Open `execution/pdf_tools.py` and locate the insertion point**

Find this exact block (lines 3220–3229):
```python
def _powerpoint_available() -> bool:
    """Return True if PowerPoint COM automation is usable."""
    try:
        import win32com.client, pythoncom  # noqa: F401
        import winreg
        winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\POWERPNT.EXE")
        return True
    except Exception:
        return False
```

- [ ] **Step 2: Insert both new functions after line 3229 (the `return False` line of `_powerpoint_available`)**

The `old_string` for the Edit tool is the blank line after `_powerpoint_available` followed by `_PPTX_TO_PDF_SLIDE_PROMPT`. Insert the two new functions between them:

**old_string** (lines 3229–3231):
```python
    except Exception:
        return False

_PPTX_TO_PDF_SLIDE_PROMPT = (
```

**new_string:**
```python
    except Exception:
        return False


def _libreoffice_available() -> bool:
    """Return True if LibreOffice (soffice) is on PATH."""
    return shutil.which("soffice") is not None or shutil.which("libreoffice") is not None


def _office_to_pdf_via_libreoffice(input_path: Path, output_path: Path) -> None:
    """Convert any Office file → PDF using LibreOffice headless.

    Works on Linux, macOS, and Windows wherever soffice is on PATH.
    Does NOT honour slides_per_page, paper_size, or orientation —
    uses the document's own settings. The _conversion_pipeline QA check
    will fall through to the AI engine if layout is wrong.
    """
    with tempfile.TemporaryDirectory(prefix="cf_libre_") as tmp:
        tmp_path = Path(tmp)
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
                f"LibreOffice conversion failed: "
                f"{result.stderr.decode(errors='replace')[:200]}"
            )

        out_pdf = tmp_path / (src.stem + ".pdf")
        if not out_pdf.exists() or out_pdf.stat().st_size == 0:
            raise RuntimeError("LibreOffice produced no output.")

        shutil.copy2(str(out_pdf), str(output_path))


_PPTX_TO_PDF_SLIDE_PROMPT = (
```

- [ ] **Step 3: Add `import subprocess` to the top-level imports**

`shutil` and `tempfile` are already imported (lines 6–7). `subprocess` is missing. Add it:

**old_string** (lines 4–7):
```python
import io
import re
import shutil
import tempfile
```

**new_string:**
```python
import io
import re
import shutil
import subprocess
import tempfile
```

- [ ] **Step 4: Smoke-test the new functions in isolation**

```bash
cd "d:/Web App/Converter"
python - <<'EOF'
import sys
sys.path.insert(0, ".")
from execution.pdf_tools import _libreoffice_available, _office_to_pdf_via_libreoffice
print("_libreoffice_available():", _libreoffice_available())
EOF
```

Expected output (Linux with LibreOffice installed):
```
_libreoffice_available(): True
```

Expected output (Windows without LibreOffice):
```
_libreoffice_available(): False
```

No `ImportError` or `SyntaxError` is acceptable. If either appears, fix before proceeding.

- [ ] **Step 5: Commit**

```bash
git add "execution/pdf_tools.py"
git commit -m "feat: add _libreoffice_available and _office_to_pdf_via_libreoffice helpers"
```

---

## Task 2: Wire LibreOffice into `word_to_pdf`

**Files:**
- Modify: `execution/pdf_tools.py:2688-2692`

- [ ] **Step 1: Locate the current engine chain in `word_to_pdf` (lines 2688–2692)**

Verify it looks exactly like this:
```python
    engines: list[tuple[str, Callable[[Path], None]]] = []
    if _powerpoint_available():
        engines.append(("word_com", lambda o: _word_to_pdf_via_com(input_path, o)))
    engines.append(("basic", lambda o: _word_to_pdf_basic(input_path, o)))
    _conversion_pipeline(engines, output_path)
```

- [ ] **Step 2: Insert the LibreOffice engine between COM and Basic**

**old_string:**
```python
    engines: list[tuple[str, Callable[[Path], None]]] = []
    if _powerpoint_available():
        engines.append(("word_com", lambda o: _word_to_pdf_via_com(input_path, o)))
    engines.append(("basic", lambda o: _word_to_pdf_basic(input_path, o)))
    _conversion_pipeline(engines, output_path)
```

**new_string:**
```python
    engines: list[tuple[str, Callable[[Path], None]]] = []
    if _powerpoint_available():
        engines.append(("word_com", lambda o: _word_to_pdf_via_com(input_path, o)))
    if _libreoffice_available():
        engines.append(("libreoffice", lambda o: _office_to_pdf_via_libreoffice(input_path, o)))
    engines.append(("basic", lambda o: _word_to_pdf_basic(input_path, o)))
    _conversion_pipeline(engines, output_path)
```

- [ ] **Step 3: Also update the docstring inside `word_to_pdf` to document the new chain**

**old_string:**
```python
    """Convert Word → PDF.

    Engine chain (tried in order, each QA-checked by Ollama):
      1. Word COM — full fidelity: fonts, colors, images, tables, shapes
      2. Basic    — text-only fallback via python-docx + fpdf2
    """
```

**new_string:**
```python
    """Convert Word → PDF.

    Engine chain (tried in order, each QA-checked by Ollama):
      1. Word COM    — full fidelity: fonts, colors, images, tables, shapes (Windows + Office only)
      2. LibreOffice — high fidelity headless fallback (Linux / any platform with soffice on PATH)
      3. Basic       — text-only fallback via python-docx + fpdf2
    """
```

- [ ] **Step 4: Verify the function parses cleanly**

```bash
cd "d:/Web App/Converter"
python -c "from execution.pdf_tools import word_to_pdf; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add "execution/pdf_tools.py"
git commit -m "feat: add LibreOffice engine to word_to_pdf chain"
```

---

## Task 3: Wire LibreOffice into `pptx_to_pdf`

**Files:**
- Modify: `execution/pdf_tools.py:3453-3470`

- [ ] **Step 1: Locate the current engine chain in `pptx_to_pdf` (lines 3453–3470)**

Verify it looks exactly like this:
```python
    engines: list[tuple[str, Callable[[Path], None]]] = []

    if engine in ("powerpoint", "auto") and _powerpoint_available():
        engines.append(("powerpoint_com", lambda o: _pptx_to_pdf_via_com(input_path, o, slides_per_page=slides_per_page, orientation=orientation)))

    ai_engine = engine if engine in ("ollama", "github", "openai") else "auto"
    if engine not in ("basic",):
        engines.append((
            f"ai_{ai_engine}",
            lambda o: _pptx_to_pdf_ai(input_path, o, ai_engine, paper_size, orientation, margin_mm, slides_per_page),
        ))

    engines.append((
        "basic",
        lambda o: _pptx_to_pdf_basic(input_path, o, paper_size, orientation, margin_mm, slides_per_page),
    ))

    _conversion_pipeline(engines, output_path)
```

- [ ] **Step 2: Insert the LibreOffice engine after the COM block**

**old_string:**
```python
    engines: list[tuple[str, Callable[[Path], None]]] = []

    if engine in ("powerpoint", "auto") and _powerpoint_available():
        engines.append(("powerpoint_com", lambda o: _pptx_to_pdf_via_com(input_path, o, slides_per_page=slides_per_page, orientation=orientation)))

    ai_engine = engine if engine in ("ollama", "github", "openai") else "auto"
```

**new_string:**
```python
    engines: list[tuple[str, Callable[[Path], None]]] = []

    if engine in ("powerpoint", "auto") and _powerpoint_available():
        engines.append(("powerpoint_com", lambda o: _pptx_to_pdf_via_com(input_path, o, slides_per_page=slides_per_page, orientation=orientation)))

    if engine in ("powerpoint", "auto") and _libreoffice_available():
        engines.append(("libreoffice", lambda o: _office_to_pdf_via_libreoffice(input_path, o)))

    ai_engine = engine if engine in ("ollama", "github", "openai") else "auto"
```

- [ ] **Step 3: Update the docstring inside `pptx_to_pdf`**

**old_string:**
```python
    """Convert PowerPoint → PDF.

    Engine chain (tried in order, each QA-checked by Ollama):
      1. PowerPoint COM — full fidelity: colors, images, fonts, shapes, logos
      2. AI (ollama/github) — styled HTML per slide via AI
      3. Basic — plain text extraction via python-pptx + fpdf2
    """
```

**new_string:**
```python
    """Convert PowerPoint → PDF.

    Engine chain (tried in order, each QA-checked by Ollama):
      1. PowerPoint COM — full fidelity: colors, images, fonts, shapes, logos (Windows + Office only)
      2. LibreOffice    — high fidelity headless fallback; ignores slides_per_page/orientation (Linux)
      3. AI (ollama/github) — styled HTML per slide via AI
      4. Basic          — plain text extraction via python-pptx + fpdf2
    """
```

- [ ] **Step 4: Verify the function parses cleanly**

```bash
cd "d:/Web App/Converter"
python -c "from execution.pdf_tools import pptx_to_pdf; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add "execution/pdf_tools.py"
git commit -m "feat: add LibreOffice engine to pptx_to_pdf chain"
```

---

## Task 4: Wire LibreOffice into `excel_to_pdf`

**Files:**
- Modify: `execution/pdf_tools.py:3581-3603`

- [ ] **Step 1: Locate the current engine chain in `excel_to_pdf` (lines 3581–3603)**

Verify it looks exactly like this:
```python
    engines: list[tuple[str, Callable[[Path], None]]] = []

    if engine in ("excel", "auto") and _powerpoint_available():
        engines.append(("excel_com", lambda o: _excel_to_pdf_via_com(
            input_path, o,
            paper_size=paper_size,
            orientation=orientation,
            fit_pages_wide=fit_pages_wide,
        )))

    ai_engine = engine if engine in ("ollama", "github", "openai") else "auto"
    if engine not in ("basic",):
        engines.append((
            f"ai_{ai_engine}",
            lambda o: _excel_to_pdf_ai(input_path, o, ai_engine, paper_size, orientation, margin_mm),
        ))

    engines.append((
        "basic",
        lambda o: _excel_to_pdf_basic(input_path, o, paper_size, orientation, margin_mm, fit_columns),
    ))

    _conversion_pipeline(engines, output_path)
```

- [ ] **Step 2: Insert the LibreOffice engine after the COM block**

**old_string:**
```python
    engines: list[tuple[str, Callable[[Path], None]]] = []

    if engine in ("excel", "auto") and _powerpoint_available():
        engines.append(("excel_com", lambda o: _excel_to_pdf_via_com(
            input_path, o,
            paper_size=paper_size,
            orientation=orientation,
            fit_pages_wide=fit_pages_wide,
        )))

    ai_engine = engine if engine in ("ollama", "github", "openai") else "auto"
```

**new_string:**
```python
    engines: list[tuple[str, Callable[[Path], None]]] = []

    if engine in ("excel", "auto") and _powerpoint_available():
        engines.append(("excel_com", lambda o: _excel_to_pdf_via_com(
            input_path, o,
            paper_size=paper_size,
            orientation=orientation,
            fit_pages_wide=fit_pages_wide,
        )))

    if engine in ("excel", "auto") and _libreoffice_available():
        engines.append(("libreoffice", lambda o: _office_to_pdf_via_libreoffice(input_path, o)))

    ai_engine = engine if engine in ("ollama", "github", "openai") else "auto"
```

- [ ] **Step 3: Update the docstring inside `excel_to_pdf`**

**old_string:**
```python
    """Convert Excel → PDF.

    Engine chain (tried in order, each QA-checked by Ollama):
      1. Excel COM  — full fidelity: colors, charts, merged cells, formatting
      2. AI (ollama/github) — HTML table via AI
      3. Basic      — plain fpdf2 grid
    """
```

**new_string:**
```python
    """Convert Excel → PDF.

    Engine chain (tried in order, each QA-checked by Ollama):
      1. Excel COM   — full fidelity: colors, charts, merged cells, formatting (Windows + Office only)
      2. LibreOffice — high fidelity headless fallback; ignores paper_size/orientation (Linux)
      3. AI (ollama/github) — HTML table via AI
      4. Basic       — plain fpdf2 grid
    """
```

- [ ] **Step 4: Verify all three public functions parse cleanly**

```bash
cd "d:/Web App/Converter"
python -c "from execution.pdf_tools import word_to_pdf, pptx_to_pdf, excel_to_pdf; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Run the existing test suite**

```bash
cd "d:/Web App/Converter"
python test_all_tools.py
```

Expected: Word/PPTX/Excel tests are skipped (no LibreOffice on Windows dev machine) or pass (Linux). No new failures. `_libreoffice_available()` in the test file will correctly detect whether to skip.

- [ ] **Step 6: Final commit**

```bash
git add "execution/pdf_tools.py"
git commit -m "feat: add LibreOffice engine to excel_to_pdf chain

Completes LibreOffice fallback for all three Office→PDF tools.
Engine chains now: COM (Windows) → LibreOffice (Linux) → AI → Basic."
```

---

## Verification Checklist

After all tasks are done, confirm:

- [ ] `python -c "from execution.pdf_tools import _libreoffice_available, _office_to_pdf_via_libreoffice; print('OK')"` → OK
- [ ] `python -c "from execution.pdf_tools import word_to_pdf, pptx_to_pdf, excel_to_pdf; print('OK')"` → OK
- [ ] `python test_all_tools.py` → no new failures
- [ ] On Linux with LibreOffice: `_libreoffice_available()` returns `True` and word/pptx/excel tests pass without COM
- [ ] `grep -n "_libreoffice_available\|_office_to_pdf_via_libreoffice" execution/pdf_tools.py` → 8 matches (2 defs + 3 availability checks + 3 engine appends)

---

## Notes for Future Sessions

- `_powerpoint_available()` is defined at **line 3220** — the two new functions go immediately after its closing `return False` at line 3229
- `word_to_pdf` engine chain is at **lines 2688–2692**
- `pptx_to_pdf` engine chain is at **lines 3453–3470**
- `excel_to_pdf` engine chain is at **lines 3581–3603**
- These line numbers are from the version read on 2026-04-16. Always re-verify with a grep before editing.
- LibreOffice does NOT honour `slides_per_page`, `paper_size`, or `orientation` via CLI — this is intentional and documented. The QA pipeline handles it.
- The test file already contains `_libreoffice_available()` at line 369 — do NOT import it from the test file; the production version lives in `pdf_tools.py`.
