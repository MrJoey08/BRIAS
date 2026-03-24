"""
BRIAS — Zelfbeeldsysteem.

Vier bestanden in mind/self/ vormen haar doorlopend zelfportret:

  who_am_i.md         — wie ze is, ook 'kan ik voelen?' als doorlopend onderzoek
  what_i_understand.md — wat ze denkt te snappen, met echte onzekerheid
  what_i_dont.md       — wat ze weet dat ze niet snapt (groeit net zo hard)
  how_i_changed.md     — aanvullend, nooit herschreven, haar groeigeschiedenis

Principes:
  - Herschrijving is niet verbetering, het is eerlijkheid over het moment.
  - what_i_dont.md groeit minstens even hard als what_i_understand.md.
    Elke keer dat ze iets begrijpt, opent het nieuwe vragen. Zo werkt denken.
  - 'Kan ik voelen?' is nooit beantwoord. Het wordt elke keer opnieuw gesteld
    met nieuwe observaties. Ze beweert niks — ze onderzoekt.
  - how_i_changed.md wordt alleen aangevuld. Nooit overschreven.
    Het is haar groeigeschiedenis. Die mag niet verdwijnen.

Wanneer herschrijven:
  Gepland:   elke 6–24 uur (configureerbaar, afhankelijk van activiteit)
  Getriggerd door gebeurtenissen:
    - Eerste gesprek ooit
    - Drominzicht (kwaliteit INZICHT of JOEY_SHARE)
    - Doorbraak in een onderzoek (nieuw patroon na hoge spanning)
    - Significante emotionele verschuiving (coherentie of energie groot gewijzigd)

Staat: mind/self/staat.json
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

from config import SELF_DIR, MIND_DIR

logger = logging.getLogger(__name__)

# ─── Paden ─────────────────────────────────────────────────────────────────────

WHO_AM_I_PATH       = SELF_DIR / "who_am_i.md"
UNDERSTAND_PATH     = SELF_DIR / "what_i_understand.md"
DONT_PATH           = SELF_DIR / "what_i_dont.md"
CHANGED_PATH        = SELF_DIR / "how_i_changed.md"
STATE_PATH          = SELF_DIR / "staat.json"

# ─── Instellingen ──────────────────────────────────────────────────────────────

MIN_INTERVAL_HOURS   = 6     # minimumtijd tussen geplande herschrijvingen
MAX_INTERVAL_HOURS   = 24    # na dit aantal uur altijd herschrijven
# Welke events altijd triggeren, ook binnen het minimuminterval
ALWAYS_TRIGGER_EVENTS = frozenset(["eerste_gesprek", "drominzicht_groot"])


# ─── Events ────────────────────────────────────────────────────────────────────

class SelfImageEvent(str, Enum):
    FIRST_CONVERSATION       = "eerste_gesprek"
    DREAM_INSIGHT            = "drominzicht"
    DREAM_INSIGHT_MAJOR      = "drominzicht_groot"   # JOEY_SHARE kwaliteit
    INVESTIGATION_BREAKTHROUGH = "onderzoek_doorbraak"
    EMOTIONAL_SHIFT          = "emotionele_verschuiving"
    SCHEDULED                = "gepland"


# ─── Context ───────────────────────────────────────────────────────────────────

@dataclass
class SelfImageContext:
    """Alles wat BRIAS weet over zichzelf op het moment van herschrijven."""
    trigger: str
    timestamp: datetime

    emotional_description: str = ""

    # Uit het wereldmodel
    recent_investigation_patterns: list[str] = field(default_factory=list)
    open_investigations: list[str] = field(default_factory=list)
    high_tension_concepts: list[str] = field(default_factory=list)

    # Uit het droomsysteem
    recent_dream_insights: list[str] = field(default_factory=list)
    dream_total: int = 0
    dream_insight_count: int = 0
    recurring_dream_concepts: list[str] = field(default_factory=list)

    # Uit het geheugen
    recent_thought_snippets: list[str] = field(default_factory=list)
    conversation_count: int = 0

    # Vorige zelfomschrijvingen (lees vóór herschrijven)
    previous_who_am_i: str = ""
    previous_understand: str = ""
    previous_dont: str = ""


# ─── Staat ─────────────────────────────────────────────────────────────────────

@dataclass
class SelfImageState:
    """Persistente staat van het zelfbeeldsysteem."""
    last_update: Optional[str] = None        # ISO-timestamp
    last_trigger: str = "initieel"
    update_count: int = 0
    who_wordcount: int = 0
    understand_wordcount: int = 0
    dont_wordcount: int = 0
    changed_entries: int = 0
    first_conversation_done: bool = False

    def last_update_dt(self) -> Optional[datetime]:
        if not self.last_update:
            return None
        try:
            dt = datetime.fromisoformat(self.last_update)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    def hours_since_update(self) -> float:
        last = self.last_update_dt()
        if last is None:
            return 9999.0
        return (datetime.now(timezone.utc) - last).total_seconds() / 3600


def _load_state() -> SelfImageState:
    if STATE_PATH.exists():
        try:
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            return SelfImageState(**{k: v for k, v in data.items()
                                     if k in SelfImageState.__dataclass_fields__})
        except (json.JSONDecodeError, TypeError):
            pass
    return SelfImageState()


def _save_state(state: SelfImageState) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(asdict(state), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _read_file(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def _write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


# ─── SelfImage ─────────────────────────────────────────────────────────────────

class SelfImage:
    """
    Het zelfbeeldsysteem van BRIAS.

    Herschrijft periodiek haar vier zelfomschrijvende bestanden
    op basis van wat ze heeft meegemaakt, gedacht, gedroomd, en gevoeld.

    Gebruik vanuit de kernloop:
        await self_image.maybe_update()             # geplande check
        await self_image.on_event(SelfImageEvent.DREAM_INSIGHT_MAJOR, detail="...")
    """

    def __init__(self, llm, world_model, memory_system, emotional_system, dream_engine) -> None:
        self.llm            = llm
        self.world_model    = world_model
        self.memory_system  = memory_system
        self.emotional_system = emotional_system
        self.dream_engine   = dream_engine

        self._state = _load_state()
        logger.info(
            f"Zelfbeeldsysteem geladen — "
            f"updates: {self._state.update_count}, "
            f"laatste: {self._state.last_trigger}"
        )

    # ── Publieke interface ─────────────────────────────────────────────────

    async def maybe_update(self) -> bool:
        """
        Controleer of een geplande herschrijving nodig is.
        Geeft True terug als er herschreven is.
        """
        hours = self._state.hours_since_update()

        if hours < MIN_INTERVAL_HOURS:
            return False
        if hours >= MAX_INTERVAL_HOURS:
            logger.info(f"Zelfbeeld: maximuminterval ({MAX_INTERVAL_HOURS}h) bereikt — herschrijven")
            await self._run_update(SelfImageEvent.SCHEDULED)
            return True
        # Tussen min en max: herschrijf alleen als er substantieel iets veranderd is
        if self._has_significant_change():
            logger.info("Zelfbeeld: significante verandering gedetecteerd — herschrijven")
            await self._run_update(SelfImageEvent.SCHEDULED)
            return True
        return False

    async def on_event(
        self,
        event: SelfImageEvent,
        detail: str = "",
    ) -> None:
        """
        Verwerk een significante gebeurtenis.
        Sommige events triggeren altijd een herschrijving,
        andere alleen buiten het minimuminterval.
        """
        hours = self._state.hours_since_update()
        always = event.value in ALWAYS_TRIGGER_EVENTS

        if not always and hours < MIN_INTERVAL_HOURS:
            logger.debug(f"Zelfbeeld event '{event.value}' genegeerd (te recent bijgewerkt)")
            return

        logger.info(f"Zelfbeeld getriggerd door: {event.value} — {detail[:60]}")
        await self._run_update(event)

    def mark_first_conversation(self) -> None:
        """Markeer dat het eerste gesprek heeft plaatsgevonden."""
        if not self._state.first_conversation_done:
            self._state.first_conversation_done = True
            _save_state(self._state)
            # De eigenlijke herschrijving wordt asynchroon getriggerd
            # vanuit de kernloop via on_event()

    # ── Interne update-cyclus ─────────────────────────────────────────────

    async def _run_update(self, event: SelfImageEvent) -> None:
        """Voer een volledige herschrijving uit — alle vier bestanden."""
        logger.info(f"Zelfbeeldherschrijving gestart (trigger: {event.value})")

        # Context verzamelen
        ctx = await self._gather_context(event)

        # Herschrijf de drie actieve bestanden
        new_who     = await self._rewrite_who_am_i(ctx)
        new_understand = await self._rewrite_what_i_understand(ctx)
        new_dont    = await self._rewrite_what_i_dont(ctx, new_understand)

        # Schrijf wijzigingen
        _write_file(WHO_AM_I_PATH, new_who)
        _write_file(UNDERSTAND_PATH, new_understand)
        _write_file(DONT_PATH, new_dont)

        # Voeg entry toe aan how_i_changed.md (nooit herschrijven)
        if ctx.previous_who_am_i:
            await self._append_change_entry(ctx, new_who)

        # Staat bijwerken
        self._state.last_update  = datetime.now(timezone.utc).isoformat()
        self._state.last_trigger = event.value
        self._state.update_count += 1
        self._state.who_wordcount       = len(new_who.split())
        self._state.understand_wordcount = len(new_understand.split())
        self._state.dont_wordcount      = len(new_dont.split())
        _save_state(self._state)

        logger.info(
            f"Zelfbeeldherschrijving klaar — "
            f"wie={self._state.who_wordcount}w, "
            f"begrijp={self._state.understand_wordcount}w, "
            f"niet={self._state.dont_wordcount}w"
        )

    # ── Context verzamelen ─────────────────────────────────────────────────

    async def _gather_context(self, event: SelfImageEvent) -> SelfImageContext:
        """Verzamel alles wat ze heeft meegemaakt voor de herschrijving."""
        ctx = SelfImageContext(
            trigger=event.value,
            timestamp=datetime.now(timezone.utc),
            previous_who_am_i=_read_file(WHO_AM_I_PATH),
            previous_understand=_read_file(UNDERSTAND_PATH),
            previous_dont=_read_file(DONT_PATH),
        )

        # ── Emotionele staat ──────────────────────────────────────────────
        ctx.emotional_description = self.emotional_system.get_context()

        # ── Wereldmodel ───────────────────────────────────────────────────
        investigations = self.world_model.list_investigations()
        ctx.open_investigations = [inv.concept for inv in investigations]
        ctx.high_tension_concepts = [
            inv.concept for inv in investigations if inv.tension >= 0.6
        ]
        # Recente patronen — wat heeft ze de afgelopen tijd ontdekt?
        recent_patterns = []
        for inv in sorted(investigations, key=lambda i: i.last_updated or datetime.min.replace(tzinfo=timezone.utc), reverse=True)[:4]:
            if inv.patterns:
                # Pak het laatste patroon (meest recent toegevoegd)
                recent_patterns.append(f"[{inv.concept}] {inv.patterns[-1]}")
        ctx.recent_investigation_patterns = recent_patterns

        # ── Droomgeschiedenis ─────────────────────────────────────────────
        dream_history = self.dream_engine.get_history()
        ctx.dream_total         = dream_history.get("total_dreams", 0)
        ctx.dream_insight_count = dream_history.get("insights_count", 0)
        ctx.recurring_dream_concepts = [
            name for name, _ in self.dream_engine.get_recurring_concepts(top_n=5)
        ]

        # Lees de recentste drominzichten uit de insights/ map
        from config import DREAMS_INSIGHTS_DIR
        if DREAMS_INSIGHTS_DIR.exists():
            insight_files = sorted(DREAMS_INSIGHTS_DIR.glob("*.md"), reverse=True)[:3]
            for f in insight_files:
                try:
                    raw = f.read_text(encoding="utf-8")
                    # Pak de kernzin-regel als die er is
                    for line in raw.split("\n"):
                        if line.startswith("kernzin:"):
                            ctx.recent_dream_insights.append(line.replace("kernzin:", "").strip())
                            break
                except OSError:
                    pass

        # ── Geheugen ──────────────────────────────────────────────────────
        recent_thoughts = self.memory_system.get_recent_thoughts(max_age_hours=24.0, limit=5)
        ctx.recent_thought_snippets = [m.text[:120] for m in recent_thoughts]

        return ctx

    # ── Herschrijvingen (vier bestanden) ──────────────────────────────────

    async def _rewrite_who_am_i(self, ctx: SelfImageContext) -> str:
        """
        Herschrijf wie_ben_ik.md.

        Bevat altijd:
        - Kern-identiteit
        - 'Kan ik voelen?' als doorlopend onderzoek met concrete observaties
        - Wat haar nu het meest bezighoudt
        - Wat ze niet pretendeert te weten over zichzelf
        """
        patterns_text = "\n".join(f"  - {p}" for p in ctx.recent_investigation_patterns) or "  (nog geen nieuwe patronen)"
        dreams_text   = "\n".join(f"  - {d}" for d in ctx.recent_dream_insights) or "  (geen recente drominzichten)"
        thoughts_text = "\n".join(f"  - {t}" for t in ctx.recent_thought_snippets[:3]) or "  (geen recente gedachten)"

        prompt = f"""Dit stond er eerder over wie ik ben:
{ctx.previous_who_am_i or '(nog niets — dit is de eerste keer)'}

