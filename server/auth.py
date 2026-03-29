"""
BRIAS — Authenticatie.

Simpel. Email + wachtwoord. Tokens opgeslagen in SQLite.
Elke gebruiker heeft een uniek account_id dat BRIAS gebruikt
om hen te herkennen.

Admin: bailey.haks@gmail.com — heeft toegang tot het admin panel.
"""

import hashlib
import logging
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

ADMIN_EMAIL = "bailey.haks@gmail.com"
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
                id          TEXT PRIMARY KEY,
                email       TEXT UNIQUE NOT NULL,
                name        TEXT NOT NULL,
                password    TEXT NOT NULL,
                created_at  TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS tokens (
                token       TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                created_at  TEXT NOT NULL
            )
        """)


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def register(email: str, name: str, password: str) -> dict | None:
    """Registreer een nieuwe gebruiker. Geeft None terug als email al bestaat."""
    uid = secrets.token_hex(16)
    now = datetime.now(timezone.utc).isoformat()
    try:
        with _conn() as c:
            c.execute(
                "INSERT INTO users (id, email, name, password, created_at) VALUES (?,?,?,?,?)",
                (uid, email.lower().strip(), name.strip(), _hash(password), now),
            )
        return {"id": uid, "email": email.lower().strip(), "name": name.strip()}
    except sqlite3.IntegrityError:
        return None


def login(email: str, password: str) -> str | None:
    """Login. Geeft een sessie-token terug, of None bij verkeerde gegevens."""
    with _conn() as c:
        row = c.execute(
            "SELECT id FROM users WHERE email=? AND password=?",
            (email.lower().strip(), _hash(password)),
        ).fetchone()
        if not row:
            return None
        token = secrets.token_hex(32)
        now = datetime.now(timezone.utc).isoformat()
        c.execute(
            "INSERT INTO tokens (token, user_id, created_at) VALUES (?,?,?)",
            (token, row["id"], now),
        )
        return token


def get_user_by_token(token: str) -> dict | None:
    """Haal gebruiker op via token. Geeft None bij ongeldig token."""
    with _conn() as c:
        row = c.execute("""
            SELECT u.id, u.email, u.name
            FROM tokens t JOIN users u ON t.user_id = u.id
            WHERE t.token = ?
        """, (token,)).fetchone()
        if not row:
            return None
        return {"id": row["id"], "email": row["email"], "name": row["name"]}


def logout(token: str) -> None:
    with _conn() as c:
        c.execute("DELETE FROM tokens WHERE token=?", (token,))


def list_users() -> list[dict]:
    """Alle gebruikers — alleen voor admin."""
    with _conn() as c:
        rows = c.execute(
            "SELECT id, email, name, created_at FROM users ORDER BY created_at"
        ).fetchall()
        return [dict(r) for r in rows]


def is_admin(user: dict) -> bool:
    return user["email"].lower() == ADMIN_EMAIL.lower()
