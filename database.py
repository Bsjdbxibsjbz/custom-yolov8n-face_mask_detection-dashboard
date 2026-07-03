import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "database", "mask_detection.db")


def create_database():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time       TEXT NOT NULL,
            end_time         TEXT,
            person_count     INTEGER DEFAULT 0,
            clear_face_count INTEGER DEFAULT 0,
            head_count       INTEGER DEFAULT 0,
            masked_face_count INTEGER DEFAULT 0,
            not_sure_count   INTEGER DEFAULT 0,
            compliance       REAL DEFAULT 0.0
        )
    """)
    conn.commit()
    conn.close()


def save_session(
    start_time: str,
    end_time: str,
    person_count: int,
    clear_face_count: int,
    head_count: int,
    masked_face_count: int,
    not_sure_count: int,
    compliance: float,
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO sessions
            (start_time, end_time, person_count, clear_face_count,
             head_count, masked_face_count, not_sure_count, compliance)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            start_time,
            end_time,
            person_count,
            clear_face_count,
            head_count,
            masked_face_count,
            not_sure_count,
            compliance,
        ),
    )
    conn.commit()
    conn.close()


def get_previous_session() -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM sessions
        ORDER BY id DESC
        LIMIT 1
        """
    )
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)
