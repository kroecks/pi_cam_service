FROM balenalib/raspberry-pi-debian:bullseye

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-dev \
        python3-numpy \
        python3-opencv \
        ffmpeg \
        v4l-utils \
        libcamera-apps \
        libcamera-dev \
        build-essential \
        && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir picamera2[gui] && \
    pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Expose port
EXPOSE 8000

# Run the application
CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]