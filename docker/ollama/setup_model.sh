#!/bin/bash
# SENTINEL AI - Model Setup Script
# Configures Ollama with Qwen 2.5 3B Instruct model
#
# Usage (standalone):
#   ./setup_model.sh

set -e

echo "=========================================="
echo "SENTINEL AI - Ollama Model Setup"
echo "Model: Qwen 2.5 3B Instruct"
echo "=========================================="

# -----------------------------------------------------------
# 1) Start Ollama server in background
# -----------------------------------------------------------
echo "[1/5] Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

# Wait for server readiness
echo "[2/5] Waiting for Ollama to be ready..."
sleep 5
until curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
    echo "  Waiting..."
    sleep 3
done
echo "Ollama is ready!"

# -----------------------------------------------------------
# Helper: setup a single model
# -----------------------------------------------------------
setup_model() {
    local model_name="$1"
    local modelfile_path="$2"
    local gguf_url="$3"
    local gguf_size="$4"

    # Check if model already exists
    if ollama list 2>/dev/null | grep -q "$model_name"; then
        echo "[INFO] Model '${model_name}' already exists, skipping."
        return 0
    fi

    echo "[3/5] Downloading ${model_name} GGUF (~${gguf_size})..."
    local gguf_file="/tmp/${model_name}.gguf"
    curl -L --progress-bar -o "$gguf_file" "$gguf_url"

    echo "[4/5] Creating Modelfile for ${model_name}..."
    sed "s|FROM ./.*\.gguf|FROM $gguf_file|" "$modelfile_path" > /tmp/Modelfile

    echo "[5/5] Registering model '${model_name}' in Ollama..."
    ollama create "$model_name" -f /tmp/Modelfile

    # Cleanup temp files
    rm -f "$gguf_file" /tmp/Modelfile
    echo "[OK] ${model_name} registered."
}

# -----------------------------------------------------------
# 2) Setup Qwen 2.5 3B Instruct (Q4_K_M)
# -----------------------------------------------------------
QWEN_URL="https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf"

setup_model "sentinel-qwen" "/Modelfile.qwen2.5" "$QWEN_URL" "1.9GB"

echo "=========================================="
echo "SENTINEL AI - Model Ready!"
echo "API: http://localhost:11434"
echo "=========================================="

# Keep container running
wait $OLLAMA_PID
