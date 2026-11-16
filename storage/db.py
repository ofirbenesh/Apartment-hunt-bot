import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).parent / "seen_posts.db"


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(str(DB_PATH))
        self._create_tables()

    def _create_tables(self):
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_posts (
                post_id TEXT PRIMARY KEY,
                seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.commit()

    def is_seen(self, post_id: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM seen_posts WHERE post_id = ?", (post_id,)
        ).fetchone()
        return row is not None

    def mark_seen(self, post_id: str):
        self.conn.execute(
            "INSERT OR IGNORE INTO seen_posts (post_id) VALUES (?)", (post_id,)
        )
        self.conn.commit()

    def total_seen(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM seen_posts").fetchone()[0]

    def close(self):
        self.conn.close()
