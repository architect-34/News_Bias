"""SQLite-backed cache for scraped articles and a simple fetch-log."""
import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "cache.db"
CACHE_TTL_SECONDS = 60 * 60  # 1 hour


SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    publisher_id    TEXT    NOT NULL,
    scope           TEXT    NOT NULL,          -- 'national' | 'state'
    title           TEXT    NOT NULL,
    url             TEXT    NOT NULL UNIQUE,
    published_at    TEXT,
    snippet         TEXT,
    state           TEXT,
    parties         TEXT,                       -- JSON array
    sentiment       REAL,
    weighted_bias   REAL,
    bias_label      TEXT,
    bias_color      TEXT,
    bias_profile    TEXT,                       -- JSON BiasProfile (Six-Lens)
    body            TEXT,                       -- full article text (trafilatura)
    ml_analysis     TEXT,                       -- JSON ML output (sentiment + stance)
    fetched_at      INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_articles_publisher ON articles(publisher_id);
CREATE INDEX IF NOT EXISTS idx_articles_fetched   ON articles(fetched_at);
CREATE INDEX IF NOT EXISTS idx_articles_scope     ON articles(scope);

CREATE TABLE IF NOT EXISTS fetch_log (
    publisher_id TEXT PRIMARY KEY,
    last_fetched INTEGER NOT NULL
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        # Idempotent migrations for older cache.db files.
        for stmt in (
            "ALTER TABLE articles ADD COLUMN bias_profile TEXT",
            "ALTER TABLE articles ADD COLUMN body TEXT",
            "ALTER TABLE articles ADD COLUMN ml_analysis TEXT",
        ):
            try:
                conn.execute(stmt)
            except sqlite3.OperationalError:
                pass  # column already present


def cache_is_fresh(publisher_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT last_fetched FROM fetch_log WHERE publisher_id = ?",
            (publisher_id,),
        ).fetchone()
    if not row:
        return False
    return (time.time() - row["last_fetched"]) < CACHE_TTL_SECONDS


def replace_articles(publisher_id: str, articles: list[dict]) -> None:
    now = int(time.time())
    with get_conn() as conn:
        conn.execute("DELETE FROM articles WHERE publisher_id = ?", (publisher_id,))
        for a in articles:
            conn.execute(
                """INSERT OR REPLACE INTO articles
                   (publisher_id, scope, title, url, published_at, snippet,
                    state, parties, sentiment, weighted_bias, bias_label,
                    bias_color, bias_profile, body, ml_analysis, fetched_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    publisher_id,
                    a.get("scope", "national"),
                    a["title"],
                    a["url"],
                    a.get("published_at"),
                    a.get("snippet"),
                    a.get("state"),
                    json.dumps(a.get("parties", [])),
                    a.get("sentiment"),
                    a.get("weighted_bias"),
                    a.get("bias_label"),
                    a.get("bias_color"),
                    json.dumps(a.get("bias_profile")) if a.get("bias_profile") else None,
                    a.get("body"),
                    json.dumps(a.get("ml_analysis")) if a.get("ml_analysis") else None,
                    now,
                ),
            )
        conn.execute(
            "INSERT OR REPLACE INTO fetch_log (publisher_id, last_fetched) VALUES (?, ?)",
            (publisher_id, now),
        )


def load_articles(publisher_id: str | None = None) -> list[dict]:
    with get_conn() as conn:
        if publisher_id:
            rows = conn.execute(
                "SELECT * FROM articles WHERE publisher_id = ? ORDER BY id DESC",
                (publisher_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM articles ORDER BY fetched_at DESC, id DESC"
            ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["parties"] = json.loads(d["parties"] or "[]")
        if d.get("bias_profile"):
            try:
                d["bias_profile"] = json.loads(d["bias_profile"])
            except (TypeError, ValueError):
                d["bias_profile"] = None
        if d.get("ml_analysis"):
            try:
                d["ml_analysis"] = json.loads(d["ml_analysis"])
            except (TypeError, ValueError):
                d["ml_analysis"] = None
        out.append(d)
    return out
