# SENTINEL AI - Ollama LLM Service
# Model: Qwen 2.5 3B Instruct (intent classification)

FROM ollama/ollama:latest

# Install dependencies
USER root
RUN apt-get update && apt-get install -y curl bash && rm -rf /var/lib/apt/lists/*

# Copy setup script
COPY docker/ollama/setup_model.sh /setup_model.sh
RUN chmod +x /setup_model.sh

# Copy Modelfiles
COPY models/Modelfile.qwen2.5 /Modelfile.qwen2.5

# Expose Ollama port
EXPOSE 11434

ENV SENTINEL_MODEL=qwen2.5

# Use shell entrypoint
ENTRYPOINT ["/bin/bash", "-c"]
CMD ["/setup_model.sh"]
