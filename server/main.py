"""
BRIAS — Account server.

Beheert alleen gebruikersaccounts, sessies, chats en memories.
BRIAS zelf draait NIET op deze server — brias_active is altijd False.
"""

import asyncio
import json
import logging
import secrets
import sqlite3
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import server.admin_config as admin_config
import server.auth as auth

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DB = Path(__file__).parent.parent / "network_state" / "users.db"

ALLOWED_ORIGINS = [
    "https://brias.eu",
    "https://www.brias.eu",
]

COOKIE_NAME = "brias_session"
COOKIE_MAX_AGE = 30 * 24 * 3600  # 30 days


@asynccontextmanager
async def lifespan(app: FastAPI):
    auth.init_db()
    logger.info("BRIAS account server gestart.")
    yield
    logger.info("BRIAS account server gestopt.")


app = FastAPI(title="BRIAS Accounts", version="2.0.0", lifespan=lifespan, docs_url="/api/docs", redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth dependencies ────────────────────────────────────────────────────────

def _resolve_token(
    authorization: str | None = Header(default=None),
    brias_session: str | None = Cookie(default=None),
) -> str:
    """Extract token from httpOnly cookie (preferred) or Authorization header."""
    if brias_session:
        return brias_session
    if authorization and authorization.startswith("Bearer "):
        return authorization.removeprefix("Bearer ").strip()
    raise HTTPException(401, "Niet ingelogd")


def _require_user(token: str = Depends(_resolve_token)) -> dict:
    user = auth.get_user_by_token(token)
    if not user:
        raise HTTPException(401, "Sessie verlopen")
    return user


def _require_admin(user: dict = Depends(_require_user)) -> dict:
    if not auth.is_admin(user["contact"]):
        raise HTTPException(403, "Geen toegang")
    return user


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        domain=".brias.eu",
        max_age=COOKIE_MAX_AGE,
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, domain=".brias.eu")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db():
    c = sqlite3.connect(str(DB))
    c.row_factory = sqlite3.Row
    return c


# ── Pydantic ─────────────────────────────────────────────────────────────────

class LoginBody(BaseModel):
    contact: str
    password: str

class ProfileBody(BaseModel):
    display_name: str
    age: int | None = None

class PasswordBody(BaseModel):
    old_password: str
    new_password: str

class DeleteAccountBody(BaseModel):
    password: str = ""

class ChatBody(BaseModel):
    title: str = "New chat"

class MessageBody(BaseModel):
    content: str

class PatchMessageBody(BaseModel):
    content: str

class MemoryBody(BaseModel):
    tier: str
    content: str

class AdminUpdate(BaseModel):
    allow_new_users:     bool | None = None
    silent_mode:         bool | None = None
    maintenance_message: str  | None = None


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"ok": True, "brias_active": False}


# ── Auth ─────────────────────────────────────────────────────────────────────

@app.get("/api/me")
async def me(
    authorization: str | None = Header(default=None),
    brias_session: str | None = Cookie(default=None),
):
    token = brias_session or (
        authorization.removeprefix("Bearer ").strip()
        if authorization and authorization.startswith("Bearer ")
        else None
    )
    if not token:
        return {"logged_in": False, "brias_active": False}
    user = auth.get_user_by_token(token)
    if not user:
        return {"logged_in": False, "brias_active": False}
    return {
        "logged_in":    True,
        "username":     user["username"] or user["contact"],
        "display_name": user["username"],
        "email":        user["contact"],
        "age":          user.get("age"),
        "is_admin":     auth.is_admin(user["contact"]),
        "profile_done": user["profile_done"],
        "brias_active": False,
    }


@app.get("/api/auth/google/config")
async def google_config():
    return {"client_id": None}


@app.post("/api/auth/google")
async def google_auth_endpoint(request: Request):
    raise HTTPException(501, "Google OAuth not configured on this server")


