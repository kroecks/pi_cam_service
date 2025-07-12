from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from picamera2 import Picamera2
import subprocess
import asyncio
from typing import Dict, Optional, List
import logging
import psutil
import os
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Pi Camera RTSP Service")

# Global state for camera and streams
camera_streams: Dict[str, subprocess.Popen] = {}
picam2: Optional[Picamera2] = None


class StreamRequest(BaseModel):
    resolution: str = "1920x1080"
    framerate: int = 30
    stream_name: str = "camera"


class CameraInfo(BaseModel):
    id: str
    name: str
    status: str
    device_path: str


@app.on_event("startup")
async def startup_event():
    global picam2
    try:
        # Initialize picamera2
        picam2 = Picamera2()
        logger.info("Camera initialized successfully")

        # Wait a moment for camera to be ready
        await asyncio.sleep(2)

    except Exception as e:
        logger.error(f"Failed to initialize camera: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    # Stop all streams
    for stream_id, process in camera_streams.items():
        if process.poll() is None:
            logger.info(f"Stopping stream {stream_id}")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    # Clean up camera
    if picam2:
        try:
            if picam2.started:
                picam2.stop()
            picam2.close()
            logger.info("Camera cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up camera: {e}")


@app.get("/")
async def root():
    return {"message": "Pi Camera RTSP Service", "version": "1.0.0"}


@app.get("/cameras", response_model=List[CameraInfo])
async def list_cameras():
    """List available cameras"""
    cameras = []

    # Check for video devices
    for i in range(2):  # Check video0 and video1
        device_path = f"/dev/video{i}"
        if os.path.exists(device_path):
            cameras.append(CameraInfo(
                id=f"camera{i}",
                name=f"Pi Camera {i}",
                status="available",
                device_path=device_path
            ))

    return cameras


@app.post("/stream/start/{camera_id}")
async def start_stream(camera_id: str, request: StreamRequest):
    """Start RTSP stream for a camera to MediaMTX"""
    try:
        if camera_id in camera_streams:
            process = camera_streams[camera_id]
            if process.poll() is None:
                return {
                    "message": f"Stream already running for {camera_id}",
                    "rtsp_url": f"rtsp://localhost:8554/{request.stream_name}"
                }

        # Determine device path
        device_num = camera_id.replace("camera", "")
        device_path = f"/dev/video{device_num}"

        if not os.path.exists(device_path):
            raise HTTPException(status_code=404, detail=f"Camera device {device_path} not found")

        # Configure picamera2 if using camera0
        if camera_id == "camera0" and picam2:
            try:
                if picam2.started:
                    picam2.stop()

                # Parse resolution
                width, height = map(int, request.resolution.split('x'))

                config = picam2.create_video_configuration(
                    main={"size": (width, height)},
                    encode="main"
                )
                picam2.configure(config)
                picam2.start()

                # Give camera time to start
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error configuring picamera2: {e}")

        # Start FFmpeg stream to MediaMTX
        # MediaMTX accepts RTMP on port 1935 by default
        ffmpeg_cmd = [
            "ffmpeg",
            "-f", "v4l2",
            "-input_format", "mjpeg",  # Try MJPEG first
            "-video_size", request.resolution,
            "-framerate", str(request.framerate),
            "-i", device_path,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-f", "rtsp",
            f"rtsp://mediamtx:8554/{request.stream_name}"
        ]

        logger.info(f"Starting FFmpeg with command: {' '.join(ffmpeg_cmd)}")

        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        # Give FFmpeg a moment to start
        await asyncio.sleep(2)

        # Check if process is still running
        if process.poll() is not None:
            # Process died, get error output
            _, stderr = process.communicate()
            logger.error(f"FFmpeg failed to start: {stderr}")

            # Try alternative format
            ffmpeg_cmd[3] = "yuyv422"  # Try different input format
            logger.info(f"Retrying with YUYV422 format")

            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            await asyncio.sleep(2)

            if process.poll() is not None:
                _, stderr = process.communicate()
                raise HTTPException(status_code=500, detail=f"Failed to start stream: {stderr}")

        camera_streams[camera_id] = process

        return {
            "message": f"Stream started for {camera_id}",
            "rtsp_url": f"rtsp://localhost:8554/{request.stream_name}",
            "stream_name": request.stream_name,
            "resolution": request.resolution,
            "framerate": request.framerate
        }

    except Exception as e:
        logger.error(f"Error starting stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stream/stop/{camera_id}")
async def stop_stream(camera_id: str):
    """Stop RTSP stream for a camera"""
    try:
        if camera_id not in camera_streams:
            raise HTTPException(status_code=404, detail="Stream not found")

        process = camera_streams[camera_id]
        if process.poll() is None:
            logger.info(f"Stopping stream for {camera_id}")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing stream for {camera_id}")
                process.kill()
                process.wait()

        del camera_streams[camera_id]

        # Stop picamera2 if this was camera0
        if camera_id == "camera0" and picam2 and picam2.started:
            picam2.stop()

        return {"message": f"Stream stopped for {camera_id}"}

    except Exception as e:
        logger.error(f"Error stopping stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stream/status/{camera_id}")
async def stream_status(camera_id: str):
    """Get stream status for a camera"""
    if camera_id not in camera_streams:
        return {"status": "stopped"}

    process = camera_streams[camera_id]
    if process.poll() is None:
        return {
            "status": "running",
            "pid": process.pid,
            "cpu_percent": psutil.Process(process.pid).cpu_percent(),
            "memory_info": psutil.Process(process.pid).memory_info()._asdict()
        }
    else:
        return {"status": "stopped", "return_code": process.returncode}


@app.get("/streams")
async def list_streams():
    """List all active streams"""
    active_streams = {}
    for camera_id, process in list(camera_streams.items()):
        if process.poll() is None:
            try:
                proc_info = psutil.Process(process.pid)
                active_streams[camera_id] = {
                    "status": "running",
                    "pid": process.pid,
                    "cpu_percent": proc_info.cpu_percent(),
                    "memory_mb": proc_info.memory_info().rss / 1024 / 1024
                }
            except psutil.NoSuchProcess:
                active_streams[camera_id] = {"status": "stopped"}
                # Clean up dead process
                del camera_streams[camera_id]
        else:
            active_streams[camera_id] = {"status": "stopped", "return_code": process.returncode}
            # Clean up stopped process
            del camera_streams[camera_id]

    return {"streams": active_streams}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "camera_initialized": picam2 is not None,
        "active_streams": len([p for p in camera_streams.values() if p.poll() is None]),
        "system_info": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
    }