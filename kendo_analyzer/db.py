import sqlite3
from pathlib import Path
from typing import Iterable, List

from kendo_analyzer.models import Detection


class DetectionRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS waza_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    waza_name TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    detected_at_sec REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(waza_results)").fetchall()
            }
            if "detected_at_sec" not in columns:
                conn.execute("ALTER TABLE waza_results ADD COLUMN detected_at_sec REAL")

    def save(self, detection: Detection):
        self.init_db()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO waza_results (waza_name, confidence, detected_at_sec)
                VALUES (?, ?, ?)
                """,
                (detection.name, detection.confidence, detection.timestamp_sec),
            )

    def save_many(self, detections: Iterable[Detection]):
        self.init_db()
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                """
                INSERT INTO waza_results (waza_name, confidence, detected_at_sec)
                VALUES (?, ?, ?)
                """,
                [(item.name, item.confidence, item.timestamp_sec) for item in detections],
            )

    def recent(self, limit: int = 20) -> List[Detection]:
        self.init_db()
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT waza_name, confidence, detected_at_sec
                FROM waza_results
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            Detection(name=row[0], confidence=float(row[1]), timestamp_sec=row[2])
            for row in rows
        ]
