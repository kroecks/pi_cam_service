# Use the official Raspberry Pi OS base image
FROM --platform=linux/arm/v7 balenalib/raspberry-pi-debian:bookworm

# Add Raspberry Pi repository for camera packages
RUN echo "deb http://archive.raspberrypi.org/debian/ bookworm main" >> /etc/apt/sources.list.d/raspi.list && \
    apt-get update --allow-unauthenticated && \
    apt-get install -y --allow-unauthenticated raspberrypi-archive-keyring && \
    apt-get update

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    v4l-utils \
    libv4l-dev \
    python3-opencv \
    python3-dev \
    python3-pip \
    gcc \
    pkg-config \
    libcamera-dev \
    libcamera-tools \
    && rm -rf /var/lib/apt/lists/*

# Install picamera2 via pip instead of apt
RUN pip3 install --no-cache-dir picamera2

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY api/ ./api/
COPY config/ ./config/

# Create logs directory
RUN mkdir -p logs

# Create non-root user
RUN useradd -m -u 1000 apiuser && chown -R apiuser:apiuser /app
USER apiuser

EXPOSE 8000

CMD ["python3", "-m", "api.main"]