# Edit PDF — pdf.js + pdf-lib Redesign Spec

---

## Current State

> **Update this block at the end of every session before stopping.**
> Any AI (Claude, Codex, Gemini, etc.) should read ONLY this block to resume work.

```
Phase active    : QA COMPLETE — all sections D + E signed off
Last completed  : Section E Ollama Quality — ALL E1–E4 items complete ✅ (signed off 2026-04-15)
Last file touched: QA_MANUAL.md, execution/pdf_tools.py,
                  docs/superpowers/specs/2026-04-13-edit-pdf-pdfjs-redesign.md
Next step       : None — full QA checklist signed off. Project is feature-complete and QA-complete.
                  Optional: run with a real printed/scanned invoice to validate E4 OCR on true
                  raster images (current E4 test used a rendered PNG, not a camera scan).
Changes in this session (2026-04-15):
  - Ollama started (gemma4:e4b, RTX 4050 6 GB); full test suite: 77 PASS / 0 FAIL / 0 SKIP.
  - E1 PDF to Word (Ollama) ✅ — structured PDF: Heading 1/2, List Bullet, Normal all correct.
  - E2 PDF to Text (Ollama) ✅ — two-column PDF: left column before right, clean reading order.
  - E3 PDF to Excel (Ollama) ✅ (with fix) — numbers like 1,250 were split across cells when
    using CSV delimiter; fixed by switching _EXCEL_PROMPT + csv.reader to pipe (|) delimiter.
  - E4 Image to Doc (Ollama) ✅ — invoice PNG: all text captured; minor: line items merged
    into paragraphs rather than a table (acceptable behaviour for gemma4 model).
  - QA_MANUAL.md — E1–E4 ticked; Section E signed off in table.
E1 ✅ .docx produced; Heading 1 title, Heading 2 sections, List Bullet bullets, Normal body
E2 ✅ plain text in reading order; left column precedes right column
E3 ✅ .xlsx produced; headers row 1; 1,250 / $62,500 intact (pipe-delimiter fix applied)
E4 ✅ .docx produced; OCR captures all invoice text accurately
Open risks      : Font size approximation in beginInlineEdit uses nh * page_height_pt * 0.82 —
                  may need tuning on PDFs with large/small text.
                  E4 tested on rendered PNG — camera-scanned invoices may have lower OCR accuracy.
Blocked?        : No — QA complete.
```

---

## Phase Checklist

Use this as the master progress tracker. Check items off as they are completed.
Update `## Current State` after every session.

### Phase 1 — pdf.js Viewer
- [x] P1-1: Add pdf.js to the project (CDN or local bundle in `static/`)
- [x] P1-2: Modify upload endpoint response — drop full-res base64 page images from the JSON payload; keep low-res thumbnails (used by page rail), text blocks, and page dimensions
- [x] P1-3: Cache raw PDF binary client-side after upload (ArrayBuffer in memory)
- [x] P1-4: Replace `<img>` page rendering with pdf.js canvas per page
- [x] P1-5: Reposition overlay system (hitboxes, drag handles) over pdf.js canvases
- [x] P1-6: Keep page rail using server-side thumbnails (no change)
- [x] P1-7: Verify zoom / fit-width / fit-page controls still work with canvas layout
- [x] P1-8: Verify text hitbox click-to-replace still works in replace mode
- [x] P1-9: Smoke test on 3 PDF types: simple text, scanned image, mixed layout
- [x] P1-10: Update `## Current State` and commit

### Phase 2 — pdf-lib Client-Side Export
- [x] P2-1: Add pdf-lib to the project (CDN or local bundle in `static/`)
- [x] P2-2: On upload, store raw PDF ArrayBuffer in a closure-scoped variable inside the editor IIFE (same scope as `operations`, `batchId`, etc.)
- [x] P2-3: Implement `applyOperationsClientSide(pdfBytes, operations)` using pdf-lib
- [x] P2-4: Map each operation type to pdf-lib calls:
  - [x] P2-4a: `text` → PDFPage.drawText
  - [x] P2-4b: `replace_text` → whiteout rect + drawText
  - [x] P2-4c: `image` → PDFPage.drawImage
  - [x] P2-4d: `whiteout` → drawRectangle (white fill)
  - [x] P2-4e: `highlight` / `underline` / `strikethrough` → drawRectangle with opacity
  - [x] P2-4f: `rect_shape` / `ellipse` → drawRectangle / drawEllipse
  - [x] P2-4g: `line` → drawLine
  - [x] P2-4h: `stamp` / `symbol` → drawText (unicode glyph) or drawImage
  - [x] P2-4i: `link` → skip for Phase 2 (no pdf-lib hyperlink API for existing pages)
- [x] P2-5: Replace server `POST /convert/edit-pdf` call with client-side pdf-lib blob download
- [x] P2-6: Keep AI routes hitting server (ai-fix, ai-stamp) — no change
- [x] P2-7: Remove dead server route `/convert/edit-pdf` apply endpoint from `app.py`
- [x] P2-8: Test round-trip: upload → edit → download → open in Acrobat / browser PDF viewer
- [x] P2-9: Update `## Current State` and commit

### Phase 3 — Inline Text Editing
- [x] P3-1: Enable pdf.js text layer rendering (TextLayerBuilder)
- [x] P3-2: Style text layer spans to be transparent but selectable
- [x] P3-3: On click of a text span, record its bounding box and content
- [x] P3-4: Position a `<textarea>` overlay exactly over the clicked text span
- [x] P3-5: On textarea confirm (Enter / blur), record a `replace_text` operation
- [x] P3-6: Style the confirmed replacement as a visual overlay on the canvas
- [x] P3-7: Handle font fallback — document expected font-matching behaviour in a code comment
- [x] P3-8: Test on PDFs with embedded fonts (expect fallback), standard fonts (expect clean output)
- [x] P3-9: Update `## Current State` and commit

