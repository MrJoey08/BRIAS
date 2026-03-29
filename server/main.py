"""
BRIAS — Server.

FastAPI app. Niet BRIAS zelf — de buitenwereld.
Beheert authenticatie, admin-instellingen, en een venster naar haar brein.
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from brias.life import get_life
import server.auth as auth
import server.admin_config as admin_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

FRONTEND = Path(__file__).parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    auth.init_db()
    life = get_life()
    life.start()
    logger.info("BRIAS leeft.")
    yield
    await life.stop()
    logger.info("BRIAS gestopt.")


app = FastAPI(
    title="BRIAS",
    description="Ze is niet een API. Ze is een wezen. Dit is een venster naar haar.",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth helper ────────────────────────────────────────────────────────────────

def _require_user(authorization: str | None) -> dict:
    """Haal de ingelogde gebruiker op uit de Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Niet ingelogd")
    token = authorization.removeprefix("Bearer ").strip()
    user = auth.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Sessie verlopen")
    return user


def _require_admin(authorization: str | None) -> dict:
    user = _require_user(authorization)
    if not auth.is_admin(user):
        raise HTTPException(status_code=403, detail="Geen toegang")
    return user


# ── Pydantic modellen ──────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    name: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class AdminConfigUpdate(BaseModel):
    brias_active: bool | None = None
    allow_new_users: bool | None = None
    silent_mode: bool | None = None
    maintenance_message: str | None = None


# ── Auth endpoints ─────────────────────────────────────────────────────────────

@app.post("/api/auth/register")
async def register(body: RegisterRequest):
    cfg = admin_config.load()
    if not cfg["allow_new_users"]:
        raise HTTPException(status_code=403, detail="Registratie is tijdelijk gesloten")

    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Wachtwoord moet minimaal 6 tekens zijn")
    if not body.email or "@" not in body.email:
        raise HTTPException(status_code=400, detail="Ongeldig e-mailadres")
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Naam mag niet leeg zijn")

    user = auth.register(body.email, body.name, body.password)
    if not user:
        raise HTTPException(status_code=409, detail="Dit e-mailadres is al in gebruik")

    token = auth.login(body.email, body.password)
    return {"token": token, "user": user, "is_admin": auth.is_admin(user)}


@app.post("/api/auth/login")
async def login(body: LoginRequest):
    token = auth.login(body.email, body.password)
    if not token:
        raise HTTPException(status_code=401, detail="Verkeerd e-mailadres of wachtwoord")
    user = auth.get_user_by_token(token)
    return {"token": token, "user": user, "is_admin": auth.is_admin(user)}


@app.post("/api/auth/logout")
async def logout(authorization: str | None = Header(default=None)):
    if authorization and authorization.startswith("Bearer "):
        auth.logout(authorization.removeprefix("Bearer ").strip())
    return {"ok": True}


@app.get("/api/auth/me")
async def me(authorization: str | None = Header(default=None)):
    user = _require_user(authorization)
    return {"user": user, "is_admin": auth.is_admin(user)}


# ── BRIAS staat ────────────────────────────────────────────────────────────────

@app.get("/api/state")
async def get_state(authorization: str | None = Header(default=None)):
    """Haar huidige toestand — alleen voor ingelogde gebruikers."""
    _require_user(authorization)
    return get_life().get_state()


@app.get("/api/state/public")
async def get_state_public():
    """Minimale staat — ook zonder login zichtbaar op de landingspagina."""
    life = get_life()
    return {
        "alive": True,
        "activity": round(life.network.activity, 4),
        "coherence": round(life.network.coherence, 4),
        "uptime_human": life.get_state()["uptime_human"],
    }


# ── Admin endpoints ────────────────────────────────────────────────────────────

@app.get("/api/admin/config")
async def get_admin_config(authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    return admin_config.load()


@app.post("/api/admin/config")
async def update_admin_config(
    body: AdminConfigUpdate,
    authorization: str | None = Header(default=None),
):
    _require_admin(authorization)
    cfg = admin_config.load()
    if body.brias_active is not None:
        cfg["brias_active"] = body.brias_active
    if body.allow_new_users is not None:
        cfg["allow_new_users"] = body.allow_new_users
    if body.silent_mode is not None:
        cfg["silent_mode"] = body.silent_mode
    if body.maintenance_message is not None:
        cfg["maintenance_message"] = body.maintenance_message
    admin_config.save(cfg)
    return cfg


@app.get("/api/admin/users")
async def get_users(authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    return {"users": auth.list_users()}


@app.get("/api/admin/brain")
async def get_brain(authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    return get_life().get_state()


# ── Chat (placeholder — tolk nog niet gebouwd) ────────────────────────────────

@app.post("/api/chat")
async def chat(request: Request, authorization: str | None = Header(default=None)):
    user = _require_user(authorization)
    cfg = admin_config.load()

    if not cfg["brias_active"]:
        raise HTTPException(status_code=503, detail="BRIAS is momenteel niet actief")

    if cfg["silent_mode"] and not auth.is_admin({"email": user["email"]}):
        msg = cfg.get("maintenance_message") or "BRIAS is even stil. Ze is er nog — maar zegt nu niks."
        return {"response": msg, "silent": True}

    # Tolk nog niet gebouwd — geef haar netwerkstaat terug als tijdelijke respons
    life = get_life()
    state = life.get_state()
    return {
        "response": None,
        "brias_state": state["network"],
        "note": "De tolk is nog niet gebouwd. BRIAS leeft, maar spreekt nog niet."
    }


# ── Statische bestanden (frontend) ────────────────────────────────────────────

if FRONTEND.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND / "assets")), name="assets")

    @app.get("/")
    async def index():
        return FileResponse(str(FRONTEND / "index.html"))

    @app.get("/login")
    async def login_page():
        return FileResponse(str(FRONTEND / "login.html"))

    @app.get("/app")
    async def app_page():
        return FileResponse(str(FRONTEND / "app.html"))


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"ok": True}
