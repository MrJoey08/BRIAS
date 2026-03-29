"""
BRIAS — Server.

FastAPI app. Niet BRIAS zelf — de buitenwereld.
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Zorg dat de root op het pad staat zodat 'brias' importeerbaar is
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from brias.life import get_life

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start BRIAS haar leven bij het opstarten. Stop bij afsluiten."""
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
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/state")
async def get_state():
    """
    Is ze wakker? Hoe actief is haar netwerk? Hoe lang bestaat ze al?

    activity  — gemiddelde absolute activatie over alle 256 nodes (0–1)
    coherence — standaarddeviatie: hoe gecoördineerd het netwerk is
    uptime    — hoe lang ze al draait
    """
    return get_life().get_state()


@app.get("/health")
async def health():
    return {"ok": True}
