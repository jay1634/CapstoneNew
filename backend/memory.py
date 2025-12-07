import sqlite3
from typing import List, Dict, Any
import json
import time

DB_PATH = "memory.db"
TTL_SECONDS = 1800   # ✅ 30 minutes TTL (change as needed)


class Memory:
    def __init__(self):
        self._init_db()
        self.cleanup_old_data()   # ✅ auto cleanup on startup

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                session_id TEXT,
                role TEXT,
                content TEXT,
                ts REAL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS user_prefs (
                session_id TEXT PRIMARY KEY,
                prefs TEXT
            )
        """)

        conn.commit()
        conn.close()

    # ✅ TTL Cleanup Function
    def cleanup_old_data(self):
        cutoff = time.time() - TTL_SECONDS
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Delete expired chat messages
        c.execute("DELETE FROM chat_history WHERE ts < ?", (cutoff,))

        conn.commit()
        conn.close()

    def get_history(self, session_id: str) -> List[str]:
        self.cleanup_old_data()   # ✅ cleanup before fetching

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute(
            "SELECT role, content FROM chat_history WHERE session_id = ? ORDER BY ts",
            (session_id,),
        )

        rows = c.fetchall()
        conn.close()

        return [f"{r.capitalize()}: {c}" for r, c in rows]

    def add_turn(self, session_id: str, text: str):
        self.cleanup_old_data()   # ✅ cleanup before inserting

        role, content = text.split(":", 1)

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute(
            "INSERT INTO chat_history VALUES (?, ?, ?, ?)",
            (session_id, role.lower(), content.strip(), time.time()),
        )

        conn.commit()
        conn.close()

    def get_prefs(self, session_id: str) -> Dict[str, Any]:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute(
            "SELECT prefs FROM user_prefs WHERE session_id = ?",
            (session_id,),
        )

        row = c.fetchone()
        conn.close()

        if not row:
            return {}

        return json.loads(row[0])

    def update_prefs(self, session_id: str, updates: Dict[str, Any]):
        current = self.get_prefs(session_id)
        current.update(updates)

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute("""
            INSERT INTO user_prefs (session_id, prefs)
            VALUES (?, ?)
            ON CONFLICT(session_id) DO UPDATE SET prefs = excluded.prefs
        """, (session_id, json.dumps(current)))

        conn.commit()
        conn.close()

    # ✅ Optional: Explicitly delete a session
    def delete_session_data(self, session_id: str):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))
        c.execute("DELETE FROM user_prefs WHERE session_id = ?", (session_id,))

        conn.commit()
        conn.close()


memory = Memory()
