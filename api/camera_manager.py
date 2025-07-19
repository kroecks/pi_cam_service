import cv2
import asyncio
import json
import os
from typing import List, Dict, Optional
from .models import CameraInfo


class CameraManager:
    def __init__(self):
        self.cameras = {}
        self.config_file = "config/camera_config.json"

    async def initialize(self):
        """Initialize camera manager"""
        await self.detect_cameras()
        await self.load_config()

    async def detect_cameras(self):
        """Detect available cameras using OpenCV and libcamera"""
        detected_cameras = []

        # Check for USB/CSI cameras using OpenCV
        for i in range(4):  # Check first 4 camera indices
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret:
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        fps = int(cap.get(cv2.CAP_PROP_FPS))

                        detected_cameras.append(CameraInfo(
                            id=i,
                            name=f"Camera {i}",
                            type="USB/CSI",
                            resolution=f"{width}x{height}",
                            fps=fps,
                            available=True
                        ))
                cap.release()
            except:
                continue

        # Try to detect libcamera devices
        try:
            import subprocess
            result = subprocess.run(['libcamera-hello', '--list-cameras'],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # Parse libcamera output (simplified)
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'Available cameras' in line:
                        # Add libcamera devices
                        detected_cameras.append(CameraInfo(
                            id=len(detected_cameras),
                            name="Pi Camera",
                            type="libcamera",
                            resolution="1920x1080",
                            fps=30,
                            available=True
                        ))
        except:
            pass

        self.cameras = {cam.id: cam for cam in detected_cameras}

    async def load_config(self):
        """Load camera configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Update camera settings from config
                    for cam_id, settings in config.items():
                        if int(cam_id) in self.cameras:
                            camera = self.cameras[int(cam_id)]
                            camera.name = settings.get('name', camera.name)
                            camera.resolution = settings.get('resolution', camera.resolution)
                            camera.fps = settings.get('fps', camera.fps)
            except Exception as e:
                print(f"Error loading config: {e}")

    async def get_available_cameras(self) -> List[CameraInfo]:
        """Get list of available cameras"""
        return list(self.cameras.values())

    async def get_camera(self, camera_id: int) -> Optional[CameraInfo]:
        """Get specific camera by ID"""
        return self.cameras.get(camera_id)