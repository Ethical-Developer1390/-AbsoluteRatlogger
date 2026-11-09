#!/usr/bin/env python3
"""File operations module — upload, download, ls, rm, mkdir, cat, mv."""
import os
import struct
import shutil

def list_dir(path):
    """List directory contents."""
    try:
        entries = []
        for name in os.listdir(path):
            full = os.path.join(path, name)
            try:
                stat = os.stat(full)
                entries.append({
                    "name": name,
                    "size": stat.st_size,
                    "is_dir": os.path.isdir(full),
                    "modified": stat.st_mtime,
                })
            except:
                entries.append({"name": name, "error": "access denied"})
        return str(entries).encode()
    except Exception as e:
        return f"error: {e}".encode()

def read_file(path):
    """Read file contents."""
    try:
        with open(path, "rb") as f:
            return f.read()
    except Exception as e:
        return f"error: {e}".encode()

def write_file(path, data):
    """Write data to file."""
    try:
        with open(path, "wb") as f:
            f.write(data)
        return b"ok"
    except Exception as e:
        return f"error: {e}".encode()

def delete_file(path):
    """Delete a file."""
    try:
        os.remove(path)
        return b"ok"
    except Exception as e:
        return f"error: {e}".encode()

def make_dir(path):
    """Create a directory."""
    try:
        os.makedirs(path, exist_ok=True)
        return b"ok"
    except Exception as e:
        return f"error: {e}".encode()

def move_file(src, dst):
    """Move/rename a file."""
    try:
        shutil.move(src, dst)
        return b"ok"
    except Exception as e:
        return f"error: {e}".encode()

def file_info(path):
    """Get detailed file info."""
    try:
        stat = os.stat(path)
        return str({
            "path": path,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "created": stat.st_ctime,
            "mode": oct(stat.st_mode),
            "is_dir": os.path.isdir(path),
            "is_file": os.path.isfile(path),
            "is_link": os.path.islink(path),
        }).encode()
    except Exception as e:
        return f"error: {e}".encode()
