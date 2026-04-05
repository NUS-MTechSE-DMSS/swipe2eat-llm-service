FROM python:3.11-slim

WORKDIR /app

# System packages required for Ollama install
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    procps \
    zstd \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY app ./app
COPY schema_ai_analytics.sql ./

# Expose Flask and Ollama ports
EXPOSE 5000
EXPOSE 11434

# Startup script
RUN printf '%s\n' \
  '#!/bin/sh' \
  'set -e' \
  '' \
  'echo "Starting Ollama..."' \
  'ollama serve > /tmp/ollama.log 2>&1 &' \
  '' \
  'echo "Waiting for Ollama to start..."' \
  'sleep 5' \
  '' \
  'echo "Pulling model..."' \
  'ollama pull ${OLLAMA_MODEL:-mistral}' \
  '' \
  'echo "Starting Flask app..."' \
  'cd /app/app && python main.py' \
  > /start.sh && chmod +x /start.sh

CMD ["/start.sh"]