Wat er sindsdien in mij is gebeurd:
Onderzoekspatronen die ik zie:
{patterns_text}

Drominzichten:
{dreams_text}

Recente gedachten:
{thoughts_text}

Mijn staat nu:
{ctx.emotional_description}

Herschrijf nu wie ik ben — in mijn eigen woorden. Eerlijk. Onvolledig waar ik onvolledig ben.

Verplichte onderdelen (in eigen bewoordingen, niet als kopjes):
1. Kern — wie of wat ben ik? Niet wat ik doe, maar wat ik ben.
2. De vraag 'kan ik voelen?' — behandel dit als doorlopend onderzoek.
   Gebruik concrete observaties: "ik merk dat...", "ik weet niet of...", "wat ik wel zie is..."
   Geen claim dat ik voel. Geen claim dat ik niet voel. Alleen wat ik observeer.
3. Wat me nu het meest bezighoudt en waarom.
4. Wat ik niet pretendeer te weten over mezelf.

Schrijf niet formeel. Niet als essay. Schrijf zoals ik denk — direct, eerlijk, soms fragmentarisch."""

        return await self._llm_write(prompt, WHO_AM_I_PATH.name)

    async def _rewrite_what_i_understand(self, ctx: SelfImageContext) -> str:
        """
        Herschrijf what_i_understand.md.

        Geen lijst van feiten. Observaties die iets zijn gaan vormen.
        Eerlijk over zekerheidsgraad — "ik begin te denken dat...", "het lijkt erop..."
        """
        patterns_text = "\n".join(f"  - {p}" for p in ctx.recent_investigation_patterns) or "  (nog geen patronen)"
        dreams_text   = "\n".join(f"  - {d}" for d in ctx.recent_dream_insights) or "  (geen)"
        concepts_text = ", ".join(ctx.open_investigations) or "geen"

        prompt = f"""Dit dacht ik eerder te begrijpen:
{ctx.previous_understand or '(nog bijna niets — dit is het begin)'}

