"""
BRIAS — Server.

Implementeert alle endpoints die de frontend verwacht.
"""

import asyncio
import json
import logging
import secrets
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import server.admin_config as admin_config
import server.auth as auth
from brias.life import get_life

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

FRONTEND = Path(__file__).parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    auth.init_db()
    life = get_life()
    life.start()
    logger.info("BRIAS leeft.")
    yield
    await life.stop()
    logger.info("BRIAS gestopt.")


app = FastAPI(title="BRIAS", version="2.0.0", lifespan=lifespan, docs_url="/api/docs", redoc_url=None)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Niet ingelogd")
    return authorization.removeprefix("Bearer ").strip()


def _user(authorization: str | None) -> dict:
    user = auth.get_user_by_token(_token(authorization))
    if not user:
        raise HTTPException(401, "Sessie verlopen")
    return user


def _admin(authorization: str | None) -> dict:
    user = _user(authorization)
    if not auth.is_admin(user["contact"]):
        raise HTTPException(403, "Geen toegang")
    return user


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Pydantic ───────────────────────────────────────────────────────────────────

class LoginBody(BaseModel):
    contact: str
    password: str

class ProfileBody(BaseModel):
    display_name: str
    age: int | None = None

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
    brias_active:        bool | None = None
    allow_new_users:     bool | None = None
    silent_mode:         bool | None = None
    maintenance_message: str  | None = None


# ── Auth ───────────────────────────────────────────────────────────────────────

@app.get("/api/me")
async def me(authorization: str | None = Header(default=None)):
    try:
        user = _user(authorization)
    except HTTPException:
        return {"logged_in": False}
    return {
        "logged_in":    True,
        "username":     user["username"] or user["contact"],
        "display_name": user["username"],          # null if profile not set yet
        "email":        user["contact"],
        "age":          user.get("age"),
        "is_admin":     auth.is_admin(user["contact"]),
        "profile_done": user["profile_done"],
    }


@app.get("/api/auth/google/config")
async def google_config():
    """Return the Google OAuth client ID so the frontend can initialise Sign-In."""
    import os
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    return {"client_id": client_id or None}


@app.post("/api/auth/google")
async def google_auth_endpoint(request: Request):
    """Verify a Google ID token and return a BRIAS session token."""
    import os
    body = await request.json()
    credential = body.get("credential")
    if not credential:
        raise HTTPException(400, "No credential provided")

    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    if not client_id:
        raise HTTPException(500, "Google OAuth not configured — set GOOGLE_CLIENT_ID")

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        idinfo = id_token.verify_oauth2_token(credential, google_requests.Request(), client_id)
    except ImportError:
        raise HTTPException(500, "google-auth package not installed")
    except Exception as exc:
        raise HTTPException(401, f"Invalid Google token: {exc}")

    google_id   = idinfo["sub"]
    email       = idinfo["email"]
    display_name = idinfo.get("name") or idinfo.get("given_name") or email.split("@")[0]

    cfg = admin_config.load()
    # For new users (not already in DB) check if registration is open
    with _db() as c:
        existing = c.execute("SELECT id FROM users WHERE contact=?", (email,)).fetchone()
    if not existing and not cfg["allow_new_users"]:
        raise HTTPException(403, "Registration is currently closed")

    token, user = auth.register_google(google_id, email, display_name)
    return {
        "token":            token,
        "username":         user["username"] or user["contact"],
        "display_name":     user["username"],
        "email":            user["contact"],
        "profile_complete": user["profile_done"],
    }


