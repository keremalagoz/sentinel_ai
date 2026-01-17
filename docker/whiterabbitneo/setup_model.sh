#!/bin/bash
# SENTINEL AI - WhiteRabbitNeo Model Setup
# Downloads and configures WhiteRabbitNeo 7B for Ollama

set -e

MODEL_NAME="whiterabbitneo"
GGUF_URL="https://huggingface.co/bartowski/WhiteRabbitNeo_WhiteRabbitNeo-V3-7B-GGUF/resolve/main/WhiteRabbitNeo_WhiteRabbitNeo-V3-7B-Q4_K_M.gguf"
GGUF_FILE="/tmp/whiterabbitneo.gguf"

echo "=========================================="
echo "SENTINEL AI - WhiteRabbitNeo Setup"
echo "=========================================="

# Start Ollama in background
echo "[1/5] Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "[2/5] Waiting for Ollama to be ready..."
sleep 5
until curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
    echo "  Waiting..."
    sleep 3
done
echo "Ollama is ready!"

# Check if model already exists
if ollama list 2>/dev/null | grep -q "$MODEL_NAME"; then
    echo "[INFO] Model already exists, skipping download."
    echo "=========================================="
    echo "WhiteRabbitNeo Ready!"
    echo "API: http://localhost:11434"
    echo "=========================================="
    wait $OLLAMA_PID
    exit 0
fi

# Download GGUF file
echo "[3/5] Downloading WhiteRabbitNeo GGUF (~4.5GB)..."
curl -L --progress-bar -o "$GGUF_FILE" "$GGUF_URL"

# Update Modelfile with correct path
echo "[4/5] Creating Modelfile..."
sed "s|FROM ./whiterabbitneo-7b-q4.gguf|FROM $GGUF_FILE|" /Modelfile.whiterabbitneo > /tmp/Modelfile

# Create model in Ollama
echo "[5/5] Registering model in Ollama..."
ollama create "$MODEL_NAME" -f /tmp/Modelfile

# Cleanup
rm -f "$GGUF_FILE"
rm -f /tmp/Modelfile

echo "=========================================="
echo "WhiteRabbitNeo Ready!"
echo "API: http://localhost:11434"
echo "=========================================="

# Keep container running
wait $OLLAMA_PID
