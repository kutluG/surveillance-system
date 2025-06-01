# Edge AI Service Dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY edge_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY edge_service/ .

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]