# Installed student-product acceptance

Use this standalone configuration only. It has no runtime network, published
ports, volumes or host mounts. A nonroot/read-only container with dropped
capabilities and CPU/RAM/PID limits creates disposable collections under tmpfs.
The primary uses its locked Python dependencies; the packaged companion owns the
collection in a separate stdio child, avoiding cross-process dependency mixing.
Both textual and numeric Anki add-on names must pass.

Build the companion archive in its dedicated checkout using its documented
Python 3.13 package.sh. Copy that explicit archive to ignored
`tests/isolated/input/companion.ankiaddon`, recording its revision and SHA-256.
No installed add-on is read, replaced or restarted. Build contexts use this
repository root; the archive is the only documented external build input.

```sh
# Set actual revisions, appending -dirty to each uncommitted build input.
ANKIPLUS_REVISION=<primary-sha> COMPANION_REVISION=<companion-sha> \
  docker compose -f tests/isolated/compose.yaml config --format json
# Inspect: no ports/volumes/privileged/host networking; resource caps in place.
ANKIPLUS_REVISION=<primary-sha> COMPANION_REVISION=<companion-sha> \
  docker compose -f tests/isolated/compose.yaml build
ANKIPLUS_REVISION=<primary-sha> COMPANION_REVISION=<companion-sha> \
  docker compose -f tests/isolated/compose.yaml run --rm --no-deps acceptance
ANKIPLUS_REVISION=<primary-sha> COMPANION_REVISION=<companion-sha> \
  docker compose -f tests/isolated/compose.yaml run --rm --no-deps acceptance \
  python /artifact/product_workflow.py 124672614
```

The script exercises actual installed SDK/MCP tools, source extraction, scoped
coverage, source-linked session state, quality refusal/acceptance mechanics,
verified setup, guarded real-note creation, generated-card suspension/readback,
replay, mapping reuse, real accepted-acknowledgement loss, fresh primary recovery
without resending, permanent history and actual Tesseract OCR. The production
review bundle is loaded through resources/read; its browser interactions and
accessibility have a separate real-SDK browser test in test_review_app.py.

All reviewer/host receipts here are explicitly signed synthetic fixtures. They
test local enforcement and are not independent card-quality review, actual host
execution, HTTP/Qt main-thread scheduling, Mac embedding or private acceptance.
No weaker review or paid API substitutes are used.

Record rendered configuration, source/dirty labels, input archive hash, image ID,
pip freeze and complete stdout/stderr in ignored plan evidence. Initial harness
failures (missing Qt runtime library and same-interpreter native-dependency mixing)
are retained as diagnostics; they are not hidden as product passes.
