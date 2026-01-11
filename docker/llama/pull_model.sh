#!/bin/bash
# SENTINEL AI - Llama 3 Model Pull Script
# Model: llama3:8b-instruct-q4_K_M

echo "=========================================="
echo "SENTINEL AI - Llama 3 Service Starting..."
echo "=========================================="

echo "[1/3] Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

echo "[2/3] Waiting for Ollama to initialize..."
sleep 10

echo "[3/3] Checking model..."
MODEL_NAME="llama3:8b-instruct-q4_K_M"
if ollama list | grep -q "$MODEL_NAME"; then
    echo "Model $MODEL_NAME already exists, skipping download."
else
    echo "Pulling Llama 3 model (this may take a while)..."
    echo "Model: $MODEL_NAME (~4.7GB)"
    ollama pull $MODEL_NAME
fi

echo "=========================================="
echo "SENTINEL AI - Llama 3 Service Ready!"
echo "API: http://localhost:11434"
echo "=========================================="

wait $OLLAMA_PID
