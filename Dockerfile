FROM python:3.13-slim

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code (.dockerignore keeps .env, .venv, etc. out).
COPY . .

# Don't buffer stdout/stderr so container logs appear in real time.
ENV PYTHONUNBUFFERED=1
# Persist dedup state and the heartbeat on the mounted volume (see compose).
ENV STATE_FILE=/data/replied.json \
    HEARTBEAT_FILE=/data/heartbeat

# Report health to Portainer based on the bot's heartbeat freshness.
HEALTHCHECK --interval=60s --timeout=10s --start-period=90s --retries=3 \
    CMD ["python", "healthcheck.py"]

# This is a background worker, not a web server — just run the bot.
CMD ["python", "bot.py"]
