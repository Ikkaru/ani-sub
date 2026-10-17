import hashlib
import sqlite3
from pathlib import Path

from platformdirs import user_state_dir

APP_NAME = "ani_sub"
STATE_DIR = Path(user_state_dir(APP_NAME)) / "cache.db"

def _conn() -> sqlite3.Connection:
    STATE_DIR.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(STATE_DIR)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS subs (
            key TEXT PRIMARY KEY,
            src TEXT, tgt TEXT,
            text TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    return conn


# Encode text to  key 
def make_key(source_text: str, engine: str, model_version: str, src: str, tgt: str) -> str | None:
    raw = f"{source_text}|{engine}|{model_version}|{src}|{tgt}"
    return hashlib.sha1(raw.encode()).hexdigest()


# Get the Subtitle Cache
def get(key: str) -> str | None:
    with _conn() as conn:
           row = conn.execute("SELECT text FROM subs WHERE key = ?",
           (key,)).fetchone()
    return row[0] if row else None


# Store the Subtitle Cache
def store(key: str, src: str, tgt: str, text: str) -> None:
    with _conn() as conn:
        conn.execute(
             "INSERT OR REPLACE INTO subs (key, src, tgt, text) VALUES (?, ?, ?, ?)",
             (key, src, tgt, text),
        )


# Count cache entry
def count() -> int:
    with _conn() as conn:
        row = conn.execute("SELECT COUNT(*) FROM subs").fetchone()
    return row[0]


# Count cache Byte size
def size() -> int:
    if not STATE_DIR.exists():
        return 0
    return STATE_DIR.stat().st_size


def size_estimated() -> str:
    b = size()
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:1.f} TB"


# Clear Cache
def clear() -> bool:
    if count() == 0:
        return False
    with _conn() as conn:
        conn.execute("DELETE FROM subs")
    return True