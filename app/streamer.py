import subprocess, shlex, signal
import os

_MEDIAMTX_PORT = 8554  # rtsp://<pi>:8554/cam0 etc.
_BASE_PIPELINE = (
    "libcamera-vid -t 0 -n --codec h264 --width 1280 --height 720 "
    "--framerate 30 --profile high --inline --listen -o -"
)

class StreamManager:
    def __init__(self):
        self._procs = {}

    def start(self, dev: str):
        if dev in self._procs:
            return False  # already active
        # Publish to MediaMTX via RTP *in* over UDP; mediaMTX exposes RTSP.
        rtsp_name = dev.replace("/dev/", "")
        cmd = f"{_BASE_PIPELINE} | ffmpeg -i pipe:0 -f rtsp rtsp://127.0.0.1:{_MEDIAMTX_PORT}/{rtsp_name}"
        proc = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)
        self._procs[dev] = proc
        return True

    def stop(self, dev: str):
        proc = self._procs.pop(dev, None)
        if not proc:
            return False
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        return True