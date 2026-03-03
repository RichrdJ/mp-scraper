FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Persistent data lives here
RUN mkdir -p data

EXPOSE 7070

CMD ["python", "main.py"]
