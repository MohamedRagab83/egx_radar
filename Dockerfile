FROM python:3.11-slim

LABEL maintainer="EGX Radar Team"
LABEL version="0.8.3"
LABEL description="EGX Radar - High-performance algorithmic trading system"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Create directories for logs and data
RUN mkdir -p /app/logs /app/data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from egx_radar.backtest.engine import run_backtest; print('OK')" || exit 1

# Install package
RUN pip install -e . --user

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV WORKERS_COUNT=4
ENV MAX_BACKTEST_SECONDS=60

# Default command
CMD ["python", "-m", "egx_radar"]
