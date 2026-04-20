# Run MCP server (stdio) from repository root. Requires `uv sync` or a venv with the project installed.
Set-Location (Split-Path -Parent $PSScriptRoot)
if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv run python -m mcp_fc @args
} elseif (Test-Path .\.venv\Scripts\python.exe) {
    .\.venv\Scripts\python.exe -m mcp_fc @args
} else {
    python -m mcp_fc @args
}
