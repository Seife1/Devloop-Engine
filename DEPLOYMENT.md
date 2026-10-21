# LearnLoop Deployment Configuration
# HTTP/SSE Distribution Strategy

## HTTP Endpoints

### Base URL: https://learnloop.yourdomain.com

### Endpoints:
1. **GET /** - Server status, docs, and endpoint dashboard
2. **GET /health** - Health check and SQLite database path
3. **GET /mcp** - Streamable HTTP info and tool discovery
4. **POST /mcp** - Modern Streamable HTTP JSON-RPC transport (`initialize`, `tools/list`, `tools/call`)
5. **GET /sse** - Standard Server-Sent Events stream (yields endpoint `/mcp/v1/call`)
6. **POST /mcp/v1/call** - MCP JSON-RPC execution endpoint
7. **GET /mcp/v1/tools** - JSON-RPC tools listing
8. **GET /rules** - Raw official `AGENTS.md` rules
9. **GET /setup.ps1** - Dynamic one-shot PowerShell LAN/remote installer
10. **GET /setup.sh** - Dynamic one-shot Bash LAN/remote installer
11. **GET /tools** & **POST /call/{name}** - Legacy REST testing endpoints

## Docker Deployment

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 learnloop
USER learnloop

# Expose port
EXPOSE 8000

# Start server
CMD ["python", "learnloop_http.py"]
```

## Environment Variables

```bash
# Database
LEARNLOOP_DB_PATH=/data/learnloop.db
LEARNLOOP_DATA_DIR=/data

# Server
LEARNLOOP_HTTP_HOST=0.0.0.0
LEARNLOOP_HTTP_PORT=8000
LEARNLOOP_DASHBOARD_PORT=8765

# Security
LEARNLOOP_ALLOWED_ORIGINS=*
LEARNLOOP_API_KEY=optional-auth-key
```

## Deployment Platforms

### 1. **Fly.io** (Recommended)
```bash
fly launch --dockerfile Dockerfile
fly scale memory 256
fly deploy
```

### 2. **Railway.app**
```bash
railway init
railway add
railway up
```

### 3. **Replit**
- Upload `learnloop_http.py`
- Set `replit.nix` with Python dependencies
- Configure Secrets for environment variables

### 4. **DigitalOcean App Platform**
- Connect GitHub repository
- Set build command: `pip install -r requirements.txt`
- Set run command: `python learnloop_http.py`

## Client Integration

### 1. One-Shot LAN / Remote Setup (Recommended)
From any remote computer on the same network or internet:

* **Windows (PowerShell):**
  ```powershell
  irm http://<SERVER-HOST>:8000/setup.ps1 | iex
  ```
* **macOS / Linux (Bash):**
  ```bash
  curl -sSL http://<SERVER-HOST>:8000/setup.sh | bash
  ```

This automatically downloads `AGENTS.md` and `.windsurfrules` and configures `mcp_config.json` with `mcp-remote`.

### 2. Manual MCP Client Configuration (Windsurf, Claude Desktop, Cursor)
```json
{
  "mcpServers": {
    "learnloop": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://<SERVER-HOST>:8000/sse"
      ]
    }
  }
}
```

### 3. Direct Modern Streamable HTTP (Cursor / Future IDEs)
```json
{
  "mcpServers": {
    "learnloop": {
      "url": "http://<SERVER-HOST>:8000/mcp"
    }
  }
}
```

### Web Client Example
```javascript
// Connect to SSE
const eventSource = new EventSource('https://learnloop.yourdomain.com/api/events');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('LearnLoop event:', data);
};

// Execute tool
async function executeTool(tool, args) {
  const response = await fetch('https://learnloop.yourdomain.com/api/execute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tool, arguments: args })
  });
  return await response.json();
}
```

## Security Considerations

1. **API Authentication**: Optional API key for production
2. **CORS**: Configure allowed origins
3. **Rate Limiting**: Implement per-IP rate limiting
4. **Data Isolation**: Projects isolated by workspace hash
5. **Redaction**: Always enabled for HTTP transport

---

## Windows Standalone Desktop App & GUI

LearnLoop provides a zero-dependency standalone Windows executable (`dist/learnloop.exe`) bundling Microsoft Edge WebView2:

### Usage on Windows:
- **Interactive Double-Click**: Double-clicking `learnloop.exe` in File Explorer automatically detaches the console and launches a native desktop application window into the 3-Step Setup Wizard.
- **IDE MCP Mode**: When spawned silently by Cursor, VS Code, or Windsurf via stdio pipes (`learnloop`), it runs the headless FastMCP server.
- **CLI Commands**:
  ```powershell
  # Launch native desktop application window
  learnloop gui

  # Launch native desktop window directly into dashboard
  learnloop gui --route /

  # Run setup wizard in external web browser tab instead
  learnloop setup --browser

  # Run dashboard directly in native desktop window
  learnloop dashboard --gui
  ```
