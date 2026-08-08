FROM python:3.11-slim

WORKDIR /app

# Prevent bytecode + enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy full project
COPY backend /app/backend
COPY scripts /app/scripts
COPY migrations /app/migrations
COPY alembic.ini /app/alembic.ini

# Run the Telegram polling bot
CMD ["python", "scripts/run_polling.py"]
