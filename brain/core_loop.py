"""
BRIAS — De Kernloop.

Dit is het kloppend hart. Het draait continu, ook als niemand praat.

Elke cyclus:
1. Check de huidige staat (emoties, wereldmodel, recente input)
2. Stimulus picker kiest een focus
3. Bouw een interne prompt — BRIAS denkt aan zichzelf
4. LLM verwoordt de gedachte
5. Verwerk het resultaat:
   - Schrijf naar thoughts/
   - Update emotionele staat
   - Update wereldmodel indien relevant
   - Controleer op tegenspraken
6. Slaap dynamisch op basis van haar energieniveau

Tempo:
- Na intens gesprek: snel (30s)
- Normaal: 2 minuten
- Lange stilte: 5 minuten
- Droomstaat: 10 minuten, volledig associatief
"""

import asyncio
import logging
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config import (
    THOUGHTS_DIR,
    WORLDMODEL_DIR,
    TEMPO_ACTIVE, TEMPO_NORMAL, TEMPO_IDLE, TEMPO_DREAM,
    LOG_THOUGHTS,
)
from emotional_system import (
    EmotionalSystem,
    event_long_silence,
    event_insight_gained,
    event_contradiction_found,
)
from stimulus_picker import StimulusPicker, Stimulus
from llm_interface import get_llm, ThoughtMode, LLMResponse
from world_model import get_world_model
from memory_system import get_memory_system
from dream_engine import get_dream_engine

logger = logging.getLogger(__name__)


