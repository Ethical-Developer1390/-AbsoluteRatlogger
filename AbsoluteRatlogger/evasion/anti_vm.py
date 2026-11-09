#!/usr/bin/env python3
"""Evasion: Anti-VM — detect virtual machines and sandboxes."""
import os
import sys
import platform
import subprocess

def is_vm():
    """Check if running in a VM."""
    system = platform.system()
    if system == "Windows":
        return _check_windows()
    elif system == "Linux":
        return _check_linux()
    return False

def _check_windows():
    """Windows VM detection."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\BIOS", 0, winreg.KEY_READ) as k:
            for name in ("SystemManufacturer", "SystemProductName", "BIOSVendor"):
                try:
                    val, _ = winreg.QueryValueEx(k, name)
                    v = str(val).lower()
                    if any(x in v for x in ["vmware", "virtualbox", "vbox",
                                            "qemu", "xen", "hyper-v", "innotek"]):
                        return True
                except: pass
    except: pass

    # Check for VM-specific processes
    vm_procs = {"vmtoolsd.exe", "vmwaretray.exe", "vboxservice.exe",
                "vboxtray.exe", "xenservice.exe", "vgauthservice.exe"}
    try:
        out = subprocess.check_output(["tasklist.exe", "/FO", "CSV", "/NH"],
            text=True, creationflags=0x08000000)
        for line in out.splitlines():
            name = line.split('","')[0].strip('"').lower()
            if name in vm_procs:
                return True
    except: pass

    # Check MAC address OUI
    try:
        import uuid
        mac = uuid.getnode()
        mac_hex = f"{mac:012x}"
        # VMware: 00:0c:29, 00:50:56
        # VirtualBox: 08:00:27
        # Hyper-V: 00:15:5d
        vm_ouis = ["000c29", "005056", "080027", "00155d", "000569"]
        if mac_hex[:6] in vm_ouis:
            return True
    except: pass

    return False

def _check_linux():
    """Linux VM detection."""
    # Check DMI
    for path in ["/sys/class/dmi/id/sys_vendor", "/sys/class/dmi/id/product_name",
                 "/sys/class/dmi/id/board_vendor"]:
        try:
            with open(path) as f:
                val = f.read().lower()
                if any(x in val for x in ["vmware", "virtualbox", "vbox",
                                          "qemu", "xen", "microsoft", "kvm"]):
                    return True
        except: pass

    # Check /proc/cpuinfo for hypervisor flag
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if "hypervisor" in line.lower():
                    return True
    except: pass

    # Check for VM-specific kernel modules
    try:
        out = subprocess.check_output(["lsmod"], text=True)
        for mod in ["vmware", "vboxdrv", "vboxnetflt", "xen_", "kvm"]:
            if mod in out.lower():
                return True
    except: pass

    return False

def is_sandbox():
    """Check if running in a sandbox."""
    # Check for low uptime (< 10 min)
    try:
        import time
        if platform.system() == "Windows":
            import ctypes
            uptime = ctypes.windll.kernel32.GetTickCount64() / 1000
            if uptime < 600:
                return True
        else:
            with open("/proc/uptime") as f:
                uptime = float(f.read().split()[0])
                if uptime < 600:
                    return True
    except: pass

    # Check for few processes
    try:
        if platform.system() == "Windows":
            out = subprocess.check_output(["tasklist.exe", "/FO", "CSV", "/NH"],
                text=True, creationflags=0x08000000)
            count = sum(1 for l in out.splitlines() if l.strip())
            if count < 30:
                return True
        else:
            out = subprocess.check_output(["ps", "aux"], text=True)
            count = sum(1 for l in out.splitlines() if l.strip())
            if count < 30:
                return True
    except: pass

    # Check for no mouse movement (sandbox with no human)
    try:
        if platform.system() == "Windows":
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.WinDLL("user32")
            a = wintypes.POINT()
            b = wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(a))
            time.sleep(3)
            user32.GetCursorPos(ctypes.byref(b))
            dx, dy = a.x - b.x, a.y - b.y
            if dx * dx + dy * dy < 100:
                return True
    except: pass

    return False

def should_exit():
    """Return True if we should exit (VM + sandbox detected)."""
    if is_vm() and is_sandbox():
        return True
    return False
