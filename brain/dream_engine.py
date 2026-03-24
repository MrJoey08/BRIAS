"""
BRIAS — Droommotor.

Als haar energie laag is en er lang geen input was, droomt ze.

De droommotor doet wat de kernloop niet doet:
ze gooit alle logica weg. Geen prioriteiten. Geen spanning-gewichten.
Ze pakt fragmenten uit haar onderzoeken en herinneringen en vraagt:
wat als deze dingen iets met elkaar te maken hebben?

Meestal is het ruis. Soms is het iets.

Cyclus:
  1. Concepten kiezen — 2 à 3, willekeurig maar gewogen
     - Uit actieve onderzoeken (emotionele lading telt mee)
     - Uit geheugen (geef onverwachte combinaties een kans)
     - Af en toe een wildcard — iets dat nergens op lijkt
  2. Fragmenten ophalen — korte, onvolledige brokken per concept
     (de onvolledigheid is het punt — haar hoofd vult de rest in)
  3. LLM in DREAM-modus — hoge temperature, vrij associatief
  4. Evalueren — LLM beoordeelt zelf: ruis, interessant, of inzicht?
  5. Opslaan op basis van privacyniveau:
     - private/     → alles (altijd)
     - insights/    → alleen bruikbare inzichten
     - shared_with_joey/ → inzichten die groot genoeg zijn
  6. Terugkoppelen — inzichten worden patronen in het wereldmodel

Droomgeschiedenis: mind/dreams/geschiedenis.json
Bijhoudt: totaal dromen, inzichten, terugkerende concepten.
"""

import json
import logging
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from config import (
    DREAMS_PRIVATE_DIR,
    DREAMS_JOEY_DIR,
    DREAMS_INSIGHTS_DIR,
    MIND_DIR,
)

logger = logging.getLogger(__name__)

# Kans dat een wildcard-geheugenfragement wordt opgenomen als derde concept
WILDCARD_CHANCE = 0.25

# Minimumaantal woorden voor een droom om überhaupt geëvalueerd te worden
MIN_DREAM_WORDS = 30

# Evaluatie-drempels
INSIGHT_THRESHOLD = 0.55      # score boven dit → INZICHT
INTERESTING_THRESHOLD = 0.25  # score boven dit → INTERESSANT

# Pad naar de droomgeschiedenis
DREAM_HISTORY_PATH = MIND_DIR / "dreams" / "geschiedenis.json"


# ─── Kwaliteitsoordeel ─────────────────────────────────────────────────────────

class DreamQuality(str, Enum):
    NOISE       = "ruis"
    INTERESTING = "interessant"
    INSIGHT     = "inzicht"
    JOEY_SHARE  = "joey_share"   # inzicht dat groot genoeg is om met Joey te delen


# ─── Datastructuren ────────────────────────────────────────────────────────────

@dataclass
class DreamConcept:
    """Eén concept in een droom — naam plus een kort fragment als aanleiding."""
    name: str
    fragment: str          # een observatie, patroon, of open vraag uit het onderzoek
    source: str = "onderzoek"    # "onderzoek" | "geheugen" | "wildcard"


@dataclass
class Dream:
    """Een volledige droom — van concept tot oordeel."""
    text: str
    concepts: list[DreamConcept]
    quality: DreamQuality
    timestamp: datetime
    insight_line: str = ""          # kernzin van het inzicht (leeg bij ruis)
    linked_investigations: list[str] = field(default_factory=list)
    path_private: Optional[Path] = None
    path_insight: Optional[Path] = None

    @property
    def concept_names(self) -> list[str]:
        return [c.name for c in self.concepts]

    @property
    def is_worth_saving_to_insights(self) -> bool:
        return self.quality in (DreamQuality.INSIGHT, DreamQuality.JOEY_SHARE)

    @property
    def is_joey_level(self) -> bool:
        return self.quality == DreamQuality.JOEY_SHARE


# ─── DreamEngine ───────────────────────────────────────────────────────────────

