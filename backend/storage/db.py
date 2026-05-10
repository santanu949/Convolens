"""
SQLite storage — schema, connection management, CRUD operations.
All data persists across restarts. Processing only runs once.
"""
import os
import json
import sqlite3
import threading
from typing import List, Optional, Dict, Any, Tuple

from config import DB_PATH, DATA_DIR
from models.message import Message
from models.segment import TopicSegment, TimeCheckpoint


_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    sender TEXT NOT NULL,
    text TEXT NOT NULL,
    timestamp TEXT,
    global_idx INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_global ON messages(global_idx);

CREATE TABLE IF NOT EXISTS topic_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    start_idx INTEGER NOT NULL,
    end_idx INTEGER NOT NULL,
    topic_label TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    embedding BLOB
);

CREATE INDEX IF NOT EXISTS idx_segments_conv ON topic_segments(conversation_id);

CREATE TABLE IF NOT EXISTS time_checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_global_idx INTEGER NOT NULL,
    end_global_idx INTEGER NOT NULL,
    summary TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS personas (
    conversation_id INTEGER PRIMARY KEY,
    persona_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS processing_jobs (
    task_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'pending',
    progress INTEGER NOT NULL DEFAULT 0,
    stage TEXT NOT NULL DEFAULT '',
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def _get_conn() -> sqlite3.Connection:
    """Get a thread-local SQLite connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=15.0)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA synchronous=NORMAL")
    return _local.conn


def init_db():
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.executescript(SCHEMA)
    conn.commit()


def is_processed() -> bool:
    """Check if data has already been processed (survives restarts)."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT value FROM meta WHERE key='processed'").fetchone()
        return row is not None and row["value"] == "true"
    except Exception:
        return False


def mark_processed():
    """Mark the database as having been fully processed."""
    conn = _get_conn()
    conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('processed', 'true')")
    conn.commit()


def get_total_messages() -> int:
    conn = _get_conn()
    row = conn.execute("SELECT COUNT(*) as cnt FROM messages").fetchone()
    return row["cnt"] if row else 0


def get_total_conversations() -> int:
    conn = _get_conn()
    row = conn.execute("SELECT COUNT(DISTINCT conversation_id) as cnt FROM messages").fetchone()
    return row["cnt"] if row else 0


# --- Message CRUD ---

def insert_messages_batch(messages: List[Message]):
    """Bulk insert messages for one conversation."""
    conn = _get_conn()
    conn.executemany(
        "INSERT INTO messages(conversation_id, sender, text, timestamp, global_idx) VALUES(?,?,?,?,?)",
        [(m.conversation_id, m.sender, m.text, m.timestamp, m.global_idx) for m in messages]
    )
    conn.commit()


def get_messages_by_conversation(conversation_id: int) -> List[Message]:
    """Get all messages for a specific conversation."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM messages WHERE conversation_id=? ORDER BY global_idx",
        (conversation_id,)
    ).fetchall()
    return [Message(id=r["id"], conversation_id=r["conversation_id"], sender=r["sender"],
                    text=r["text"], timestamp=r["timestamp"], global_idx=r["global_idx"]) for r in rows]


def get_messages_by_global_range(start: int, end: int) -> List[Message]:
    """Get messages by global index range (inclusive)."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM messages WHERE global_idx >= ? AND global_idx <= ? ORDER BY global_idx",
        (start, end)
    ).fetchall()
    return [Message(id=r["id"], conversation_id=r["conversation_id"], sender=r["sender"],
                    text=r["text"], timestamp=r["timestamp"], global_idx=r["global_idx"]) for r in rows]


def get_conversations_paginated(page: int = 1, per_page: int = 20) -> Tuple[List[Dict], int]:
    """Get paginated list of conversations with message counts."""
    conn = _get_conn()
    total_row = conn.execute("SELECT COUNT(DISTINCT conversation_id) as cnt FROM messages").fetchone()
    total = total_row["cnt"] if total_row else 0
    offset = (page - 1) * per_page
    rows = conn.execute(
        """SELECT conversation_id, COUNT(*) as msg_count,
           MIN(global_idx) as first_idx, MAX(global_idx) as last_idx
           FROM messages GROUP BY conversation_id
           ORDER BY conversation_id LIMIT ? OFFSET ?""",
        (per_page, offset)
    ).fetchall()
    convos = [{"conversation_id": r["conversation_id"], "message_count": r["msg_count"],
               "first_idx": r["first_idx"], "last_idx": r["last_idx"]} for r in rows]
    return convos, total


# --- Segment CRUD ---

def insert_segment(seg: TopicSegment) -> int:
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO topic_segments(conversation_id, start_idx, end_idx, topic_label, summary) VALUES(?,?,?,?,?)",
        (seg.conversation_id, seg.start_idx, seg.end_idx, seg.topic_label, seg.summary)
    )
    conn.commit()
    return cur.lastrowid


def insert_segments_batch(segments: List[TopicSegment]):
    conn = _get_conn()
    conn.executemany(
        "INSERT INTO topic_segments(conversation_id, start_idx, end_idx, topic_label, summary) VALUES(?,?,?,?,?)",
        [(s.conversation_id, s.start_idx, s.end_idx, s.topic_label, s.summary) for s in segments]
    )
    conn.commit()