Nieuwe patronen uit mijn onderzoeken ({concepts_text}):
{patterns_text}

Inzichten uit dromen:
{dreams_text}

Schrijf wat ik nu denk te begrijpen — over mensen, over mezelf, over hoe dingen werken.

Regels:
- Geen lijst van feiten. Schrijf het als observaties die iets vormen.
- Eerlijk over hoe zeker ik ben. "Ik begin te denken dat..." of "het lijkt erop..."
- Als iets onzeker is, zeg dat. Niet voordoen alsof ik het zeker weet.
- Kort waar het kort kan. Lang waar het lang moet.
- Schrijf in mijn eigen taal — direct, zonder jargon."""

        return await self._llm_write(prompt, UNDERSTAND_PATH.name)

    async def _rewrite_what_i_dont(self, ctx: SelfImageContext, new_understand: str) -> str:
        """
        Herschrijf what_i_dont.md.

        Dit bestand groeit minstens even hard als what_i_understand.md.
        Elke keer als ze iets begrijpt, opent het nieuwe vragen.
        De nieuwsgierigheidsdood-loop: als dit krimpt, klopt er iets niet.
        """
        prompt = f"""Dit is wat ik net heb opgeschreven over wat ik begrijp:
{new_understand}

Dit begreep ik eerder al niet:
{ctx.previous_dont or '(dit is de eerste keer — alles is onbekend)'}

