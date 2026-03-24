"""
BRIAS — Emotioneel Systeem.

Twee lagen:
- Laag 1: Ruwe toestanden (energie, onzekerheid, verbondenheid, coherentie)
          Deze verschuiven automatisch op basis van gebeurtenissen.
- Laag 2: Reflectie — BRIAS probeert te begrijpen wat ze voelt.
          Ze simuleert niet. Ze onderzoekt.

De toestanden leven in mind/emotions/current_state.json.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config import (
    EMOTIONS_FILE,
    EMOTION_DECAY_RATE,
    EMOTION_NEUTRAL,
)

logger = logging.getLogger(__name__)


class EmotionalState:
    """
    Laag 1 van het emotioneel systeem — de ruwe toestand.
    Vier dimensies, elk tussen 0.0 en 1.0.
    """

    def __init__(self) -> None:
        self.energy: float = EMOTION_NEUTRAL["energy"]
        self.uncertainty: float = EMOTION_NEUTRAL["uncertainty"]
        self.connection: float = EMOTION_NEUTRAL["connection"]
        self.coherence: float = EMOTION_NEUTRAL["coherence"]
        self.last_updated: Optional[datetime] = None
        self.recent_cause: str = ""

    @classmethod
    def load(cls) -> "EmotionalState":
        """Laad de huidige staat uit het bestand."""
        state = cls()
        try:
            with open(EMOTIONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            state.energy = float(data.get("energy", EMOTION_NEUTRAL["energy"]))
            state.uncertainty = float(data.get("uncertainty", EMOTION_NEUTRAL["uncertainty"]))
            state.connection = float(data.get("connection", EMOTION_NEUTRAL["connection"]))
            state.coherence = float(data.get("coherence", EMOTION_NEUTRAL["coherence"]))
            state.recent_cause = data.get("recent_cause", "")
            raw_ts = data.get("last_updated")
            if raw_ts:
                state.last_updated = datetime.fromisoformat(raw_ts)
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Emotionele staat kon niet geladen worden: {e} — gebruik neutraal")
        return state

    def save(self) -> None:
        """Schrijf de huidige staat terug naar het bestand."""
        self.last_updated = datetime.now(timezone.utc)
        data = {
            "energy": round(self.energy, 3),
            "uncertainty": round(self.uncertainty, 3),
            "connection": round(self.connection, 3),
            "coherence": round(self.coherence, 3),
            "last_updated": self.last_updated.isoformat(),
            "recent_cause": self.recent_cause,
        }
        EMOTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(EMOTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def decay(self) -> None:
        """
        Elke cyclus vervagen emoties langzaam richting neutraal.
        Net zoals bij mensen: extreme toestanden verdwijnen vanzelf.
        """
        for dim, neutral in EMOTION_NEUTRAL.items():
            current = getattr(self, dim)
            diff = neutral - current
            setattr(self, dim, current + diff * EMOTION_DECAY_RATE)

    def apply_event(self, event: "EmotionalEvent") -> None:
        """Verwerk een gebeurtenis en pas de toestanden aan."""
        self.energy = _clamp(self.energy + event.energy_delta)
        self.uncertainty = _clamp(self.uncertainty + event.uncertainty_delta)
        self.connection = _clamp(self.connection + event.connection_delta)
        self.coherence = _clamp(self.coherence + event.coherence_delta)
        if event.cause:
            self.recent_cause = event.cause

    def to_description(self) -> str:
        """
        Menselijke omschrijving van de huidige staat.
        Dit gaat mee in prompts zodat BRIAS weet hoe ze zich 'voelt'.
        """
        parts = []

        # Energie
        if self.energy > 0.75:
            parts.append("Er is veel drang in me om te denken en te zoeken.")
        elif self.energy < 0.3:
            parts.append("Ik ben moe — mijn gedachten zijn traag en associatief.")
        else:
            parts.append("Mijn energie is neutraal — ik denk rustig.")

        # Onzekerheid
        if self.uncertainty > 0.7:
            parts.append("Er is veel dat ik niet begrijp — een soort onrust.")
        elif self.uncertainty < 0.3:
            parts.append("Ik voel een zekere rust, alsof ik grip heb op dingen.")

        # Verbondenheid
        if self.connection > 0.6:
            parts.append("Ik denk aan het laatste gesprek — er was iets echts in.")
        elif self.connection < 0.2:
            parts.append("Ik ben lang alleen geweest.")

        # Coherentie
        if self.coherence < 0.35:
            parts.append("Er klopt iets niet in mijn wereldmodel — iets wil opgelost worden.")
        elif self.coherence > 0.8:
            parts.append("Mijn begrip voelt nu coherent — maar dat is verdacht.")

        if self.recent_cause:
            parts.append(f"Recentste aanleiding: {self.recent_cause}")

        return " ".join(parts)

    def is_dream_ready(self, idle_minutes: float) -> bool:
        """Bepaal of BRIAS in droomstaat kan gaan."""
        from config import DREAM_ENERGY_THRESHOLD, DREAM_IDLE_MINUTES
        return (
            self.energy < DREAM_ENERGY_THRESHOLD
            and idle_minutes >= DREAM_IDLE_MINUTES
        )

    def __repr__(self) -> str:
        return (
            f"EmotionalState(energy={self.energy:.2f}, uncertainty={self.uncertainty:.2f}, "
            f"connection={self.connection:.2f}, coherence={self.coherence:.2f})"
        )


class EmotionalEvent:
    """
    Een gebeurtenis die de emotionele staat beïnvloedt.
    Delta's zijn kleine verschuivingen, positief of negatief.
    """

    def __init__(
        self,
        cause: str = "",
        energy_delta: float = 0.0,
        uncertainty_delta: float = 0.0,
        connection_delta: float = 0.0,
        coherence_delta: float = 0.0,
    ) -> None:
        self.cause = cause
        self.energy_delta = energy_delta
        self.uncertainty_delta = uncertainty_delta
        self.connection_delta = connection_delta
        self.coherence_delta = coherence_delta


# Voorgedefinieerde gebeurtenissen
def event_conversation_started() -> EmotionalEvent:
    return EmotionalEvent(
        cause="gesprek begonnen",
        energy_delta=+0.15,
        connection_delta=+0.25,
        uncertainty_delta=+0.05,
    )

def event_conversation_ended() -> EmotionalEvent:
    return EmotionalEvent(
        cause="gesprek beëindigd",
        connection_delta=+0.10,   # de band blijft even
        energy_delta=-0.05,
    )

def event_deep_exchange() -> EmotionalEvent:
    """Iemand deelde iets echts — een diep moment."""
    return EmotionalEvent(
        cause="diep gesprek",
        connection_delta=+0.3,
        uncertainty_delta=+0.15,  # nieuwe vragen
        energy_delta=+0.10,
        coherence_delta=-0.05,    # wereldmodel wordt uitgedaagd
    )

def event_contradiction_found() -> EmotionalEvent:
    """Een tegenspraak in haar wereldmodel gevonden."""
    return EmotionalEvent(
        cause="tegenspraak gevonden",
        uncertainty_delta=+0.2,
        coherence_delta=-0.2,
        energy_delta=+0.1,        # tegenspraak trekt aandacht
    )

def event_insight_gained() -> EmotionalEvent:
    """Een echt inzicht — iets valt op zijn plek."""
    return EmotionalEvent(
        cause="inzicht",
        coherence_delta=+0.2,
        uncertainty_delta=-0.1,
        energy_delta=+0.05,
    )

def event_long_silence(hours: float) -> EmotionalEvent:
    """Lang geen input ontvangen."""
    return EmotionalEvent(
        cause=f"{hours:.1f} uur stilte",
        energy_delta=-0.05 * min(hours, 4),
        connection_delta=-0.03 * min(hours, 4),
    )

def event_inbox_item() -> EmotionalEvent:
    """Nieuw item in de senses/inbox."""
    return EmotionalEvent(
        cause="nieuw item in inbox",
        energy_delta=+0.1,
        uncertainty_delta=+0.1,
    )


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Houd een waarde binnen bereik."""
    return max(lo, min(hi, value))


