# ADR 0003: The git hook writes a local queue; it never calls the server

**Status:** accepted

MCP servers are pull-based and may not be running at commit time; a hook must never slow or break
`git commit`. The hook writes a redacted, metadata-only JSON file to `.learn/queue/<sha>.json`
(gitignored). The server ingests it on `ingest_queue`, deduped by sha. Diff bodies are NOT stored.
