FROM dtcooper/raspberrypi-os:python3.11-bookworm

RUN apt update -y && apt upgrade -y && apt install git vim -y

#libcamera
RUN apt install libcamera-tools libcamera-apps-lite -y
RUN apt install libcap-dev libcamera-dev -y
RUN apt install libatlas-base-dev libopenjp2-7 libkms++-dev libfmt-dev libdrm-dev -y
RUN pip install rpi-libcamera rpi-kms

#picamera2
RUN apt install -y python3-picamera2 --no-install-recommends
RUN pip install picamera2

FROM raspbian/bookworm:latest

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    v4l-utils \
    libv4l-dev \
    python3-opencv \
    python3-dev \
    gcc \
    pkg-config \
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

# Create non-root user
RUN useradd -m -u 1000 apiuser && chown -R apiuser:apiuser /app
USER apiuser

EXPOSE 8000

CMD ["python", "-m", "api.main"]