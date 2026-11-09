#!/usr/bin/env python3
"""Screen capture module — captures screen as JPEG."""
import io
import os
import platform

def capture():
    """Capture the primary screen and return JPEG bytes."""
    system = platform.system()

    if system == "Windows":
        return _capture_windows()
    elif system == "Linux":
        return _capture_linux()
    elif system == "Darwin":
        return _capture_macos()
    return b"error: unsupported platform"

def _capture_windows():
    """Windows screen capture using PIL."""
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab(all_screens=False)
        if img.mode != "RGB":
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=60)
        return buf.getvalue()
    except ImportError:
        return b"error: Pillow not installed"
    except Exception as e:
        return f"error: {e}".encode()

def _capture_linux():
    """Linux screen capture using scrot or ImageMagick."""
    import subprocess
    import tempfile
    tmp = tempfile.mktemp(suffix=".jpg")
    # Try import (ImageMagick) first, then scrot
    for tool in (["import", "-window", "root", tmp], ["scrot", tmp]):
        try:
            result = subprocess.run(tool, capture_output=True, timeout=5)
            if result.returncode == 0 and os.path.exists(tmp):
                with open(tmp, "rb") as f:
                    data = f.read()
                os.unlink(tmp)
                return data
        except:
            continue
    return b"error: install scrot or imagemagick"

def _capture_macos():
    """macOS screen capture using screencapture."""
    import subprocess
    import tempfile
    tmp = tempfile.mktemp(suffix=".jpg")
    try:
        subprocess.run(["screencapture", "-x", "-t", "jpg", tmp], timeout=5)
        if os.path.exists(tmp):
            with open(tmp, "rb") as f:
                data = f.read()
            os.unlink(tmp)
            return data
    except:
        pass
    return b"error: screencapture failed"
