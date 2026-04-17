# ConvertFlow — Manual QA Checklist

Start the app first: double-click `start.bat`  
Browser opens at `http://localhost:8080`

---

## D. Browser / UI

Goal: a reviewer should understand ConvertFlow as a local-first document workspace, not just an OCR utility.

### D1. Homepage
- [x] Page loads, no red errors in browser console (F12 → Console)
- [x] Search box filters tool cards as you type
- [x] Category chips (Prepare PDFs, Convert documents, Recover scanned files, Review and finalize) filter cards correctly
- [x] Clicking a chip a second time clears the filter
- [x] Clicking any tool card navigates to the correct tool page

### D2. Upload zone (check on any tool page)
- [x] Clicking the upload zone opens the file picker
- [x] Dragging a file onto the zone highlights it, then accepts the file on drop
- [x] File name appears after upload

### D3. Engine dropdown (PDF to Word / PDF to Text / PDF to Excel)
- [x] Dropdown shows **Basic**, **Ollama**, **Auto** options
- [x] Selecting each option sticks before submitting

### D4. Image to Document extras panel
- [x] Uploading an image reveals the "PDF output options" panel
- [x] Toggling the panel open/closed works without JS errors

### D5. Form submission & download
Test at least three tools end-to-end:
- [x] **Merge PDF** — upload 2 PDFs → submit → file downloads
- [x] **Compress PDF** — upload a PDF → submit → file downloads
- [x] **PDF to Text (Basic)** — upload a PDF → submit → .txt downloads
- [x] **Watermark PDF** — upload a PDF, enter text → submit → file downloads
- [x] **Sign PDF** — draw a signature on the canvas → submit → signed PDF downloads
- [x] **Organize PDF** — upload PDF, drag pages to reorder → submit → reordered PDF downloads

### D6. Error handling in the browser
- [x] Submitting with no file shows a validation message (not a crash/blank page)
- [x] Unlock PDF with wrong password shows a clear error message on screen

---

## E. Ollama Quality (run with Ollama on, use a real scanned document)

Use a scanned invoice, contract, or multi-column article as your test file.

### E1. PDF to Word — engine: Ollama
- [x] Output is a .docx that opens in Word/LibreOffice
- [x] Headings are styled as headings, not plain paragraphs
- [x] Bullet lists are formatted as lists
- [x] Not a single wall of text — structure is preserved

### E2. PDF to Text — engine: Ollama
- [x] Output is readable plain text
- [x] Multi-column pages are not garbled (columns merged in reading order)
- [x] Tables render as tab/space-separated rows, not jumbled

### E3. PDF to Excel — engine: Ollama
- [x] Output opens in Excel/LibreOffice Calc
- [x] Table headers appear in row 1
- [x] Data rows match the source document
- [x] Numbers are not split across cells
  Note: Fixed 2026-04-15 — switched prompt from CSV to pipe-delimited to prevent
  comma-formatted numbers (e.g. 1,250) from splitting across cells.

### E4. Image to Document — engine: Ollama
- [x] Upload a scanned invoice or form as a PNG/JPG
- [x] OCR output captures all visible text accurately
- [x] Formatting (labels, values, line items) is recognisable in the output
  Note: model (gemma4:e4b) captures all text; line-item rows may merge into
  paragraphs rather than a table — acceptable for txt/docx output formats.

---

---

## F. Sprint fixes (2026-04-09) — code-level verifications

These were verified by code review and static analysis, not browser testing.

- [x] `render_pdf_edit_previews` — fitz doc now closed in try/finally
- [x] `pdf_to_excel` basic — fitz doc now closed in try/finally
- [x] `pdf_to_pptx` basic and github/openai paths — fitz doc now closed in try/finally
- [x] `pdf_to_word` basic — heading, bullet, and numbered-list detection added
- [x] `pdf_to_pptx` basic — smarter title detection, 8 bullets at 150 chars
- [x] Upload size capped at 200 MB (HTTP 413 on exceed)
- [x] Hourly background temp cleanup thread added
- [x] Edit PDF session timeout warning — banner at 30-min mark, countdown, persists across reload

---

## G. Real-file Office QA snapshot (2026-04-09)

These checks were verified against the live app routes on `http://127.0.0.1:8080` using real sample files.

### G1. `BUSINESS CARD.pdf`
- [x] `PDF to Word` returns `200` and a valid `.docx`
- [x] Word output is visual-first: no appendix, no fragile textbox overlay markup
- [x] `PDF to PowerPoint` returns `200` and a valid `.pptx`
- [x] PowerPoint output uses `2` slides with small-page pairing
- [x] PowerPoint output does not add notes slides for this small-format layout

### G2. `MONTALBAN 20 REV - DUP-A1.pdf`
- [x] `PDF to Word` returns `200` and a valid `.docx`
- [x] Word output stays visual-first: no appendix, no textbox overlays
- [x] `PDF to PowerPoint` returns `200` and a valid `.pptx`
- [x] PowerPoint output stays visual-first with `0` notes slides

### G3. `Company Profile MTI - 2026 For Construction 1.pdf`
- [x] `PDF to Word` returns `200` and a valid `.docx`
- [x] Word output includes page visuals plus the `Editable Text Extract` appendix
- [x] `PDF to PowerPoint` returns `200` and a valid `.pptx`
- [x] PowerPoint output contains `52` slides and `49` notes slides for editable extract support
- [x] `PDF to Excel` returns `200` and a valid `.xlsx`
- [x] Excel output contains `52` worksheets
- [x] `Page 26` contains a real Excel table object
- [x] `Page 26` freeze panes is set to `A91`

### G4. Known caveats from this pass
- [ ] Browser click-through automation was unavailable during this pass, so this section reflects live route verification rather than Playwright UI interaction
- [ ] `PDF to PowerPoint` notes are intentionally suppressed for small-format layouts and drawing sheets, but remain enabled for long regular documents
- [ ] `PDF to Word`, `PDF to PowerPoint`, and `PDF to Excel` are still fidelity-preserving conversions, not full native Office re-authoring

### G5. Route validation and download behavior
- [x] `PDF to Word` with no file returns `422` validation instead of a server crash
- [x] `PDF to PowerPoint` with no file returns `422` validation instead of a server crash
- [x] `PDF to Excel` with no file returns `422` validation instead of a server crash
- [x] Successful Office conversions return attachment downloads with expected filenames:
  - `converted.docx`
  - `converted.pptx`
  - `converted.xlsx`
- [x] Business-card Office route downloads complete successfully
- [x] Company-profile Office route downloads complete successfully

---

## Sign-off

| Section | Tester | Date | Result |
|---------|--------|------|--------|
| D — Browser / UI | Playwright automated | 2026-04-14 | ✅ |
| E — Ollama Quality | Automated (gemma4:e4b) | 2026-04-15 | ✅ (E3 pipe-fix applied) |
| F — Sprint fixes | Code review | 2026-04-09 | ✅ |
| G — Real-file Office QA | Codex route verification | 2026-04-09 | ✅ with caveats |
