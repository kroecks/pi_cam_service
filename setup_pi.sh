#!/usr/bin/env bash
set -e

echo "🚀 Starting Pi Camera Service setup..."

# 1. System prep
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y git libcamera-apps ffmpeg v4l-utils python3-pip python3-venv python3-full libcap-dev

# 2. Camera setup
echo "📹 Configuring camera..."
# Enable camera in config
if ! grep -q "camera_auto_detect=1" /boot/config.txt; then
    echo "camera_auto_detect=1" | sudo tee -a /boot/config.txt
fi

# Add user to video group
sudo usermod -aG video "$USER"

# 3. Docker (for MediaMTX only)
echo "🐳 Setting up Docker..."
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
fi
if ! command -v docker compose &>/dev/null; then
    sudo apt install -y docker-compose-plugin
fi

# 4. Clone or pull latest repo
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

# 5. Setup Python virtual environment
echo "🐍 Setting up Python environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r app/requirements.txt
deactivate

# 6. Create MediaMTX config and start with Docker
echo "🎥 Setting up MediaMTX config..."
cat > mediamtx.yml << 'EOF'
# MediaMTX configuration for Pi Camera Service

# General settings
logLevel: info
logDestinations: [stdout]
logFile: ""

# API settings
api: yes
apiAddress: :9997

# Metrics
metrics: yes
metricsAddress: :9998

# Playback server (for recorded streams)
playback: yes
playbackAddress: :9996

# RTSP settings
rtspAddress: :8554
rtspEncryption: no
rtspServerKey: server.key
rtspServerCert: server.crt
rtspAuthMethods: [basic, digest]

# RTMP settings
rtmpAddress: :1935
rtmpEncryption: no
rtmpServerKey: server.key
rtmpServerCert: server.crt

# HLS settings
hlsAddress: :8888
hlsEncryption: no
hlsServerKey: server.key
hlsServerCert: server.crt
hlsAlwaysRemux: no
hlsVariant: lowLatency
hlsSegmentCount: 7
hlsSegmentDuration: 1s
hlsPartDuration: 200ms
hlsSegmentMaxSize: 50M
hlsAllowOrigin: "*"
hlsTrustedProxies: []
hlsDirectory: ""

# WebRTC settings
webrtcAddress: :8889
webrtcEncryption: no
webrtcServerKey: server.key
webrtcServerCert: server.crt
webrtcAllowOrigin: "*"
webrtcTrustedProxies: []
webrtcICEServers2: []

# SRT settings
srtAddress: :8890
srtEncryption: no

# Recording settings
recordPath: ./recordings/%path/%Y-%m-%d_%H-%M-%S-%f
recordFormat: fmp4
recordPartDuration: 1s
recordSegmentDuration: 1h
recordDeleteAfter: 24h

# Default path settings (for any stream)
pathDefaults:
  source: publisher
  sourceFingerprint: ""
  sourceOnDemand: no
  sourceOnDemandStartTimeout: 10s
  sourceOnDemandCloseAfter: 10s
  sourceRedirect: ""
  disablePublisherOverride: no
  fallback: ""
  publishUser: ""
  publishPass: ""
  publishIPs: []
  readUser: ""
  readPass: ""
  readIPs: []
  record: no
  playback: no
  runOnInit: ""
  runOnInitRestart: no
  runOnDemand: ""
  runOnDemandRestart: no
  runOnDemandStartTimeout: 10s
  runOnDemandCloseAfter: 10s
  runOnUnDemand: ""
  runOnReady: ""
  runOnNotReady: ""
  runOnRead: ""
  runOnUnread: ""
  runOnRecordSegmentCreate: ""
  runOnRecordSegmentComplete: ""

# Path-specific settings
paths:
  camera:
    source: publisher
  camera0:
    source: publisher
  camera1:
    source: publisher
  test:
    source: publisher
EOF

echo "🎥 Starting MediaMTX..."
docker compose up -d mediamtx

# 7. Setup systemd service for FastAPI
echo "🔧 Setting up systemd service..."
cat > /tmp/pi_cam_service.service << EOF
[Unit]
Description=Pi Camera RTSP Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/pi_cam_service
Environment=PATH=/opt/pi_cam_service/venv/bin
ExecStart=/opt/pi_cam_service/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --app-dir /opt/pi_cam_service/app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/pi_cam_service.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pi_cam_service.service

# 8. Test camera devices
echo "🔍 Checking camera devices..."
for i in {0..1}; do
    if [ -e "/dev/video$i" ]; then
        echo "✅ Found camera device: /dev/video$i"
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
echo "2. Start the service: sudo systemctl start pi_cam_service"
echo "3. Test the API: curl http://localhost:8000/cameras"
echo "4. Start a stream: curl -X POST http://localhost:8000/stream/start/camera0"
echo "5. View stream: rtsp://your-pi-ip:8554/camera"
echo ""
echo "🌐 Web interfaces:"
echo "- API: http://localhost:8000/docs"
echo "- MediaMTX: http://localhost:9997"
echo "- HLS streams: http://localhost:8888"
echo ""
echo "⚠️  A reboot is recommended so camera and group changes take effect."