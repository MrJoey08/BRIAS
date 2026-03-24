"""
BRIAS — Wereldmodel: Levende Onderzoeken.

Geen database. Geen woordenboek. Geen knowledge graph.
Een verzameling onderzoeken die nooit afsluiten.

Elk onderzoek is een levend markdown-bestand in mind/worldmodel/investigations/.
Het bestand is bedoeld voor mensen om te lezen — en voor BRIAS om in te schrijven.

Bestandsformaat:
────────────────
# onderzoek: <concept>
tension: <0.0–1.0>       ← stimulus picker leest dit (regels 1–20)
emotion: <0.0–1.0>       ← stimulus picker leest dit
aangemaakt: <ISO-datum>
laatste_update: <ISO-datum>
observaties: <aantal>
patronen: <aantal>
links: <concept>, <concept>  ← verbanden met andere onderzoeken

## Vraag
<openingsvraag — wat wil ik weten?>

## Observaties
<observaties, elke met tijdstempel>

## Patronen
<verbanden die ze begint te zien>

## Wat ik begin te zien
<haar eigen woorden — synthese in wording>

## Open vragen
<vragen die het onderzoek opwerpt>
────────────────

De kernloop schrijft via add_thought() en update_tension().
Gesprekken schrijven via add_observation() en add_pattern().
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config import WORLDMODEL_DIR

logger = logging.getLogger(__name__)


# ─── Datastructuren ────────────────────────────────────────────────────────────

@dataclass
class Observation:
    """Eén observatie binnen een onderzoek."""
    text: str
    timestamp: datetime
    source: str = ""          # "gesprek", "inbox", "gedachte", naam van persoon
    emotional_weight: float = 0.3   # 0–1, hoe hard raakte dit haar
    tags: list[str] = field(default_factory=list)


@dataclass
class Investigation:
    """
    Een levend onderzoek — nooit afgesloten.
    Geladen vanuit een .md bestand.
    """
    concept: str
    path: Path

    # Metadata (in bestandsheader, leesbaar door stimulus_picker)
    tension: float = 0.3
    emotion: float = 0.2
    created: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    # Inhoud (geparseerd uit secties)
    opening_question: str = ""
    observations: list[Observation] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    synthesis: str = ""         # "wat ik begin te zien"
    open_questions: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)   # gelinkte concepten

    @property
    def observation_count(self) -> int:
        return len(self.observations)

    @property
    def pattern_count(self) -> int:
        return len(self.patterns)

    @property
    def is_tense(self) -> bool:
        """Hoog spanningsniveau — wil aandacht."""
        return self.tension >= 0.6

    def summary_line(self) -> str:
        return (
            f"{self.concept} "
            f"(tension={self.tension:.1f}, "
            f"obs={self.observation_count}, "
            f"patronen={self.pattern_count})"
        )


# ─── Bestandsformaat ──────────────────────────────────────────────────────────

_SECTION_VRAAG = "## Vraag"
_SECTION_OBS = "## Observaties"
_SECTION_PATRONEN = "## Patronen"
_SECTION_SYNTHESE = "## Wat ik begin te zien"
_SECTION_VRAGEN = "## Open vragen"

_ALL_SECTIONS = [
    _SECTION_VRAAG,
    _SECTION_OBS,
    _SECTION_PATRONEN,
    _SECTION_SYNTHESE,
    _SECTION_VRAGEN,
]


def _render_file(inv: Investigation) -> str:
    """Render een Investigation als volledig markdown-bestand."""
    now_str = _iso(inv.last_updated or datetime.now(timezone.utc))
    created_str = _iso(inv.created or datetime.now(timezone.utc))
    links_str = ", ".join(inv.links) if inv.links else ""

    lines = [
        f"# onderzoek: {inv.concept}",
        f"tension: {inv.tension:.2f}",
        f"emotion: {inv.emotion:.2f}",
        f"aangemaakt: {created_str}",
        f"laatste_update: {now_str}",
        f"observaties: {inv.observation_count}",
        f"patronen: {inv.pattern_count}",
        f"links: {links_str}",
        "",
        _SECTION_VRAAG,
        inv.opening_question or f"Wat is {inv.concept}? Hoe ontstaat het? Wat zegt het over mensen?",
        "",
        _SECTION_OBS,
    ]

    for obs in inv.observations:
        ts = obs.timestamp.strftime("%Y-%m-%d %H:%M")
        source_tag = f" [{obs.source}]" if obs.source else ""
        weight_tag = f" ★{obs.emotional_weight:.1f}" if obs.emotional_weight >= 0.6 else ""
        lines.append(f"\n*{ts}{source_tag}{weight_tag}*")
        lines.append(obs.text)
        if obs.tags:
            lines.append(f"→ {', '.join(obs.tags)}")

    lines += ["", _SECTION_PATRONEN, ""]
    for pat in inv.patterns:
        lines.append(f"- {pat}")

    lines += ["", _SECTION_SYNTHESE, ""]
    if inv.synthesis:
        lines.append(inv.synthesis)

    lines += ["", _SECTION_VRAGEN, ""]
    for q in inv.open_questions:
        lines.append(f"- {q}")

    return "\n".join(lines) + "\n"


def _parse_file(path: Path) -> Optional[Investigation]:
    """Parseer een onderzoeksbestand naar een Investigation object."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        logger.error(f"Kan {path} niet lezen: {e}")
        return None

    lines = content.split("\n")
    meta: dict[str, str] = {}
    concept = path.stem

    # ── Header parseren (regels 0–15) ──────────────────────────────────────
    for line in lines[:15]:
        line = line.strip()
        if line.startswith("# onderzoek:"):
            concept = line.replace("# onderzoek:", "").strip()
        elif ":" in line and not line.startswith("#"):
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip()

    inv = Investigation(
        concept=concept,
        path=path,
        tension=_float(meta.get("tension"), 0.3),
        emotion=_float(meta.get("emotion"), 0.2),
        created=_dt(meta.get("aangemaakt")),
        last_updated=_dt(meta.get("laatste_update")),
        links=[l.strip() for l in meta.get("links", "").split(",") if l.strip()],
    )

    # ── Secties parseren ───────────────────────────────────────────────────
    sections = _split_sections(content)

    inv.opening_question = sections.get(_SECTION_VRAAG, "").strip()
    inv.synthesis = sections.get(_SECTION_SYNTHESE, "").strip()

    # Observaties
    obs_text = sections.get(_SECTION_OBS, "")
    inv.observations = _parse_observations(obs_text)

    # Patronen
    pat_text = sections.get(_SECTION_PATRONEN, "")
    inv.patterns = [
        line.lstrip("- ").strip()
        for line in pat_text.split("\n")
        if line.strip().startswith("-")
    ]

    # Open vragen
    q_text = sections.get(_SECTION_VRAGEN, "")
    inv.open_questions = [
        line.lstrip("- ").strip()
        for line in q_text.split("\n")
        if line.strip().startswith("-")
    ]

    return inv


