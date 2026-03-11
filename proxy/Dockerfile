FROM python:3.11-slim

WORKDIR /app

# Install system deps for asyncpg + tiktoken
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer cache)
COPY proxy/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy proxy package
COPY proxy/ ./proxy/

# Expose port
EXPOSE 8000

# Run from /app so `proxy` package resolves correctly
CMD ["uvicorn", "proxy.main:app", "--host", "0.0.0.0", "--port", "8000"]
