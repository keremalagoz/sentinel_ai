#!/bin/bash
# SENTINEL AI - Llama 3 Model Pull Script
# Sprint 0.2: Model initialization
# Model: llama3:8b-instruct-q4_K_M (Optimized for local usage - ~4.7GB)

echo "=========================================="
echo "SENTINEL AI - Llama 3 Service Starting..."
echo "=========================================="

# Start Ollama server in background
echo "[1/3] Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "[2/3] Waiting for Ollama to initialize..."
sleep 10

# Check if model exists, if not pull it
if ollama list | grep -q "llama3"; then
    echo "[3/3] Model already exists, skipping download."
else
    echo "[3/3] Pulling Llama 3 model (this may take a while on first run)..."
    ollama pull llama3:8b-instruct-q4_K_M
fi

echo "=========================================="
echo "SENTINEL AI - Llama 3 Service Ready!"
echo "API available at: http://localhost:11434"
echo "=========================================="

# Keep container running by waiting for Ollama process
wait $OLLAMA_PID



