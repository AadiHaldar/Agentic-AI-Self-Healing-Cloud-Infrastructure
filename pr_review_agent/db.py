"""
pr_review_agent/db.py — SQLite persistence layer.
Stores GitHub App credentials, installation records, review logs, and learning dismissals.

NEVER uses os.environ as the sole storage for credentials. All app credentials are
persisted here and in .env.app. See implementation_plan.md §Decisions Locked In #2.
"""
import sqlite3
import json
import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# DB file lives next to this module unless overridden by env var
_DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "pr_review_agent.db")
DB_PATH: str = os.getenv("PR_REVIEW_AGENT_DB", _DEFAULT_DB_PATH)


def _ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)


@contextmanager
def _conn():
    """Yield a thread-safe SQLite connection with WAL mode."""
    _ensure_dir(DB_PATH)
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db() -> None:
    """Create all tables if they do not exist."""
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS app_config (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS installations (
                installation_id INTEGER PRIMARY KEY,
                account_login   TEXT    NOT NULL,
                account_type    TEXT    NOT NULL DEFAULT 'User',
                app_id          INTEGER NOT NULL,
                webhook_secret  TEXT,
                installed_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS installation_repos (
                installation_id INTEGER NOT NULL,
                repo_full_name  TEXT    NOT NULL,
                PRIMARY KEY (installation_id, repo_full_name),
                FOREIGN KEY (installation_id) REFERENCES installations(installation_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS review_log (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_full_name  TEXT    NOT NULL,
                pr_number       INTEGER NOT NULL,
                commit_sha      TEXT,
                findings_count  INTEGER NOT NULL DEFAULT 0,
                critical_count  INTEGER NOT NULL DEFAULT 0,
                status          TEXT    NOT NULL DEFAULT 'pending',
                reviewed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS dismissals (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_full_name  TEXT NOT NULL,
                rule_id         TEXT NOT NULL,
                note            TEXT,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    logger.info("[db] Tables initialised at %s", DB_PATH)


# ── app_config ──────────────────────────────────────────────────────────────

def set_app_config(key: str, value: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO app_config(key, value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value)
        )


def get_app_config(key: str) -> Optional[str]:
    with _conn() as con:
        row = con.execute("SELECT value FROM app_config WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def get_all_app_config() -> Dict[str, str]:
    with _conn() as con:
        rows = con.execute("SELECT key, value FROM app_config").fetchall()
    return {r["key"]: r["value"] for r in rows}


# ── installations ────────────────────────────────────────────────────────────

def upsert_installation(
    installation_id: int,
    account_login: str,
    account_type: str,
    app_id: int,
    webhook_secret: Optional[str] = None,
) -> None:
    with _conn() as con:
        con.execute(
            """
            INSERT INTO installations(installation_id, account_login, account_type,
                                       app_id, webhook_secret)
            VALUES(?,?,?,?,?)
            ON CONFLICT(installation_id) DO UPDATE SET
                account_login  = excluded.account_login,
                account_type   = excluded.account_type,
                app_id         = excluded.app_id,
                webhook_secret = excluded.webhook_secret
            """,
            (installation_id, account_login, account_type, app_id, webhook_secret),
        )
    logger.info("[db] Upserted installation %s for %s", installation_id, account_login)


def get_installation(installation_id: int) -> Optional[Dict[str, Any]]:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM installations WHERE installation_id=?", (installation_id,)
        ).fetchone()
    return dict(row) if row else None


def add_installation_repo(installation_id: int, repo_full_name: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT OR IGNORE INTO installation_repos(installation_id, repo_full_name) VALUES(?,?)",
            (installation_id, repo_full_name),
        )


def remove_installation_repo(installation_id: int, repo_full_name: str) -> None:
    with _conn() as con:
        con.execute(
            "DELETE FROM installation_repos WHERE installation_id=? AND repo_full_name=?",
            (installation_id, repo_full_name),
        )


def get_installation_id_for_repo(repo_full_name: str) -> Optional[int]:
    """Resolve the installation_id for a given repo (used in pipeline auth)."""
    with _conn() as con:
        row = con.execute(
            "SELECT installation_id FROM installation_repos WHERE repo_full_name=?",
            (repo_full_name,)
        ).fetchone()
    return row["installation_id"] if row else None


def delete_installation(installation_id: int) -> None:
    with _conn() as con:
        con.execute("DELETE FROM installations WHERE installation_id=?", (installation_id,))
    logger.info("[db] Deleted installation %s", installation_id)


# ── review_log ───────────────────────────────────────────────────────────────

def log_review(
    repo_full_name: str,
    pr_number: int,
    commit_sha: Optional[str],
    findings_count: int,
    critical_count: int,
    status: str = "completed",
) -> int:
    with _conn() as con:
        cur = con.execute(
            """
            INSERT INTO review_log(repo_full_name, pr_number, commit_sha,
                                   findings_count, critical_count, status)
            VALUES(?,?,?,?,?,?)
            """,
            (repo_full_name, pr_number, commit_sha, findings_count, critical_count, status),
        )
        return cur.lastrowid


def get_review_log(repo_full_name: str, limit: int = 50) -> List[Dict[str, Any]]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM review_log WHERE repo_full_name=? ORDER BY reviewed_at DESC LIMIT ?",
            (repo_full_name, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_review_log(limit: int = 100) -> List[Dict[str, Any]]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM review_log ORDER BY reviewed_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ── dismissals ───────────────────────────────────────────────────────────────

def add_dismissal(repo_full_name: str, rule_id: str, note: Optional[str] = None) -> int:
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO dismissals(repo_full_name, rule_id, note) VALUES(?,?,?)",
            (repo_full_name, rule_id, note),
        )
        return cur.lastrowid


def get_suppressed_rules(repo_full_name: str) -> set:
    with _conn() as con:
        rows = con.execute(
            "SELECT rule_id FROM dismissals WHERE repo_full_name=?", (repo_full_name,)
        ).fetchall()
    return {r["rule_id"] for r in rows}


def get_dismissals(repo_full_name: str) -> List[Dict[str, Any]]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM dismissals WHERE repo_full_name=? ORDER BY created_at DESC",
            (repo_full_name,),
        ).fetchall()
    return [dict(r) for r in rows]


def remove_dismissal(dismissal_id: int) -> None:
    with _conn() as con:
        con.execute("DELETE FROM dismissals WHERE id=?", (dismissal_id,))


# ── bootstrap ────────────────────────────────────────────────────────────────

def load_env_app_into_db(env_app_path: str = ".env.app") -> None:
    """
    At startup, read .env.app (if it exists) and populate app_config table.
    This is the recovery path for restarts — .env.app is the durable source of truth.
    """
    if not os.path.exists(env_app_path):
        return
    with open(env_app_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            set_app_config(key.strip(), value.strip())
    logger.info("[db] Loaded .env.app into app_config table")
