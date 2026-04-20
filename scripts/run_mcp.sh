#!/usr/bin/env sh
# Run MCP server (stdio) from repository root. Requires `uv sync` or a venv with the project installed.
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT" || exit 1
if command -v uv >/dev/null 2>&1; then
  exec uv run python -m mcp_fc "$@"
elif [ -x .venv/bin/python ]; then
  exec .venv/bin/python -m mcp_fc "$@"
else
  exec python -m mcp_fc "$@"
fi