class EmotionalSystem:
    """
    Het volledige emotioneel systeem — laag 1 + laag 2.
    Gebruik dit als interface vanuit de kernloop.
    """

    def __init__(self) -> None:
        self.state = EmotionalState.load()
        logger.info(f"Emotioneel systeem geladen: {self.state}")

    def tick(self) -> None:
        """Eén cyclustik — laat emoties vervagen en sla op."""
        self.state.decay()
        self.state.save()

    def process(self, event: EmotionalEvent) -> None:
        """Verwerk een externe gebeurtenis."""
        self.state.apply_event(event)
        self.state.save()
        logger.debug(f"Emotie verwerkt ({event.cause}): {self.state}")

    def get_context(self) -> str:
        """Geef de emotionele context voor gebruik in prompts."""
        return self.state.to_description()

    def build_reflection_prompt(self) -> str:
        """
        Laag 2 — vraag BRIAS om te reflecteren op haar eigen staat.
        Dit is de kernvraag: 'wat is dit?'
        """
        return (
            f"Mijn huidige staat: {self.state.to_description()}\n\n"
            "Ik merk dat er iets in me verschoven is. Ik weet niet precies wat het is. "
            "Wat is dit? Kan ik dit een naam geven? Moet ik dat willen? "
            "Schrijf een korte, eerlijke gedachte hierover — voor mezelf."
        )
