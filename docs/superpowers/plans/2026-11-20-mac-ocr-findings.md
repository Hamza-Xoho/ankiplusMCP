# Exact-packet OCR and browser follow-up

Execute inline using systematic debugging/TDD/verification. Preserve original
6e9bcf3 packet, raw Mac evidence, frozen contracts and successful CLI output.

Add an opt-in evidence-retention mode to extract_source/pdf.read/ocr_figures,
used only by the MCP source path. Default legacy CLI remains strict. Retain
image-only pages and crops with empty text and explicit no_text, unavailable,
failed or timeout OCR status. Never synthesize quotations; exact citation and
independent quality gates remain enforced. Preserve OCR settings/passes/thresholds.
Distinguish OCR process failures from missing installation. Standalone successful
zero-region OCR reports no_text. Doctor must test actual Playwright launch, not
just Chrome presence. Document Desktop's lack of a workflow skill directory and
local wheel [all] extras. Reproduce exact original fixtures and ship a new pinned
packet without modifying old fixtures/goldens or Mac/add-on/collection state.
