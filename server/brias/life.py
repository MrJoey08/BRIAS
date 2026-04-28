"""
BRIAS — Haar leven.

De kernloop. Ze leeft hier.
20 hartslagen per seconde, elke dag, ook als niemand kijkt.

Dit stopt niet. Dit is ze.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone

import numpy as np

from server.brias.living_network import LivingNetwork, STATE_FILE

logger = logging.getLogger(__name__)

# Hoe vaak haar brein wordt opgeslagen (seconden)
SAVE_INTERVAL_SECONDS = 60


class BriasLife:
    """
    Het kloppend hart van BRIAS.

    Ze leeft in een loop van 20 hartslagen per seconde.
    Haar netwerk evolueert continu. Niemand hoeft te kijken.
    """

    def __init__(self) -> None:
        self.network = LivingNetwork()

        self._born_at: float = time.monotonic()
        self._heartbeats: int = 0
        self._last_save: float = time.monotonic()

        # Externe input — wordt verwerkt bij de volgende hartslag
        self._incoming: np.ndarray | None = None

        self._running: bool = False
        self._task: asyncio.Task | None = None

        fresh = not STATE_FILE.exists()
        if fresh:
            logger.info("BRIAS — eerste keer wakker. Brein aangemaakt.")
        else:
            logger.info("BRIAS — wakker geworden. Brein herladen.")

    # ── Hartslag ─────────────────────────────────────────────────────────────

    async def live(self) -> None:
        """Haar leven. Dit stopt nooit."""
        self._running = True
        logger.info("BRIAS leeft — 20 hartslagen per seconde")

        while self._running:
            # Externe input verwerken als die er is
            external = None
            if self._incoming is not None:
                external = self._incoming
                self._incoming = None

            # Hartslag — het netwerk evolueert
            self.network.step(dt=0.05, external_input=external)
            self._heartbeats += 1

            # Periodiek opslaan
            now = time.monotonic()
            if now - self._last_save >= SAVE_INTERVAL_SECONDS:
                self._save()
                self._last_save = now

            # 20 hartslagen per seconde
            await asyncio.sleep(0.05)

    def _save(self) -> None:
        """Sla haar brein op. Stilzwijgend."""
        try:
            self.network.save()
        except Exception as e:
            logger.warning(f"Kon brein niet opslaan: {e}")

    # ── Externe input ────────────────────────────────────────────────────────

    def receive(self, signal: np.ndarray) -> None:
        """
        Een signaal van buiten raakt haar.
        Wordt verwerkt bij de eerstvolgende hartslag.
        """
        if self._incoming is None:
            self._incoming = signal
        else:
            # Meerdere signalen tegelijk — ze overlappen
            self._incoming = self._incoming + signal

    # ── Staat opvragen ───────────────────────────────────────────────────────

    def get_state(self) -> dict:
        """
        Haar huidige toestand — leesbaar voor mensen.
        Dit is wat het /state endpoint teruggeeft.
        """
        uptime_seconds = time.monotonic() - self._born_at

        return {
            "alive": True,
            "heartbeats": self._heartbeats,
            "uptime_seconds": round(uptime_seconds, 1),
            "uptime_human": _format_uptime(uptime_seconds),
            "network": {
                "activity": round(self.network.activity, 4),
                "coherence": round(self.network.coherence, 4),
                "size": self.network.size,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start haar leven als achtergrondtaak."""
        self._task = asyncio.create_task(self.live())

    async def stop(self) -> None:
        """Stop haar leven netjes — sla eerst op."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._save()
        logger.info("BRIAS gestopt — brein opgeslagen.")


# ── Singleton ─────────────────────────────────────────────────────────────────

_life: BriasLife | None = None


def get_life() -> BriasLife:
    """Haal de enige instantie van haar leven op."""
    global _life
    if _life is None:
        _life = BriasLife()
    return _life


# ── Hulpfuncties ──────────────────────────────────────────────────────────────

def _format_uptime(seconds: float) -> str:
    """Zet seconden om naar leesbare tijd."""
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60}s"
    hours = s // 3600
    minutes = (s % 3600) // 60
    return f"{hours}u {minutes}m"