@app.post("/api/register")
async def register(body: LoginBody, response: Response):
    cfg = admin_config.load()
    if not cfg["allow_new_users"]:
        raise HTTPException(403, "Registration is currently closed")
    if len(body.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    user = auth.register(body.contact, body.password)
    if not user:
        raise HTTPException(409, "This contact is already registered")
    token, u = auth.login(body.contact, body.password)
    _set_session_cookie(response, token)
    return {"token": token, "username": u["username"] or u["contact"], "profile_complete": u["profile_done"]}


@app.post("/api/login")
async def login(body: LoginBody, response: Response):
    result = auth.login(body.contact, body.password)
    if not result:
        raise HTTPException(401, "Wrong contact or password")
    token, user = result
    _set_session_cookie(response, token)
    return {"token": token, "username": user["username"] or user["contact"], "profile_complete": user["profile_done"]}


@app.post("/api/verify")
async def verify(request: Request):
    return {"detail": "Verification not required"}


@app.post("/api/resend")
async def resend(request: Request):
    return {"ok": True}


@app.post("/api/profile")
async def profile(body: ProfileBody, user: dict = Depends(_require_user)):
    username = auth.update_profile(user["id"], body.display_name, body.age)
    return {"username": username}


@app.post("/api/account/password")
async def change_password(body: PasswordBody, user: dict = Depends(_require_user)):
    if len(body.new_password) < 6:
        raise HTTPException(400, "New password must be at least 6 characters")
    ok = auth.change_password(user["id"], body.old_password, body.new_password)
    if not ok:
        raise HTTPException(401, "Current password is incorrect")
    return {"ok": True}


@app.post("/api/account/delete")
async def delete_account(body: DeleteAccountBody, response: Response, user: dict = Depends(_require_user)):
    ok = auth.delete_account(user["id"], body.password)
    if not ok:
        raise HTTPException(401, "Password is incorrect")
    _clear_session_cookie(response)
    return {"ok": True}


@app.post("/api/logout")
async def logout(
    response: Response,
    authorization: str | None = Header(default=None),
    brias_session: str | None = Cookie(default=None),
):
    token = brias_session or (
        authorization.removeprefix("Bearer ").strip()
        if authorization and authorization.startswith("Bearer ")
        else None
    )
    if token:
        try:
            auth.logout(token)
        except Exception:
            pass
    _clear_session_cookie(response)
    return {"ok": True}


# ── Chats ────────────────────────────────────────────────────────────────────

@app.get("/api/chats")
async def list_chats(user: dict = Depends(_require_user)):
    with _db() as c:
        rows = c.execute(
            "SELECT id, title, created_at, updated_at FROM chats WHERE user_id=? ORDER BY updated_at DESC",
            (user["id"],)
        ).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/chats")
async def create_chat(body: ChatBody, user: dict = Depends(_require_user)):
    cid = secrets.token_hex(16)
    now = _now()
    with _db() as c:
        c.execute(
            "INSERT INTO chats (id, user_id, title, created_at, updated_at) VALUES (?,?,?,?,?)",
            (cid, user["id"], body.title, now, now)
        )
    return {"id": cid, "title": body.title, "created_at": now, "updated_at": now}


@app.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: str, user: dict = Depends(_require_user)):
    with _db() as c:
        c.execute("DELETE FROM messages WHERE chat_id=?", (chat_id,))
        c.execute("DELETE FROM chats WHERE id=? AND user_id=?", (chat_id, user["id"]))
    return {"ok": True}


@app.get("/api/chats/{chat_id}/messages")
async def get_messages(chat_id: str, user: dict = Depends(_require_user)):
    with _db() as c:
        chat = c.execute("SELECT id FROM chats WHERE id=? AND user_id=?", (chat_id, user["id"])).fetchone()
        if not chat:
            raise HTTPException(404, "Chat not found")
        rows = c.execute(
            "SELECT id, role, content, created_at FROM messages WHERE chat_id=? ORDER BY created_at",
            (chat_id,)
        ).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/chats/{chat_id}/messages/stream")
