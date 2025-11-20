FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py config.py models.py exceptions.py validators.py ./
COPY routes ./routes
COPY services ./services
COPY utils ./utils
COPY scripts ./scripts
RUN mkdir -p /app/data /app/data/backups && \
    chmod +x /app/scripts/*.py 2>/dev/null || true

EXPOSE 5000

CMD ["python", "app.py"]
