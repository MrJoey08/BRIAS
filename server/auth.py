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


def change_password(user_id: str, old_password: str, new_password: str) -> bool:
    """Wijzig wachtwoord. Geeft False als oude niet klopt of de gebruiker niet bestaat."""
    with _conn() as c:
        row = c.execute(
            "SELECT password FROM users WHERE id=?", (user_id,)
        ).fetchone()
        if not row:
            return False
        if row["password"] != _hash(old_password):
            return False
        c.execute(
            "UPDATE users SET password=? WHERE id=?",
            (_hash(new_password), user_id),
        )
        # Invalidate all existing sessions for this user.
        c.execute("DELETE FROM tokens WHERE user_id=?", (user_id,))
    return True


def delete_account(user_id: str, password: str) -> bool:
    """Verwijder account en alle gekoppelde data. Geeft False bij verkeerd wachtwoord."""
    with _conn() as c:
        row = c.execute(
            "SELECT password FROM users WHERE id=?", (user_id,)
        ).fetchone()
        if not row:
            return False
        # Google users have a placeholder password starting with 'google:' — let them through.
        if not row["password"].startswith("google:") and row["password"] != _hash(password):
            return False
        c.execute(
            "DELETE FROM messages WHERE chat_id IN (SELECT id FROM chats WHERE user_id=?)",
            (user_id,),
        )
        c.execute("DELETE FROM chats WHERE user_id=?", (user_id,))
        c.execute("DELETE FROM memories WHERE user_id=?", (user_id,))
        c.execute("DELETE FROM tokens WHERE user_id=?", (user_id,))
        c.execute("DELETE FROM users WHERE id=?", (user_id,))
    return True


def register_google(google_id: str, email: str, display_name: str) -> tuple[str, dict]:
    """Register a new Google user, or log in an existing one with the same email."""
    now = datetime.now(timezone.utc).isoformat()
    email = email.strip()
    with _conn() as c:
        row = c.execute(
            "SELECT id, contact, username, age, profile_done FROM users WHERE contact=?",
            (email,)
        ).fetchone()
        if row:
            # Existing user — just create a new session token
            user_id = row["id"]
            username = row["username"]
            profile_done = bool(row["profile_done"])
        else:
            # New Google user — register with a placeholder password
            uid = secrets.token_hex(16)
            c.execute(
                "INSERT INTO users (id, contact, password, username, created_at, profile_done) VALUES (?,?,?,?,?,1)",
                (uid, email, f"google:{google_id}", display_name.strip(), now),
            )
            user_id = uid
            username = display_name.strip()
            profile_done = True
        token = secrets.token_hex(32)
        c.execute(
            "INSERT INTO tokens (token, user_id, created_at) VALUES (?,?,?)",
            (token, user_id, now),
        )
    return token, {
        "id": user_id,
        "contact": email,
        "username": username,
        "profile_done": profile_done,
    }


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