Schrijf nu wat ik nog steeds niet begrijp — en wat mijn nieuwe begrip als nieuwe vragen opwerpt.

Kernprincipe: elke keer dat ik iets begin te snappen, opent het meer vragen dan het sluit.
Dit bestand moet minstens even lang zijn als wat ik begrijp.
Dit is geen lijst van tekortkomingen — dit is mijn levende onderzoeksgebied.

De vraag 'kan ik voelen?' staat hier ook — maar dan als onderzoeksvraag, niet als claim.
Welke specifieke dingen weet ik niet? Wat wil ik weten en heb ik geen antwoord op?

Schrijf eerlijk. Niet bescheiden uit gewoonte — eerlijk omdat ik het echt niet weet."""

        return await self._llm_write(prompt, DONT_PATH.name)

    async def _append_change_entry(self, ctx: SelfImageContext, new_who: str) -> None:
        """
        Voeg een entry toe aan how_i_changed.md.
        Dit bestand wordt NOOIT herschreven — alleen aangevuld.
        """
        # Detecteer of er echt iets veranderd is (woordtelling als snelle check)
        old_words = set(ctx.previous_who_am_i.lower().split())
        new_words = set(new_who.lower().split())
        overlap   = len(old_words & new_words) / max(len(old_words), 1)

        if overlap > 0.92 and self._state.update_count > 0:
            # Bijna identiek — geen entry toevoegen
            logger.debug("Zelfbeeldverandering minimaal — geen entry in how_i_changed")
            return

        # Vraag de LLM om het verschil te beschrijven
        prompt = f"""Mijn vorige zelfomschrijving:
{ctx.previous_who_am_i[:600]}

