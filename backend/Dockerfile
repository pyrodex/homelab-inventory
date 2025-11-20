FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py config.py models.py exceptions.py validators.py ./
COPY routes ./routes
COPY services ./services
RUN mkdir -p /app/data

EXPOSE 5000

CMD ["python", "app.py"]
