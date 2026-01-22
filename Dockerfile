# Multi-stage build for trading application with MetaTrader 5 support

# Base image with Python and wine for MT5
FROM python:3.10-slim

# Install system dependencies including wine for MT5
RUN apt-get update && apt-get install -y \
    wine wine32 wine64 \
    winetricks \
    xvfb \
    x11-utils \
    x11-apps \
    curl \
    ca-certificates \
    fonts-liberation \
    libxrender1 \
    libxext6 \
    libx11-6 \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Set environment variables for wine
ENV WINEPREFIX=/root/.wine \
    WINEARCH=win64 \
    DISPLAY=:99 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create application directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY data/ ./data/
COPY scripts/ ./scripts/

# Create data directories
RUN mkdir -p /app/data/backups /app/data/historical /app/logs /app/reports

# Health check: verify Python can import main modules
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "from src.main import TradingController; print('OK')" || exit 1

# Volume mount points
VOLUME ["/app/data", "/app/logs", "/app/config"]

# Default command: run trading system with auto-restart
CMD ["python", "-u", "src/main.py"]
