# ConvertFlow — Build & QA Plan

Goal: surpass ilovePDF with a fully local, AI-powered document tool suite.

---

## Current QA status (2026-04-09)

- Build scope is complete for all planned tools in Phases 1-3.
- `Edit PDF` is now live as an overlay editor with text, image, whiteout, signature, stamp, shape, highlight, link, multi-select, undo/redo, zoom, fit modes, and local session restore.
- Automated coverage exists for Sections A-C in `test_all_tools.py`.
- Verified on 2026-04-08:
  - Basic/local PDF operations passed targeted automated checks.
  - The explicit Ollama-backed routes were hardened so they no longer hard-fail when the local model returns `memory layout cannot be allocated`.
  - In that runtime-failure case, Ollama routes now degrade to the next available extraction or AI path instead of crashing.
- Remaining work:
  - Finish Section D browser/UI manual QA in `QA_MANUAL.md`.
  - Finish Section E real-document Ollama quality QA.
  - Optionally replace the current local Ollama model with one that can reliably serve multimodal requests on this machine.

---

## Sprint completed (2026-04-09)

Focus: improve real-user output quality for the hardest workflows instead of adding broad new surface area.

### 1. Office-conversion quality ✅

- **PDF to Word basic engine** — now detects headings (short ALL-CAPS lines), bullet lists (`-`, `*`, `•`), and numbered lists (`1.`, `2)`) using regex; applies correct DOCX styles instead of dumping plain paragraphs.
- **PDF to PowerPoint basic engine** — smarter title detection (skips page numbers, "Section X", single-digit lines); increased body to 8 bullets at 150 chars each.
- **PDF to Excel basic engine** — fitz document now properly closed after extraction (was a file-handle leak).

### 2. Edit PDF UX hardening ✅

- **Session timeout warning** — after 2 h 30 min a dismissable banner appears warning the session expires in 30 min; countdown updates every minute. Upload timestamp is persisted in localStorage so the warning also fires correctly after a page reload or session restore.
- **Stale session on 410** — already handled correctly; session is cleared from localStorage and the UI recovers gracefully.

### 3. Performance and packaging ✅

- **fitz document leaks fixed** — `render_pdf_edit_previews`, `pdf_to_excel` basic, `pdf_to_pptx` basic, and `pdf_to_pptx` github/openai paths all now close the fitz document in a `try/finally` block, preventing file-handle exhaustion under load.
- **200 MB upload cap** — `_save_upload` now streams in 64 KB chunks and raises HTTP 413 if the limit is exceeded, preventing runaway disk usage.
- **Hourly temp cleanup** — a background daemon thread runs `_cleanup_tmp()` every hour (previously only ran once at startup), keeping `.tmp/` from growing unbounded between restarts.

### 4. Real-document QA pass

- Pending manual testing — run the tools against business cards, CAD sheets, long company profiles, and scanned documents; record results in `QA_MANUAL.md`.

---

## Current tool status

| # | Tool | Route | Engines | Status |
|---|---|---|---|---|
| 1 | Merge PDF | /tool/merge-pdf | — | ✅ Done |
| 2 | Split PDF | /tool/split-pdf | — | ✅ Done |
| 3 | Extract Pages | /tool/extract-pages | — | ✅ Done |
| 4 | Remove Pages | /tool/remove-pages | — | ✅ Done |
| 5 | Rotate PDF | /tool/rotate-pdf | — | ✅ Done |
| 6 | Compress PDF | /tool/compress-pdf | — | ✅ Done |
| 7 | Repair PDF | /tool/repair-pdf | — | ✅ Done |
| 8 | Images to PDF | /tool/images-to-pdf | — | ✅ Done |
| 9 | Word to PDF | /tool/word-to-pdf | — | ✅ Done |
| 10 | PowerPoint to PDF | /tool/pptx-to-pdf | — | ✅ Done |
| 11 | Excel to PDF | /tool/excel-to-pdf | — | ✅ Done |
| 12 | HTML to PDF | /tool/html-to-pdf | — | ✅ Done |
| 13 | PDF to Word | /tool/pdf-to-word | basic / ollama / auto | ✅ Done |
| 14 | PDF to Text | /tool/pdf-to-text | basic / ollama / auto | ✅ Done |
| 15 | PDF to Excel | /tool/pdf-to-excel | basic / ollama / auto | ✅ Done |
| 16 | PDF to Images | /tool/pdf-to-images | — | ✅ Done |
| 17 | PDF to PDF/A | /tool/pdf-to-pdfa | — | ✅ Done |
| 18 | Add Page Numbers | /tool/add-page-numbers | — | ✅ Done |
| 19 | Watermark PDF | /tool/watermark-pdf | — | ✅ Done |
| 20 | Crop PDF | /tool/crop-pdf | — | ✅ Done |
| 21 | Protect PDF | /tool/protect-pdf | — | ✅ Done |
| 22 | Unlock PDF | /tool/unlock-pdf | — | ✅ Done |
| 23 | Image to Document | /tool/image-to-doc | tesseract / ollama / openai / github / auto | ✅ Done |
| 24 | Edit PDF | /tool/edit-pdf | overlay editor | ✅ Done |
| 27 | Redact PDF | /tool/redact-pdf | — | ✅ Done |
| 28 | Compare PDF | /tool/compare-pdf | — | ✅ Done |
| 29 | Organize PDF | /tool/organize-pdf | — | ✅ Done |
| 30 | Sign PDF | /tool/sign-pdf | — | ✅ Done |

