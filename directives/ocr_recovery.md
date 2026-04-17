# OCR and Recovery Directive

## Purpose

Recover scanned files, screenshots, forms, and photographed documents into working outputs.

## Inputs

- one or more image files
- desired output format
- optional title
- selected recovery engine
- document style profile

## Orchestration Rules

1. Validate supported image inputs.
2. Preserve intended page order through filename sorting.
3. Use `execution/converter.py` for OCR and output building.
4. Default to local recovery when hosted engines are not configured.
5. Surface hosted OCR engines as optional assistive choices only when explicitly selected or available through `auto`.

## Output Rules

- Preserve paragraph boundaries and visible structure where possible.
- Mark unreadable areas explicitly instead of inventing content.
- Keep generated files in `.tmp/outputs/`.

## Capability Boundary

- local: `tesseract`, `ollama`
- optional hosted assist: `github`, `openai`