def get_all_segments() -> List[TopicSegment]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM topic_segments ORDER BY id").fetchall()
    return [TopicSegment(id=r["id"], conversation_id=r["conversation_id"],
                         start_idx=r["start_idx"], end_idx=r["end_idx"],
                         topic_label=r["topic_label"], summary=r["summary"],
                         message_count=r["end_idx"] - r["start_idx"] + 1) for r in rows]


def get_segments_paginated(page: int = 1, per_page: int = 20, conversation_id: int = None) -> Tuple[List[Dict], int]:
    conn = _get_conn()
    if conversation_id is not None:
        total_row = conn.execute("SELECT COUNT(*) as cnt FROM topic_segments WHERE conversation_id=?", (conversation_id,)).fetchone()
        total = total_row["cnt"]
        offset = (page - 1) * per_page
        rows = conn.execute(
            "SELECT * FROM topic_segments WHERE conversation_id=? ORDER BY start_idx LIMIT ? OFFSET ?",
            (conversation_id, per_page, offset)
        ).fetchall()
    else:
        total_row = conn.execute("SELECT COUNT(*) as cnt FROM topic_segments").fetchone()
        total = total_row["cnt"]
        offset = (page - 1) * per_page
        rows = conn.execute(
            "SELECT * FROM topic_segments ORDER BY id LIMIT ? OFFSET ?",
            (per_page, offset)
        ).fetchall()
    segments = [{
        "id": r["id"], "conversation_id": r["conversation_id"],
        "start_idx": r["start_idx"], "end_idx": r["end_idx"],
        "topic_label": r["topic_label"], "summary": r["summary"],
        "message_count": r["end_idx"] - r["start_idx"] + 1,
    } for r in rows]
    return segments, total


def get_segment_by_id(segment_id: int) -> Optional[TopicSegment]:
    conn = _get_conn()
    r = conn.execute("SELECT * FROM topic_segments WHERE id=?", (segment_id,)).fetchone()
    if not r:
        return None
    return TopicSegment(id=r["id"], conversation_id=r["conversation_id"],
                        start_idx=r["start_idx"], end_idx=r["end_idx"],
                        topic_label=r["topic_label"], summary=r["summary"],
                        message_count=r["end_idx"] - r["start_idx"] + 1)


# --- Checkpoint CRUD ---

def insert_checkpoints_batch(checkpoints: List[TimeCheckpoint]):
    conn = _get_conn()
    conn.executemany(
        "INSERT INTO time_checkpoints(start_global_idx, end_global_idx, summary) VALUES(?,?,?)",
        [(c.start_global_idx, c.end_global_idx, c.summary) for c in checkpoints]
    )
    conn.commit()


def get_checkpoints_paginated(page: int = 1, per_page: int = 20) -> Tuple[List[Dict], int]:
    conn = _get_conn()
    total_row = conn.execute("SELECT COUNT(*) as cnt FROM time_checkpoints").fetchone()
    total = total_row["cnt"]
    offset = (page - 1) * per_page
    rows = conn.execute(
        "SELECT * FROM time_checkpoints ORDER BY id LIMIT ? OFFSET ?",
        (per_page, offset)
    ).fetchall()
    cps = [{
        "id": r["id"], "start_global_idx": r["start_global_idx"],
        "end_global_idx": r["end_global_idx"], "summary": r["summary"],
        "message_count": r["end_global_idx"] - r["start_global_idx"] + 1,
    } for r in rows]
    return cps, total


# --- Persona CRUD ---

def save_persona(conversation_id: int, persona_json: str):
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO personas(conversation_id, persona_json) VALUES(?,?)",
        (conversation_id, persona_json)
    )
    conn.commit()


def get_persona(conversation_id: int) -> Optional[Dict]:
    conn = _get_conn()
    row = conn.execute("SELECT persona_json FROM personas WHERE conversation_id=?", (conversation_id,)).fetchone()
    if row:
        return json.loads(row["persona_json"])
    return None


# --- Processing Jobs ---

def create_job(task_id: str):
    conn = _get_conn()
    conn.execute("INSERT INTO processing_jobs(task_id, status) VALUES(?, 'pending')", (task_id,))
    conn.commit()


def update_job(task_id: str, status: str = None, progress: int = None, stage: str = None, error: str = None):
    conn = _get_conn()
    updates = []
    params = []
    if status is not None:
        updates.append("status=?")
        params.append(status)
    if progress is not None:
        updates.append("progress=?")
        params.append(progress)
    if stage is not None:
        updates.append("stage=?")
        params.append(stage)
    if error is not None:
        updates.append("error=?")
        params.append(error)
    if updates:
        params.append(task_id)
        conn.execute(f"UPDATE processing_jobs SET {','.join(updates)} WHERE task_id=?", params)
        conn.commit()


def get_job(task_id: str) -> Optional[Dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM processing_jobs WHERE task_id=?", (task_id,)).fetchone()
    if row:
        return {"task_id": row["task_id"], "status": row["status"], "progress": row["progress"],
                "stage": row["stage"], "error": row["error"]}
    return None
