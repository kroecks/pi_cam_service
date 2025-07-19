from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import os
from .camera_manager import CameraManager
from .stream_manager import StreamManager
from .models import CameraInfo, StreamStatus, StreamRequest

app = FastAPI(title="Raspberry Pi Camera API", version="1.0.0")

# Initialize managers
camera_manager = CameraManager()
stream_manager = StreamManager()

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await camera_manager.initialize()
    await stream_manager.initialize()

@app.get("/")
async def root():
    return {"message": "Raspberry Pi Camera API", "version": "1.0.0"}

@app.get("/cameras", response_model=list[CameraInfo])
async def get_cameras():
    """Get list of available cameras"""
    try:
        cameras = await camera_manager.get_available_cameras()
        return cameras
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stream/start")
async def start_stream(request: StreamRequest):
    """Start RTSP stream for a camera"""
    try:
        result = await stream_manager.start_stream(
            request.camera_id,
            request.stream_name
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stream/stop/{stream_name}")
async def stop_stream(stream_name: str):
    """Stop RTSP stream"""
    try:
        result = await stream_manager.stop_stream(stream_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/streams", response_model=list[StreamStatus])
async def get_streams():
    """Get list of active streams"""
    try:
        streams = await stream_manager.get_active_streams()
        return streams
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "cameras": len(await camera_manager.get_available_cameras()),
        "streams": len(await stream_manager.get_active_streams())
    }

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=False
    )