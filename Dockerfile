FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ .

# Data directory (mounted as volume)
RUN mkdir -p /data

EXPOSE 8000

CMD ["python", "server.py"]
