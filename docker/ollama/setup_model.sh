#!/bin/bash
# SENTINEL AI - Model Setup Script
# Configures Ollama with the selected model(s)
#
# Environment:
#   SENTINEL_MODEL  - qwen2.5 (default) | whiterabbitneo | both
#
# Usage (standalone):
#   SENTINEL_MODEL=qwen2.5 ./setup_model.sh

set -e

SENTINEL_MODEL="${SENTINEL_MODEL:-qwen2.5}"

echo "=========================================="
echo "SENTINEL AI - Ollama Model Setup"
echo "Model: ${SENTINEL_MODEL}"
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
# 2) Setup requested model(s)
# -----------------------------------------------------------

# Qwen 2.5 3B Instruct (Q4_K_M) — primary model
QWEN_URL="https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf"

# WhiteRabbitNeo 7B (Q4_K_M) — legacy / fallback
WRN_URL="https://huggingface.co/bartowski/WhiteRabbitNeo_WhiteRabbitNeo-V3-7B-GGUF/resolve/main/WhiteRabbitNeo_WhiteRabbitNeo-V3-7B-Q4_K_M.gguf"

case "$SENTINEL_MODEL" in
    qwen2.5)
        setup_model "sentinel-qwen" "/Modelfile.qwen2.5" "$QWEN_URL" "1.9GB"
        ;;
    whiterabbitneo)
        # Legacy: requires Modelfile.whiterabbitneo in container
        if [ -f /Modelfile.whiterabbitneo ]; then
            setup_model "whiterabbitneo" "/Modelfile.whiterabbitneo" "$WRN_URL" "4.5GB"
        else
            echo "[WARN] Modelfile.whiterabbitneo not found, skipping."
        fi
        ;;
    both)
        setup_model "sentinel-qwen" "/Modelfile.qwen2.5" "$QWEN_URL" "1.9GB"
        if [ -f /Modelfile.whiterabbitneo ]; then
            setup_model "whiterabbitneo" "/Modelfile.whiterabbitneo" "$WRN_URL" "4.5GB"
        fi
        ;;
    *)
        echo "[ERROR] Unknown SENTINEL_MODEL='${SENTINEL_MODEL}'. Use: qwen2.5 | whiterabbitneo | both"
        exit 1
        ;;
esac

echo "=========================================="
echo "SENTINEL AI - Model(s) Ready!"
echo "API: http://localhost:11434"
echo "=========================================="

# Keep container running
wait $OLLAMA_PID