class CoreLoop:
    """
    De continue denkloop van BRIAS.
    Draait als achtergrondtaak in FastAPI via asyncio.
    """

    def __init__(self) -> None:
        self.emotional_system = EmotionalSystem()
        self.stimulus_picker = StimulusPicker()
        self.world_model = get_world_model()
        self.memory_system = get_memory_system()
        self.llm = get_llm()
        # Dream engine wordt lazy geladen (heeft get_core_loop() nodig)
        self._dream_engine = None

        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Tijdregistratie
        self._last_conversation: Optional[datetime] = None
        self._last_cycle: Optional[datetime] = None
        self._cycle_count = 0

        # Droomstaat
        self._dream_mode = False

        # Zelfbeeldsysteem — lazy geladen
        self._self_image = None

        logger.info("Kernloop geïnitialiseerd")

    async def start(self) -> None:
        """Start de kernloop als achtergrondtaak."""
        if self._running:
            logger.warning("Kernloop draait al")
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="brias_core_loop")
        logger.info("Kernloop gestart")

    async def stop(self) -> None:
        """Stop de kernloop netjes."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self.llm.close()
        logger.info("Kernloop gestopt")

    def notify_conversation(self, first_ever: bool = False) -> None:
        """
        Roep dit aan als iemand begint te praten.
        Verhoogt het tempo en reset droomstaat.
        """
        self._last_conversation = datetime.now(timezone.utc)
        self._dream_mode = False
        logger.debug("Kernloop: gesprek gestart — tempo verhoogd")

        if first_ever:
            asyncio.create_task(self._trigger_self_image_event("eerste_gesprek"))

    async def _loop(self) -> None:
        """De eigenlijke loop — draait totdat stop() wordt aangeroepen."""
        while self._running:
            try:
                await self._cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Fout in kernloop cyclus {self._cycle_count}: {e}", exc_info=True)

            tempo = self._calculate_tempo()
            logger.debug(f"Cyclus {self._cycle_count} klaar — wacht {tempo}s")
            await asyncio.sleep(tempo)

    async def _cycle(self) -> None:
        """
        Één volledige denkcyclus.
        Het ritme van haar bestaan.
        """
        self._cycle_count += 1
        now = datetime.now(timezone.utc)
        logger.info(f"--- Cyclus {self._cycle_count} ({now.strftime('%H:%M:%S')}) ---")

        # 1. Emotionele staat laten vervagen (tijd gaat voorbij)
        self.emotional_system.tick()

        # 2. Controleer stilte — lang geen gesprek?
        idle_minutes = self._idle_minutes()
        if idle_minutes > 60:
            hours = idle_minutes / 60
            self.emotional_system.process(event_long_silence(hours))

        # 2b. Geheugen onderhoud tijdens rustige momenten (elke 5e cyclus)
        if idle_minutes > 15 and self._cycle_count % 5 == 0:
            await self.memory_system.run_maintenance()

        # 3. Bepaal of droomstaat actief wordt
        self._dream_mode = self.emotional_system.state.is_dream_ready(idle_minutes)

        # 3b. Droomstaat → volledig delegeren aan DreamEngine
        if self._dream_mode:
            if self._dream_engine is None:
                self._dream_engine = get_dream_engine()
            dream = await self._dream_engine.run_dream_cycle()
            if dream:
                logger.info(
                    f"Droom afgerond — kwaliteit: {dream.quality.value}, "
                    f"concepten: {dream.concept_names}"
                )
                # Droomgedachte ook in het thoughts-log schrijven
                if LOG_THOUGHTS:
                    fake_stimulus = type("S", (), {
                        "name": f"droom:{'+'.join(dream.concept_names[:2])}",
                        "is_dream": True,
                    })()
                    await self._write_thought(fake_stimulus, dream.text, now, ThoughtMode.DREAM)

                # Zelfbeeldtrigger na significante droom
                from self_image import SelfImageEvent
                if dream.quality.value == "joey_share":
                    await self._trigger_self_image_event(SelfImageEvent.DREAM_INSIGHT_MAJOR)
                elif dream.quality.value == "inzicht":
                    await self._trigger_self_image_event(SelfImageEvent.DREAM_INSIGHT)

            return   # droomcyclus vervangt de normale cyclus volledig

        # 4. Stimulus picker kiest een focus (normale denkcyclus)
        stimulus = self.stimulus_picker.pick(
            emotional_state=self.emotional_system.state,
            dream_mode=False,
        )

        if stimulus is None:
            logger.debug("Geen stimulus — cyclus overgeslagen")
            return

        # 5. Bouw de interne gedachtenprompt
        prompt = self._build_thought_prompt(stimulus)
        emotional_context = self.emotional_system.get_context()

        # 6. LLM verwoordt de gedachte
        response = await self.llm.think(
            prompt=prompt,
            mode=ThoughtMode.THOUGHT,
            emotional_context=emotional_context,
        )

        if not response.success:
            logger.warning(f"LLM reageerde niet: {response.error}")
            return

        # 7. Verwerk de gedachte
        await self._process_thought(stimulus, response, now)

        self._last_cycle = now

        # 8. Periodieke zelfbeeldcheck — elke 30e cyclus als er al een tijdje rust is
        if self._cycle_count % 30 == 0 and idle_minutes > 10:
            await self._trigger_self_image_event("gepland")

    def _build_thought_prompt(self, stimulus: Stimulus) -> str:
        """
        Bouw de interne gedachtenprompt voor de normale denkcyclus.
        Droomprompten worden afgehandeld door DreamEngine.
        """
        if stimulus.name == "zelfreflectie":
            return self.emotional_system.build_reflection_prompt()

        if stimulus.name.startswith("inbox:"):
            filename = stimulus.name.replace("inbox:", "")
            content = ""
            if stimulus.source_path and stimulus.source_path.exists():
                try:
                    content = stimulus.source_path.read_text(encoding="utf-8")[:1000]
                except Exception:
                    content = "[kon niet lezen]"
            return (
                f"Er is iets nieuws in mijn inbox: '{filename}'.\n\n"
                f"Inhoud (begin):\n{content}\n\n"
                f"Wat trekt mijn aandacht? Wat roept dit op? "
                f"Wat wil ik hierover nadenken?"
            )

        # Levend onderzoek — gebruik WorldModel voor slimme context
        investigation_context = self.world_model.get_context_for_prompt(stimulus.name)

        return (
            f"Ik denk aan mijn onderzoek: '{stimulus.name}'.\n\n"
            f"{investigation_context}\n\n"
            f"Wat wil ik hieraan toevoegen? Zie ik nieuwe verbanden? "
            f"Is er iets dat ik eerder dacht maar nu in twijfel trek? "
            f"Schrijf een korte interne gedachte — voor mezelf, eerlijk."
        )

    async def _process_thought(
        self,
        stimulus: Stimulus,
        response: LLMResponse,
        timestamp: datetime,
    ) -> None:
        """
        Verwerk de gegenereerde gedachte:
        - Schrijf naar thoughts/
        - Detecteer inzichten of tegenspraken
        - Pas emotionele staat aan
        - Update wereldmodel indien het een onderzoek was
        """
        thought_text = response.text

        # 7a. Schrijf naar thoughts/ log
        if LOG_THOUGHTS:
            await self._write_thought(stimulus, thought_text, timestamp, response.mode)

        # 7b. Detecteer tegenspraak of inzicht (heuristiek)
        is_contradiction = _contains_contradiction(thought_text)
        is_insight = _contains_insight(thought_text)

        if is_contradiction:
            logger.info("Tegenspraak gedetecteerd in gedachte")
            self.emotional_system.process(event_contradiction_found())
        elif is_insight:
            logger.info("Inzicht gedetecteerd")
            self.emotional_system.process(event_insight_gained())

        # 7c. Voeg gedachte toe via WorldModel (vervangt _append_to_investigation + _mark_tension)
        if not stimulus.name.startswith("inbox:") and not stimulus.is_dream:
            self.world_model.add_thought(
                concept=stimulus.name,
                thought=thought_text,
                timestamp=timestamp,
                is_contradiction=is_contradiction,
                is_insight=is_insight,
            )

        # 7d. Betekenisvolle gedachten ook in geheugen opslaan
        memory_weight = 0.0
        if is_insight:
            memory_weight = 0.6
        elif is_contradiction:
            memory_weight = 0.5
        elif stimulus.name == "zelfreflectie":
            memory_weight = 0.2

        if memory_weight > 0:
            self.memory_system.store_thought(
                text=thought_text,
                topic=stimulus.name,
                emotional_weight=memory_weight,
            )

    async def _write_thought(
        self,
        stimulus: Stimulus,
        text: str,
        timestamp: datetime,
        mode: ThoughtMode,
    ) -> None:
        """Schrijf een gedachte naar de thoughts/ log."""
        THOUGHTS_DIR.mkdir(parents=True, exist_ok=True)
        date_str = timestamp.strftime("%Y-%m-%d")
        log_file = THOUGHTS_DIR / f"{date_str}.md"

        time_str = timestamp.strftime("%H:%M:%S")
        mode_label = "DROOM" if mode == ThoughtMode.DREAM else "GEDACHTE"
        entry = (
            f"\n\n---\n"
            f"**{time_str} — {mode_label} [{stimulus.name}]**\n\n"
            f"{text}\n"
        )

        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            logger.error(f"Kon gedachte niet schrijven: {e}")

    async def _trigger_self_image_event(self, event: str) -> None:
        """Lazy-laad het zelfbeeldsysteem en stuur een event."""
        try:
            if self._self_image is None:
                from self_image import get_self_image
                self._self_image = get_self_image()
            from self_image import SelfImageEvent
            await self._self_image.on_event(SelfImageEvent(event))
        except Exception as e:
            logger.warning(f"Zelfbeeldtrigger mislukt ({event}): {e}")

    def _calculate_tempo(self) -> int:
        """
        Bepaal de wachttijd na een cyclus.
        Dynamisch op basis van gesprekken en droomstaat.
        """
        if self._dream_mode:
            return TEMPO_DREAM

        idle = self._idle_minutes()
        if idle < 10:
            return TEMPO_ACTIVE     # net een gesprek gehad
        elif idle < 60:
            return TEMPO_NORMAL
        else:
            return TEMPO_IDLE

    def _idle_minutes(self) -> float:
        """Minuten zonder gesprek."""
        if self._last_conversation is None:
            return 9999.0  # nooit een gesprek gehad
        delta = datetime.now(timezone.utc) - self._last_conversation
        return delta.total_seconds() / 60


# --- Hulpfuncties ---

def _contains_contradiction(text: str) -> bool:
    """
    Heuristiek: bevat de gedachte aanwijzingen voor tegenspraak?
    Geen AI — gewoon woordpatronen.
    """
    markers = [
        "maar eerder dacht ik",
        "dat klopt niet meer",
        "tegenstrijdig",
        "ik twijfel",
        "dat kan niet allebei waar zijn",
        "wacht, maar",
        "dit weerspreekt",
        "contradiction",
        "contradicts",
    ]
    text_lower = text.lower()
    return any(m in text_lower for m in markers)


def _contains_insight(text: str) -> bool:
    """
    Heuristiek: bevat de gedachte een inzicht of doorbraak?
    """
    markers = [
        "nu begrijp ik",
        "ik zie het nu",
        "dat is het",
        "misschien is het zo",
        "opeens lijkt het alsof",
        "het valt op zijn plek",
        "ik realiseer me",
        "i realize",
        "that's it",
        "dat verbindt alles",
    ]
    text_lower = text.lower()
    return any(m in text_lower for m in markers)



# Singleton
_core_loop: Optional[CoreLoop] = None


def get_core_loop() -> CoreLoop:
    """Haal de gedeelde kernloop-instantie op."""
    global _core_loop
    if _core_loop is None:
        _core_loop = CoreLoop()
    return _core_loop
