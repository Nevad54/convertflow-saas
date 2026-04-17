# Edit PDF — Google Docs-Style UX Redesign Spec

---

## Current State

```
Phase active    : COMPLETE — all phases done and smoke-tested
Last completed  : Phase 7 smoke tests passed (2026-04-15)
Next step       : Ship / no known blockers
Files touched   : templates/tools/edit-pdf.html (only file)
Blocked?        : No

Bugs fixed during P7 smoke run:
  - CSS: .edit-tab-tools[hidden] was overridden by display:flex → added [hidden]{display:none}
  - CSS: .edit-mode-banner[hidden] was overridden by display:flex → added [hidden]{display:none}
```

---

## Problem

Current text editing flow requires 3 steps:
1. Switch to "Replace" mode via left sidebar
2. Click a text span
3. A separate modal opens → fill text → press "Save replacement"

The target UX is Google Docs: click text → cursor appears → type. No mode switching, no modal, no save button.

---

## Target UX: Google Docs feel

### What "editing in Docs" means

- Click anywhere on existing text → cursor appears right inside that text (like a word processor)
- No visible textarea box, no border appearing — the text just becomes editable in-place
- A formatting toolbar is always visible at the top of the editor (not in a sidebar)
- Blur or click elsewhere → edit commits silently. No button press needed.
- Clicking blank space → places a new text insertion point (new text box)
- Annotation tools (highlight, underline, etc.) live in a separate "Annotate" mode

### Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ home │  Edit  |  Annotate  │  [format toolbar — always visible] │  Save PDF
├──────┴─────────────────────────────────────────────────────────-┤
│  zoom: − 120% +   │  (active tool buttons for current tab)      │
├───────┬─────────────────────────────────────────────────────────┤
│       │                                                         │
│  pg   │         PDF page canvas                                 │
│  rail │    ← click text: cursor appears, type to edit →        │
│       │                                                         │
└───────┴─────────────────────────────────────────────────────────┘
```

The format toolbar (right side of top bar, always visible in Edit mode):
`[Font ▾] [Size] [B] [I] [U] [Color ■] [Align ▾]`

---

## Tab: Edit (default)

**Toolbar buttons (top center):**
`[+ Add Text] [🖼 Add Image] [⬜ Whiteout]`

**Click behaviour:**
- Click on existing PDF text → `beginInlineEdit` fires. A transparent `contenteditable` div appears over the text with matching font size/color. Cursor is placed at the click position.
- Click on blank area → places a new draggable text overlay (existing "Add Text" flow).
- No mode switching required. This is always the default behaviour.

**Contenteditable editor (replaces textarea):**
- Positioned exactly over the text span (same coordinate math as current `beginInlineEdit`)
- Styled to be invisible: `background: transparent; border: none; outline: none; caret-color: #1a73e8`
- Font size and color matched to the source span's computed style
- Thin blue underline on the line being edited (CSS `border-bottom: 2px solid #1a73e8`) — subtle Docs-like indicator
- Confirm: click elsewhere (blur) or Tab
- Cancel: Escape
- On confirm: creates `replace_text` operation (same as now)

**Format toolbar interaction:**
- While contenteditable is active, format toolbar items are enabled
- Changing font/size/color/bold/italic applies to the pending operation (updates the operation that will be saved on blur)
- Format bar items are greyed out when no text is being edited

---

## Tab: Annotate

**Toolbar buttons (top center):**
`[Highlight ▾] [Strikethrough ▾] [Underline ▾] [Shape ▾] [Draw ▾] [Stamp ▾] [Signature] [Link] [AI 🤖]`

- Each button sets the active mode (same as current sidebar buttons)
- Dropdowns: color picker for markup tools, sub-type picker for shapes
- Clicking on text in Annotate mode does NOT trigger inline editing

---

## Phase Checklist

### Phase 1 — New HTML Structure

- [x] P1-1: Remove `edit-editor-sidebar` div (tool palette + inspector panel + shortcuts)
- [x] P1-2: Add `.edit-topbar` bar as the first child of `.edit-editor-shell`:
  ```html
  <div class="edit-topbar">
    <div class="edit-topbar__left">
      <button class="edit-home-btn">🏠</button>
      <button class="edit-tab is-active" data-tab="edit">Edit</button>
      <button class="edit-tab" data-tab="annotate">Annotate</button>
    </div>
    <div class="edit-topbar__center" id="edit-format-bar">
      <!-- Font family, size, B, I, U, color, align — always in DOM, greyed when inactive -->
      <select id="edit-font-family">…</select>
      <input  id="edit-font-size" type="number" …>
      <button id="edit-bold-btn" …>B</button>
      <button id="edit-italic-btn" …>I</button>
      <button id="edit-underline-btn" …>U</button>
      <input  id="edit-color" type="color" …>
      <select id="edit-align">…</select>
    </div>
    <div class="edit-topbar__right">
      <button id="edit-download-btn" class="btn">Save PDF</button>
    </div>
  </div>
  ```
