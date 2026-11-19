---
name: AnkiPlus student review
description: Source-linked decisions before guarded collection changes
colors:
  paper: "#ffffff"
  surface: "#f2f5f4"
  ink: "#172a24"
  muted: "#4b6159"
  line: "#6c8379"
  accent: "#155940"
  focus: "#925100"
  error: "#9c2525"
  button-ink: "#ffffff"
  dark-paper: "#15231d"
  dark-surface: "#21372c"
  dark-ink: "#edf7f0"
  dark-muted: "#c0d1c6"
  dark-line: "#738d7b"
  dark-accent: "#a4dec0"
  dark-focus: "#f0bd67"
  dark-error: "#ffb5ae"
  dark-button-ink: "#123222"
typography:
  body:
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "16px"
    lineHeight: 1.5
    fontWeight: 400
  heading:
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "1.6rem"
    lineHeight: 1.2
    fontWeight: 700
rounded:
  control: "6px"
  field: "5px"
  aside: "8px"
spacing:
  compact: "8px"
  control-gap: "10px"
  mobile: "16px"
  desktop: "24px"
  columns: "28px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.button-ink}"
    rounded: "{rounded.control}"
    padding: "9px 15px"
  button-secondary:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.accent}"
    rounded: "{rounded.control}"
    padding: "9px 15px"
---

## Overview

AnkiPlus lets a student compare proposed card text with cited evidence and existing
coverage, then save a local decision. Quality and exact authorization follow the
current proposal. This system inherits the tested compatibility surface's green
controls and native typography. The surface contract is in
[review-surface.md](docs/refactor/review-surface.md).

## Colors

The reading surface is light by default with a second neutral source panel. Dark
mode follows the browser preference using the dark tokens above. Green identifies
actions; brown/gold focus stays visible on both themes; red names errors and
explicit-update warnings. Body contrast is tested in the rendered dark view.

## Typography

One system font family serves reading, editing and controls. Fixed rem headings
keep hierarchy stable in embedded host widths. Prose is limited to 70 characters;
labels are bold and card/source text retains meaningful line breaks. Pagination
uses tabular numerals. Field contents are inert text, never live card HTML.

## Layout

The desktop editor is a 960px maximum document with two columns in a 1.15:1 ratio
and a 28px gutter. The card/editor precedes the evidence panel in DOM order. At
640px and below it becomes one column with 16px outer padding and a 20px gap.
Controls wrap without horizontal page overflow. Quality/approval follows the
current item and stays distinct from saving a reversible local decision.

## Elevation & Depth

Panels use surface color and spacing. There are no decorative shadows, gradients,
illustrations or external assets. Borders identify controls and section boundaries.

## Shapes

Buttons have 6px corners and at least 44px height; fields use 5px corners. Source
panels use 8px corners. Checkboxes have 22px visual controls within labelled rows.
Focus uses a 3px outline with 3px offset. Form controls retain native semantics.

## Components

Buttons expose hover, active, focus, disabled and busy states. Unsaved edits disable approval, paging and recheck; a save locks editing until its result returns. An explicit reload returns to retained state. The page announces
status politely and marks main content busy during calls. Every field/control has
a label. Existing-note update requires choosing the target and checking an explicit
confirmation. A source-disagreement resolution has its own explicit checkbox.

Source and existing-coverage sections expose origin, page/section and OCR labels. A cited PDF page opens inline through the current bound review; PNGs fit the panel and have descriptive source/page alternative text.
Findings are inspectable with full retained evidence available through history.
Long fields load complete bounded slices before editing. Stale/offline errors
retain saved decisions and tell the student to reopen/recheck. Empty review state
explains that no actionable decisions remain. Approval stays disabled until the
current proposal has valid quality evidence and no blockers.

## Do's and Don'ts

Use native controls, visible focus and actual source/card text. Keep local save,
quality evidence and collection application distinct. Retain review selections on
reconnect. Show pending and partial outcomes honestly. Do not render user HTML,
invent quality results, hide source uncertainty or treat a disabled button as the
server-side authorization check.
