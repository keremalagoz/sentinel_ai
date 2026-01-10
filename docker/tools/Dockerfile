# SENTINEL AI - Security Tools Container
# Ubuntu 22.04 + Penetration Testing Tools

FROM ubuntu:22.04

# Prevent interactive prompts during install
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Istanbul

# Update and install security tools
RUN apt-get update && apt-get install -y \
    # Core tools
    nmap \
    gobuster \
    nikto \
    dirb \
    hydra \
    sqlmap \
    netcat-openbsd \
    curl \
    wget \
    whois \
    dnsutils \
    iputils-ping \
    net-tools \
    # Python for scripts
    python3 \
    python3-pip \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Create output directory for scan results
RUN mkdir -p /app/output

# Default command - keep container running
CMD ["tail", "-f", "/dev/null"]

