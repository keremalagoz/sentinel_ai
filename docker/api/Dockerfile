# SENTINEL AI - API Backend Service
# Sprint 0.2: Placeholder (Will be configured in Sprint 2)
# Purpose: AI Orchestrator API endpoint

FROM python:3.11-slim

WORKDIR /app

# Install base dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true

# Expose API port
EXPOSE 8000

# Placeholder: Simple health check server
# Will be replaced with FastAPI in Sprint 2
CMD ["python", "-c", "import http.server; import socketserver; handler = http.server.SimpleHTTPRequestHandler; httpd = socketserver.TCPServer(('', 8000), handler); print('SENTINEL API placeholder running on port 8000'); httpd.serve_forever()"]