---

## Remaining tools — build order

### Phase 1 — Easy (Ollama prompt jobs) ✅ DONE

| # | Tool | Route | Approach | Output |
|---|---|---|---|---|
| 24 | AI Summarizer | /tool/summarize-pdf | Pages → Ollama "summarize" prompt → .txt / .docx / .pdf | txt, docx, pdf |
| 25 | Translate PDF | /tool/translate-pdf | Pages → Ollama "translate to [lang]" → rebuild doc | docx, pdf |
| 26 | PDF to PowerPoint | /tool/pdf-to-pptx | Text per page → detect title + bullets → python-pptx | .pptx |

---

### Phase 2 — Medium (new logic, no heavy UI) ✅ DONE

| # | Tool | Route | Approach |
|---|---|---|---|
| 27 | Redact PDF | /tool/redact-pdf | User types phrases → pymupdf searches + permanently blacks them out |
| 28 | Compare PDF | /tool/compare-pdf | Upload 2 PDFs → extract text → difflib → HTML diff report download |

**Redact approach:**
- Form: file upload + textarea of lines/phrases to redact
- Backend: `fitz.Page.search_for(phrase)` → `page.add_redact_annot()` → `page.apply_redactions()`
- Output: redacted PDF

**Compare approach:**
- Form: two file uploads
- Backend: extract text from both with pymupdf → `difflib.HtmlDiff` → save as `.html`
- Output: side-by-side HTML diff file

---

### Phase 3 — Complex UI (significant frontend work) ✅ DONE

| # | Tool | Route | Approach |
|---|---|---|---|
| 29 | Organize PDF | /tool/organize-pdf | Upload → render page thumbnails → JS drag-to-reorder → reorder via pypdf |
| 30 | Sign PDF | /tool/sign-pdf | HTML canvas signature pad → save as image → embed into PDF via pymupdf |

**Organize approach:**
- Upload PDF → server renders page thumbnails with pymupdf at low DPI
- Return thumbnail URLs to frontend
- JS: sortable grid (use native HTML5 drag-and-drop or SortableJS)
- On submit: send new page order as JSON → pypdf reorders → download
- New endpoint: `POST /convert/organize-pdf` body: `{file, page_order: [2,0,1,3]}`

**Sign approach:**
- HTML `<canvas>` for drawing signature
- "Clear" and "Download preview" buttons
- On submit: canvas → base64 PNG → server embeds at selected position in PDF
- Position selector: top-left / top-right / bottom-left / bottom-right / center

---

### Phase 4 — Defer

| Tool | Reason |
|---|---|
| Scan to PDF | Needs camera API + mobile UX — separate project |

---

## QA Checklist

Run this checklist after any significant change or before releasing to another device.

### A. Smoke test (all tools return output)
Run `python test_all_tools.py` from the project root.
Each test creates a sample input, calls the tool function directly, and checks that the output file exists and is non-zero bytes.

