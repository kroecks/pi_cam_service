#!/usr/bin/env bash
set -e

echo "🚀 Starting Pi Camera Service setup..."

# 1. System prep
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y git libcamera-apps ffmpeg v4l-utils

# 2. Camera setup
echo "📹 Configuring camera..."
# Enable camera in config
if ! grep -q "camera_auto_detect=1" /boot/config.txt; then
    echo "camera_auto_detect=1" | sudo tee -a /boot/config.txt
fi

# Add user to video group
sudo usermod -aG video "$USER"

# 3. Docker (skip if already present)
echo "🐳 Setting up Docker..."
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
fi
if ! command -v docker compose &>/dev/null; then
    sudo apt install -y docker-compose-plugin
fi

# 4. Clone or pull latest repo into /opt
echo "📁 Setting up application..."
sudo mkdir -p /opt && sudo chown "$USER" /opt
cd /opt
if [ -d pi_cam_service/.git ]; then
    echo "Updating existing repo…"
    cd pi_cam_service && git pull
else
    git clone https://github.com/kroecks/pi_cam_service.git
    cd pi_cam_service
fi

# 5. Build & start stack
echo "🏗️ Building container images…"
docker compose build

echo "🚀 Starting services..."
docker compose up -d

# 6. Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
if docker compose ps | grep -q "Up"; then
    echo "✅ Services are running"
else
    echo "❌ Some services may not be running properly"
    docker compose logs
fi

# 7. Enable systemd service
echo "🔧 Setting up systemd service..."
sudo cp systemd/pi_cam_service.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pi_cam_service.service

# 8. Test camera devices
echo "🔍 Checking camera devices..."
for i in {0..1}; do
    if [ -e "/dev/video$i" ]; then
        echo "✅ Found camera device: /dev/video$i"
        # Test camera briefly
        if timeout 3 v4l2-ctl --device=/dev/video$i --list-formats-ext > /dev/null 2>&1; then
            echo "   📹 Camera $i is responsive"
        else
            echo "   ⚠️  Camera $i may not be working properly"
        fi
    else
        echo "❌ Camera device /dev/video$i not found"
    fi
done

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Reboot your Pi: sudo reboot"
echo "2. Test the API: curl http://localhost:8000/cameras"
echo "3. Start a stream: curl -X POST http://localhost:8000/stream/start/camera0"
echo "4. View stream: rtsp://your-pi-ip:8554/camera"
echo ""
echo "🌐 Web interfaces:"
echo "- API: http://localhost:8000/docs"
echo "- MediaMTX: http://localhost:9997"
echo "- HLS streams: http://localhost:8888"
echo ""
echo "⚠️  A reboot is recommended so camera and group changes take effect."