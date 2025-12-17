FROM python:3.13-slim

WORKDIR /app

# Install cron for scheduled backups
RUN apt-get update && apt-get install -y --no-install-recommends cron && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py config.py models.py exceptions.py validators.py ./
COPY routes ./routes
COPY services ./services
COPY utils ./utils
COPY migrations ./migrations
COPY scripts ./scripts
RUN mkdir -p /app/data /app/data/backups && \
    chmod +x /app/scripts/*.py /app/scripts/*.sh 2>/dev/null || true

EXPOSE 5000

# Use entrypoint script to set up cron and run the app
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["python", "app.py"]