- [x] P1-3: Add `.edit-toolbar-row` below the topbar:
  ```html
  <div class="edit-toolbar-row">
    <div class="edit-zoom-controls"><!-- existing zoom controls --></div>
    <div class="edit-tab-tools" id="edit-tools-edit">
      <button data-mode-button="text">+ Add Text</button>
      <button data-mode-button="image">🖼 Add Image</button>
      <button data-mode-button="whiteout">⬜ Whiteout</button>
    </div>
    <div class="edit-tab-tools" id="edit-tools-annotate" hidden>
      <button data-mode-button="highlight">Highlight ▾</button>
      <!-- strikethrough, underline, shape dropdown, draw, stamp, signature, link, AI -->
    </div>
  </div>
  ```
- [x] P1-4: Keep all hidden state inputs (`<select id="edit-mode">`, opacity, etc.) in the DOM — just hide them. Format bar inputs keep their existing IDs so no JS references break.
- [x] P1-5: Remove `#edit-replace-modal` and its footer ("Cancel" / "Save replacement" buttons)

### Phase 2 — CSS

- [x] P2-1: `.edit-topbar` — `display:flex; align-items:center; justify-content:space-between; height:48px; border-bottom:1px solid #e0e0e0; background:#fff; padding:0 12px`
- [x] P2-2: `.edit-tab` — plain text button, no border. `.edit-tab.is-active` — blue underline `border-bottom:2px solid #1a73e8; color:#1a73e8`
- [x] P2-3: `.edit-format-bar` inputs — compact, inline, greyed when `disabled`. Match Google Docs toolbar aesthetic: small font, tight spacing.
- [x] P2-4: `.edit-toolbar-row` — `display:flex; align-items:center; gap:8px; height:40px; border-bottom:1px solid #e0e0e0; padding:0 8px; background:#fafafa`
- [x] P2-5: `.edit-inline-ce` (the new contenteditable) — `position:absolute; background:transparent; border:none; outline:none; caret-color:#1a73e8; border-bottom:2px solid #1a73e8; white-space:pre; overflow:visible; cursor:text; z-index:20`
- [x] P2-6: Remove all `.edit-editor-sidebar`, `.edit-tool-palette`, `.edit-inspector`, `.edit-replace-modal` CSS

### Phase 3 — JS: contenteditable inline editor

Replace the `<textarea>` in `beginInlineEdit` with a `<div contenteditable>`:

- [x] P3-1: In `beginInlineEdit`, replace `document.createElement('textarea')` with `document.createElement('div')`
- [x] P3-2: Set `ce.contentEditable = 'true'`; class = `edit-inline-ce`
- [x] P3-3: Copy text content: `ce.textContent = originalText`
- [x] P3-4: Position using the same coord math as current textarea (left/top/width/height from spanRect)
- [x] P3-5: Match font: `ce.style.fontSize = ...`; `ce.style.color = spanEl style color or '#111'`; `ce.style.fontFamily = spanEl computed fontFamily`
- [x] P3-6: On append + focus, use `Selection` API to place cursor at click position:
  ```js
  ce.focus();
  const range = document.createRange();
  range.selectNodeContents(ce);
  range.collapse(false); // cursor at end, or use caretPositionFromPoint for exact click pos
  getSelection().removeAllRanges();
  getSelection().addRange(range);
  ```
- [x] P3-7: `commit()` reads `ce.textContent` instead of `ta.value` — rest of commit logic unchanged
- [x] P3-8: Keydown: `Tab` → commit (in addition to current Enter); `Escape` → cancel
- [x] P3-9: Enable format-bar inputs when `ce` is focused; update pending op on change; disable on blur

### Phase 4 — JS: Remove mode gate on text click

- [x] P4-1: In the pdf.js text-layer click handler (~line 5110), remove the guard:
  ```js
  // REMOVE THIS:
  if (modeInput.value !== 'replace_text') return;
  ```
  Replace with:
  ```js
  if (activeTab !== 'edit') return; // only in Edit mode, not Annotate
  ```
- [x] P4-2: Remove `openReplaceModal` calls (dblclick handler on overlays ~line 4859) — replace with calling `beginInlineEdit` directly on the overlay's span, or open `beginInlineEdit` for the operation's text
- [x] P4-3: Remove `openReplaceModal` function definition
- [x] P4-4: Remove `#edit-replace-modal` show/hide JS logic (`replaceModal` variable, `openReplaceModal`, `replaceCancel`, `replaceSave` event listeners)

