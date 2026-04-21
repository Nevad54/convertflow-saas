# Office and PDF Conversion Directive

## Purpose

Move documents between PDF and editable business formats from one workspace.

## Included workflows

- images to PDF
- Word to PDF
- PowerPoint to PDF
- Excel to PDF
- HTML to PDF
- PDF to Word
- PDF to text
- PDF to Excel
- PDF to PowerPoint
- PDF to images
- PDF to SVG
- PDF to PDF/A

## Orchestration Rules

1. Classify the workflow as conversion into PDF or conversion out of PDF.
2. Use deterministic helpers in `execution/pdf_tools.py`.
3. Keep output naming and attachment downloads consistent.
4. Recommend local-first execution paths by default.
5. Treat optional AI-assisted extraction as a capability choice inside the workflow, not as a separate product.
6. When an image-to-PDF engine fails, log engine and input metadata for diagnosis while keeping the user-facing failure message stable.

## Output Rules

- Preserve layout where fidelity matters.
- Prefer editable recovery when the selected target supports it.
- Return local file downloads with explicit output extensions.
