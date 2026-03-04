"""Persistent conversation memory for backend chat flows.

Backend-only utility:
- Session lifecycle
- Turn persistence
- Context rendering for multi-turn intent resolution
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


class ConversationMemoryStore:
    """SQLite-backed conversation session and turn storage."""

    def __init__(self, db_path: str = "data/databases/sentinel_state.db") -> None:
        self.db_path = Path(db_path)
        self._lock = threading.RLock()
        self._conn: Optional[sqlite3.Connection] = None
        self._initialize()

    def _initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

        cursor = self._conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_sessions (
                session_id TEXT PRIMARY KEY,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                metadata JSON
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_turns (
                turn_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL NOT NULL,
                metadata JSON,
                FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversation_turns_session_created "
            "ON conversation_turns(session_id, created_at)"
        )
        self._conn.commit()

    def create_session(self, session_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        sid = session_id or f"sess_{uuid.uuid4().hex[:12]}"
        now = time.time()
        payload = json.dumps(metadata or {})

        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO conversation_sessions (session_id, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?)
                """,
                (sid, now, now, payload),
            )
            self._conn.commit()

        return sid

    def append_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not session_id:
            raise ValueError("session_id is required")
        if role not in {"user", "assistant", "system", "tool"}:
            raise ValueError(f"unsupported role: {role}")
        if not content or not content.strip():
            raise ValueError("content is required")

        sid = self.create_session(session_id=session_id)
        turn_id = f"turn_{uuid.uuid4().hex[:12]}"
        now = time.time()
        payload = json.dumps(metadata or {})

        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                INSERT INTO conversation_turns (turn_id, session_id, role, content, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (turn_id, sid, role, content.strip(), now, payload),
            )
            cursor.execute(
                "UPDATE conversation_sessions SET updated_at = ? WHERE session_id = ?",
                (now, sid),
            )
            self._conn.commit()

        return turn_id

    def get_recent_turns(self, session_id: str, limit: int = 8) -> List[Dict[str, Any]]:
        if not session_id:
            return []

        lim = max(1, int(limit))
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                SELECT turn_id, session_id, role, content, created_at, metadata
                FROM conversation_turns
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (session_id, lim),
            )
            rows = cursor.fetchall()

        turns: List[Dict[str, Any]] = []
        for row in reversed(rows):
            turns.append(
                {
                    "turn_id": row["turn_id"],
                    "session_id": row["session_id"],
                    "role": row["role"],
                    "content": row["content"],
                    "created_at": row["created_at"],
                    "metadata": json.loads(row["metadata"] or "{}"),
                }
            )
        return turns

    def render_context(self, session_id: str, limit: int = 6) -> str:
        turns = self.get_recent_turns(session_id, limit=limit)
        if not turns:
            return ""

        lines: List[str] = []
        for turn in turns:
            role = turn["role"]
            prefix = "Kullanici" if role == "user" else "Asistan"
            if role not in {"user", "assistant"}:
                continue
            lines.append(f"{prefix}: {turn['content']}")
        return "\n".join(lines)
