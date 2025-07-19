from pydantic import BaseModel
from typing import Optional

class CameraInfo(BaseModel):
    id: int
    name: str
    type: str
    resolution: str
    fps: int
    available: bool

class StreamRequest(BaseModel):
    camera_id: int
    stream_name: str

class StreamStatus(BaseModel):
    stream_name: str
    camera_id: int
    rtsp_url: str
    status: str