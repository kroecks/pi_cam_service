from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import os
import logging
from contextlib import asynccontextmanager
from .camera_manager import CameraManager
from .stream_manager import StreamManager
from .models import CameraInfo, StreamStatus, StreamRequest
from picamera2 import Picamera2

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize managers
camera_manager = CameraManager()
stream_manager = StreamManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    try:
        logger.info("Starting up camera API...")
        await camera_manager.initialize()
        logger.info("Camera manager initialized")

        # Try to initialize stream manager, but don't fail if MediaMTX isn't ready
        try:
            await stream_manager.initialize()
            logger.info("Stream manager initialized")
        except Exception as e:
            logger.warning(f"Stream manager initialization failed: {e}")
            logger.info("API will start without stream functionality")

        yield
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        yield
    finally:
        logger.info("Shutting down...")


app = FastAPI(
    title="Raspberry Pi Camera API",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    return {"message": "Raspberry Pi Camera API", "version": "1.0.0"}


@app.get("/cameras", response_model=list[CameraInfo])
async def get_cameras():
    """Get list of available cameras"""
    try:
        cameras = await camera_manager.get_available_cameras()
        others = Picamera2.global_camera_info()
        logger.info(f"Found cameras: {cameras} and others: {others}")
        return cameras
    except Exception as e:
        logger.error(f"Error getting cameras: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stream/start")
async def start_stream(request: StreamRequest):
    """Start RTSP stream for a camera"""
    try:
        if not stream_manager.is_ready:
            raise HTTPException(status_code=503, detail="Stream manager not ready")

        result = await stream_manager.start_stream(
            request.camera_id,
            request.stream_name
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stream/stop/{stream_name}")
async def stop_stream(stream_name: str):
    """Stop RTSP stream"""
    try:
        if not stream_manager.is_ready:
            raise HTTPException(status_code=503, detail="Stream manager not ready")

        result = await stream_manager.stop_stream(stream_name)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/streams", response_model=list[StreamStatus])
async def get_streams():
    """Get list of active streams"""
    try:
        if not stream_manager.is_ready:
            return []

        streams = await stream_manager.get_active_streams()
        return streams
    except Exception as e:
        logger.error(f"Error getting streams: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        cameras = await camera_manager.get_available_cameras()
        streams = await stream_manager.get_active_streams() if stream_manager.is_ready else []

        return {
            "status": "healthy",
            "cameras": len(cameras),
            "streams": len(streams),
            "stream_manager_ready": stream_manager.is_ready
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "degraded",
            "error": str(e),
            "cameras": 0,
            "streams": 0,
            "stream_manager_ready": False
        }


if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=False
    )