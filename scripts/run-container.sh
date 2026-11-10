#!/bin/sh
# Start only an already-built image; build output must never enter MCP stdout.
set -eu
cd "$(dirname "$0")/.."
export ANKIPLUS_REVISION="${1:-development-dirty}"
export ANKIPLUS_SOURCES="${2:-$PWD/examples}"
if ! docker image inspect "ankiplusmcp:$ANKIPLUS_REVISION" >/dev/null 2>&1; then
    echo "Build ankiplusmcp:$ANKIPLUS_REVISION with Compose before starting its stdio transport." >&2
    exit 2
fi
exec docker compose -p ankiplusmcp run --rm -T --pull never mcp
