#!/bin/sh
# Full local checks; check-mcp.sh remains available for Python-only development.
set -eu
cd "$(dirname "$0")/.."
.venv/bin/python scripts/check_privacy.py
.venv/bin/python scripts/check_versions.py
npm test
./scripts/check-mcp.sh