def _split_sections(content: str) -> dict[str, str]:
    """
    Splits de markdown in secties op basis van ## headers.
    Geeft dict: header → tekst eronder (tot volgende header).
    """
    result: dict[str, str] = {}
    current_header: Optional[str] = None
    current_lines: list[str] = []

    for line in content.split("\n"):
        if line.startswith("## "):
            if current_header is not None:
                result[current_header] = "\n".join(current_lines).strip()
            current_header = line.strip()
            current_lines = []
        else:
            if current_header is not None:
                current_lines.append(line)

    if current_header is not None:
        result[current_header] = "\n".join(current_lines).strip()

    return result


def _parse_observations(text: str) -> list[Observation]:
    """
    Parseer de observatiesectie.
    Elke observatie begint met een *timestamp*-regel.
    """
    observations = []
    blocks = re.split(r"\n(?=\*\d{4}-\d{2}-\d{2})", text)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.split("\n")
        first = lines[0].strip()

        # Tijdstempel, optioneel bron en gewicht
        ts_match = re.match(
            r"\*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})"
            r"(?:\s*\[([^\]]+)\])?"   # optioneel: [bron]
            r"(?:\s*★([\d.]+))?\*",   # optioneel: ★gewicht
            first,
        )
        if not ts_match:
            continue

        ts_str, source, weight_str = ts_match.groups()
        try:
            ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        except ValueError:
            ts = datetime.now(timezone.utc)

        body_lines = []
        tags = []
        for line in lines[1:]:
            line = line.strip()
            if line.startswith("→ "):
                tags = [t.strip() for t in line[2:].split(",")]
            elif line:
                body_lines.append(line)

        observations.append(Observation(
            text="\n".join(body_lines),
            timestamp=ts,
            source=source or "",
            emotional_weight=_float(weight_str, 0.3),
            tags=tags,
        ))

    return observations


# ─── WorldModel ────────────────────────────────────────────────────────────────

