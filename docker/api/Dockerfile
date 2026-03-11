# SENTINEL AI - API Backend Service
# Öncelik 5: AI Orchestrator API endpoint
# Purpose: Expose AI Orchestrator via REST API

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY main.py .

# Create database directory
RUN mkdir -p /app/data/databases

# Expose API port
EXPOSE 8000

# Environment variable to enable API mode
ENV SENTINEL_MODE=api

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI with uvicorn
CMD ["python", "-m", "uvicorn", "src.application.api_server:app", "--host", "0.0.0.0", "--port", "8000"]



