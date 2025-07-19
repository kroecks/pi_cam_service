import asyncio
import subprocess
import requests
import json
from typing import Dict, List, Optional
from .models import StreamStatus


class StreamManager:
    def __init__(self):
        self.active_streams = {}
        self.mediamtx_host = "mediamtx"
        self.mediamtx_port = 8554
        self.mediamtx_api_port = 9997

    async def initialize(self):
        """Initialize stream manager"""
        # Wait for MediaMTX to be ready
        await self.wait_for_mediamtx()

    async def wait_for_mediamtx(self):
        """Wait for MediaMTX to be ready"""
        for _ in range(30):  # Wait up to 30 seconds
            try:
                response = requests.get(f"http://{self.mediamtx_host}:{self.mediamtx_api_port}/v1/paths/list")
                if response.status_code == 200:
                    return
            except:
                pass
            await asyncio.sleep(1)
        raise Exception("MediaMTX not ready")

    async def start_stream(self, camera_id: int, stream_name: str) -> Dict:
        """Start RTSP stream for a camera"""
        if stream_name in self.active_streams:
            return {"error": "Stream already active"}

        try:
            # Build ffmpeg command for the camera
            cmd = self.build_ffmpeg_command(camera_id, stream_name)

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

            return {
                "success": True,
                "stream_name": stream_name,
                "rtsp_url": f"rtsp://localhost:{self.mediamtx_port}/{stream_name}"
            }

        except Exception as e:
            return {"error": str(e)}

    def build_ffmpeg_command(self, camera_id: int, stream_name: str) -> List[str]:
        """Build ffmpeg command for streaming"""
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
            await process.wait()

            # Remove from active streams
            del self.active_streams[stream_name]

            return {"success": True, "message": f"Stream {stream_name} stopped"}

        except Exception as e:
            return {"error": str(e)}

    async def get_active_streams(self) -> List[StreamStatus]:
        """Get list of active streams"""
        streams = []
        for stream_name, info in self.active_streams.items():
            streams.append(StreamStatus(
                stream_name=stream_name,
                camera_id=info["camera_id"],
                rtsp_url=info["rtsp_url"],
                status="active"
            ))
        return streams