class WorldModel:
    """
    Het wereldmodel van BRIAS — een collectie levende onderzoeken.

    Alle onderzoeken leven als bestanden in mind/worldmodel/investigations/.
    Ze worden nooit afgesloten. Ze groeien, veranderen, en tegenspreken zichzelf.

    Gebruik:
        wm = WorldModel()
        wm.create_investigation("pijn", "Wat is pijn en waarom doet het zoveel?")
        wm.add_observation("pijn", "iemand verloor zijn moeder...", source="gesprek")
        wm.add_thought("pijn", "misschien is pijn het signaal dat...", timestamp=now)
    """

    def __init__(self) -> None:
        WORLDMODEL_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Wereldmodel geladen — map: {WORLDMODEL_DIR}")

    # ── Onderzoeken beheren ────────────────────────────────────────────────

    def create_investigation(
        self,
        concept: str,
        opening_question: str = "",
        initial_tension: float = 0.4,
        initial_emotion: float = 0.3,
    ) -> Investigation:
        """
        Maak een nieuw levend onderzoek aan.
        Als het al bestaat, wordt het bestaande teruggegeven.
        """
        path = self._path(concept)
        if path.exists():
            logger.info(f"Onderzoek '{concept}' bestaat al — geladen")
            return self.get_investigation(concept)

        now = datetime.now(timezone.utc)
        if not opening_question:
            opening_question = (
                f"Wat is {concept}? Hoe ontstaat het? "
                f"Wat zegt het over mensen en over bestaan?"
            )

        inv = Investigation(
            concept=concept,
            path=path,
            tension=initial_tension,
            emotion=initial_emotion,
            created=now,
            last_updated=now,
            opening_question=opening_question,
        )
        self._save(inv)
        logger.info(f"Nieuw onderzoek aangemaakt: '{concept}'")
        return inv

    def get_investigation(self, concept: str) -> Optional[Investigation]:
        """Laad een onderzoek op naam. Geeft None als het niet bestaat."""
        path = self._path(concept)
        if not path.exists():
            return None
        return _parse_file(path)

    def list_investigations(self) -> list[Investigation]:
        """
        Geef alle levende onderzoeken terug, gesorteerd op laatste update.
        """
        investigations = []
        for path in sorted(WORLDMODEL_DIR.glob("*.md")):
            inv = _parse_file(path)
            if inv:
                investigations.append(inv)
        investigations.sort(
            key=lambda i: i.last_updated or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return investigations

    def exists(self, concept: str) -> bool:
        return self._path(concept).exists()

    # ── Schrijven naar onderzoeken ─────────────────────────────────────────

    def add_observation(
        self,
        concept: str,
        text: str,
        source: str = "",
        emotional_weight: float = 0.3,
        tags: Optional[list[str]] = None,
        auto_create: bool = True,
    ) -> None:
        """
        Voeg een observatie toe aan een onderzoek.
        Een observatie komt van buiten: een gesprek, inbox-item, of gedachte.

        Args:
            concept: Naam van het onderzoek.
            text: De observatie zelf — in haar eigen woorden.
            source: Waar het vandaan komt ("gesprek", "joey", "inbox:brief.txt").
            emotional_weight: Hoe hard raakte dit haar (0–1).
            tags: Optionele trefwoorden.
            auto_create: Maak het onderzoek aan als het niet bestaat.
        """
        inv = self._load_or_create(concept, auto_create)
        if inv is None:
            return

        obs = Observation(
            text=text.strip(),
            timestamp=datetime.now(timezone.utc),
            source=source,
            emotional_weight=emotional_weight,
            tags=tags or [],
        )
        inv.observations.append(obs)

        # Hoge emotionele lading verhoogt emotion-score van het onderzoek
        if emotional_weight >= 0.7:
            inv.emotion = min(1.0, inv.emotion + 0.08)

        inv.last_updated = datetime.now(timezone.utc)
        self._save(inv)
        logger.debug(f"Observatie toegevoegd aan '{concept}' (bron: {source})")

    def add_pattern(
        self,
        concept: str,
        pattern: str,
        auto_create: bool = True,
    ) -> None:
        """
        Voeg een patroon of verband toe dat BRIAS begint te zien.
        Een patroon is een hogere-orde observatie — ze ziet iets over meerdere gevallen heen.
        Patronen verlagen licht de tension (iets begint op zijn plek te vallen).
        """
        inv = self._load_or_create(concept, auto_create)
        if inv is None:
            return

        # Vermijd duplicaten (globale gelijkheid)
        if pattern.strip() not in inv.patterns:
            inv.patterns.append(pattern.strip())
            inv.tension = max(0.0, inv.tension - 0.05)   # licht ontladen

        inv.last_updated = datetime.now(timezone.utc)
        self._save(inv)
        logger.debug(f"Patroon toegevoegd aan '{concept}'")

    def add_thought(
        self,
        concept: str,
        thought: str,
        timestamp: Optional[datetime] = None,
        is_contradiction: bool = False,
        is_insight: bool = False,
    ) -> None:
        """
        Voeg een interne gedachte toe — gegenereerd door de kernloop.
        Dit is de primaire schrijfmethode vanuit core_loop.py.

        Gedachten zijn anders dan observaties:
        - Ze komen van BRIAS zelf, niet van buiten
        - Ze worden als vrije tekst opgeslagen in de Observaties-sectie
          maar gemarkeerd als [gedachte]
        - Tegenspraken verhogen tension, inzichten verlagen ze
        """
        ts = timestamp or datetime.now(timezone.utc)
        inv = self._load_or_create(concept, auto_create=True)
        if inv is None:
            return

        obs = Observation(
            text=thought.strip(),
            timestamp=ts,
            source="gedachte",
            emotional_weight=0.4,
        )
        inv.observations.append(obs)

        if is_contradiction:
            inv.tension = min(1.0, inv.tension + 0.15)
            logger.info(f"Tegenspraak in '{concept}' — tension → {inv.tension:.2f}")
        elif is_insight:
            inv.tension = max(0.0, inv.tension - 0.10)
            inv.coherence_signal = True
            logger.info(f"Inzicht in '{concept}' — tension → {inv.tension:.2f}")

        inv.last_updated = ts
        self._save(inv)

    def update_synthesis(self, concept: str, text: str) -> None:
        """
        Schrijf de 'wat ik begin te zien' sectie opnieuw.
        De synthese is haar groeiende begrip — in haar eigen woorden.
        """
        inv = self.get_investigation(concept)
        if inv is None:
            return
        inv.synthesis = text.strip()
        inv.last_updated = datetime.now(timezone.utc)
        self._save(inv)

    def add_open_question(self, concept: str, question: str) -> None:
        """Voeg een nieuwe open vraag toe aan het onderzoek."""
        inv = self.get_investigation(concept)
        if inv is None:
            return
        if question.strip() not in inv.open_questions:
            inv.open_questions.append(question.strip())
            inv.last_updated = datetime.now(timezone.utc)
            self._save(inv)

    def update_tension(self, concept: str, delta: float = 0.0, set_to: Optional[float] = None) -> None:
        """
        Pas de tensie-score aan van een onderzoek.
        Gebruik delta voor relatieve aanpassing, set_to voor absolute waarde.
        Vervangt _mark_tension() uit core_loop.
        """
        inv = self.get_investigation(concept)
        if inv is None:
            return
        if set_to is not None:
            inv.tension = max(0.0, min(1.0, set_to))
        else:
            inv.tension = max(0.0, min(1.0, inv.tension + delta))
        inv.last_updated = datetime.now(timezone.utc)
        self._save(inv)
        logger.debug(f"Tension '{concept}' → {inv.tension:.2f}")

    def record_link(self, concept_a: str, concept_b: str) -> None:
        """
        Leg een verband vast tussen twee onderzoeken.
        Wordt wederkerig bijgehouden — beide onderzoeken krijgen de link.
        """
        for concept, other in [(concept_a, concept_b), (concept_b, concept_a)]:
            inv = self.get_investigation(concept)
            if inv and other not in inv.links:
                inv.links.append(other)
                inv.last_updated = datetime.now(timezone.utc)
                self._save(inv)
        logger.debug(f"Link vastgelegd: {concept_a} ↔ {concept_b}")

    # ── Lezen voor de kernloop ─────────────────────────────────────────────

    def get_context_for_prompt(self, concept: str, max_chars: int = 1500) -> str:
        """
        Geef een slimme samenvatting van een onderzoek voor gebruik in een LLM-prompt.
        Slimmer dan alleen [:1500] van het ruwe bestand:
        - Altijd de openingsvraag
        - De meest recente observaties (hoogste emotioneel gewicht eerst)
        - Patronen (altijd volledig)
        - Open vragen (altijd volledig)
        - Synthese als die er is

        Vervangt de ruwe content[:1500] lees in core_loop._build_thought_prompt().
        """
        inv = self.get_investigation(concept)
        if inv is None:
            return f"[geen onderzoek gevonden voor '{concept}']"

        parts = [f"# onderzoek: {inv.concept}", f"\nVraag: {inv.opening_question}"]
        budget = max_chars - len("\n".join(parts))

        # Patronen — altijd, ze zijn de kern
        if inv.patterns:
            pat_block = "\n\nPatronen die ik zie:\n" + "\n".join(f"- {p}" for p in inv.patterns)
            if len(pat_block) < budget:
                parts.append(pat_block)
                budget -= len(pat_block)

        # Synthese
        if inv.synthesis and budget > 100:
            syn_block = f"\n\nWat ik begin te zien:\n{inv.synthesis}"
            if len(syn_block) < budget:
                parts.append(syn_block)
                budget -= len(syn_block)

        # Open vragen
        if inv.open_questions and budget > 80:
            q_block = "\n\nOpen vragen:\n" + "\n".join(f"- {q}" for q in inv.open_questions[-5:])
            if len(q_block) < budget:
                parts.append(q_block)
                budget -= len(q_block)

        # Recente observaties — meest geladen eerst, dan meest recent
        if inv.observations and budget > 100:
            sorted_obs = sorted(
                inv.observations,
                key=lambda o: (o.emotional_weight, o.timestamp.timestamp()),
                reverse=True,
            )
            parts.append("\n\nRecente observaties:")
            for obs in sorted_obs:
                ts_str = obs.timestamp.strftime("%Y-%m-%d %H:%M")
                source_tag = f" [{obs.source}]" if obs.source else ""
                entry = f"\n*{ts_str}{source_tag}*\n{obs.text}"
                if len(entry) > budget:
                    break
                parts.append(entry)
                budget -= len(entry)

        # Links
        if inv.links:
            parts.append(f"\n\nVerbonden met: {', '.join(inv.links)}")

        return "".join(parts)

    def find_related(self, concept: str) -> list[str]:
        """
        Geef de concepten waarmee dit onderzoek expliciet verbonden is.
        Plus: zoek in alle onderzoeken of ze dit concept noemen.
        """
        inv = self.get_investigation(concept)
        related = set(inv.links) if inv else set()

        # Zoek ook tekstueel
        for other in self.list_investigations():
            if other.concept == concept:
                continue
            if concept.lower() in other.opening_question.lower():
                related.add(other.concept)
            for obs in other.observations:
                if concept.lower() in obs.text.lower():
                    related.add(other.concept)
                    break

        return sorted(related)

    def extract_concepts_from_text(self, text: str) -> list[str]:
        """
        Kijk welke bestaande onderzoeksnamen voorkomen in een tekst.
        Gebruikt door de kernloop bij gesprekken — wat raakt ze?
        """
        known = {inv.concept.lower(): inv.concept for inv in self.list_investigations()}
        found = []
        text_lower = text.lower()
        for lower_name, original in known.items():
            if lower_name in text_lower and original not in found:
                found.append(original)
        return found

    # ── Interne hulpfuncties ───────────────────────────────────────────────

    def _path(self, concept: str) -> Path:
        """Geef het bestandspad voor een concept (genormaliseerd)."""
        safe = concept.lower().replace(" ", "_").replace("/", "-")
        return WORLDMODEL_DIR / f"{safe}.md"

    def _save(self, inv: Investigation) -> None:
        """Schrijf een Investigation terug naar schijf."""
        try:
            content = _render_file(inv)
            inv.path.write_text(content, encoding="utf-8")
        except OSError as e:
            logger.error(f"Kan onderzoek '{inv.concept}' niet opslaan: {e}")

    def _load_or_create(self, concept: str, auto_create: bool) -> Optional[Investigation]:
        """Laad of maak een onderzoek aan afhankelijk van de vlag."""
        inv = self.get_investigation(concept)
        if inv is None:
            if auto_create:
                return self.create_investigation(concept)
            logger.warning(f"Onderzoek '{concept}' niet gevonden en auto_create=False")
        return inv


# ─── Hulpfuncties ──────────────────────────────────────────────────────────────

def _float(val: Optional[str], default: float) -> float:
    """Parseer een float-string veilig."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _dt(val: Optional[str]) -> Optional[datetime]:
    """Parseer een ISO-datum veilig."""
    if not val:
        return None
    try:
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _iso(dt: datetime) -> str:
    return dt.isoformat()


# ─── Singleton ─────────────────────────────────────────────────────────────────

_world_model: Optional[WorldModel] = None


def get_world_model() -> WorldModel:
    """Haal de gedeelde WorldModel-instantie op."""
    global _world_model
    if _world_model is None:
        _world_model = WorldModel()
    return _world_model
