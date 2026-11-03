FROM python:3.12-slim

WORKDIR /app

# Install system utilities if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application codebase
COPY . .

# Install package in non-editable mode
RUN pip install --no-cache-dir .

# Create non-root user and persistent data volume directory
RUN mkdir -p /data && useradd -m -u 1000 learnloop && chown -R learnloop:learnloop /data /app
USER learnloop

# Environment defaults
ENV LEARNLOOP_DB_PATH=/data/learnloop.db
ENV LEARNLOOP_DATA_DIR=/data
ENV LEARNLOOP_HTTP_HOST=0.0.0.0
ENV LEARNLOOP_HTTP_PORT=8000
ENV LEARNLOOP_DASHBOARD_PORT=8765
ENV PYTHONUNBUFFERED=1

# Expose HTTP/SSE MCP (8000) and Dashboard (8765)
EXPOSE 8000 8765

# Start HTTP/SSE server
CMD ["python", "learnloop_http.py"]