### Phase 4 — Link Annotation Export
- [x] P4-1: Implement link annotation embedding using pdf-lib's low-level `PDFContext` API
  - URI action for `url`, `email`, `phone` link types
  - GoTo action for `page` link type (internal navigation via `page.ref + /Fit`)
  - Draw visual indicator (`underline` / `box` / `invisible`) on the page canvas
  - Merge annotation into existing page `/Annots` array; handle both direct PDFArray and indirect PDFRef
- [x] P4-2: Remove `skippedLinks` variable and its `warnings` return field
- [x] P4-3: Remove `skippedLinks` notice from download warning flow
- [x] P4-4: Test round-trip: URL link → download → open in browser PDF viewer → click link
- [x] P4-5: Update `## Current State` and check off completed items

---

## Architecture Reference

> Read this section only when starting a new phase or debugging a cross-cutting issue.
> Do not re-read every session.

### Current Stack (before redesign)

| Layer | Tech | Notes |
|---|---|---|
| Page rendering | Server → base64 PNG → `<img>` | PyMuPDF renders at 150 DPI |
| Overlay engine | HTML divs over `<img>` | Normalized (0–1) coordinates |
| Edit export | `POST /convert/edit-pdf` → PyMuPDF composite → FileResponse | Server-side |
| AI features | `POST /convert/edit-pdf/ai-fix` and `/ai-stamp` | LLM via Ollama / OpenAI |
| Session | batch_id in UPLOAD_DIR, validated by `_validated_batch_id()` | 3-hour TTL |

### Target Stack (after redesign)

| Layer | Tech | Notes |
|---|---|---|
| Page rendering | pdf.js canvas (client-side) | Renders raw PDF binary cached from upload |
| Page rail | Server thumbnails (unchanged) | Still fast/cheap via server PNG |
| Overlay engine | HTML divs over pdf.js canvas | Same coordinate system, repositioned |
| Edit export | pdf-lib.js (client-side blob) | No server roundtrip |
| AI features | Server (unchanged) | Cannot move client-side |
| Session | Upload still server-side, batch_id kept for AI routes | TTL logic unchanged |

### Coordinate System

All overlay operations use **normalized coordinates (0.0–1.0)** relative to page width/height.
- pdf.js canvas size varies with zoom — overlays must recompute pixel positions on zoom change
- pdf-lib uses **points (pt)** — multiply normalised coords by page width/height in points
- Page dimensions in points are available from pdf.js: `page.getViewport({ scale: 1 }).width/height`

### Known pdf-lib Limitations

- Cannot edit or remove existing PDF text (can only draw on top)
- Cannot reuse embedded/subset fonts from the original PDF
- Standard fonts (Helvetica, Times-Roman, Courier) render cleanly
- Custom embedded fonts fall back to Helvetica — document this to the user
- Hyperlinks on existing pages: no clean API; skip in Phase 2, revisit in Phase 3+
- Large PDFs (>10 MB) may cause memory pressure — consider chunked processing

### AI Routes (server, permanent)

| Route | Purpose |
|---|---|
| `POST /convert/edit-pdf/ai-fix` | Rephrase / grammar / formal / bullet via LLM |
| `POST /convert/edit-pdf/ai-stamp` | Suggest stamp label from page 1 text |

These routes stay in `app.py`. They do not change across any phase.

---

## Handoff Protocol

### Starting a new session (any AI)

1. Read `## Current State` only — do not read the full doc
2. Find the next unchecked item in `## Phase Checklist`
3. Read the relevant Phase section in this spec
4. Read the files listed in `## Current State` → `Last file touched`
5. Implement the next checklist item
6. Before stopping: update `## Current State` and check off completed items

### Handing off to a different AI (e.g. Codex)

Copy-paste this prompt to start the new session:

```
Read d:/Web App/Converter/docs/superpowers/specs/2026-04-13-edit-pdf-pdfjs-redesign.md
— specifically the "## Current State" block only.
Then find the next unchecked item in "## Phase Checklist" and continue from there.
The project root is d:/Web App/Converter.
Do not rewrite the overlay architecture beyond what the spec describes.
Do not claim proprietary copying — frame all work as UX parity and local-first implementation.
```

### End-of-session checklist (mandatory)

Before ending any session:
- [ ] Check off all completed Phase Checklist items
- [ ] Update `## Current State` with the exact next step
- [ ] Update `.tmp/codex_handoff.md` → `## Recommended Next Steps`
- [ ] Commit both files

---

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| pdf-lib can't reuse embedded fonts | Medium | Fall back to Helvetica; show user a warning on download |
| pdf.js canvas zoom reflow breaks overlay positioning | Medium | Recompute overlay px positions on every zoom change (already done for img, adapt for canvas) |
| Large PDFs cause memory pressure with ArrayBuffer caching | Low-Medium | Warn if file > 8 MB; consider streaming in Phase 2+ |
| pdf.js text layer coordinates don't align with PyMuPDF text blocks | Medium | Cross-check in P3-1; may need to drop server text blocks and use pdf.js text layer exclusively |
| Session TTL expires before Phase 2 removes server dependency | Low | Session only needed for AI routes post-Phase 2; TTL risk shrinks significantly |
| Inline editing (Phase 3) font fallback is visible to user | Low | Document clearly in UI: "Replaced text uses a standard font" |
