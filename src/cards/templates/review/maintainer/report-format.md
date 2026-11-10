# Review Report — anki-maintainer

Write Markdown only. One `## Note` section per note, then optional `## Set Finding` sections, then exactly one `## Summary` last.

## Note n017 — FIX — A3 (blocker)
**Evidence:** exact text or visible fault, with the slide for fidelity.
**Rewrite Text:**
`<b>Biceps brachii</b> long head originates from {{c1::supraglenoid tubercle}}`
**Rewrite Extra:** unchanged

## Note n018 — PASS
No issues found.

## Set Finding — S2
**Notes affected:** n017, n018
**Finding:** concrete evidence.
**Fix:** correction.

## Summary
**Verdict:** PASS_WITH_FIXES
**Stats:** notes=27, pass=22, fix=4, reject=0, blockers=1

Rules: `## Note <id> — PASS|FIX|REJECT — CODES`; add `(blocker)` only for a blocker. Fields are `**Evidence:**`, `**Rewrite Text:**`, `**Rewrite Extra:**` or any note field; use `unchanged` to preserve a field. A rewrite must pass house-style lint (at most five cloze numbers, no comma inside a cloze, Extra within three lines): `cards apply` refuses a rewrite that adds a lint blocker, keeps the draft and sends the note to round 2. Split a long list into two notes instead of using more than five clozes. Code families never mix: note records use A1–A13 only; set records use S1–S9 only. Judge the verdict on the set after your rewrites are applied. FAIL = a blocker with no workable rewrite, a reject, or a set finding needing re-extraction; a fixed blocker and polish-only findings are PASS_WITH_FIXES; otherwise PASS.