#!/usr/bin/env python3
"""Evasion: Anti-debug — detect debuggers and analysis tools."""
import sys
import os
import platform
import ctypes
import time

def is_debugged():
    """Check if a debugger is present."""
    system = platform.system()
    if system == "Windows":
        return _check_windows()
    elif system == "Linux":
        return _check_linux()
    return False

def _check_windows():
    """Windows debugger detection."""
    try:
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)

        # Method 1: IsDebuggerPresent
        if k32.IsDebuggerPresent():
            return True

        # Method 2: NtQueryInformationProcess (ProcessDebugPort)
        ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
        proc = k32.GetCurrentProcess()
        port = ctypes.c_void_p()
        ret_len = ctypes.c_ulong(0)

        # ProcessDebugPort = 7
        status = ntdll.NtQueryInformationProcess(
            proc, 7, ctypes.byref(port),
            ctypes.sizeof(port), ctypes.byref(ret_len)
        )
        if status == 0 and port.value:
            return True

        # Method 3: ProcessDebugFlags = 0x1F
        flags = ctypes.c_ulong(0)
        status = ntdll.NtQueryInformationProcess(
            proc, 0x1F, ctypes.byref(flags),
            ctypes.sizeof(flags), ctypes.byref(ret_len)
        )
        if status == 0 and flags.value == 0:
            return True

    except Exception:
        pass

    # Method 4: Check for debug processes
    debug_procs = {"ollydbg.exe", "x64dbg.exe", "x32dbg.exe", "windbg.exe",
                   "ida.exe", "ida64.exe", "idaq.exe", "idaq64.exe"}
    try:
        import subprocess
        out = subprocess.check_output(["tasklist.exe", "/FO", "CSV", "/NH"],
            text=True, creationflags=0x08000000)
        for line in out.splitlines():
            name = line.split('","')[0].strip('"').lower()
            if name in debug_procs:
                return True
    except:
        pass

    return False

def _check_linux():
    """Linux debugger detection."""
    # Method 1: Check TracerPid in /proc/self/status
    try:
        with open(f"/proc/self/status") as f:
            for line in f:
                if line.startswith("TracerPid:"):
                    pid = int(line.split(":")[1].strip())
                    if pid != 0:
                        return True
    except:
        pass

    # Method 2: Check for debug processes
    debug_tools = {"gdb", "strace", "ltrace", "ida", "radare2", "r2", "frida"}
    try:
        import subprocess
        out = subprocess.check_output(["ps", "aux"], text=True)
        for tool in debug_tools:
            if tool in out.lower():
                return True
    except:
        pass

    return False

def check_timing():
    """Timing-based anti-debug. Returns True if timing anomaly detected."""
    t0 = time.perf_counter()
    # Do some work
    total = sum(range(100000))
    t1 = time.perf_counter()

    elapsed = t1 - t0
    # If execution took way too long, we're probably being single-stepped
    if elapsed > 0.5:  # Should take ~5ms, not 500ms
        return True
    return False

def should_exit():
    """Return True if debugger detected."""
    return is_debugged()
