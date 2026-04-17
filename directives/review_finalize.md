# Review and Finalize Directive

## Purpose

Finish business-ready document handoffs after preparation or recovery.

## Included workflows

- edit PDF
- compare PDF
- redact PDF
- add page numbers
- watermark PDF
- sign PDF
- protect PDF
- unlock PDF

## Orchestration Rules

1. Treat these workflows as final-mile document tasks.
2. Preserve the original file until a finalized copy is generated.
3. Use deterministic helpers in `execution/pdf_tools.py`.
4. Keep session-based editing flows inside the temporary workspace.
5. Present outputs as clean handoff files rather than experimental edits.

## Output Rules

- Finalized documents should download immediately with explicit filenames.
- Review tools should produce clear error states for invalid pages, signatures, passwords, or missing sessions.
- Security and signing flows remain local-first.
- The Edit PDF flow should avoid dead-end setup steps: choosing a file should move directly into the editor, and the editor should scroll into view once previews are ready.
- Editing controls must stay usable on touch-sized screens: keep the main editor ahead of tips, avoid cramped inspector regions, and prefer tap-friendly copy such as "click or tap".
- When the Edit PDF tool behaves like a workspace, keep page-level orientation visible: a compact page rail or quick-jump control makes multi-page editing feel more document-first.
- Replace-text mode should advertise itself clearly in the canvas so detected text blocks look intentionally editable, not like invisible hotspots.
- In multi-page editing, surface which page is current and which pages already contain edits; page rails are more useful when they behave like a navigator, not just a static page list.
