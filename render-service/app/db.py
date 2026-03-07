import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn(db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with get_conn(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS renders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                run_date TEXT NOT NULL,
                verse TEXT NOT NULL,
                reference TEXT NOT NULL,
                output_name TEXT NOT NULL,
                output_path TEXT NOT NULL,
                metadata_path TEXT NOT NULL,
                duration REAL NOT NULL,
                music_file TEXT,
                status TEXT NOT NULL,
                error_message TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                run_date TEXT NOT NULL,
                verse TEXT NOT NULL,
                reference TEXT NOT NULL,
                output_name TEXT NOT NULL,
                youtube_video_id TEXT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                privacy_status TEXT NOT NULL,
                status TEXT NOT NULL,
                UNIQUE(run_date, verse, reference)
            )
            """
        )


def has_uploaded_today(db_path: Path, verse: str, reference: str, run_date: str) -> bool:
    with get_conn(db_path) as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM uploads
            WHERE run_date = ? AND verse = ? AND reference = ?
            LIMIT 1
            """,
            (run_date, verse, reference),
        ).fetchone()
        return row is not None


def record_render(
    db_path: Path,
    run_date: str,
    verse: str,
    reference: str,
    output_name: str,
    output_path: str,
    metadata_path: str,
    duration: float,
    music_file: str | None,
    status: str,
    error_message: str | None,
) -> None:
    with get_conn(db_path) as conn:
        conn.execute(
            """
            INSERT INTO renders (
                created_at, run_date, verse, reference, output_name,
                output_path, metadata_path, duration, music_file, status, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _utc_now_iso(),
                run_date,
                verse,
                reference,
                output_name,
                output_path,
                metadata_path,
                duration,
                music_file,
                status,
                error_message,
            ),
        )


def record_upload(
    db_path: Path,
    run_date: str,
    verse: str,
    reference: str,
    output_name: str,
    youtube_video_id: str | None,
    title: str,
    description: str,
    tags: list[str],
    privacy_status: str,
    status: str,
) -> None:
    with get_conn(db_path) as conn:
        conn.execute(
            """
            INSERT INTO uploads (
                created_at, run_date, verse, reference, output_name,
                youtube_video_id, title, description, tags_json, privacy_status, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_date, verse, reference) DO UPDATE SET
                created_at = excluded.created_at,
                output_name = excluded.output_name,
                youtube_video_id = excluded.youtube_video_id,
                title = excluded.title,
                description = excluded.description,
                tags_json = excluded.tags_json,
                privacy_status = excluded.privacy_status,
                status = excluded.status
            """,
            (
                _utc_now_iso(),
                run_date,
                verse,
                reference,
                output_name,
                youtube_video_id,
                title,
                description,
                json.dumps(tags),
                privacy_status,
                status,
            ),
        )
