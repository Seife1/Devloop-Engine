# ADR 0008: Dashboard threat model and limits

**Status:** accepted

**Context.**
LearnLoop is designed to help learners understand and defend the code their AI coding assistants build. To review project components, explain-backs, readiness, and documentation outside the IDE without exposing the system to network risk or data corruption, LearnLoop introduces a local web dashboard (`learnloop dashboard`).

Because AI-generated content (code summaries, explanations, tags, titles) stored in SQLite is fundamentally untrusted, and because a local web server binds to a port on the developer's machine, the dashboard requires a rigorous, defense-in-depth threat model.

**Threats considered:**
1. **Accidental or malicious database modification:** Web requests causing writes, migrations, or database corruption.
2. **Cross-Site Scripting (XSS):** Malicious payloads stored in knowledge item summaries, learner explain-backs, project names, or markdown documents executing scripts in the developer's browser.
3. **DNS Rebinding & Cross-Origin attacks:** Malicious websites accessed by the developer triggering cross-origin requests to `localhost:8765` or rebinding DNS to interact with the local server.
4. **Local File Inclusion / Path Traversal:** Accessing arbitrary files on the developer's filesystem via document routes.
5. **Information Leakage:** Revealing full absolute paths, usernames, or sensitive repository locations.
6. **Denial of Service / Memory Exhaustion:** Large files in `.learn/` exhausting server memory.

**Decisions.**
1. **Read-Only SQLite by Construction:**
   - The dashboard opens SQLite exclusively via URI with `mode=ro`.
   - Any SQL write attempt is blocked at the SQLite engine level (`sqlite3.OperationalError: attempt to write a readonly database`).
   - The dashboard never runs database migrations; if `user_version` is older than required, it prints `"run: learnloop doctor"` and exits.
   - Pure queries only: computing readiness, staleness, and due items does not ingest the commit queue (`ingest=False`).

2. **Strict Localhost Binding & Port Handling:**
   - The server binds strictly to IPv4 `127.0.0.1`. Binding to `0.0.0.0` or public interfaces is rejected.
   - If the port is busy, the server prints a clear error to `stderr` and exits immediately without auto-incrementing.
   - Ctrl+C terminates the server cleanly.

3. **HTTP Verb & Method Restrictions:**
   - Only `GET` and `HEAD` methods are supported.
   - All other methods (`POST`, `PUT`, `DELETE`, `PATCH`) return `405 Method Not Allowed` with `Allow: GET, HEAD`.

4. **DNS Rebinding Protection:**
   - The `Host` header is strictly validated against `127.0.0.1:<port>` and `localhost:<port>`. Any other `Host` header immediately returns `403 Forbidden`.

5. **Security Headers on Every Route:**
   - `Content-Security-Policy: default-src 'none'; style-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'`
   - `X-Content-Type-Options: nosniff`
   - `Referrer-Policy: no-referrer`
   - `X-Frame-Options: DENY`
   - `Cache-Control: no-store`
   - No JavaScript is used or served in v1. No external CDNs, Google Fonts, or remote analytics.

6. **Strict HTML Escaping & Markdown Renderer:**
   - The custom markdown renderer escapes all HTML first via `html.escape()`.
   - Links are restricted to `http://` and `https://` schemas only, with `rel="noopener noreferrer"`.
   - `javascript:`, `data:`, and local file links are stripped. Images and raw HTML tags are strictly blocked.

7. **Path Traversal & Safe Document Reads:**
   - Documentation is read only from `<repo>/.learn/*.md`.
   - Files must be regular files (symlinks rejected), `<= 500 KB` in size, with their resolved parent directory matching `<repo>/.learn` exactly.
   - Project IDs must strictly match `^[a-f0-9]{12}$`.
   - Absolute filesystem paths are never displayed in HTML: only repository directory basenames are shown.

**Consequences.**
The dashboard is completely secure against remote web exploits, local path traversal, and data corruption. It has zero third-party dependencies, runs within the standard library (`http.server.ThreadingHTTPServer`), and provides a clean, private, read-only interface for reviewing project confidence.
