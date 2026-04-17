# PDF Operations Directive

## Purpose

Prepare and organize PDF files before review, delivery, or export.

## Included workflows

- merge PDF
- split PDF
- extract pages
- remove pages
- rotate PDF
- organize PDF
- compress PDF
- repair PDF

## Orchestration Rules

1. Validate upload presence and page-related inputs early.
2. Save uploads into the temporary workspace.
3. Call deterministic helpers from `execution/pdf_tools.py`.
4. Return finished files immediately as downloads or ZIP archives when multiple outputs are generated.
5. Keep workflow language centered on document preparation, not generic file conversion.

## Output Rules

- Preserve page content unless the selected tool explicitly changes layout or ordering.
- Return clear range or password errors instead of generic failures.
- Use local execution only; no hosted AI engine is needed for this domain.
