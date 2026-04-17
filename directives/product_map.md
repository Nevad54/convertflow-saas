# ConvertFlow Product Map

## Product Position

ConvertFlow is a local-first document workspace for operations-heavy document work.

It is not just an OCR utility. The product groups document work into five domains:
- document conversion
- PDF operations
- OCR and recovery
- review and finalize
- AI assist

## Product Promise

- Convert, clean up, recover, and finalize documents from one workspace
- Keep core workflows on-device
- Use optional cloud engines only when explicitly selected

## Domain Map

### 1. PDF operations
- merge
- split
- extract
- remove
- rotate
- organize
- compress
- repair

### 2. Document conversion
- images to PDF
- Office to PDF
- PDF to Word, text, Excel, PowerPoint, images, SVG, PDF/A

### 3. OCR and recovery
- image to document
- scan reconstruction
- scanned invoice, form, and contract recovery

### 4. Review and finalize
- edit
- compare
- redact
- watermark
- page numbering
- sign
- protect
- unlock

### 5. AI assist
- summarize
- translate
- optional recovery acceleration through Ollama, GitHub Models, or OpenAI

## Orchestration Guidance

- Route users by workflow goal, not just file type
- Prefer local execution paths for the default recommendation
- Surface hosted engines as optional assistive choices, not the default product identity
- Keep tool pages consistent with the workspace-level promise

## Public Benchmark Notes

The public PDFSimpli editor experience was reviewed as a product benchmark on April 11, 2026.
These notes describe visible behavior and capability categories only. They are intended to guide
feature parity decisions, not source-level copying.

### Observed edit surface areas

- Viewer shell built around a live PDF reader with thumbnails, zoom, rotate, print, open, and download actions
- Top-level document actions such as save, convert, delayed delivery, send, FAQ, feedback, and summarizer upsells
- Core edit tools for pointer/select, text, replace text, highlight, underline, strikeout, redact, add image, watermark, and reset
- Shape and drawing tools including box, circle, line, arrow, polyline, polygon, freehand drawing, and eraser
- Signature-oriented flows including add e-signature, send for signature, and signature placement
- More advanced document flows including crop, rotate, password protect, form fields, bookmark support, and page arrangement

### Product implications for ConvertFlow

- Our current Edit PDF tool already covers much of the visible editing surface:
  text, replace text, image, link, highlight, underline, strikethrough, whiteout,
  shapes, draw, stamp, and signature
- The largest gap is architecture, not just buttons:
  PDFSimpli appears to use a live `pdf.js` style viewer with a text and annotation model,
  while our current editor works by placing overlays on rendered page previews
- We should treat competitor parity as two tracks:
  short-term parity through overlay-based features and UX polish,
  long-term parity through a true viewer-driven editor shell

### Guardrails

- Recreate public interaction patterns and user-facing capabilities where helpful
- Do not copy proprietary source, assets, or implementation details
- Prefer local-first execution and keep hosted/upsell behavior out of the core product promise

### Broader site taxonomy observed on pdfsimpli.com

Their public homepage presents the product as a broader document platform, not just a PDF editor.
The top navigation and tool groupings cluster into five areas:

- PDF Converter
  PDF to Word, JPG, PNG, TIFF, PowerPoint, Excel, DOCX, plus reverse conversions such as Word, JPG,
  PNG, TIFF, PowerPoint, Excel, HTML, and TXT to PDF
- PDF Editor
  Edit, add images, number pages, watermark, redact, hyperlinks, checkboxes, merge, split, extract,
  delete pages, reorder pages, insert pages, rotate, compress, repair, OCR, scan, protect, unlock
- Translate
  Translate PDFs and other document types, with language-specific SEO landing pages
- Forms
  Category-driven form library such as banking, business, career, financial, government, IRS, legal,
  real estate, medical, and event workflows
- Templates
  Category-driven document templates such as affidavit, bill of sale, wills, employment, family,
  finance, business, and government

### Strategic takeaway for ConvertFlow

ConvertFlow already aligns most closely with the PDF Converter and PDF Editor pillars.
The strongest upgrade path is:

- First, deepen the PDF Editor and review/finalize experience
- Second, sharpen conversion quality and workflow packaging around existing routes
- Third, consider whether forms/templates belong in-product or as a later adjacent offering
- Keep translation and AI assist positioned as supportive workflows, not the whole product identity
