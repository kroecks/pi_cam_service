# Stage 1: Raspberry Pi specific dependencies
FROM dtcooper/raspberrypi-os:python3.11-bookworm AS rpi-stage

RUN apt update -y && apt upgrade -y && apt install git vim -y

# Install libcamera dependencies
RUN apt install libcamera-tools libcamera-apps-lite -y
RUN apt install libcap-dev libcamera-dev -y
RUN apt install libatlas-base-dev libopenjp2-7 libkms++-dev libfmt-dev libdrm-dev -y

# Install Python packages for RPi
RUN pip install rpi-libcamera rpi-kms

# Install picamera2
RUN apt install -y python3-picamera2 --no-install-recommends
RUN pip install picamera2

# Stage 2: Final application image
FROM python:3.11-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    v4l-utils \
    libv4l-dev \
    python3-opencv \
    python3-dev \
    gcc \
    pkg-config \
    # Add libraries that picamera2 needs at runtime
    libc6 \
    libstdc++6 \
    libgcc-s1 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python site-packages from RPi stage
COPY --from=rpi-stage /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy system-installed Python packages (like python3-picamera2)
COPY --from=rpi-stage /usr/lib/python3/dist-packages /usr/lib/python3/dist-packages

# Copy libcamera libraries and binaries
COPY --from=rpi-stage /usr/lib/aarch64-linux-gnu/libcamera* /usr/lib/aarch64-linux-gnu/
COPY --from=rpi-stage /usr/lib/aarch64-linux-gnu/libdrm* /usr/lib/aarch64-linux-gnu/
COPY --from=rpi-stage /usr/lib/aarch64-linux-gnu/libkms* /usr/lib/aarch64-linux-gnu/
COPY --from=rpi-stage /usr/lib/aarch64-linux-gnu/libfmt* /usr/lib/aarch64-linux-gnu/
COPY --from=rpi-stage /usr/bin/libcamera-* /usr/bin/

# Copy any additional RPi-specific libraries that might be needed
COPY --from=rpi-stage /usr/include/libcamera /usr/include/libcamera
COPY --from=rpi-stage /usr/lib/aarch64-linux-gnu/pkgconfig/libcamera* /usr/lib/aarch64-linux-gnu/pkgconfig/

WORKDIR /app

# Copy requirements and install additional Python dependencies
COPY requirements.txt .
RUN pip install --break-system-packages --no-cache-dir -r requirements.txt

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