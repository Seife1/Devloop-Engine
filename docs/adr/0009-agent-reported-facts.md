# ADR 0009: Agent-Reported Sourced Facts ("Did You Know")

## Status
Accepted

## Context
Learners retain more context and feel more engaged when they learn surprising, practical, or historical engineering facts connected to the actual technologies, libraries, and architectural patterns used in their codebase.

However, LLMs and AI coding agents have a notorious tendency to generate confident hallucinations when asked for trivia, historical claims ("first invented by...", "created in 199X"), or subtle specification details.

LearnLoop is built on two core principles:
1. **Offline and Zero-Network by Design**: The LearnLoop MCP server runs locally, makes zero outbound HTTP requests, holds no API keys, and has no built-in LLM. It cannot browse the internet or verify external content.
2. **Grounding in Reality**: Exposure and learning must be tied to verified evidence, not loose agent speculation.

## Decision

We introduce the `project_facts` store and the `add_did_you_know` MCP tool with a strict division of responsibility:

### 1. Server-Side Structural & Syntactic Guardrails
Because the server cannot verify semantic truth, it aggressively enforces strict structural guarantees before accepting any fact:
- **Mandatory HTTPS Sources**: `source_url` must strictly use `https://`, have a valid domain hostname, contain no userinfo (`user:pass@`), and reject localhost, loopback addresses, private networks, and IP literals.
- **Bounded Lengths**: Topic <= 80 characters, fact text <= 300 characters, `source_url` <= 500 characters, `source_title` <= 200 characters.
- **Temporally Grounded**: `retrieved_at` must be a valid ISO 8601 UTC timestamp not in the future.
- **Daily Rate Limiting**: Maximum 5 facts per project per UTC calendar day to prevent trivia flooding or spam.
- **Deduplication**: Facts are normalized and hashed with SHA-256 (`(project_id, source_url, fact_hash)`) so repeated attempts are strictly idempotent.
- **Mandatory Redaction**: All agent-provided text passes through credential redaction before persistence.

### 2. Agent Protocol Requirements
The server offloads retrieval to the AI coding agent's own web tools:
- The agent **must** fetch and read the source page before proposing a fact.
- The fact must be phrased in the agent's own words (no raw copyrighted text blocks).
- Claims must be strictly supported by what the fetched source actually states.
- If the agent lacks web-browsing capabilities, it must decline and add nothing rather than guess or invent URLs.
- The agent must prefer official project documentation, RFCs, and release notes over blog aggregates.

### 3. Transparent UI Presentation
Every fact rendered in the LearnLoop dashboard:
- Displays an active, safe HTTPS link with `rel="noopener noreferrer"`.
- Displays the UTC retrieval date.
- Prominently displays the permanent label: **"Agent-reported: check the source"**.

## Consequences
- **Security**: The server never makes outbound network connections, completely eliminating Server-Side Request Forgery (SSRF) vulnerabilities.
- **Integrity**: Hallucinated URLs, internal network probing, and unsourced trivia are rejected at the protocol boundary.
- **Transparency**: The learner is never misled into believing the server verified the fact; the source link and disclosure banner empower the learner to verify the citation directly.
- **Rot & Drift**: Real links can decay or change over time. The immutable retrieval date documents the exact point in time when the citation was recorded.
