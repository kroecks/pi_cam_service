#!/bin/bash
set -e

echo "Starting Raspberry Pi Camera API setup..."

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "Please run this script as a regular user, not root"
    echo "The script will use sudo when needed"
    exit 1
fi

# Update system
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required system packages
echo "Installing system dependencies..."
sudo apt install -y \
    curl \
    wget \
    git \
    python3-full \
    python3-pip \
    python3-venv \
    v4l-utils \
    ffmpeg \
    libcamera-apps \
    libcamera-dev

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "Docker installed. You may need to log out and back in for group changes to take effect."
fi

# Install Docker Compose using apt (preferred method for Debian/Pi OS)
if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    sudo apt install -y docker-compose-plugin docker-compose
fi

# Enable camera interface (legacy camera support)
echo "Enabling camera interface..."
sudo raspi-config nonint do_camera 0

# Add user to video group for camera access
sudo usermod -aG video $USER

# Create necessary directories
mkdir -p logs
mkdir -p data
mkdir -p config

# Copy environment file
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file. Please edit it with your configuration."
fi

# Set permissions
chmod +x scripts/*.sh

# Check if user is in docker group
if ! groups $USER | grep &>/dev/null '\bdocker\b'; then
    echo "WARNING: User $USER is not in the docker group."
    echo "Please run 'newgrp docker' or log out and back in, then run this script again."
    exit 1
fi

# Test Docker
echo "Testing Docker installation..."
if ! docker --version; then
    echo "Docker installation failed"
    exit 1
fi

# Build and start services
echo "Building Docker containers..."
docker-compose build

echo "Starting services..."
docker-compose up -d

# Wait a moment for services to start
sleep 5

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "Setup complete! Services are running."
    echo "API should be available at http://localhost:8000"
    echo "MediaMTX web interface available at http://localhost:8889"
    echo ""
    echo "To check service status: docker-compose ps"
    echo "To view logs: docker-compose logs"
    echo "To stop services: docker-compose down"
else
    echo "WARNING: Some services may not have started properly."
    echo "Check logs with: docker-compose logs"
fi