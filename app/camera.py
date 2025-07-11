import glob, os

def list_cameras():
    # Works for USB cams (v4l2) & libcamera‑apps’ v4l2loopback path.
    return [{
        "id": dev,
        "name": os.path.basename(dev)
    } for dev in sorted(glob.glob("/dev/video*"))]