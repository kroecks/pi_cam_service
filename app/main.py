from fastapi import FastAPI, HTTPException, Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import logging
import urllib.parse

from camera import list_cameras
from streamer import StreamManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pi_cam_service")

app = FastAPI(title="Pi Camera Service")

stream = StreamManager()

# ---------- API ----------
@app.get("/api/cameras")
def cameras():
    cams = list_cameras()
    logger.info("Listing cameras: %s", cams)
    return cams

@app.post("/api/stream/{camera_id:path}/start")
def start(camera_id: str = Path(...)):
    camera_id = urllib.parse.unquote(camera_id)
    if not stream.start(camera_id):
        raise HTTPException(404, "camera not found or already streaming")
    return {"status": "started", "camera": camera_id}

@app.post("/api/stream/{camera_id:path}/stop")
def stop(camera_id: str = Path(...)):
    camera_id = urllib.parse.unquote(camera_id)
    if not stream.stop(camera_id):
        raise HTTPException(404, "camera not active")
    return {"status": "stopped", "camera": camera_id}

# ---------- Front‑end ----------
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    return FileResponse("static/index.html")