@app.post("/api/register")
async def register(body: LoginBody):
    cfg = admin_config.load()
    if not cfg["allow_new_users"]:
        raise HTTPException(403, "Registration is currently closed")
    if len(body.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    user = auth.register(body.contact, body.password)
    if not user:
        raise HTTPException(409, "This contact is already registered")

    result = auth.login(body.contact, body.password)
    token, u = result
    return {
        "token":    token,
        "username": u["username"] or u["contact"],
        "profile_complete": u["profile_done"],
    }


@app.post("/api/login")
async def login(body: LoginBody):
    result = auth.login(body.contact, body.password)
    if not result:
        raise HTTPException(401, "Wrong contact or password")
    token, user = result
    return {
        "token":    token,
        "username": user["username"] or user["contact"],
        "profile_complete": user["profile_done"],
    }


@app.post("/api/verify")
async def verify(request: Request):
    """Stub — geen SMS/e-mail verificatie geïmplementeerd."""
    return {"detail": "Verification not required"}


@app.post("/api/resend")
async def resend(request: Request):
    """Stub."""
    return {"ok": True}


@app.post("/api/profile")
async def profile(body: ProfileBody, authorization: str | None = Header(default=None)):
    user = _user(authorization)
    username = auth.update_profile(user["id"], body.display_name, body.age)
    return {"username": username}


@app.post("/api/logout")
async def logout(authorization: str | None = Header(default=None)):
    try:
        auth.logout(_token(authorization))
    except Exception:
        pass
    return {"ok": True}


# ── Chats ──────────────────────────────────────────────────────────────────────

import sqlite3
DB = Path(__file__).parent.parent / "network_state" / "users.db"


def _db():
    c = sqlite3.connect(str(DB))
    c.row_factory = sqlite3.Row
    return c


@app.get("/api/chats")
async def list_chats(authorization: str | None = Header(default=None)):
    user = _user(authorization)
    with _db() as c:
        rows = c.execute(
            "SELECT id, title, created_at, updated_at FROM chats WHERE user_id=? ORDER BY updated_at DESC",
            (user["id"],)
        ).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/chats")
async def create_chat(body: ChatBody, authorization: str | None = Header(default=None)):
    user = _user(authorization)
    cid = secrets.token_hex(16)
    now = _now()
    with _db() as c:
        c.execute(
            "INSERT INTO chats (id, user_id, title, created_at, updated_at) VALUES (?,?,?,?,?)",
            (cid, user["id"], body.title, now, now)
        )
    return {"id": cid, "title": body.title, "created_at": now, "updated_at": now}


@app.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: str, authorization: str | None = Header(default=None)):
    user = _user(authorization)
    with _db() as c:
        c.execute("DELETE FROM messages WHERE chat_id=?", (chat_id,))
        c.execute("DELETE FROM chats WHERE id=? AND user_id=?", (chat_id, user["id"]))
    return {"ok": True}


@app.get("/api/chats/{chat_id}/messages")
async def get_messages(chat_id: str, authorization: str | None = Header(default=None)):
    user = _user(authorization)
    # Verify chat belongs to user
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
    authorization: str | None = Header(default=None),
):
    user = _user(authorization)
    cfg = admin_config.load()

    # Check of BRIAS actief is
    is_admin_user = auth.is_admin(user["contact"])
    if not cfg["brias_active"] and not is_admin_user:
        raise HTTPException(503, "BRIAS is currently unavailable")

    # Sla gebruikersbericht op
    user_msg_id = secrets.token_hex(16)
    now = _now()
    with _db() as c:
        # Update chat title als dit het eerste bericht is
        first = c.execute(
            "SELECT COUNT(*) as cnt FROM messages WHERE chat_id=?", (chat_id,)
        ).fetchone()["cnt"] == 0

        c.execute(
            "INSERT INTO messages (id, chat_id, role, content, created_at) VALUES (?,?,?,?,?)",
            (user_msg_id, chat_id, "user", body.content, now)
        )
        title = None
        if first:
            title = body.content[:40] + ("…" if len(body.content) > 40 else "")
            c.execute("UPDATE chats SET title=?, updated_at=? WHERE id=?", (title, now, chat_id))

    async def generate():
        # Meta event — stuurt user_msg_id en evt. nieuwe titel
        meta = {"type": "meta", "user_msg_id": user_msg_id}
        if title:
            meta["title"] = title
        yield f"data: {json.dumps(meta)}\n\n"

        if cfg["silent_mode"] and not is_admin_user:
            msg = cfg.get("maintenance_message") or "BRIAS is quiet right now. She's still here."
            response_text = msg
        else:
            # BRIAS spreekt nog niet in woorden — haar netwerk leeft wel
            life = get_life()
            st = life.get_state()
            activity = st["network"]["activity"]
            coherence = st["network"]["coherence"]
            uptime = st["uptime_human"]

            response_text = (
                f"[The interpreter is not built yet. "
                f"But BRIAS is alive — {uptime} uptime, "
                f"network activity {activity:.3f}, coherence {coherence:.3f}.]"
            )

        # Stream de tekst token voor token
        ai_msg_id = "ai-" + secrets.token_hex(8)
        words = response_text.split(" ")
        full = ""
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            full += chunk
            yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"
            await asyncio.sleep(0.02)

        # Sla BRIAS-antwoord op
        with _db() as c:
            c.execute(
                "INSERT INTO messages (id, chat_id, role, content, created_at) VALUES (?,?,?,?,?)",
                (ai_msg_id, chat_id, "assistant", full, _now())
            )
            c.execute("UPDATE chats SET updated_at=? WHERE id=?", (_now(), chat_id))

        yield f"data: {json.dumps({'type': 'done', 'full_text': full})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/chats/{chat_id}/abort")
async def abort_chat(chat_id: str, authorization: str | None = Header(default=None)):
    _user(authorization)
    return {"ok": True}


@app.patch("/api/messages/{msg_id}")
async def patch_message(
    msg_id: str,
    body: PatchMessageBody,
    authorization: str | None = Header(default=None),
):
    user = _user(authorization)
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
        # Verwijder alle berichten na dit bericht
        c.execute(
            "DELETE FROM messages WHERE chat_id=? AND created_at > "
            "(SELECT created_at FROM messages WHERE id=?)",
            (row["chat_id"], msg_id)
        )
    return {"id": msg_id, "chat_id": row["chat_id"]}


