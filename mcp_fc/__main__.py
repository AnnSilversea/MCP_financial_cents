"""Run the Financial Cents MCP server over stdio (default FastMCP transport)."""

from __future__ import annotations


def run() -> None:
    """Console script entrypoint (`financial-cents-mcp`)."""
    from mcp_fc.server import mcp

    mcp.run()


if __name__ == "__main__":
    run()
