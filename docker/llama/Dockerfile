# SENTINEL AI - Llama 3 Local LLM Service
# Base: Ollama (Local LLM Runner)
# Sprint 0.2: Docker servis yapılandırması

FROM ollama/ollama:latest

# Copy the model pull script
COPY pull_model.sh /pull_model.sh
RUN chmod +x /pull_model.sh

# Expose Ollama default port
EXPOSE 11434

# Entrypoint: Start Ollama and pull model
ENTRYPOINT ["/bin/bash", "/pull_model.sh"]



