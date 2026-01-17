# SENTINEL AI - WhiteRabbitNeo Service
# Cybersecurity-focused LLM for decision engine

FROM ollama/ollama:latest

# Install dependencies
USER root
RUN apt-get update && apt-get install -y curl bash && rm -rf /var/lib/apt/lists/*

# Copy setup script
COPY docker/whiterabbitneo/setup_model.sh /setup_model.sh
RUN chmod +x /setup_model.sh

# Copy Modelfile
COPY models/Modelfile.whiterabbitneo /Modelfile.whiterabbitneo

# Expose Ollama port
EXPOSE 11434

# Use shell entrypoint
ENTRYPOINT ["/bin/bash", "-c"]
CMD ["/setup_model.sh"]
