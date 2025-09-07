# src/tobyworld/db.py — minimal SQLite store for Mirror V3
from __future__ import annotations
import os, json, sqlite3
from datetime import datetime, timedelta

# --- Paths ---
PKG_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(PKG_ROOT), "..", "..", "data")
DATA_DIR = os.path.abspath(DATA_DIR)
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.getenv("DB_PATH", os.path.join(DATA_DIR, "mirror.db"))

# --- Connection ---
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- Schema ---
def init_db():
    conn = _conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
          id INTEGER PRIMARY KEY,
          ts TEXT NOT NULL,              -- ISO8601 UTC
          user_id TEXT,
          route TEXT NOT NULL,
          question TEXT,
          answer TEXT,
          meta_json TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_ts ON conversations(ts)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS lucidity_metrics (
          id INTEGER PRIMARY KEY,
          ts TEXT NOT NULL,           -- ISO8601 UTC
          route TEXT NOT NULL,        -- e.g. 'mirror.answer'
          engagement REAL,
          clarity REAL,
          depth REAL,
          guard_score REAL,
          notes TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_lucidity_ts ON lucidity_metrics(ts)")

    # --- NEW: training examples cache (for auto-learning/export) ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS training_examples (
          id INTEGER PRIMARY KEY,
          ts TEXT NOT NULL,           -- ISO8601 UTC
          user_id TEXT,
          question TEXT NOT NULL,
          answer TEXT NOT NULL,
          route_symbol TEXT NOT NULL,
          intent TEXT NOT NULL,
          depth INTEGER NOT NULL,
          guard_score REAL,
          sha TEXT UNIQUE             -- content hash to dedupe
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_training_ts ON training_examples(ts)")

    conn.commit()
    conn.close()

# --- Conversations API ---
def insert_conversation(user_id: str | None, route: str, question: str, answer: str, meta: dict | None = None):
    init_db()
    conn = _conn()
    conn.execute(
        "INSERT INTO conversations (ts, user_id, route, question, answer, meta_json) VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.utcnow().isoformat() + "Z",
         user_id,
         route,
         question,
         answer,
         json.dumps(meta or {}, ensure_ascii=False))
    )
    conn.commit()
    conn.close()

# --- Lucidity helpers ---
def insert_lucidity_metric(route: str, engagement: float, clarity: float, depth: float, guard_score: float, notes):
    init_db()
    if isinstance(notes, list):
        notes_json = json.dumps(notes[:8], ensure_ascii=False)
    else:
        notes_json = json.dumps([str(notes)], ensure_ascii=False) if notes is not None else "[]"
    conn = _conn()
    conn.execute(
        "INSERT INTO lucidity_metrics (ts, route, engagement, clarity, depth, guard_score, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (datetime.utcnow().isoformat() + "Z",
         route,
         float(engagement),
         float(clarity),
         float(depth),
         float(guard_score),
         notes_json)
    )
    conn.commit()
    conn.close()

def fetch_lucidity_summary(hours: int = 24):
    init_db()
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
    conn = _conn()
    row = conn.execute("""
      SELECT
        COUNT(*) AS count,
        COALESCE(AVG(engagement),0)  AS avg_engagement,
        COALESCE(AVG(clarity),0)     AS avg_clarity,
        COALESCE(AVG(depth),0)       AS avg_depth,
        COALESCE(AVG(guard_score),0) AS avg_guard_score,
        MAX(ts) AS last_ts
      FROM lucidity_metrics
      WHERE ts >= ?
    """, (since,)).fetchone()
    conn.close()
    return dict(row)

def fetch_lucidity_samples(hours: int = 24, limit: int = 200):
    init_db()
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
    conn = _conn()
    rows = conn.execute("""
      SELECT id, ts, route, engagement, clarity, depth, guard_score, notes
      FROM lucidity_metrics
      WHERE ts >= ?
      ORDER BY ts DESC
      LIMIT ?
    """, (since, int(limit))).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- NEW: Training examples API ---
def insert_training_example(user_id: str | None, question: str, answer: str,
                            route_symbol: str, intent: str, depth: int, guard_score: float | None):
    """
    Store a high-quality Q→A pair for future training/export.
    Deduped by content hash (sha) to avoid repeats.
    """
    init_db()
    from hashlib import sha256  # local import to keep module top light
    payload = (question or "") + "\n---\n" + (answer or "")
    sha = sha256(payload.encode("utf-8", "ignore")).hexdigest()

    conn = _conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO training_examples "
            "(ts, user_id, question, answer, route_symbol, intent, depth, guard_score, sha) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.utcnow().isoformat() + "Z",
             user_id, question, answer, route_symbol, intent, int(depth or 1), float(guard_score or 0.0), sha)
        )
        conn.commit()
    finally:
        conn.close()
