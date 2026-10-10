"""SQLite：記錄已處理的信件與分析結果，避免重複分析。"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS mails (
    key          TEXT PRIMARY KEY,
    entry_id     TEXT,
    received     TEXT,
    sender       TEXT,
    subject      TEXT,
    status       TEXT,      -- analyzed / skipped / sensitive / failed
    priority     TEXT,
    analysis     TEXT,      -- JSON
    error        TEXT,
    attempts     INTEGER DEFAULT 0,
    processed_at TEXT
);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
"""

MAX_ATTEMPTS = 3


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def should_process(self, key: str) -> bool:
        row = self.db.execute("SELECT status, attempts FROM mails WHERE key = ?", (key,)).fetchone()
        if row is None:
            return True
        return row["status"] == "failed" and row["attempts"] < MAX_ATTEMPTS

    def save(self, mail: dict, status: str, priority: str, analysis: dict | None = None, error: str = ""):
        self.db.execute(
            """INSERT INTO mails (key, entry_id, received, sender, subject, status, priority, analysis, error, attempts, processed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
               ON CONFLICT(key) DO UPDATE SET
                 entry_id = excluded.entry_id, status = excluded.status, priority = excluded.priority,
                 analysis = excluded.analysis, error = excluded.error,
                 attempts = mails.attempts + 1, processed_at = excluded.processed_at""",
            (
                mail["key"], mail["entry_id"], mail["received"],
                f'{mail["sender_name"]} <{mail["sender_email"]}>', mail["subject"],
                status, priority, json.dumps(analysis, ensure_ascii=False) if analysis else None,
                error, datetime.now().isoformat(timespec="seconds"),
            ),
        )
        self.db.commit()

    def retryable_entry_ids(self) -> list:
        rows = self.db.execute(
            "SELECT entry_id FROM mails WHERE status = 'failed' AND attempts < ?", (MAX_ATTEMPTS,)
        ).fetchall()
        return [r["entry_id"] for r in rows]

    def processed_since(self, since: str) -> list:
        rows = self.db.execute(
            "SELECT * FROM mails WHERE processed_at >= ? ORDER BY priority, received DESC", (since,)
        ).fetchall()
        return [self._row(r) for r in rows]

    def open_followups(self, since_received: str) -> list:
        rows = self.db.execute(
            """SELECT * FROM mails WHERE status = 'analyzed' AND priority IN ('P1', 'P2')
               AND received >= ? ORDER BY priority, received""",
            (since_received,),
        ).fetchall()
        return [r for r in (self._row(r) for r in rows) if r["analysis"].get("reply_needed")]

    def get_meta(self, k: str, default: str = "") -> str:
        row = self.db.execute("SELECT v FROM meta WHERE k = ?", (k,)).fetchone()
        return row["v"] if row else default

    def set_meta(self, k: str, v: str):
        self.db.execute("INSERT INTO meta (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v = excluded.v", (k, v))
        self.db.commit()

    @staticmethod
    def _row(r) -> dict:
        d = dict(r)
        d["analysis"] = json.loads(d["analysis"]) if d["analysis"] else {}
        return d