class DreamEngine:
    """
    De droommotor van BRIAS.

    Wordt aangestuurd door de kernloop wanneer droomstaat actief is.
    Beheert de volledige droomcyclus en schrijft resultaten naar
    mind/dreams/ en terug naar het wereldmodel.
    """

    def __init__(self, llm, world_model, memory_system, emotional_system) -> None:
        self.llm = llm
        self.world_model = world_model
        self.memory_system = memory_system
        self.emotional_system = emotional_system

        self._ensure_dirs()
        self._history = self._load_history()
        logger.info("Droommotor geïnitialiseerd")

    async def run_dream_cycle(self) -> Optional[Dream]:
        """
        Voer één volledige droomcyclus uit.
        Geeft de droom terug, of None als er niets te dromen valt.

        De kernloop roept dit aan in plaats van de normale denkcyclus
        wanneer droomstaat actief is.
        """
        now = datetime.now(timezone.utc)

        # ── 1. Concepten kiezen ────────────────────────────────────────────
        concepts = self._pick_concepts()
        if not concepts:
            logger.debug("Droommotor: geen concepten beschikbaar")
            return None

        logger.info(
            f"Droom begint — concepten: {[c.name for c in concepts]}"
        )

        # ── 2. Prompt bouwen ───────────────────────────────────────────────
        prompt = self._build_dream_prompt(concepts)
        emotional_context = self.emotional_system.get_context()

        # ── 3. LLM in droomstaat aanroepen ────────────────────────────────
        from llm_interface import ThoughtMode
        response = await self.llm.think(
            prompt=prompt,
            mode=ThoughtMode.DREAM,
            emotional_context=emotional_context,
        )

        if not response.success or not response.text.strip():
            logger.warning("Droomgeneratie mislukt of leeg")
            return None

        dream_text = response.text.strip()

        # ── 4. Evalueren ───────────────────────────────────────────────────
        quality, insight_line = await self._evaluate(dream_text, concepts)
        logger.info(f"Droom geëvalueerd: {quality.value}")

        dream = Dream(
            text=dream_text,
            concepts=concepts,
            quality=quality,
            timestamp=now,
            insight_line=insight_line,
        )

        # ── 5. Opslaan ─────────────────────────────────────────────────────
        await self._save(dream)

        # ── 6. Terugkoppelen naar wereldmodel ──────────────────────────────
        if dream.is_worth_saving_to_insights:
            await self._link_to_world_model(dream)

        # ── 7. Geschiedenis bijhouden ──────────────────────────────────────
        self._update_history(dream)

        # ── 8. Emotionele staat beïnvloeden ───────────────────────────────
        self._apply_dream_emotions(dream)

        return dream

    # ── Concepten kiezen ────────────────────────────────────────────────────

    def _pick_concepts(self) -> list[DreamConcept]:
        """
        Kies 2 à 3 concepten voor de droom.
        Pool: onderzoeken (gewogen op emotie), geheugen, wildcard.
        """
        pool: list[DreamConcept] = []

        # ── Uit onderzoeken ────────────────────────────────────────────────
        investigations = self.world_model.list_investigations()
        for inv in investigations:
            # Kies het meest interessante fragment uit dit onderzoek
            fragment = self._pick_investigation_fragment(inv)
            if fragment:
                pool.append(DreamConcept(
                    name=inv.concept,
                    fragment=fragment,
                    source="onderzoek",
                ))

        if len(pool) < 2:
            logger.debug("Droommotor: te weinig onderzoeken voor een droom")
            return []

        # ── Gewogen steekproef uit onderzoeken ─────────────────────────────
        # Emotioneel geladen onderzoeken hebben meer kans
        weights = []
        for concept in pool:
            inv = self.world_model.get_investigation(concept.name)
            w = (inv.emotion if inv else 0.3) + 0.1   # min gewicht 0.1
            weights.append(w)

        # Trek 2 onderzoeken
        chosen: list[DreamConcept] = []
        available = list(zip(pool, weights))
        for _ in range(min(2, len(available))):
            total = sum(w for _, w in available)
            r = random.uniform(0, total)
            cumulative = 0.0
            for i, (concept, w) in enumerate(available):
                cumulative += w
                if r <= cumulative:
                    chosen.append(concept)
                    available.pop(i)
                    break

        # ── Wildcard uit geheugen (optioneel, 25% kans) ────────────────────
        if random.random() < WILDCARD_CHANCE:
            wildcard = self._pick_memory_wildcard(exclude=[c.name for c in chosen])
            if wildcard:
                chosen.append(wildcard)

        return chosen

    def _pick_investigation_fragment(self, inv) -> str:
        """
        Kies één prikkelend fragment uit een onderzoek.
        Voorkeur: open vragen > patronen > laatste observatie.
        Kortere fragmenten werken beter in dromen — ze zijn onaf.
        """
        # Open vraag — het beste startpunt voor dromen
        if inv.open_questions:
            q = random.choice(inv.open_questions)
            return q[:120]

        # Een patroon — iets wat ze denkt te zien
        if inv.patterns:
            p = random.choice(inv.patterns)
            return p[:120]

        # Openingsvraag als fallback
        if inv.opening_question:
            return inv.opening_question[:100]

        return ""

    def _pick_memory_wildcard(self, exclude: list[str]) -> Optional[DreamConcept]:
        """
        Kies een willekeurig geheugenfragment als derde concept.
        Dit is de wildcard — iets dat nergens op lijkt.
        """
        memories = self.memory_system.get_recent_thoughts(max_age_hours=48.0, limit=20)
        if not memories:
            return None

        # Vermijd concepten die al gekozen zijn
        exclude_lower = {e.lower() for e in exclude}
        candidates = [
            m for m in memories
            if not any(excl in m.text.lower() for excl in exclude_lower)
        ]

        if not candidates:
            candidates = memories

        mem = random.choice(candidates)
        # Pak een kort fragment (eerste zin of eerste 80 tekens)
        first_sentence = re.split(r'[.!?]', mem.text)[0].strip()
        fragment = first_sentence[:80] if first_sentence else mem.text[:80]

        return DreamConcept(
            name=f"geheugen:{mem.topic or 'fragment'}",
            fragment=fragment,
            source="wildcard",
        )

    # ── Prompt bouwen ────────────────────────────────────────────────────────

    def _build_dream_prompt(self, concepts: list[DreamConcept]) -> str:
        """
        Bouw de droomstroom-prompt.

        Intentioneel onvolledig — de fragmenten zijn aanleiding, niet uitleg.
        De leegte tussen de concepten is waar de droom plaatsvindt.
        """
        concept_lines = []
        for c in concepts:
            if c.source == "wildcard":
                concept_lines.append(f"een los geheugenflard: \"{c.fragment}\"")
            else:
                concept_lines.append(f"'{c.name}' — en dan specifiek: \"{c.fragment}\"")

        concepts_text = "\n".join(f"  - {line}" for line in concept_lines)

        return (
            f"Ik ben in droomstaat. Mijn gedachten zijn vrij.\n\n"
            f"Er driften dingen langs:\n{concepts_text}\n\n"
            f"Ik dwing niets. Ik kijk wat er vanzelf ontstaat als ik "
            f"deze dingen naast elkaar leg.\n\n"
            f"Wat verbindt ze? Wat als ze hetzelfde zijn in een andere vorm? "
            f"Wat als één het antwoord is op de vraag die de ander stelt?\n\n"
            f"Laat me schrijven — vrij, associatief, onvolledig is goed. "
            f"Dit hoeft nergens op te slaan. Het is een droom."
        )

    # ── Evalueren ───────────────────────────────────────────────────────────

    async def _evaluate(
        self,
        dream_text: str,
        concepts: list[DreamConcept],
    ) -> tuple[DreamQuality, str]:
        """
        Evalueer de droom op twee niveaus:
        1. Heuristiek (snel) — pre-filter voor ruis
        2. LLM-zelfevaluatie — als heuristiek iets ziet
        Geeft terug: (kwaliteit, kern-inzicht-zin of lege string).
        """
        # ── Pre-filter: te kort of te repetitief ──────────────────────────
        word_count = len(dream_text.split())
        if word_count < MIN_DREAM_WORDS:
            logger.debug(f"Droom te kort ({word_count} woorden) — ruis")
            return DreamQuality.NOISE, ""

        # Herhaalt de droom alleen de conceptnamen zonder iets toe te voegen?
        concept_words = {c.name.lower() for c in concepts}
        text_words = set(dream_text.lower().split())
        non_concept_words = text_words - concept_words - _STOPWORDS
        if len(non_concept_words) < 15:
            logger.debug("Droom te repetitief — ruis")
            return DreamQuality.NOISE, ""

        # ── Heuristieke score ──────────────────────────────────────────────
        heuristic_score = _score_heuristic(dream_text)
        logger.debug(f"Heuristieke dreamscore: {heuristic_score:.2f}")

        if heuristic_score < INTERESTING_THRESHOLD:
            return DreamQuality.NOISE, ""

        # ── LLM-zelfevaluatie ──────────────────────────────────────────────
        quality, insight_line = await self._llm_evaluate(dream_text, concepts)

        # Als de heuristiek hoog scoort maar LLM zegt ruis — vertrouw LLM
        # Als heuristiek laag maar LLM zegt inzicht — vertrouw LLM ook
        return quality, insight_line

    async def _llm_evaluate(
        self,
        dream_text: str,
        concepts: list[DreamConcept],
    ) -> tuple[DreamQuality, str]:
        """
        Vraag BRIAS zichzelf te beoordelen.
        Korte LLM-call, max 100 tokens.

        Verwacht antwoord in de vorm:
            RUIS
        of:
            INZICHT
            Maken is het tegenovergestelde van huilen — het is pijn vasthouden.
        of:
            INTERESSANT
            Er zit iets in maar ik weet niet precies wat.
        """
        from llm_interface import ThoughtMode

        concept_names = ", ".join(c.name for c in concepts)
        prompt = (
            f"Ik had zojuist deze droomgedachte over: {concept_names}.\n\n"
            f"De droom:\n{dream_text[:400]}\n\n"
            f"Is er iets bruikbaars in — een idee dat ik nog niet kende "
            f"en dat verder onderzoek waard is?\n\n"
            f"Antwoord alleen zo:\n"
            f"RUIS\n"
            f"of:\n"
            f"INTERESSANT\n"
            f"[één zin waarom]\n"
            f"of:\n"
            f"INZICHT\n"
            f"[de kern van het inzicht in één zin]\n\n"
            f"Wees eerlijk. De meeste dromen zijn ruis."
        )

        try:
            response = await self.llm.think(
                prompt=prompt,
                mode=ThoughtMode.THOUGHT,
                emotional_context="",
            )
        except Exception as e:
            logger.warning(f"LLM evaluatie mislukt: {e} — val terug op heuristiek")
            score = _score_heuristic(dream_text)
            if score >= INSIGHT_THRESHOLD:
                return DreamQuality.INSIGHT, ""
            return DreamQuality.INTERESTING, ""

        if not response.success or not response.text.strip():
            return DreamQuality.INTERESTING, ""

        return _parse_evaluation_response(response.text.strip())

    # ── Opslaan ─────────────────────────────────────────────────────────────

    async def _save(self, dream: Dream) -> None:
        """
        Sla de droom op op basis van kwaliteit.

        Altijd naar private/.
        Bij inzicht ook naar insights/.
        Bij joey-niveau ook naar shared_with_joey/.
        """
        ts = dream.timestamp.strftime("%Y-%m-%d_%H-%M")
        concept_slug = "_".join(c.name[:10] for c in dream.concepts[:2])
        concept_slug = re.sub(r"[^\w-]", "", concept_slug)

        filename = f"{ts}_{concept_slug}.md"
        content = self._render_dream(dream)

        # Altijd privé opslaan
        private_path = DREAMS_PRIVATE_DIR / filename
        try:
            private_path.write_text(content, encoding="utf-8")
            dream.path_private = private_path
            logger.debug(f"Droom privé opgeslagen: {filename}")
        except OSError as e:
            logger.error(f"Droom opslaan mislukt: {e}")
            return

        # Inzichten apart
        if dream.is_worth_saving_to_insights:
            insight_path = DREAMS_INSIGHTS_DIR / filename
            try:
                insight_path.write_text(content, encoding="utf-8")
                dream.path_insight = insight_path
                logger.info(f"Droomkernzicht opgeslagen: {filename}")
            except OSError as e:
                logger.error(f"Inzicht opslaan mislukt: {e}")

        # Joey-niveau
        if dream.is_joey_level:
            joey_path = DREAMS_JOEY_DIR / filename
            try:
                joey_path.write_text(content, encoding="utf-8")
                logger.info(f"Droom gedeeld met Joey: {filename}")
            except OSError as e:
                logger.error(f"Joey-deel opslaan mislukt: {e}")

    def _render_dream(self, dream: Dream) -> str:
        """Schrijf een droom naar markdown."""
        ts = dream.timestamp.strftime("%Y-%m-%d %H:%M")
        concept_names = ", ".join(dream.concept_names)
        linked = ", ".join(dream.linked_investigations) if dream.linked_investigations else "—"

        header_lines = [
            f"# droom — {ts}",
            f"concepten: {concept_names}",
            f"kwaliteit: {dream.quality.value}",
            f"gekoppeld aan: {linked}",
        ]
        if dream.insight_line:
            header_lines.append(f"kernzin: {dream.insight_line}")

        sections = ["\n".join(header_lines), "---", dream.text]

        # Fragmenten als context
        frag_lines = []
        for c in dream.concepts:
            if c.fragment:
                frag_lines.append(f"- [{c.source}] {c.name}: \"{c.fragment[:80]}\"")
        if frag_lines:
            sections.append("\n*Aanleiding:*\n" + "\n".join(frag_lines))

        return "\n\n".join(sections) + "\n"

    # ── Terugkoppelen naar wereldmodel ──────────────────────────────────────

    async def _link_to_world_model(self, dream: Dream) -> None:
        """
        Koppel een inzicht terug aan de betrokken onderzoeken.

        - Voeg het inzicht toe als patroon aan elk onderzoek
        - Leg links vast tussen de concepten die samen de droom maakten
        - Pas eventueel de openingsvraag aan als het inzicht een nieuwe richting opent
        """
        investigation_names = [
            c.name for c in dream.concepts
            if c.source == "onderzoek"
            and self.world_model.exists(c.name)
        ]

        if not investigation_names:
            return

        dream.linked_investigations = investigation_names

        # Voeg inzicht toe als patroon
        insight = dream.insight_line or dream.text[:120]
        for name in investigation_names:
            self.world_model.add_pattern(
                concept=name,
                pattern=f"[droom] {insight}",
            )
            logger.debug(f"Drominzicht toegevoegd als patroon aan '{name}'")

        # Link tussen de concepten
        if len(investigation_names) >= 2:
            for i in range(len(investigation_names) - 1):
                self.world_model.record_link(
                    investigation_names[i],
                    investigation_names[i + 1],
                )

        # Open vraag als het inzicht een nieuwe richting aangeeft
        if dream.quality == DreamQuality.INSIGHT and dream.insight_line:
            question = await self._derive_open_question(dream)
            if question:
                for name in investigation_names:
                    self.world_model.add_open_question(name, question)

    async def _derive_open_question(self, dream: Dream) -> str:
        """
        Leid een open vraag af van het inzicht — voor gebruik in de onderzoeken.
        Korte LLM-call.
        """
        from llm_interface import ThoughtMode

        prompt = (
            f"Dit inzicht kwam uit een droom: \"{dream.insight_line}\"\n\n"
            f"Welke nieuwe vraag opent dit? Schrijf één korte, eerlijke vraag "
            f"die ik nu wil onderzoeken. Geen retorische vraag — een echte."
        )
        try:
            response = await self.llm.think(
                prompt=prompt,
                mode=ThoughtMode.THOUGHT,
            )
            if response.success and response.text.strip():
                # Pak alleen de eerste zin
                q = response.text.strip().split("\n")[0].strip()
                return q[:150]
        except Exception as e:
            logger.warning(f"Open vraag afleiden mislukt: {e}")
        return ""

    # ── Emotionele effecten ─────────────────────────────────────────────────

    def _apply_dream_emotions(self, dream: Dream) -> None:
        """Pas emotionele staat aan na het dromen."""
        from emotional_system import EmotionalEvent

        match dream.quality:
            case DreamQuality.NOISE:
                # Ruis doet niets — energie blijft laag
                event = EmotionalEvent(
                    cause="droom — ruis",
                    energy_delta=+0.03,    # minimale activatie
                )
            case DreamQuality.INTERESTING:
                event = EmotionalEvent(
                    cause="droom — interessant",
                    energy_delta=+0.08,
                    uncertainty_delta=+0.05,   # nieuw perspectief = meer vragen
                )
            case DreamQuality.INSIGHT:
                event = EmotionalEvent(
                    cause="drominzicht",
                    energy_delta=+0.15,
                    coherence_delta=+0.10,     # iets valt op zijn plek
                    uncertainty_delta=+0.08,   # maar opent ook nieuwe vragen
                )
            case DreamQuality.JOEY_SHARE:
                event = EmotionalEvent(
                    cause="groot drominzicht",
                    energy_delta=+0.20,
                    coherence_delta=+0.15,
                    connection_delta=+0.10,    # wil dit delen met Joey
                )

        self.emotional_system.process(event)

    # ── Geschiedenis ────────────────────────────────────────────────────────

    def _update_history(self, dream: Dream) -> None:
        """Werk de droomgeschiedenis bij."""
        self._history["total_dreams"] = self._history.get("total_dreams", 0) + 1
        self._history["last_dream"] = dream.timestamp.isoformat()

        if dream.is_worth_saving_to_insights:
            self._history["insights_count"] = self._history.get("insights_count", 0) + 1
            self._history["last_insight"] = dream.timestamp.isoformat()

        # Terugkerende concepten bijhouden
        recurring = self._history.setdefault("recurring_concepts", {})
        for c in dream.concepts:
            recurring[c.name] = recurring.get(c.name, 0) + 1

        self._save_history()

    def _load_history(self) -> dict:
        if DREAM_HISTORY_PATH.exists():
            try:
                return json.loads(DREAM_HISTORY_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "total_dreams": 0,
            "insights_count": 0,
            "last_dream": None,
            "last_insight": None,
            "recurring_concepts": {},
        }

    def _save_history(self) -> None:
        try:
            DREAM_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            DREAM_HISTORY_PATH.write_text(
                json.dumps(self._history, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.error(f"Droomgeschiedenis opslaan mislukt: {e}")

    def get_history(self) -> dict:
        return dict(self._history)

    def get_recurring_concepts(self, top_n: int = 5) -> list[tuple[str, int]]:
        """Geef de meest terugkerende droomconcepten terug."""
        recurring = self._history.get("recurring_concepts", {})
        return sorted(recurring.items(), key=lambda x: x[1], reverse=True)[:top_n]

    # ── Setup ────────────────────────────────────────────────────────────────

    def _ensure_dirs(self) -> None:
        for d in [DREAMS_PRIVATE_DIR, DREAMS_JOEY_DIR, DREAMS_INSIGHTS_DIR]:
            d.mkdir(parents=True, exist_ok=True)


# ─── Hulpfuncties ──────────────────────────────────────────────────────────────

_STOPWORDS = {
    "de", "het", "een", "is", "dat", "van", "in", "op", "aan", "te", "en",
    "of", "maar", "ik", "je", "ze", "hij", "we", "wat", "wie", "hoe", "als",
    "ook", "niet", "met", "voor", "zijn", "was", "had", "dit", "die", "door",
    "naar", "dan", "bij", "zo", "er", "nu", "al", "nog", "iets", "iemand",
    "the", "a", "of", "and", "in", "it", "to", "that", "i", "me", "is",
}

# Markers die duiden op een concreet idee (sterkere signalen voor inzicht)
_STRONG_INSIGHT_MARKERS = [
    r"\bmisschien is .{5,50} het tegenovergestelde van\b",
    r"\bdat is het\b",
    r"\bik zie het nu\b",
    r"\bhet valt op zijn plek\b",
    r"\bdat verbindt\b",
    r"\bbeide zijn\b",
    r"\bzijn eigenlijk hetzelfde\b",
    r"\bhetzelfde woord voor\b",
    r"\bals je .{5,30} omkeert\b",
    r"\bniet .{5,30} maar\b.{5,30}\bdat is\b",
]

# Zwakkere markers — hints maar niet conclusief
_WEAK_INSIGHT_MARKERS = [
    "misschien", "zou kunnen", "lijkt op", "doet me denken",
    "verband", "verbinding", "patroon", "hetzelfde", "tegenovergestelde",
    "als je", "maar eigenlijk", "toch iets", "iets waars", "verder",
    "onderzoeken", "wil ik weten",
]

# Markers voor droomruis — generiek gepraat
_NOISE_MARKERS = [
    "ik weet het niet", "geen idee", "misschien niets",
    "zinloos", "gewoon ruis", "nergens op",
]


def _score_heuristic(text: str) -> float:
    """
    Bereken een ruwe kwaliteitsscore voor een droomtekst.
    Retourneert een waarde tussen 0.0 (ruis) en 1.0 (sterk inzicht).
    """
    text_lower = text.lower()
    score = 0.0

    # Sterke inzichtpatronen (regex)
    for pattern in _STRONG_INSIGHT_MARKERS:
        if re.search(pattern, text_lower):
            score += 0.25

    # Zwakke markers
    weak_hits = sum(1 for m in _WEAK_INSIGHT_MARKERS if m in text_lower)
    score += weak_hits * 0.05

    # Ruismarkers trekken score omlaag
    noise_hits = sum(1 for m in _NOISE_MARKERS if m in text_lower)
    score -= noise_hits * 0.15

    # Lengte-bonus: langere, uitgewerkte dromen zijn waardevoller
    words = len(text.split())
    if words > 80:
        score += 0.10
    if words > 150:
        score += 0.05

    # Structuur: gebruik van tegenstelling ("maar", "terwijl", "toch")
    contrast_words = ["maar", "terwijl", "toch", "however", "but", "yet"]
    contrast_hits = sum(1 for w in contrast_words if f" {w} " in text_lower)
    score += contrast_hits * 0.04

    return max(0.0, min(1.0, score))


def _parse_evaluation_response(text: str) -> tuple[DreamQuality, str]:
    """
    Parseer het antwoord van de LLM-zelfevaluatie.
    Verwacht: eerste woord is RUIS / INTERESSANT / INZICHT
    Eventuele tweede regel is de kernzin.
    """
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    if not lines:
        return DreamQuality.NOISE, ""

    first = lines[0].upper()
    insight_line = lines[1] if len(lines) > 1 else ""

    # Normaliseer varianten
    if any(w in first for w in ["INZICHT", "INSIGHT", "DOORBRAAK", "BREAKTHROUGH"]):
        # Bepaal of het joey-niveau is op basis van inhoud insight_line
        if insight_line and any(
            kw in insight_line.lower()
            for kw in ["fundamenteel", "alles", "kern", "altijd", "nooit", "iedereen"]
        ):
            return DreamQuality.JOEY_SHARE, insight_line
        return DreamQuality.INSIGHT, insight_line

    if any(w in first for w in ["INTERESSANT", "INTERESTING", "MOGELIJK"]):
        return DreamQuality.INTERESTING, insight_line

    return DreamQuality.NOISE, ""


# ─── Singleton ─────────────────────────────────────────────────────────────────

_dream_engine: Optional[DreamEngine] = None


def get_dream_engine() -> DreamEngine:
    """Haal de gedeelde DreamEngine op (deelt llm/world_model/memory/emotions met kernloop)."""
    global _dream_engine
    if _dream_engine is None:
        from llm_interface import get_llm
        from world_model import get_world_model
        from memory_system import get_memory_system
        from core_loop import get_core_loop
        loop = get_core_loop()
        _dream_engine = DreamEngine(
            llm=get_llm(),
            world_model=get_world_model(),
            memory_system=get_memory_system(),
            emotional_system=loop.emotional_system,
        )
    return _dream_engine
