"""SQLite response cache so re-running a pipeline during development costs nothing."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path


def cache_key(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


class ResponseCache:
    def __init__(self, path: Path | str):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path))
        self._db.execute("CREATE TABLE IF NOT EXISTS responses (key TEXT PRIMARY KEY, body TEXT NOT NULL)")
        self._db.commit()

    def get(self, key: str) -> dict | None:
        row = self._db.execute("SELECT body FROM responses WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key: str, body: dict) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO responses (key, body) VALUES (?, ?)", (key, json.dumps(body))
        )
        self._db.commit()

    def close(self) -> None:
        self._db.close()
