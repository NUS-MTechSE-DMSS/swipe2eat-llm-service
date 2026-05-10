FROM python:3.11-slim

ARG OLLAMA_MODEL=llama3.2:1b
ENV OLLAMA_MODEL=${OLLAMA_MODEL}

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

# Bake Mistral model into the image at build time.
# This avoids a 5-10 min download on every container start (which would cause
# ECS health check failures and an infinite restart loop on Fargate).
RUN ollama serve > /tmp/ollama.log 2>&1 & \
    sleep 8 && \
    ollama pull ${OLLAMA_MODEL:-llama3.2:1b} && \
    kill $(pgrep ollama) || true

# Expose Flask port (8080 to match ALB target group)
EXPOSE 8080

# Startup: start Ollama (model already baked in), wait for it, then Flask
RUN printf '%s\n' \
  '#!/bin/sh' \
  'set -e' \
  '' \
  'echo "Starting Ollama..."' \
  'ollama serve > /tmp/ollama.log 2>&1 &' \
  '' \
  'echo "Waiting for Ollama API to be ready..."' \
  'for i in $(seq 1 30); do' \
  '  if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then' \
  '    echo "Ollama is ready."' \
  '    break' \
  '  fi' \
  '  echo "Attempt $i/30 - waiting..."' \
  '  sleep 2' \
  'done' \
  '' \
  'echo "Warming up model into RAM..."' \
  'curl -s -X POST http://localhost:11434/api/generate \' \
  '  -d "{\"model\":\"${OLLAMA_MODEL:-llama3.2:1b}\",\"prompt\":\"hi\",\"stream\":false}" \' \
  '  > /dev/null' \
  'echo "Model warm-up complete."' \
  '' \
  'echo "Starting Flask app..."' \
  'cd /app/app && python main.py' \
  > /start.sh && chmod +x /start.sh

CMD ["/start.sh"]
