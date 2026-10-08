# ADR 0002: Pin the MCP Python SDK to 1.x

**Status:** accepted, revisit

mcp 2.x renamed `FastMCP` to `MCPServer` and changed other APIs. The server is built and tested on
`mcp>=1.2,<2` (verified on 1.30). Migrating to 2.x is a deliberate task: the transport layer is isolated
in `src/learnloop/mcp/` and `server.py`, so the change should not touch domain or services.