### Phase 5 — JS: Tab switching

- [x] P5-1: Add `let activeTab = 'edit'` variable
- [x] P5-2: Tab click handler:
  ```js
  document.querySelectorAll('.edit-tab').forEach(btn => btn.addEventListener('click', () => {
    activeTab = btn.dataset.tab;
    document.querySelectorAll('.edit-tab').forEach(t => t.classList.toggle('is-active', t === btn));
    document.getElementById('edit-tools-edit').hidden = activeTab !== 'edit';
    document.getElementById('edit-tools-annotate').hidden = activeTab !== 'annotate';
    // Reset to neutral mode when switching
    if (activeTab === 'edit') modeInput.value = 'text';
  }));
  ```
- [x] P5-3: Wire toolbar buttons: each `[data-mode-button]` click sets `modeInput.value` to its value and calls `updateModeState()` (same as current sidebar buttons — just new elements triggering it)
- [x] P5-4: Shape dropdown: clicking opens a small popover with Rect / Ellipse / Arrow options; selecting one sets the mode and closes the popover
- [x] P5-5: Highlight/Strikethrough/Underline dropdowns: open a color picker popover; picking color sets `colorInput.value` and the mode

### Phase 6 — JS: Format bar enable/disable

- [x] P6-1: Default state: format bar inputs are `disabled` and visually greyed
- [x] P6-2: When `beginInlineEdit` fires → enable format bar, sync values from the span's detected font
- [x] P6-3: Format bar changes while editing → update the pending op's properties live (so blur commit picks them up)
- [x] P6-4: On commit/cancel → disable format bar again

### Phase 7 — Smoke tests

- [x] P7-1: Upload PDF → click existing text → cursor appears in text (no mode switch, no modal)
- [x] P7-2: Type replacement → click elsewhere → overlay appears → download → verify text replaced
- [x] P7-3: Annotate tab → Highlight → drag over area → download → verify highlight
- [x] P7-4: Add Text → click blank area → type → download → verify new text
- [x] P7-5: Format bar: while editing text → change font size → commit → verify size in download
- [x] P7-6: Escape while editing → text unchanged
- [x] P7-7: Update Current State block in this spec

---

## Architecture Notes

### What stays the same (do not touch)

| Component | Why |
|---|---|
| `operations[]` array and all operation types | Core data model, unchanged |
| `applyOperationsClientSide` / pdf-lib export | Export logic, unchanged |
| `beginInlineEdit` coordinate math | Correct, just replace textarea element |
| Page rail thumbnails | Unchanged |
| AI routes (`/ai-fix`, `/ai-stamp`) | Server-side, unchanged |
| Zoom controls | Unchanged |
| Undo/redo (`pushHistory`, `popHistory`) | Unchanged |
| `renderAllOverlays` | Unchanged |
| `<select id="edit-mode">` hidden in DOM | Keep it — all `modeInput.value` JS refs stay valid |

### Key insight: keep existing IDs

The format bar inputs use the **same IDs** as the old inspector inputs:
- `#edit-font-family`, `#edit-font-size`, `#edit-bold-btn`, `#edit-italic-btn`
- `#edit-color`, `#edit-align`, `#edit-opacity`

This means ALL existing JS event listeners on these elements continue to work without any changes. They just move from the sidebar to the top bar.

### What changes

| Before | After |
|---|---|
| Left sidebar (tool palette + inspector) | Top bar with Edit/Annotate tabs + format bar |
| `<textarea>` in `beginInlineEdit` | `<div contenteditable>` with transparent styling |
| Must switch to "Replace" mode first | Click any text in Edit mode → instant inline edit |
| Modal with "Save replacement" button | Silent commit on blur |
| 15-button sidebar palette | ~3 Edit buttons + ~9 Annotate buttons in toolbar row |

---

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| `contenteditable` font matching not pixel-perfect | Medium | Use `window.getComputedStyle(spanEl)` for font-size and color; good enough for editing UX |
| Clicking a span that's already been replaced triggers another inline edit on the overlay instead | Medium | After commit, mark `spanEl.dataset.replaced = '1'` (already done); check this flag in the click handler and re-open the overlay's operation instead |
| Tab key in contenteditable inserts a tab character | Low | Intercept `Tab` keydown, call `commit()`, move focus to next interactive element |
| format-bar inputs IDs clash if both old inspector AND new bar exist simultaneously during refactor | Low | Remove the old sidebar HTML first before adding the new bar |

---

## Next session

Read this spec, check the `Current State` block and Phase Checklist, then continue from the first unchecked item.
