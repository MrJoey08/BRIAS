"""
BRIAS — Authenticatie.

contact = email of telefoonnummer (opgeslagen as-is)
username = display name (ingesteld via /api/profile)
Admin = bailey.haks@gmail.com
"""

import hashlib
import logging
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

ADMIN_CONTACT = "bailey.haks@gmail.com"
DB_PATH = Path(__file__).parent.parent / "network_state" / "users.db"


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id           TEXT PRIMARY KEY,
                contact      TEXT UNIQUE NOT NULL,
                password     TEXT NOT NULL,
                username     TEXT,
                age          INTEGER,
                created_at   TEXT NOT NULL,
                profile_done INTEGER DEFAULT 0
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS tokens (
                token      TEXT PRIMARY KEY,
                user_id    TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id         TEXT PRIMARY KEY,
                user_id    TEXT NOT NULL,
                title      TEXT NOT NULL DEFAULT 'New chat',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id         TEXT PRIMARY KEY,
                chat_id    TEXT NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id         TEXT PRIMARY KEY,
                user_id    TEXT NOT NULL,
                tier       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def register(contact: str, password: str) -> dict | None:
    """Registreer. Geeft None terug als contact al bestaat."""
    uid = secrets.token_hex(16)
    now = datetime.now(timezone.utc).isoformat()
    try:
        with _conn() as c:
            c.execute(
                "INSERT INTO users (id, contact, password, created_at) VALUES (?,?,?,?)",
                (uid, contact.strip(), _hash(password), now),
            )
        return {"id": uid, "contact": contact.strip(), "username": None, "profile_done": False}
    except sqlite3.IntegrityError:
        return None


def login(contact: str, password: str) -> tuple[str, dict] | None:
    """Login. Geeft (token, user) terug of None."""
    with _conn() as c:
        row = c.execute(
            "SELECT id, contact, username, profile_done FROM users WHERE contact=? AND password=?",
            (contact.strip(), _hash(password)),
        ).fetchone()
        if not row:
            return None
        token = secrets.token_hex(32)
        now = datetime.now(timezone.utc).isoformat()
        c.execute(
            "INSERT INTO tokens (token, user_id, created_at) VALUES (?,?,?)",
            (token, row["id"], now),
        )
        return token, {
            "id": row["id"],
            "contact": row["contact"],
            "username": row["username"],
            "profile_done": bool(row["profile_done"]),
        }


def get_user_by_token(token: str) -> dict | None:
    with _conn() as c:
        row = c.execute("""
            SELECT u.id, u.contact, u.username, u.age, u.profile_done
            FROM tokens t JOIN users u ON t.user_id = u.id
            WHERE t.token = ?
        """, (token,)).fetchone()
        if not row:
            return None
        return {
            "id":           row["id"],
            "contact":      row["contact"],
            "username":     row["username"],
            "age":          row["age"],
            "profile_done": bool(row["profile_done"]),
        }


def update_profile(user_id: str, display_name: str, age: int | None) -> str:
    """Sla naam + leeftijd op. Geeft de username terug."""
    with _conn() as c:
        c.execute(
            "UPDATE users SET username=?, age=?, profile_done=1 WHERE id=?",
            (display_name.strip(), age, user_id),
        )
    return display_name.strip()


def logout(token: str) -> None:
    with _conn() as c:
        c.execute("DELETE FROM tokens WHERE token=?", (token,))


def list_users() -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, contact, username, age, created_at, profile_done FROM users ORDER BY created_at"
        ).fetchall()
        return [dict(r) for r in rows]


def is_admin(contact: str) -> bool:
    return contact.lower().strip() == ADMIN_CONTACT.lower()
