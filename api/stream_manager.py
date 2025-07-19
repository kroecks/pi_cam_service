import asyncio
import subprocess
import requests
import json
import logging
from typing import Dict, List, Optional
from .models import StreamStatus

logger = logging.getLogger(__name__)


class StreamManager:
    def __init__(self):
        self.active_streams = {}
        self.mediamtx_host = "mediamtx"
        self.mediamtx_port = 8554
        self.mediamtx_api_port = 9997
        self.is_ready = False

    async def initialize(self):
        """Initialize stream manager"""
        logger.info("Initializing stream manager...")
        try:
            # Wait for MediaMTX to be ready
            await self.wait_for_mediamtx()
            self.is_ready = True
            logger.info("Stream manager ready")
        except Exception as e:
            logger.error(f"Stream manager initialization failed: {e}")
            self.is_ready = False
            raise

    async def wait_for_mediamtx(self):
        """Wait for MediaMTX to be ready"""
        max_retries = 60  # Wait up to 60 seconds
        retry_interval = 1

        for attempt in range(max_retries):
            try:
                # Try to connect to MediaMTX API
                response = requests.get(
                    f"http://{self.mediamtx_host}:{self.mediamtx_api_port}/v2/config/global/get",
                    timeout=5
                )
                if response.status_code == 200:
                    logger.info("MediaMTX is ready")
                    return
            except requests.exceptions.RequestException as e:
                logger.debug(f"MediaMTX not ready (attempt {attempt + 1}/{max_retries}): {e}")

            if attempt < max_retries - 1:
                await asyncio.sleep(retry_interval)

        raise Exception(f"MediaMTX not ready after {max_retries} seconds")

    async def start_stream(self, camera_id: int, stream_name: str) -> Dict:
        """Start RTSP stream for a camera"""
        if not self.is_ready:
            return {"error": "Stream manager not ready"}

        if stream_name in self.active_streams:
            return {"error": "Stream already active"}

        try:
            # Build ffmpeg command for the camera
            cmd = self.build_ffmpeg_command(camera_id, stream_name)
            logger.info(f"Starting stream with command: {' '.join(cmd)}")

            # Start the process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Store stream info
            self.active_streams[stream_name] = {
                "process": process,
                "camera_id": camera_id,
                "stream_name": stream_name,
                "rtsp_url": f"rtsp://{self.mediamtx_host}:{self.mediamtx_port}/{stream_name}"
            }

            logger.info(f"Started stream {stream_name} for camera {camera_id}")

            return {
                "success": True,
                "stream_name": stream_name,
                "rtsp_url": f"rtsp://localhost:{self.mediamtx_port}/{stream_name}"
            }

        except Exception as e:
            logger.error(f"Error starting stream: {e}")
            return {"error": str(e)}

    def build_ffmpeg_command(self, camera_id: int, stream_name: str) -> List[str]:
        """Build ffmpeg command for streaming"""
        if camera_id == 100:  # libcamera device
            return [
                "libcamera-vid",
                "--timeout", "0",  # Run indefinitely
                "--width", "1920",
                "--height", "1080",
                "--framerate", "30",
                "--codec", "h264",
                "--output", "-",
                "|",
                "ffmpeg",
                "-i", "-",
                "-c:v", "copy",
                "-f", "rtsp",
                f"rtsp://{self.mediamtx_host}:{self.mediamtx_port}/{stream_name}"
            ]
        else:  # V4L2 device
            return [
                "ffmpeg",
                "-f", "v4l2",
                "-i", f"/dev/video{camera_id}",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-tune", "zerolatency",
                "-g", "30",
                "-keyint_min", "30",
                "-b:v", "2000k",
                "-maxrate", "2000k",
                "-bufsize", "2000k",
                "-f", "rtsp",
                f"rtsp://{self.mediamtx_host}:{self.mediamtx_port}/{stream_name}"
            ]

    async def stop_stream(self, stream_name: str) -> Dict:
        """Stop RTSP stream"""
        if stream_name not in self.active_streams:
            return {"error": "Stream not found"}

        try:
            stream_info = self.active_streams[stream_name]
            process = stream_info["process"]

            # Terminate the process
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=10)
            except asyncio.TimeoutError:
                # Force kill if it doesn't terminate gracefully
                process.kill()
                await process.wait()

            # Remove from active streams
            del self.active_streams[stream_name]

            logger.info(f"Stopped stream {stream_name}")
            return {"success": True, "message": f"Stream {stream_name} stopped"}

        except Exception as e:
            logger.error(f"Error stopping stream {stream_name}: {e}")
            return {"error": str(e)}

    async def get_active_streams(self) -> List[StreamStatus]:
        """Get list of active streams"""
        streams = []

        # Clean up dead processes
        dead_streams = []
        for stream_name, info in self.active_streams.items():
            process = info["process"]
            if process.returncode is not None:
                dead_streams.append(stream_name)

        for stream_name in dead_streams:
            logger.info(f"Cleaning up dead stream: {stream_name}")
            del self.active_streams[stream_name]

        # Return active streams
        for stream_name, info in self.active_streams.items():
            streams.append(StreamStatus(
                stream_name=stream_name,
                camera_id=info["camera_id"],
                rtsp_url=info["rtsp_url"],
                status="active"
            ))
        return streams