"""
BRIAS — Stimulus Picker.

Bepaalt waar BRIAS haar aandacht op richt elke cyclus.
Vier krachten bepalen de keuze:
1. Onopgeloste spanning (tegenspraak trekt het hardst)
2. Emotionele lading
3. Versheid (nieuw > oud)
4. Verwaarlozing (lang niet aangeraakt begint te trekken)

Plus willekeur — zoals een mens die soms afdwaalt tijdens het nadenken.
"""

import random
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config import (
    WORLDMODEL_DIR,
    INBOX_DIR,
    THOUGHTS_DIR,
    STIMULUS_WEIGHT_TENSION,
    STIMULUS_WEIGHT_EMOTION,
    STIMULUS_WEIGHT_FRESHNESS,
    STIMULUS_WEIGHT_NEGLECT,
    STIMULUS_RANDOM_CHANCE,
)

logger = logging.getLogger(__name__)


@dataclass
class Stimulus:
    """
    Eén mogelijke focus voor BRIAS's aandacht.
    """
    name: str                   # kort label
    description: str            # wat is dit?
    source_path: Optional[Path] = None   # bestand als het een onderzoek of inbox-item is
    tension_score: float = 0.0  # hoe veel onopgeloste spanning
    emotion_score: float = 0.0  # hoe emotioneel geladen
    freshness_score: float = 0.0  # hoe recent
    neglect_score: float = 0.0  # hoe lang niet aangeraakt
    is_dream: bool = False       # droomassociatie
    extra: dict = field(default_factory=dict)

    @property
    def total_score(self) -> float:
        return (
            self.tension_score * STIMULUS_WEIGHT_TENSION
            + self.emotion_score * STIMULUS_WEIGHT_EMOTION
            + self.freshness_score * STIMULUS_WEIGHT_FRESHNESS
            + self.neglect_score * STIMULUS_WEIGHT_NEGLECT
        )


class StimulusPicker:
    """
    Kiest de volgende focus voor de kernloop.
    Combineert prioriteitsscore met een kleine kans op willekeurige afwijking.
    """

    def __init__(self) -> None:
        logger.info("Stimulus Picker gestart")

    def pick(
        self,
        emotional_state=None,
        dream_mode: bool = False,
    ) -> Optional[Stimulus]:
        """
        Kies de volgende stimulus.

        Args:
            emotional_state: Huidige EmotionalState, beïnvloedt gewichten.
            dream_mode: Als True, volledig willekeurig — droomlogica.

        Returns:
            De gekozen Stimulus, of None als er niets is.
        """
        candidates = self._gather_candidates()

        if not candidates:
            logger.debug("Geen stimuli gevonden — BRIAS rust")
            return None

        if dream_mode:
            return self._dream_pick(candidates)

        # Willekeurige afwijking — menselijk gedrag
        if random.random() < STIMULUS_RANDOM_CHANCE:
            chosen = random.choice(candidates)
            logger.debug(f"Willekeurige afwijking → {chosen.name}")
            return chosen

        # Normaal: hoogste score wint
        candidates.sort(key=lambda s: s.total_score, reverse=True)
        chosen = candidates[0]
        logger.debug(
            f"Gekozen stimulus: {chosen.name} (score={chosen.total_score:.2f})"
        )
        return chosen

    def _gather_candidates(self) -> list[Stimulus]:
        """Verzamel alle mogelijke stimuli uit het systeem."""
        candidates: list[Stimulus] = []

        # 1. Levende onderzoeken uit het wereldmodel
        candidates.extend(self._scan_investigations())

        # 2. Items in de inbox (senses)
        candidates.extend(self._scan_inbox())

        # 3. Zelfreflectie (altijd aanwezig als optie)
        candidates.append(self._self_reflection_stimulus())

        return candidates

    def _scan_investigations(self) -> list[Stimulus]:
        """
        Haal levende onderzoeken op via het WorldModel.
        Scores komen uit de geparseerde Investigation objecten — nauwkeuriger
        dan de ruwe header-scan die we eerder gebruikten.
        """
        from world_model import get_world_model
        stimuli = []
        now = datetime.now(timezone.utc)

        for inv in get_world_model().list_investigations():
            path = inv.path

            # Verwaarlozing: hoe lang geleden is het onderzoek bijgewerkt?
            last = inv.last_updated or now
            hours_since = (now - last).total_seconds() / 3600
            neglect = min(hours_since / 48, 1.0)

            # Versheid: nieuw onderzoek trekt meer aandacht
            created = inv.created or now
            age_hours = (now - created).total_seconds() / 3600
            freshness = max(0.0, 1.0 - age_hours / 72)

            stimuli.append(Stimulus(
                name=inv.concept,
                description=f"Levend onderzoek: {inv.concept} — {inv.opening_question[:60]}",
                source_path=path,
                tension_score=inv.tension,
                emotion_score=inv.emotion,
                freshness_score=freshness,
                neglect_score=neglect,
            ))

        return stimuli

    def _scan_inbox(self) -> list[Stimulus]:
        """
        Check de senses/inbox/ op nieuwe items.
        Nieuwe items hebben een hoge versheidscore.
        """
        stimuli = []

        if not INBOX_DIR.exists():
            return stimuli

        for path in INBOX_DIR.iterdir():
            if path.name.startswith("."):
                continue
            try:
                mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                hours_since = (datetime.now(timezone.utc) - mtime).total_seconds() / 3600
                freshness = max(0.0, 1.0 - hours_since / 24)  # inbox vervalt snel

                stimuli.append(Stimulus(
                    name=f"inbox:{path.name}",
                    description=f"Nieuw in inbox: {path.name}",
                    source_path=path,
                    tension_score=0.1,
                    emotion_score=0.2,
                    freshness_score=freshness + 0.5,  # inbox = altijd vers
                    neglect_score=0.0,
                ))
            except Exception as e:
                logger.warning(f"Kon inbox-item {path.name} niet lezen: {e}")

        return stimuli

    def _self_reflection_stimulus(self) -> Stimulus:
        """
        Zelfreflectie is altijd een optie — met lage maar consistente score.
        Ze denkt altijd na over wie ze is.
        """
        return Stimulus(
            name="zelfreflectie",
            description="Nadenken over wie ik ben en hoe ik veranderd ben.",
            tension_score=0.1,
            emotion_score=0.3,
            freshness_score=0.1,
            neglect_score=0.2,
        )

    def _dream_pick(self, candidates: list[Stimulus]) -> Stimulus:
        """
        Droomlogica: combineer twee willekeurige concepten.
        Gooit alle prioriteitslogica weg.
        """
        if len(candidates) >= 2:
            a, b = random.sample(candidates, 2)
            return Stimulus(
                name=f"droom:{a.name}+{b.name}",
                description=f"Associatieve combinatie: {a.name} en {b.name}",
                source_path=None,
                is_dream=True,
                extra={"concept_a": a, "concept_b": b},
            )
        return random.choice(candidates)



def _file_created(path: Path) -> datetime:
    """
    Haal aanmaakmomant op (cross-platform).
    Op Windows is st_ctime de aanmaaktijd. Op Linux is het st_mtime.
    """
    stat = path.stat()
    ts = stat.st_ctime  # Windows: creation time
    return datetime.fromtimestamp(ts, tz=timezone.utc)