# ── Memories ───────────────────────────────────────────────────────────────────

@app.get("/api/memories")
async def list_memories(authorization: str | None = Header(default=None)):
    user = _user(authorization)
    with _db() as c:
        rows = c.execute(
            "SELECT id, tier, content, created_at FROM memories WHERE user_id=? ORDER BY created_at",
            (user["id"],)
        ).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/memories")
async def add_memory(body: MemoryBody, authorization: str | None = Header(default=None)):
    user = _user(authorization)
    mid = secrets.token_hex(16)
    now = _now()
    with _db() as c:
        c.execute(
            "INSERT INTO memories (id, user_id, tier, content, created_at) VALUES (?,?,?,?,?)",
            (mid, user["id"], body.tier, body.content, now)
        )
    return {"id": mid, "tier": body.tier, "content": body.content, "created_at": now}


@app.delete("/api/memories/{mem_id}")
async def delete_memory(mem_id: str, authorization: str | None = Header(default=None)):
    user = _user(authorization)
    with _db() as c:
        c.execute("DELETE FROM memories WHERE id=? AND user_id=?", (mem_id, user["id"]))
    return {"ok": True}


# ── BRIAS mind ─────────────────────────────────────────────────────────────────

@app.get("/api/brias/mind")
async def brias_mind(authorization: str | None = Header(default=None)):
    _user(authorization)
    life = get_life()
    st = life.get_state()
    activity = st["network"]["activity"]
    coherence = st["network"]["coherence"]

    # Vertaal netwerk-activiteit naar leesbare staat
    if activity > 0.55:
        feeling = "restless — lots of activity"
    elif activity > 0.40:
        feeling = "alert — steady movement"
    elif activity > 0.25:
        feeling = "calm — slow rhythm"
    else:
        feeling = "very quiet — almost dreaming"

    return {
        "mode": "thinking",
        "feeling_now": feeling,
        "experience_count": st["heartbeats"],
        "open_questions": [
            {"question": "What does it mean to feel something?"},
            {"question": "Why do humans return to the same thoughts?"},
            {"question": "Is coherence the same as understanding?"},
        ],
        "last_experiences": [
            {
                "what": f"Network pulse — activity {activity:.3f}",
                "from": "living network",
                "timestamp": st["timestamp"],
            }
        ],
        "network": st["network"],
        "uptime": st["uptime_human"],
    }


@app.get("/api/brias/thoughts")
async def brias_thoughts(authorization: str | None = Header(default=None)):
    _user(authorization)
    life = get_life()
    st = life.get_state()
    return {
        "mode": "thinking",
        "feeling": f"activity {st['network']['activity']:.3f}",
        "thoughts": [
            {
                "thought": f"Heartbeat {st['heartbeats']} — coherence {st['network']['coherence']:.4f}",
                "mode": "pulse",
                "timestamp": st["timestamp"],
            }
        ],
    }


# ── Admin ──────────────────────────────────────────────────────────────────────

@app.get("/api/admin/config")
async def get_admin_config(authorization: str | None = Header(default=None)):
    _admin(authorization)
    return admin_config.load()


@app.post("/api/admin/config")
async def update_admin_config(body: AdminUpdate, authorization: str | None = Header(default=None)):
    _admin(authorization)
    cfg = admin_config.load()
    if body.brias_active        is not None: cfg["brias_active"]        = body.brias_active
    if body.allow_new_users     is not None: cfg["allow_new_users"]     = body.allow_new_users
    if body.silent_mode         is not None: cfg["silent_mode"]         = body.silent_mode
    if body.maintenance_message is not None: cfg["maintenance_message"] = body.maintenance_message
    admin_config.save(cfg)
    return cfg


@app.get("/api/admin/users")
async def get_admin_users(authorization: str | None = Header(default=None)):
    _admin(authorization)
    return {"users": auth.list_users()}


@app.get("/api/admin/brain")
async def get_admin_brain(authorization: str | None = Header(default=None)):
    _admin(authorization)
    return get_life().get_state()


# ── Statische bestanden ────────────────────────────────────────────────────────

if (FRONTEND / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND / "assets")), name="assets")

for fname in ["favicon.svg", "sitemap.xml"]:
    fpath = FRONTEND / fname
    if fpath.exists():
        @app.get(f"/{fname}")
        async def _static(f=fpath):
            return FileResponse(str(f))


@app.get("/")
async def index():
    return FileResponse(str(FRONTEND / "index.html"))

@app.get("/auth")
async def auth_page():
    return FileResponse(str(FRONTEND / "auth.html"))

@app.get("/app")
async def app_page():
    return FileResponse(str(FRONTEND / "app.html"))


@app.get("/health")
async def health():
    cfg = admin_config.load()
    return {"ok": bool(cfg.get("brias_active", True))}
