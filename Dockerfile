# ═══════════════════════════════════════════════════════════════
# LOG-FIB SCALPER - DOCKERFILE
# ═══════════════════════════════════════════════════════════════
# Production-ready container for 24/7 live trading

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default command (override in docker-compose)
CMD ["python", "live_trading/crypto/crypto_agent.py"]