Status note:
- This section is automated in `test_all_tools.py` and was used as the main regression suite on 2026-04-08.
- On this machine, explicit Ollama tests may complete via fallback behavior if the configured local model cannot allocate runtime memory.

**Tools to cover:**
- [ ] merge_pdf
- [ ] split_pdf
- [ ] extract_pages
- [ ] remove_pages
- [ ] rotate_pdf
- [ ] compress_pdf
- [ ] repair_pdf
- [ ] images_to_pdf
- [ ] word_to_pdf
- [ ] pptx_to_pdf
- [ ] excel_to_pdf
- [ ] html_to_pdf
- [ ] pdf_to_word (basic)
- [ ] pdf_to_word (ollama) — skip if Ollama offline
- [ ] pdf_to_text (basic)
- [ ] pdf_to_text (ollama) — skip if Ollama offline
- [ ] pdf_to_excel (basic)
- [ ] pdf_to_excel (ollama) — skip if Ollama offline
- [ ] pdf_to_images
- [ ] pdf_to_pdfa
- [ ] add_page_numbers
- [ ] add_watermark
- [ ] crop_pdf
- [ ] protect_pdf
- [ ] unlock_pdf

### B. Engine fallback test
- [ ] Set `engine="auto"` with Ollama running → result uses Ollama
- [ ] Set `engine="auto"` with Ollama stopped → result uses basic silently
- [ ] Set `engine="ollama"` with Ollama stopped → returns clear error message
- [ ] Set `engine="basic"` → never touches Ollama

Status note:
- This section is automated in `test_all_tools.py`.

### C. Edge case tests
- [ ] Empty PDF (0 pages) → returns a clear error, not a crash
- [ ] Encrypted PDF with wrong password → clear error message
- [ ] Single-page PDF through split → returns 1 file, not a zip
- [ ] 0-byte uploaded file → validation error before processing
- [ ] Very long page spec (e.g. "1-999" on a 3-page PDF) → clear range error

Status note:
- This section is automated in `test_all_tools.py`.

### D. Browser / UI checks
- [ ] Every tool page loads without JS errors
- [ ] Upload zone accepts click AND drag-and-drop
- [ ] Form submits and triggers download
- [ ] PDF extras panel shows/hides correctly on image-to-doc page
- [ ] Engine dropdown appears on PDF to Word, PDF to Text, PDF to Excel
- [ ] Search on homepage filters cards correctly
- [ ] Category filter chips work

### E. Ollama quality checks (manual, run when Ollama is on)
Test each with a real-world scanned document:
- [ ] PDF to Word (ollama): headings detected, lists formatted, not a wall of text
- [ ] PDF to Text (ollama): clean readable output, columns not garbled
- [ ] PDF to Excel (ollama): table headers detected, rows correct
- [ ] Image to Document (ollama): OCR accurate on a scanned invoice or contract

Status note:
- Manual quality verification is still required even though runtime fallbacks now prevent hard failures.
- If the current Ollama model continues returning `memory layout cannot be allocated`, swap models before claiming stable fully local multimodal OCR.

---

## What makes us better than ilovePDF

| Feature | ilovePDF | ConvertFlow |
|---|---|---|
| Privacy | Files go to their cloud | 100% local — nothing leaves the machine |
| AI OCR | Cloud API, costs credits | Gemma 4 via Ollama — free, unlimited, offline |
| Scanned PDFs | Costs credits | Free with Ollama engine |
| File size limit | Yes (free tier) | None |
| Account required | Yes for history | No |
| PDF to Text | Not available | ✅ |
| AI on all conversions | No | Every conversion has basic / ollama / auto |
| Customisable | No | Full control — change prompts, add tools |
| Branding / white-label | No | Yes |

---

## How to start the app

```
Double-click start.bat
```

- Starts Ollama in the background (skips if already running)
- Opens browser to http://localhost:8080 after 4 seconds
- Shows live logs in the terminal

```
Double-click stop.bat
```

- Kills the app (port 8080) and Ollama

---

## Environment

- Python venv: `.venv/Scripts/python.exe`
- Ollama models: `D:\.ollama\models`
- OCR model: `gemma4:e4b` (set via `OLLAMA_OCR_MODEL` env var)
- App port: `8080`
- Temp files: `.tmp/` (auto-cleaned after 3 hours)
