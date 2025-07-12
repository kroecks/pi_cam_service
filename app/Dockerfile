FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# --- system packages -------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        # Alternative: use v4l-utils for camera access
        v4l-utils \
        # Build tools if we need to compile libcamera
        build-essential \
        pkg-config \
        libssl-dev \
        && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# --- python app ------------------------------------------------------
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]