import sqlite3
from pathlib import Path

conn = sqlite3.connect(Path("storage/seen_posts.db"))
rows = conn.execute(
    "SELECT post_id, seen_at FROM seen_posts ORDER BY seen_at DESC LIMIT 30"
).fetchall()
total = conn.execute("SELECT COUNT(*) FROM seen_posts").fetchone()[0]

print(f"Total seen posts: {total}\n")
print(f"{'Post ID':<25} {'Seen At'}")
print("-" * 55)
for post_id, seen_at in rows:
    print(f"{post_id:<25} {seen_at}")

conn.close()
