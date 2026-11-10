# Review Report — anki-student

Write Markdown only. One `## Note` section per note, then optional `## Set Finding` sections, then exactly one `## Summary` last. Every note needs an attempt.

## Note n017 — FIX — V2 (blocker)
**Evidence:** exact text or visible fault, with the slide for fidelity.
**Attempt:** my committed front answer → alternative
**Rewrite Text:**
`<b>Biceps brachii</b> long head originates from {{c1::supraglenoid tubercle}}`
**Rewrite Extra:** unchanged

## Note n018 — PASS
**Attempt:** my committed front answer → right

## Set Finding — V9
**Notes affected:** n017, n018
**Finding:** concrete evidence.
**Fix:** correction.

## Summary
**Verdict:** PASS_WITH_FIXES
**Stats:** cards=20, attempts_right=18, alternatives=2

Rules: `## Note <id> — PASS|FIX|REJECT — CODES`; codes are V1–V9 only; add `(blocker)` only for a blocker. `**Attempt:** answer → right|alternative|unknowable` is required on every note; commit the answer before judging the back. V2 with an `alternative` result becomes an A2 blocker. A rewrite must pass house-style lint: `cards apply` refuses one that adds a lint blocker, keeps the draft and sends the note to round 2. Judge the verdict on the set after your rewrites are applied, with the maintainer's FAIL and PASS_WITH_FIXES rules.