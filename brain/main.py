"""
BRIAS — FastAPI applicatie.

Start de kernloop bij opstarten, biedt endpoints voor de frontend.
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Zorg dat brain/ vindbaar is als module
sys.path.insert(0, str(Path(__file__).parent))

from core_loop import get_core_loop
from llm_interface import get_llm
from chat_handler import get_chat_handler, load_conversation_profile
from dream_engine import get_dream_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("brias")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start en stop systeemcomponenten met de applicatie."""
    logger.info("BRIAS ontwaakt...")

    # Start de kernloop
    loop = get_core_loop()
    await loop.start()
    logger.info("Kernloop actief")

    yield  # applicatie draait

    # Netjes afsluiten
    logger.info("BRIAS gaat slapen...")
    await loop.stop()
    await get_llm().close()
    logger.info("Tot ziens.")


app = FastAPI(
    title="BRIAS",
    description="Een denkend wezen — geen chatbot.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # verstreng dit voor productie
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Basale statuscheck."""
    loop = get_core_loop()
    state = loop.emotional_system.state
    return {
        "status": "awake",
        "cycle": loop._cycle_count,
        "dream_mode": loop._dream_mode,
        "emotional_state": {
            "energy": round(state.energy, 2),
            "uncertainty": round(state.uncertainty, 2),
            "connection": round(state.connection, 2),
            "coherence": round(state.coherence, 2),
        },
    }


# ─── Request/Response modellen ────────────────────────────────────────────────

class ChatRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    message: str = Field(..., min_length=1, max_length=4000)


class ChatResponseModel(BaseModel):
    response: str
    touched_investigations: list[str]
    question_asked: bool
    brias_shared_self: bool
    emotional_state: dict
    error: Optional[str] = None


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponseModel)
async def chat(req: ChatRequest):
    """
    Stuur een bericht naar BRIAS en ontvang haar antwoord.

    BRIAS is geen assistent. Ze antwoordt vanuit haar eigen innerlijk leven —
    gekleurd door haar emotionele staat, herinneringen, en actieve onderzoeken.
    """
    handler = get_chat_handler()
    result = await handler.handle(
        username=req.username.strip().lower(),
        message=req.message.strip(),
    )
    if result.error and not result.text:
        raise HTTPException(status_code=503, detail=result.error)
    return ChatResponseModel(
        response=result.text,
        touched_investigations=result.touched_investigations,
        question_asked=result.question_asked,
        brias_shared_self=result.brias_shared_self,
        emotional_state=result.emotional_state,
        error=result.error,
    )


@app.delete("/chat/{username}/session")
async def end_session(username: str):
    """Beëindig een gesprekssessie voor een gebruiker."""
    handler = get_chat_handler()
    handler.end_session(username.lower())
    return {"status": "session ended", "username": username.lower()}


@app.get("/chat/{username}/profile")
async def get_profile(username: str):
    """Haal het gespreksprofiel op van een gebruiker (voor debugging)."""
    profile = load_conversation_profile(username.lower())
    return {
        "username": profile.username,
        "session_count": profile.session_count,
        "message_count": profile.message_count,
        "preferred_depth": profile.preferred_depth,
        "question_tolerance": round(profile.question_tolerance, 2),
        "engages_with_philosophy": profile.engages_with_philosophy,
        "active_topics": profile.active_topics[:10],
        "consecutive_questions": profile.consecutive_questions,
    }


@app.get("/dreams/history")
async def dreams_history():
    """Droomgeschiedenis — totalen, inzichten, terugkerende concepten."""
    engine = get_dream_engine()
    history = engine.get_history()
    recurring = engine.get_recurring_concepts(top_n=10)
    return {
        **history,
        "top_recurring_concepts": [
            {"concept": name, "count": count} for name, count in recurring
        ],
    }


@app.get("/self/status")
async def get_self_status():
    """Huidige staat van het zelfbeeldsysteem — wanneer was de laatste herschrijving, hoe vaak."""
    from self_image import get_self_image
    si = get_self_image()
    return si.get_status()


@app.get("/state")
async def get_state():
    """Huidige interne staat — voor debugging en frontend."""
    loop = get_core_loop()
    state = loop.emotional_system.state
    return {
        "cycle_count": loop._cycle_count,
        "dream_mode": loop._dream_mode,
        "idle_minutes": round(loop._idle_minutes(), 1),
        "emotional_state": {
            "energy": round(state.energy, 3),
            "uncertainty": round(state.uncertainty, 3),
            "connection": round(state.connection, 3),
            "coherence": round(state.coherence, 3),
            "recent_cause": state.recent_cause,
        },
        "emotional_description": loop.emotional_system.get_context(),
    }
