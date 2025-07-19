FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libcamera-dev \
    libcamera-apps \
    python3-picamera2 \
    python3-libcamera \
    ffmpeg \
    v4l-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api/ ./api/
COPY config/ ./config/

# Create logs directory
RUN mkdir -p logs

EXPOSE 8000

CMD ["python", "-m", "api.main"]