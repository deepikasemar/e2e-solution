"""SQLite storage for the profile, jobs and application tracker."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from applyagent.config import TZ, database_path

APPLIED_STATES = ("applied", "replied", "interview", "offer", "declined")
STATUSES = ("draft", "approved", "rejected", *APPLIED_STATES)


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                data TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT,
                work_type TEXT,
                description TEXT,
                skills TEXT,
                posted_date TEXT,
                url TEXT,
                source TEXT,
                salary TEXT,
                level TEXT,
                dedup_key TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT,
                company TEXT,
                title TEXT,
                status TEXT NOT NULL,
                summary TEXT,
                cover_letter TEXT,
                writer TEXT,
                fact_flags TEXT,
                match_json TEXT,
                form_json TEXT,
                rating INTEGER,
                generation_ms INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                applied_on TEXT
            );
            """
        )


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def today_key() -> str:
    return datetime.now(TZ).date().isoformat()


def get_profile() -> dict | None:
    init_db()
    with connect() as connection:
        row = connection.execute("SELECT data FROM profile WHERE id = 1").fetchone()
    if not row:
        return None
    return json.loads(row["data"])


def save_profile(profile: dict) -> None:
    init_db()
    payload = json.dumps(profile)
    stamp = now_iso()
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO profile (id, data, updated_at) VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at
            """,
            (payload, stamp),
        )


def upsert_jobs(jobs: list[dict]) -> dict[str, int]:
    """Insert or refresh jobs. Returns counts of inserted and updated rows."""
    from applyagent.cleaner import dedup_key
    from applyagent.matcher import prepare_job

    init_db()
    inserted = 0
    updated = 0
    stamp = now_iso()
    with connect() as connection:
        for raw in jobs:
            job = prepare_job(raw)
            key = dedup_key(job["title"], job["company"])
            existing = connection.execute("SELECT id FROM jobs WHERE id = ? OR dedup_key = ?", (job["id"], key)).fetchone()
            payload = (
                job["title"],
                job["company"],
                job["location"],
                job["work_type"],
                job["description"],
                json.dumps(job["skills"]),
                job["posted_date"],
                job["url"],
                job["source"],
                job["salary"],
                job["level"],
                key,
                stamp,
            )
            if existing:
                connection.execute(
                    """
                    UPDATE jobs SET title=?, company=?, location=?, work_type=?, description=?,
                    skills=?, posted_date=?, url=?, source=?, salary=?, level=?, dedup_key=?, updated_at=?
                    WHERE id = ?
                    """,
                    (*payload, existing["id"]),
                )
                updated += 1
            else:
                connection.execute(
                    """
                    INSERT INTO jobs (
                        title, company, location, work_type, description, skills, posted_date,
                        url, source, salary, level, dedup_key, updated_at, id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (*payload, job["id"]),
                )
                inserted += 1
    return {"inserted": inserted, "updated": updated}


def list_jobs() -> list[dict]:
    init_db()
    with connect() as connection:
        rows = connection.execute("SELECT * FROM jobs").fetchall()
    return [_job_row(row) for row in rows]


def get_job(job_id: str) -> dict | None:
    init_db()
    with connect() as connection:
        row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return _job_row(row) if row else None


def _job_row(row: sqlite3.Row) -> dict:
    job = dict(row)
    job["skills"] = json.loads(job.get("skills") or "[]")
    return job


def create_application(record: dict) -> int:
    init_db()
    stamp = now_iso()
    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO applications (
                job_id, company, title, status, summary, cover_letter, writer,
                fact_flags, match_json, form_json, rating, generation_ms,
                created_at, updated_at, applied_on
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.get("job_id"),
                record.get("company"),
                record.get("title"),
                record.get("status") or "draft",
                record.get("summary") or "",
                record.get("cover_letter") or "",
                record.get("writer") or "template",
                json.dumps(record.get("fact_flags") or []),
                json.dumps(record.get("match") or {}),
                json.dumps(record.get("form") or {}),
                record.get("rating"),
                record.get("generation_ms"),
                stamp,
                stamp,
                record.get("applied_on"),
            ),
        )
        return int(cursor.lastrowid)


def get_application(application_id: int) -> dict | None:
    init_db()
    with connect() as connection:
        row = connection.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
    return _application_row(row) if row else None


def list_applications() -> list[dict]:
    init_db()
    with connect() as connection:
        rows = connection.execute("SELECT * FROM applications ORDER BY id DESC").fetchall()
    return [_application_row(row) for row in rows]


def find_open_draft(job_id: str) -> dict | None:
    init_db()
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM applications WHERE job_id = ? AND status = 'draft' ORDER BY id DESC LIMIT 1",
            (job_id,),
        ).fetchone()
    return _application_row(row) if row else None


def update_application(application_id: int, **fields) -> None:
    init_db()
    allowed = {
        "status",
        "summary",
        "cover_letter",
        "writer",
        "fact_flags",
        "match_json",
        "form_json",
        "rating",
        "generation_ms",
        "applied_on",
    }
    columns = []
    values = []
    for key, value in fields.items():
        if key not in allowed:
            continue
        if key in {"fact_flags", "form_json", "match_json"} and not isinstance(value, str):
            value = json.dumps(value)
        columns.append(f"{key} = ?")
        values.append(value)
    if not columns:
        return
    columns.append("updated_at = ?")
    values.append(now_iso())
    values.append(application_id)
    with connect() as connection:
        connection.execute(f"UPDATE applications SET {', '.join(columns)} WHERE id = ?", values)


def count_applied_on(day: str | None = None) -> int:
    init_db()
    day = day or today_key()
    with connect() as connection:
        row = connection.execute(
            f"SELECT COUNT(*) AS n FROM applications WHERE applied_on = ? AND status IN ({','.join('?' for _ in APPLIED_STATES)})",
            (day, *APPLIED_STATES),
        ).fetchone()
    return int(row["n"])


def _application_row(row: sqlite3.Row) -> dict:
    item = dict(row)
    item["fact_flags"] = json.loads(item.get("fact_flags") or "[]")
    item["match"] = json.loads(item.get("match_json") or "{}")
    item["form"] = json.loads(item.get("form_json") or "{}")
    return item
