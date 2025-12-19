FROM python:3.13-slim

WORKDIR /app

# Install cron for scheduled backups
RUN apt-get update && apt-get install -y --no-install-recommends cron gosu && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user/group with UID/GID 1000
RUN groupadd -g 1000 app && \
    useradd -u 1000 -g 1000 -m -s /bin/bash app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py config.py models.py exceptions.py validators.py ./
COPY routes ./routes
COPY services ./services
COPY utils ./utils
COPY migrations ./migrations
COPY migrations/alembic.ini ./migrations/alembic.ini
COPY scripts ./scripts
RUN mkdir -p /app/data /app/data/backups && \
    chmod +x /app/scripts/*.py /app/scripts/*.sh 2>/dev/null || true && \
    chown -R app:app /app

EXPOSE 5000

# Use entrypoint script to set up cron and run the app
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["python", "app.py"]
