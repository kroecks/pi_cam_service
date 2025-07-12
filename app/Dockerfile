FROM python:3.11-slim

WORKDIR /app
COPY . /app

# Add missing tools
RUN apt-get update && \
    apt-get install -y ffmpeg libcamera-apps && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
