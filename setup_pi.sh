#!/bin/bash

# Pi Camera Service Installation Script
# Run this script as a regular user (not root)

set -e

echo "🚀 Installing Pi Camera Service..."

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please run this script as a regular user (not root)"
    echo "Usage: ./install.sh"
    exit 1
fi

# Variables
SERVICE_DIR="/opt/pi_cam_service"
SERVICE_NAME="pi_cam_service"
CURRENT_USER=$(whoami)

# Create service directory
echo "📁 Creating service directory..."
sudo mkdir -p $SERVICE_DIR
sudo chown $CURRENT_USER:$CURRENT_USER $SERVICE_DIR

# Copy files to service directory
echo "📋 Copying files..."
cp -r . $SERVICE_DIR/
cd $SERVICE_DIR

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt update
sudo apt install -y python3-pip python3-venv python3-picamera2 python3-libcamera libcamera-dev docker.io docker-compose

# Install uvicorn for the current user (not in venv)
echo "🐍 Installing uvicorn for user $CURRENT_USER..."
pip3 install --user uvicorn fastapi

# Create virtual environment (as regular user, not root)
echo "🏗️ Creating virtual environment..."
python3 -m venv venv --system-site-packages
source venv/bin/activate

# Install Python dependencies in venv
echo "📚 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create systemd service file from template
echo "⚙️ Creating systemd service from template..."
if [ -f "$SERVICE_DIR/pi_cam_service.service.template" ]; then
    # Use local template file
    sed "s/{{USER}}/$CURRENT_USER/g" "$SERVICE_DIR/pi_cam_service.service.template" | \
    sed "s|{{SERVICE_DIR}}|$SERVICE_DIR|g" | \
    sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null
else
    echo "❌ Service template file not found at $SERVICE_DIR/pi_cam_service.service.template"
    exit 1
fi

# Enable and start the service
echo "🔧 Enabling service..."
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME

# Add user to docker group (for Docker option)
echo "🐳 Adding user to docker group..."
sudo usermod -a -G docker $CURRENT_USER

# Set proper permissions
echo "🔐 Setting permissions..."
sudo chown -R $CURRENT_USER:$CURRENT_USER $SERVICE_DIR
chmod +x $SERVICE_DIR/app/main.py 2>/dev/null || true

echo "✅ Installation complete!"
echo ""
echo "📋 Next steps:"
echo "1. Reboot your Pi: sudo reboot"
echo "2. Start the service: sudo systemctl start $SERVICE_NAME"
echo "3. Check status: sudo systemctl status $SERVICE_NAME"
echo "4. Test the API: curl http://localhost:8000/cameras"
echo "5. Start a stream: curl -X POST http://localhost:8000/stream/start/camera0"
echo "6. View stream: rtsp://your-pi-ip:8554/camera"
echo ""
echo "🔧 Optional: To use Docker instead, run:"
echo "   cd $SERVICE_DIR && docker compose up -d"
echo ""
echo "📝 Logs: sudo journalctl -u $SERVICE_NAME -f"