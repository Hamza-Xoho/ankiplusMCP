---
name: ankiplusmcp
description: Use AnkiPlus MCP mechanical helpers for lecture extraction, OCR, image occlusions, card checks, previews, and review changes alongside the official Anki MCP.
---

AnkiPlus handles source material and working artifacts. The separate official
Anki MCP reads and changes the Anki collection. Choose tools to fit the request;
there is no required pipeline or review panel.

Useful combinations:

- Lecture cards: extract a source, inspect relevant slides/figures, draft cards,
  check or preview them, then prepare payloads for Anki MCP.
- Existing-card review: retrieve notes and note-type templates through Anki MCP,
  save snapshots in a cards workspace, inspect previews, and consider changes.
- Diagram cards: inspect the image, use OCR for suggested rectangles, adjust
  labels/groups, and build an occlusion preview. OCR is assistance, not evidence
  that every label was detected.
- Targeted suspension/unsuspension: use the official Anki MCP directly; AnkiPlus
  is useful only if source inspection, selection preparation or previews help.

Preserve source terminology, qualifications and citations when drafting. The
optional get_guidance tool provides quality/reviewer rubrics when useful.
Mechanical checks do not establish factual accuracy.

Use explicit workspace IDs and current revisions for edits. Long operations
return job IDs; get_job supplies results. get_image returns viewable images.
Tool errors describe prerequisites and corrections without requiring a restart.

prepare_write generates files and arguments; it does not send them to Anki.
Pass those payloads through the official Anki MCP and record actual responses
if a report is useful. Note IDs identify notes; suspension uses card IDs.
