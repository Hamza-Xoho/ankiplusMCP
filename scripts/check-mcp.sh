#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src"
.venv/bin/python -m pytest -q tests/mcp tests/unit tests/contract/test_p0_foundations.py
sha256sum --check .codex/contract.sha256
.venv/bin/python -m build --wheel
