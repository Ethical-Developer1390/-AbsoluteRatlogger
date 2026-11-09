#!/usr/bin/env python3
"""Webcam module — capture from webcam, take selfies."""
import io
import os
import platform
import subprocess
import tempfile

def capture():
    """Capture a single frame from the default webcam."""
    system = platform.system()

    if system == "Windows":
        return _capture_windows()
    elif system == "Darwin":
        return _capture_macos()
    return b"error: webcam not supported on this platform"

def _capture_windows():
    """Windows webcam capture via OpenCV."""
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return b"error: cannot open webcam"
        # Set resolution
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        ret, frame = cap.read()
        cap.release()
        if ret:
            _, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            return jpg.tobytes()
        return b"error: failed to capture frame"
    except ImportError:
        return b"error: opencv not installed (pip install opencv-python)"
    except Exception as e:
        return f"error: {e}".encode()

def _capture_macos():
    """macOS webcam capture via imagesnap or OpenCV."""
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret:
                _, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                return jpg.tobytes()
    except ImportError:
        pass

    # Fallback: imagesnap
    try:
        tmp = tempfile.mktemp(suffix=".jpg")
        subprocess.run(["imagesnap", "-w", "1", tmp], capture_output=True, timeout=10)
        if os.path.exists(tmp):
            with open(tmp, "rb") as f:
                data = f.read()
            os.unlink(tmp)
            return data
    except:
        pass
    return b"error: no webcam capture method available"

def selfie():
    """Take a selfie — same as capture but with a 3-second delay."""
    import time
    time.sleep(3)
    return capture()

def list_devices():
    """List available webcam devices."""
    system = platform.system()
    devices = []
    if system == "Windows":
        try:
            import cv2
            for i in range(5):
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    devices.append(f"camera_{i}")
                    cap.release()
        except:
            pass
    return str(devices).encode()
