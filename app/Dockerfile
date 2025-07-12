FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# --- system packages -------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl gnupg && \
    # add Raspberry Pi OS repository so we can install libcamera-apps
    echo "deb http://archive.raspberrypi.com/debian bookworm main" \
        > /etc/apt/sources.list.d/raspi.list && \
    curl -fsSL https://archive.raspberrypi.com/debian/public.key \
        | gpg --dearmor -o /usr/share/keyrings/raspberrypi-archive-keyring.gpg && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        libcamera-apps && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# --- python app ------------------------------------------------------
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
