#!/usr/bin/env bash
set -e

# 1. System prep
sudo apt update && sudo apt upgrade -y
sudo apt install -y git libcamera-apps ffmpeg

# 2. Docker (skip if already present)
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER"
fi
if ! command -v docker compose &>/dev/null; then
  sudo apt install -y docker-compose-plugin
fi

# 3. Clone repo under /opt and bring it up
sudo mkdir -p /opt && sudo chown "$USER" /opt
cd /opt
if [ ! -d pi-cam-service ]; then
  git clone https://github.com/kroecks/pi-cam-service.git
fi
cd pi-cam-service

docker compose pull
docker compose up -d

# 4. Enable systemd unit so stack survives reboot
sudo cp systemd/pi-cam-service.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pi-cam-service.service

echo "✔ Setup complete. Reboot recommended so new groups & camera goodies take effect."