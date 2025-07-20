import cv2
import asyncio
import json
import os
import subprocess
import logging
from typing import List, Dict, Optional
from .models import CameraInfo

logger = logging.getLogger(__name__)


class CameraManager:
    def __init__(self):
        self.cameras = {}
        self.config_file = "config/camera_config.json"

    async def initialize(self):
        """Initialize camera manager"""
        logger.info("Initializing camera manager...")
        await self.detect_cameras()
        await self.load_config()
        logger.info(f"Found {len(self.cameras)} cameras")

    async def detect_cameras(self):
        """Detect available cameras using multiple methods"""
        detected_cameras = []

        # First check what video devices exist
        video_devices = self.get_video_devices()
        logger.info(f"Found video devices: {video_devices}")

        # Test each video device
        for device_path in video_devices:
            device_id = int(device_path.split('video')[-1])
            try:
                if await self.test_camera_device(device_path):
                    camera_info = await self.get_camera_info(device_id, device_path)
                    if camera_info:
                        detected_cameras.append(camera_info)
                        logger.info(f"Added camera: {camera_info.name}")
            except Exception as e:
                logger.warning(f"Error testing camera {device_path}: {e}")
                continue

        # Try to detect libcamera devices (Pi Camera)
        try:
            pi_cameras = await self.detect_libcamera_devices()
            detected_cameras.extend(pi_cameras)
        except Exception as e:
            logger.warning(f"Error detecting libcamera devices: {e}")

        self.cameras = {cam.id: cam for cam in detected_cameras}

    def get_video_devices(self) -> List[str]:
        """Get list of video device paths"""
        devices = []
        try:
            result = subprocess.run(['ls', '/dev/video*'],
                                    capture_output=True, text=True)
            if result.returncode == 0:
                devices = result.stdout.strip().split('\n')
                devices = [d for d in devices if d and 'video' in d]
        except Exception as e:
            logger.warning(f"Error listing video devices: {e}")
        return devices

    async def test_camera_device(self, device_path: str) -> bool:
        """Test if a camera device is accessible"""
        try:
            # Use v4l2-ctl to check if device is a camera
            result = subprocess.run([
                'v4l2-ctl', '--device', device_path, '--list-formats-ext'
            ], capture_output=True, text=True, timeout=5)

            if result.returncode == 0 and 'YUYV' in result.stdout:
                return True

        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout testing {device_path}")
        except Exception as e:
            logger.warning(f"Error testing {device_path}: {e}")

        return False

    async def get_camera_info(self, device_id: int, device_path: str) -> Optional[CameraInfo]:
        """Get camera information"""
        try:
            # Get device info using v4l2-ctl
            result = subprocess.run([
                'v4l2-ctl', '--device', device_path, '--all'
            ], capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                output = result.stdout

                # Extract camera name
                name = f"Camera {device_id}"
                for line in output.split('\n'):
                    if 'Card type' in line:
                        name = line.split(':')[-1].strip()
                        break

                # Try to get resolution info
                resolution = "Unknown"
                fps = 30

                formats_result = subprocess.run([
                    'v4l2-ctl', '--device', device_path, '--list-formats-ext'
                ], capture_output=True, text=True, timeout=5)

                if formats_result.returncode == 0:
                    lines = formats_result.stdout.split('\n')
                    for line in lines:
                        if 'Size:' in line and 'Discrete' in line:
                            # Extract resolution like "Size: Discrete 640x480"
                            parts = line.split()
                            for part in parts:
                                if 'x' in part and part.replace('x', '').replace('0', '').replace('1', '').replace('2',
                                                                                                                   '').replace(
                                        '3', '').replace('4', '').replace('5', '').replace('6', '').replace('7',
                                                                                                            '').replace(
                                        '8', '').replace('9', '') == '':
                                    resolution = part
                                    break
                            break

                return CameraInfo(
                    id=device_id,
                    name=name,
                    type="V4L2",
                    resolution=resolution,
                    fps=fps,
                    available=True
                )
        except Exception as e:
            logger.warning(f"Error getting camera info for {device_path}: {e}")

        return None

    async def detect_libcamera_devices(self) -> List[CameraInfo]:
        """Detect libcamera devices (Raspberry Pi cameras)"""
        cameras = []
        try:
            result = subprocess.run([
                '/usr/bin/libcamera-hello', '--list-cameras'
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                output = result.stdout
                if 'Available cameras' in output:
                    # Simple detection - just add one Pi camera if libcamera works
                    cameras.append(CameraInfo(
                        id=100,  # Use high ID to avoid conflicts
                        name="Raspberry Pi Camera",
                        type="libcamera",
                        resolution="1920x1080",
                        fps=30,
                        available=True
                    ))
                    logger.info("Detected Raspberry Pi camera via libcamera")
        except subprocess.TimeoutExpired:
            logger.warning("Timeout detecting libcamera devices")
        except Exception as e:
            logger.warning(f"Error detecting libcamera devices: {e}")

        return cameras

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
                logger.info("Loaded camera configuration")
            except Exception as e:
                logger.warning(f"Error loading config: {e}")

    async def get_available_cameras(self) -> List[CameraInfo]:
        """Get list of available cameras"""
        return list(self.cameras.values())

    async def get_camera(self, camera_id: int) -> Optional[CameraInfo]:
        """Get specific camera by ID"""
        return self.cameras.get(camera_id)