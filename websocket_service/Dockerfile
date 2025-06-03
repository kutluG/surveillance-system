# WebSocket Service Dockerfile
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and group
RUN groupadd -r app && useradd -r -g app app
ENV PATH=/home/app/.local/bin:$PATH

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY websocket_service/requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy application code
COPY websocket_service/ .

# Copy shared modules
COPY --chown=app:app shared/ ./shared/

# Adjust ownership
RUN chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["curl","-f","http://localhost:8000/health"]

# Run the application
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000"]
