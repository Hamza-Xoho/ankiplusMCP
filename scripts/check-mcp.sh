#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src"
.venv/bin/python -m pytest -q tests/mcp tests/unit tests/contract/test_p0_foundations.py
# macOS ships shasum, not sha256sum.
if command -v sha256sum >/dev/null 2>&1; then sha256sum --check .codex/contract.sha256; else shasum -a 256 --check .codex/contract.sha256; fi
.venv/bin/python -m build --wheel
