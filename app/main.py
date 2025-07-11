from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from camera import list_cameras
from streamer import StreamManager

app = FastAPI(title="Pi RTSP Camera Service")
# serve the SPA (index.html) from / – tweak path if relocating static/
app.mount("/", StaticFiles(directory="static", html=True), name="static")

stream = StreamManager()

@app.get("/api/cameras")
def cameras():
    """Return all /dev/video* devices (USB or CSI as v4l2loopback)."""
    return list_cameras()

@app.post("/api/stream/{camera_id}/start")
def start(camera_id: str):
    if not stream.start(camera_id):
        raise HTTPException(404, "camera not found or already streaming")
    return {"status": "started", "camera": camera_id}

@app.post("/api/stream/{camera_id}/stop")
def stop(camera_id: str):
    if not stream.stop(camera_id):
        raise HTTPException(404, "camera not active")
    return {"status": "stopped", "camera": camera_id}