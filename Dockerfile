FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set Python path to include the app directory
ENV PYTHONPATH=/app

# Create non-root user
RUN useradd --create-home --shell /bin/bash fifo && \
    chown -R fifo:fifo /app
USER fifo

# Expose port
EXPOSE 8000

# Health check (simplified to avoid curl dependency)
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the simplified application
CMD ["python", "-m", "api.app_simple"]