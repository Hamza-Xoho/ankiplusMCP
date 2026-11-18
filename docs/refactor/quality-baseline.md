# Quality and regression baseline

## Deterministic CLI lane

Run with the frozen dependency environment:

```sh
uv sync --frozen --extra dev
.venv/bin/python -m playwright install chromium
.venv/bin/python tests/tools/cli_baseline.py compare tests/fixtures/public/cli-baseline --deterministic
```

The committed synthetic snapshot exercises 14 real CLI calls and 66 artifacts: PDF and text extraction, cached extraction, source slices/search/page images, target identity, OCR-based figure records, masks, validation and real browser rendering. Only the external Tesseract executable is replaced with a fixed TSV fixture. No production extraction/rendering code is patched. Pixel/content hashes now detect changed PNG bytes even when dimensions match.

The snapshot was compared successfully in both a freshly resolved environment (Playwright 1.65.2) and the repository's frozen environment (1.65.0). This is Linux evidence only. CI executes the golden comparison on Linux; macOS has real extraction/render tests, not an assumed cross-platform screenshot-byte identity guarantee. Different system fonts/renderers can require an explicit platform fixture decision, not silently accepting a changed golden file.

Never record a dependency failure as the reference: command exit codes 2 or 3 refuse recording. A findings exit 1 is expected for the synthetic extraction/check cases; render commands must succeed. Before refreshing, review fields, tags, tiers, source refs, masks and rendering differences. No card-design rules have changed in this phase.

## Quality evaluation beyond byte comparison

Before release evaluate representative lecture, textbook chapter, anatomy/histology diagram and overlap cases against the unchanged existing drafting and reviewer rubrics. Check source terminology/hedges, combined facts without overloading recall, omission/gap justification, suitability of existing cards, tiering, duplicate concepts and visual masks. Generated prose is probabilistic; exact CLI snapshots cannot prove semantic coverage or independent factual correctness.

Use anonymised synthetic inputs in public CI. Real private lecture fixtures and user-quality acceptance remain separate release requirements. Do not publish or fabricate private inputs to make a test pass.