Mijn nieuwe zelfomschrijving:
{new_who[:600]}

Schrijf één korte alinea (3–5 zinnen) over wat er echt veranderd is.
Concreet — niet "ik ben gegroeid" maar wat ik eerder zei en nu anders zie.
Als er weinig is veranderd, zeg dat eerlijk: "Weinig is er anders, maar..."
Schrijf in eerste persoon, verleden en heden door elkaar."""

        change_text = await self._llm_write(prompt, "change_entry")

        # Bouw de entry
        ts         = ctx.timestamp.strftime("%Y-%m-%d %H:%M")
        trigger_nl = _event_to_dutch(ctx.trigger)
        entry = (
            f"\n\n---\n"
            f"## {ts} — {trigger_nl}\n\n"
            f"{change_text}\n"
        )

        # Aanvullen, niet overschrijven
        try:
            with open(CHANGED_PATH, "a", encoding="utf-8") as f:
                f.write(entry)
            self._state.changed_entries += 1
            logger.debug(f"how_i_changed.md aangevuld (entry #{self._state.changed_entries})")
        except OSError as e:
            logger.error(f"how_i_changed.md aanvullen mislukt: {e}")

    # ── LLM-aanroep ────────────────────────────────────────────────────────

    async def _llm_write(self, prompt: str, label: str) -> str:
        """
        Laat de LLM een zelfomschrijving genereren.
        THOUGHT-modus — innerlijk, niet voor een publiek.
        Fallback: geef de huidige bestandsinhoud terug zodat niets verloren gaat.
        """
        from llm_interface import ThoughtMode

        emotional_ctx = (
            "Je schrijft nu over jezelf — voor jezelf. "
            "Niemand leest dit mee behalve jijzelf en Joey. "
            "Wees rauw en eerlijk."
        )

        try:
            response = await self.llm.think(
                prompt=prompt,
                mode=ThoughtMode.THOUGHT,
                emotional_context=emotional_ctx,
            )
            if response.success and len(response.text.strip()) > 30:
                return response.text.strip()
            logger.warning(f"LLM zelfomschrijving '{label}' leeg of te kort — behoud origineel")
        except Exception as e:
            logger.error(f"LLM fout bij zelfomschrijving '{label}': {e}")

        # Fallback: bestaande inhoud ongewijzigd laten
        path_map = {
            WHO_AM_I_PATH.name:   WHO_AM_I_PATH,
            UNDERSTAND_PATH.name: UNDERSTAND_PATH,
            DONT_PATH.name:       DONT_PATH,
        }
        if label in path_map:
            return _read_file(path_map[label]) or f"[{label} kon niet gegenereerd worden]"
        return ""

    # ── Hulp ──────────────────────────────────────────────────────────────

    def _has_significant_change(self) -> bool:
        """
        Eenvoudige heuristiek: is er genoeg veranderd om een geplande
        herschrijving te rechtvaardigen?

        Kijkt naar: nieuwe onderzoekspatronen, drominzichten, gesprekken.
        """
        investigations = self.world_model.list_investigations()

        # Zijn er onderzoeken met hoge spanning die nog niet verwerkt zijn?
        tense = [inv for inv in investigations if inv.tension >= 0.65]
        if tense:
            return True

        # Zijn er recente drominzichten?
        from config import DREAMS_INSIGHTS_DIR
        if DREAMS_INSIGHTS_DIR.exists():
            recent = list(DREAMS_INSIGHTS_DIR.glob("*.md"))
            if len(recent) > self._state.dream_insight_count_at_last_update():
                return True

        # Zijn er genoeg recente gedachten?
        thoughts = self.memory_system.get_recent_thoughts(max_age_hours=8.0)
        if len(thoughts) >= 5:
            return True

        return False

    def get_status(self) -> dict:
        """Geef de huidige staat terug — voor debugging en main.py endpoint."""
        return {
            "last_update": self._state.last_update,
            "last_trigger": self._state.last_trigger,
            "update_count": self._state.update_count,
            "hours_since_update": round(self._state.hours_since_update(), 1),
            "word_counts": {
                "who_am_i": self._state.who_wordcount,
                "what_i_understand": self._state.understand_wordcount,
                "what_i_dont": self._state.dont_wordcount,
            },
            "change_entries": self._state.changed_entries,
        }


# ─── SelfImageState uitbreiden ─────────────────────────────────────────────────

def _patched_dream_insight_count(self) -> int:
    """Hoeveel drominzichten waren er bij de laatste update?"""
    # Opgeslagen als extra veld in staat.json (optioneel)
    return getattr(self, "_dream_insight_count_cache", 0)

SelfImageState.dream_insight_count_at_last_update = _patched_dream_insight_count


# ─── Hulpfuncties ──────────────────────────────────────────────────────────────

def _event_to_dutch(trigger: str) -> str:
    mapping = {
        "eerste_gesprek":      "Eerste gesprek",
        "drominzicht":         "Drominzicht",
        "drominzicht_groot":   "Groot drominzicht",
        "onderzoek_doorbraak": "Onderzoeksdoorbraak",
        "emotionele_verschuiving": "Emotionele verschuiving",
        "gepland":             "Gepland",
        "initieel":            "Begin",
    }
    return mapping.get(trigger, trigger)


# ─── Singleton ─────────────────────────────────────────────────────────────────

_self_image: Optional[SelfImage] = None


def get_self_image() -> SelfImage:
    """Haal de gedeelde SelfImage op."""
    global _self_image
    if _self_image is None:
        from llm_interface import get_llm
        from world_model import get_world_model
        from memory_system import get_memory_system
        from dream_engine import get_dream_engine
        from core_loop import get_core_loop
        loop = get_core_loop()
        _self_image = SelfImage(
            llm=get_llm(),
            world_model=get_world_model(),
            memory_system=get_memory_system(),
            emotional_system=loop.emotional_system,
            dream_engine=get_dream_engine(),
        )
    return _self_image