async def stream_message(
    chat_id: str,
    body: MessageBody,
    user: dict = Depends(_require_user),
):
    cfg = admin_config.load()

    user_msg_id = secrets.token_hex(16)
    now = _now()
    with _db() as c:
        first = c.execute("SELECT COUNT(*) as cnt FROM messages WHERE chat_id=?", (chat_id,)).fetchone()["cnt"] == 0
        c.execute(
            "INSERT INTO messages (id, chat_id, role, content, created_at) VALUES (?,?,?,?,?)",
            (user_msg_id, chat_id, "user", body.content, now)
        )
        title = None
        if first:
            title = body.content[:40] + ("…" if len(body.content) > 40 else "")
            c.execute("UPDATE chats SET title=?, updated_at=? WHERE id=?", (title, now, chat_id))

    async def generate():
        meta = {"type": "meta", "user_msg_id": user_msg_id}
        if title:
            meta["title"] = title
        yield f"data: {json.dumps(meta)}\n\n"

        if cfg.get("silent_mode") and not auth.is_admin(user["contact"]):
            response_text = cfg.get("maintenance_message") or "BRIAS is quiet right now. She's still here."
        else:
            response_text = "BRIAS is not running yet on this server. She's being built."

        ai_msg_id = "ai-" + secrets.token_hex(8)
        words = response_text.split(" ")
        full = ""
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            full += chunk
            yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"
            await asyncio.sleep(0.02)

        with _db() as c:
            c.execute(
                "INSERT INTO messages (id, chat_id, role, content, created_at) VALUES (?,?,?,?,?)",
                (ai_msg_id, chat_id, "assistant", full, _now())
            )
            c.execute("UPDATE chats SET updated_at=? WHERE id=?", (_now(), chat_id))

        yield f"data: {json.dumps({'type': 'done', 'full_text': full})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/chats/{chat_id}/abort")
async def abort_chat(chat_id: str, user: dict = Depends(_require_user)):
    return {"ok": True}


@app.patch("/api/messages/{msg_id}")
async def patch_message(
    msg_id: str,
    body: PatchMessageBody,
    user: dict = Depends(_require_user),
):
    with _db() as c:
        row = c.execute(
            "SELECT m.id, m.chat_id FROM messages m "
            "JOIN chats ch ON m.chat_id=ch.id "
            "WHERE m.id=? AND ch.user_id=? AND m.role='user'",
            (msg_id, user["id"])
        ).fetchone()
        if not row:
            raise HTTPException(404, "Message not found")
        c.execute("UPDATE messages SET content=? WHERE id=?", (body.content, msg_id))
        c.execute(
            "DELETE FROM messages WHERE chat_id=? AND created_at > "
            "(SELECT created_at FROM messages WHERE id=?)",
            (row["chat_id"], msg_id)
        )
    return {"id": msg_id, "chat_id": row["chat_id"]}


# ── Memories ─────────────────────────────────────────────────────────────────

@app.get("/api/memories")
async def list_memories(user: dict = Depends(_require_user)):
    with _db() as c:
        rows = c.execute(
            "SELECT id, tier, content, created_at FROM memories WHERE user_id=? ORDER BY created_at",
            (user["id"],)
        ).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/memories")
async def add_memory(body: MemoryBody, user: dict = Depends(_require_user)):
    mid = secrets.token_hex(16)
    now = _now()
    with _db() as c:
        c.execute(
            "INSERT INTO memories (id, user_id, tier, content, created_at) VALUES (?,?,?,?,?)",
            (mid, user["id"], body.tier, body.content, now)
        )
    return {"id": mid, "tier": body.tier, "content": body.content, "created_at": now}


@app.delete("/api/memories/{mem_id}")
async def delete_memory(mem_id: str, user: dict = Depends(_require_user)):
    with _db() as c:
        c.execute("DELETE FROM memories WHERE id=? AND user_id=?", (mem_id, user["id"]))
    return {"ok": True}


# ── BRIAS mind — offline ──────────────────────────────────────────────────────

@app.get("/api/brias/mind")
async def brias_mind(user: dict = Depends(_require_user)):
    return {"mode": "offline", "brias_active": False}


@app.get("/api/brias/thoughts")
async def brias_thoughts(user: dict = Depends(_require_user)):
    return {"mode": "offline", "brias_active": False}


# ── Admin ─────────────────────────────────────────────────────────────────────

@app.get("/api/admin/config")
async def get_admin_config(user: dict = Depends(_require_admin)):
    return admin_config.load()


@app.post("/api/admin/config")
async def update_admin_config(body: AdminUpdate, user: dict = Depends(_require_admin)):
    cfg = admin_config.load()
    if body.allow_new_users     is not None: cfg["allow_new_users"]     = body.allow_new_users
    if body.silent_mode         is not None: cfg["silent_mode"]         = body.silent_mode
    if body.maintenance_message is not None: cfg["maintenance_message"] = body.maintenance_message
    admin_config.save(cfg)
    return cfg


@app.get("/api/admin/users")
async def get_admin_users(user: dict = Depends(_require_admin)):
    return {"users": auth.list_users()}


@app.get("/api/admin/brain")
async def get_admin_brain(user: dict = Depends(_require_admin)):
    return {"brias_active": False, "note": "BRIAS draait niet op deze server."}
