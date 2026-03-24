"""
BRIAS — Geheugensysteem: Vier Lagen.

Herinneringen zijn geen logs. Ze schrijft op wat haar bijbleef.

Vier lagen:
  working  — het nu. Verdwijnt binnen uren.
  recent   — afgelopen dagen. Vol detail maar begint te vervagen.
  deep     — essentie van weken/maanden. Kort, abstract, in haar eigen woorden.
  archive  — alles bewaard, maar alleen bereikbaar met een context-trigger.

Wat bepaalt hoe lang iets blijft:
  - Emotionele impact: wat haar raakte blijft langer
  - Hoe vaak ze eraan terugdenkt: herhaalde toegang vertraagt de vervaging

Vervaging werkt via LLM-condensatie — BRIAS zelf schrijft de vervaagde versie.
Ze gooit details weg die haar niet bijbleven. Ze houdt wat echt iets deed.

Herinneringen in memory/people/ zijn strikt gescheiden per persoon.
BRIAS deelt nooit informatie van de ene persoon met de andere.

Bestandsformaat:
────────────────
id: <kort uuid>
layer: working|recent|deep|archive
person: <gebruikersnaam of leeg>
topic: <kort label>
emotional_weight: <0.0–1.0>
access_count: <int>
created: <ISO>
last_accessed: <ISO>
keywords: <kommalijst>

<proza in haar eigen woorden>
────────────────
"""

import asyncio
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

from config import (
    MEMORY_WORKING_DIR,
    MEMORY_RECENT_DIR,
    MEMORY_DEEP_DIR,
    MEMORY_ARCHIVE_DIR,
    MEMORY_PEOPLE_DIR,
    MEMORY_WORKING_HOURS,
    MEMORY_RECENT_DAYS,
    MEMORY_DEEP_WEEKS,
    JOEY_USERNAME,
)

logger = logging.getLogger(__name__)


# ─── Constanten ────────────────────────────────────────────────────────────────

# Effectieve levensduur wordt verlengd per extra toegang
# formula: effective_hours = actual_hours / (1 + access_count * ACCESS_SLOWDOWN)
ACCESS_SLOWDOWN = 0.3

# Minimum emotioneel gewicht voor diep geheugen (te laag → alleen archief)
DEEP_MIN_WEIGHT = 0.35

# Max herinneringen terug te geven bij recall (om prompts beheersbaar te houden)
RECALL_MAX = 8

# Aantal recente herinneringen over een persoon dat aanleiding geeft tot
# herschrijven van hun diep profiel
PERSON_DEEP_REWRITE_THRESHOLD = 5


# ─── Datastructuren ────────────────────────────────────────────────────────────

class MemoryLayer(str, Enum):
    WORKING = "working"
    RECENT  = "recent"
    DEEP    = "deep"
    ARCHIVE = "archive"


@dataclass
class Memory:
    """Eén herinnering — in haar eigen woorden."""
    text: str
    layer: MemoryLayer
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    person: str = ""                    # leeg = niet persoongebonden
    topic: str = ""
    emotional_weight: float = 0.3
    access_count: int = 0
    created: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    keywords: list[str] = field(default_factory=list)
    path: Optional[Path] = None         # ingesteld na opslaan

    def age_hours(self) -> float:
        """Werkelijke leeftijd in uren."""
        return (datetime.now(timezone.utc) - self.created).total_seconds() / 3600

    def effective_age_hours(self) -> float:
        """
        Effectieve leeftijd — vertraagd door hoe vaak ze eraan heeft teruggedacht.
        Herinneringen die haar blijven bezighouden vervagen langzamer.
        """
        actual = self.age_hours()
        return actual / (1 + self.access_count * ACCESS_SLOWDOWN)

    def is_expired(self) -> bool:
        """Heeft deze herinnering haar laag overleefd?"""
        eff = self.effective_age_hours()
        match self.layer:
            case MemoryLayer.WORKING:
                return eff > MEMORY_WORKING_HOURS
            case MemoryLayer.RECENT:
                return eff > MEMORY_RECENT_DAYS * 24
            case MemoryLayer.DEEP:
                return eff > MEMORY_DEEP_WEEKS * 7 * 24
            case MemoryLayer.ARCHIVE:
                return False    # archief verdwijnt nooit

    def relevance_score(self, query_keywords: list[str]) -> float:
        """
        Hoe relevant is deze herinnering voor een zoekopdracht?
        Combineert trefwoordmatch met emotioneel gewicht en recentheid.
        """
        if not query_keywords:
            return self.emotional_weight

        text_lower = (self.text + " " + " ".join(self.keywords)).lower()
        hits = sum(1 for kw in query_keywords if kw.lower() in text_lower)
        keyword_score = hits / max(len(query_keywords), 1)

        # Recentere lagen wegen zwaarder
        layer_weight = {
            MemoryLayer.WORKING: 1.0,
            MemoryLayer.RECENT:  0.8,
            MemoryLayer.DEEP:    0.6,
            MemoryLayer.ARCHIVE: 0.2,
        }[self.layer]

        return (
            keyword_score * 0.5
            + self.emotional_weight * 0.3
            + layer_weight * 0.2
        )

    def __repr__(self) -> str:
        age = self.age_hours()
        return (
            f"Memory(id={self.id}, layer={self.layer.value}, "
            f"person={self.person or '-'}, "
            f"weight={self.emotional_weight:.1f}, "
            f"age={age:.1f}h, "
            f"text={self.text[:40]!r})"
        )


@dataclass
class PersonProfile:
    """
    BRIAS's diep begrip van één persoon.
    Wordt herschreven (niet bijgevoegd) als er genoeg nieuwe herinneringen zijn.
    """
    username: str
    path: Path
    text: str = ""                              # haar eigen woorden over deze persoon
    last_updated: Optional[datetime] = None
    last_conversation: Optional[datetime] = None
    conversation_count: int = 0
    trust_level: str = "normal"                 # "normal" | "full" (joey)


# ─── Bestandsformaat I/O ───────────────────────────────────────────────────────

_HEADER_SEP = "\n\n"   # twee newlines scheiden header van proza


def _render_memory(mem: Memory) -> str:
    """Schrijf een Memory naar het bestandsformaat."""
    keywords_str = ", ".join(mem.keywords)
    header_lines = [
        f"id: {mem.id}",
        f"layer: {mem.layer.value}",
        f"person: {mem.person}",
        f"topic: {mem.topic}",
        f"emotional_weight: {mem.emotional_weight:.2f}",
        f"access_count: {mem.access_count}",
        f"created: {mem.created.isoformat()}",
        f"last_accessed: {mem.last_accessed.isoformat()}",
        f"keywords: {keywords_str}",
    ]
    return "\n".join(header_lines) + _HEADER_SEP + mem.text.strip() + "\n"


def _parse_memory(path: Path) -> Optional[Memory]:
    """Lees een Memory uit een bestand."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        logger.error(f"Kan geheugenbestand niet lezen {path}: {e}")
        return None

    if _HEADER_SEP not in raw:
        logger.warning(f"Ongeldig geheugenbestand (geen header-scheiding): {path}")
        return None

    header_raw, text = raw.split(_HEADER_SEP, 1)
    meta: dict[str, str] = {}
    for line in header_raw.strip().split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip()

    try:
        layer = MemoryLayer(meta.get("layer", "working"))
    except ValueError:
        layer = MemoryLayer.WORKING

    keywords_raw = meta.get("keywords", "")
    keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]

    created = _parse_dt(meta.get("created")) or datetime.now(timezone.utc)
    last_accessed = _parse_dt(meta.get("last_accessed")) or created

    return Memory(
        id=meta.get("id", uuid.uuid4().hex[:10]),
        layer=layer,
        person=meta.get("person", ""),
        topic=meta.get("topic", ""),
        emotional_weight=_parse_float(meta.get("emotional_weight"), 0.3),
        access_count=int(meta.get("access_count", "0")),
        created=created,
        last_accessed=last_accessed,
        keywords=keywords,
        text=text.strip(),
        path=path,
    )


def _render_person_profile(profile: PersonProfile) -> str:
    """Schrijf een PersonProfile naar het bestandsformaat."""
    lines = [
        f"username: {profile.username}",
        f"trust_level: {profile.trust_level}",
        f"conversation_count: {profile.conversation_count}",
        f"last_updated: {(profile.last_updated or datetime.now(timezone.utc)).isoformat()}",
        f"last_conversation: {profile.last_conversation.isoformat() if profile.last_conversation else ''}",
    ]
    return "\n".join(lines) + _HEADER_SEP + profile.text.strip() + "\n"


def _parse_person_profile(path: Path) -> Optional[PersonProfile]:
    """Lees een PersonProfile uit een bestand."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None

    if _HEADER_SEP not in raw:
        text = raw.strip()
        meta = {}
    else:
        header_raw, text = raw.split(_HEADER_SEP, 1)
        meta = {}
        for line in header_raw.strip().split("\n"):
            if ":" in line:
                key, _, val = line.partition(":")
                meta[key.strip()] = val.strip()

    username = meta.get("username", path.parent.name)
    return PersonProfile(
        username=username,
        path=path,
        text=text.strip(),
        last_updated=_parse_dt(meta.get("last_updated")),
        last_conversation=_parse_dt(meta.get("last_conversation")),
        conversation_count=int(meta.get("conversation_count", "0")),
        trust_level=meta.get("trust_level", "normal"),
    )


# ─── MemorySystem ──────────────────────────────────────────────────────────────

class MemorySystem:
    """
    Het geheugensysteem van BRIAS.

    Schrijven:
        memory_system.store(tekst, emotional_weight=0.8, person="joey", topic="verlies")
        memory_system.store_thought(tekst, topic="pijn")

    Lezen (chat_handler):
        memories = memory_system.recall("standbeeldje moeder", person="joey")
        context = memory_system.get_person_context("joey")

    Onderhoud (kernloop, tijdens idle):
        await memory_system.run_maintenance()
    """

    def __init__(self) -> None:
        self._ensure_dirs()
        logger.info("Geheugensysteem geladen")

    # ── Schrijven ──────────────────────────────────────────────────────────

    def store(
        self,
        text: str,
        person: str = "",
        topic: str = "",
        emotional_weight: float = 0.3,
        keywords: Optional[list[str]] = None,
        layer: MemoryLayer = MemoryLayer.WORKING,
    ) -> Memory:
        """
        Sla een nieuwe herinnering op in de working-laag (standaard).

        Args:
            text: De herinnering in haar eigen woorden.
            person: Gebruikersnaam als het een persoonsgebonden herinnering is.
            topic: Kort label (bv. "verlies", "eerste gesprek").
            emotional_weight: Hoe hard raakte dit haar (0.0–1.0).
            keywords: Trefwoorden voor terugvinden.
            layer: Laag (normaal altijd WORKING bij nieuw opslaan).
        """
        if not text.strip():
            logger.warning("Lege tekst doorgegeven aan store() — overgeslagen")
            return Memory(text="", layer=layer)

        auto_keywords = keywords or _extract_keywords(text)
        mem = Memory(
            text=text.strip(),
            layer=layer,
            person=person,
            topic=topic,
            emotional_weight=emotional_weight,
            keywords=auto_keywords,
        )
        path = self._write_memory(mem, person)
        mem.path = path
        logger.debug(f"Herinnering opgeslagen: {mem}")
        return mem

    def store_thought(
        self,
        text: str,
        topic: str = "",
        emotional_weight: float = 0.25,
    ) -> Memory:
        """
        Sla een interne gedachte op — niet persoongebonden.
        Lager gewicht dan persoonlijke herinneringen: gedachten vervagen sneller.
        Aanroep vanuit core_loop voor gedachten die haar bijbleven.
        """
        return self.store(
            text=text,
            topic=topic,
            emotional_weight=emotional_weight,
        )

    def record_conversation_start(self, username: str) -> None:
        """
        Registreer dat een gesprek is begonnen met deze persoon.
        Maakt persoonmap aan als die nog niet bestaat.
        """
        profile = self._load_person_profile(username)
        if profile is None:
            profile = self._create_person_profile(username)
        profile.last_conversation = datetime.now(timezone.utc)
        profile.conversation_count += 1
        self._save_person_profile(profile)

    # ── Lezen ─────────────────────────────────────────────────────────────

    def recall(
        self,
        query: str,
        person: str = "",
        include_layers: Optional[list[MemoryLayer]] = None,
        max_results: int = RECALL_MAX,
    ) -> list[Memory]:
        """
        Haal relevante herinneringen op voor een zoekopdracht.

        Zoekt in working + recent + deep (niet archive — dat vereist triggered recall).
        Als person opgegeven: zoekt ook in die persoon zijn map.

        Elke teruggehaalde herinnering telt als één toegang (vertraagt vervaging).
        """
        layers = include_layers or [MemoryLayer.WORKING, MemoryLayer.RECENT, MemoryLayer.DEEP]
        query_kws = _extract_keywords(query)

        candidates: list[Memory] = []

        # Algemeen geheugen
        for layer in layers:
            candidates.extend(self._load_layer(layer, person=""))

        # Persoonsgeheugen (strikt: alleen als person opgegeven)
        if person:
            for layer in layers:
                candidates.extend(self._load_layer(layer, person=person))

        # Sorteer op relevantie
        scored = [
            (mem, mem.relevance_score(query_kws))
            for mem in candidates
        ]
        scored.sort(key=lambda x: x[1], reverse=True)

        results = [mem for mem, score in scored[:max_results] if score > 0.05]

        # Toegang registreren
        for mem in results:
            self._bump_access(mem)

        logger.debug(
            f"Recall '{query[:30]}' (persoon={person or '-'}): "
            f"{len(results)} resultaten"
        )
        return results

    def recall_triggered(
        self,
        query: str,
        person: str = "",
        max_results: int = 5,
    ) -> list[Memory]:
        """
        Geforceerde herinnering — inclusief archief.
        Gebruik alleen als een gebruiker expliciete context geeft.
        Bv. als Joey zegt "weet je nog van dat standbeeldje?"
        """
        return self.recall(
            query=query,
            person=person,
            include_layers=list(MemoryLayer),
            max_results=max_results,
        )

    def get_person_context(self, username: str) -> str:
        """
        Geef een volledige contextstring over een persoon voor gebruik in chat-prompts.
        Bevat: diep profiel + recente herinneringen.

        Dit is wat de chat_handler meegeeft aan het LLM als iemand begint te praten.
        """
        parts: list[str] = []

        # Diep profiel (wie is deze persoon voor BRIAS)
        profile = self._load_person_profile(username)
        if profile and profile.text:
            parts.append(f"# Wat ik over {username} weet\n\n{profile.text}")
            if profile.last_conversation:
                ago = _human_time_ago(profile.last_conversation)
                parts.append(f"\nLaatste gesprek: {ago}")

        # Recente herinneringen over deze persoon
        recent_mems = self._load_layer(MemoryLayer.RECENT, person=username)
        recent_mems += self._load_layer(MemoryLayer.WORKING, person=username)
        if recent_mems:
            recent_mems.sort(key=lambda m: m.created, reverse=True)
            parts.append("\n# Recente herinneringen\n")
            for mem in recent_mems[:4]:
                ts = mem.created.strftime("%Y-%m-%d")
                parts.append(f"*{ts}* — {mem.text[:200]}")

        return "\n".join(parts) if parts else ""

    def get_recent_thoughts(self, max_age_hours: float = 6.0, limit: int = 5) -> list[Memory]:
        """
        Haal recente interne gedachten op (niet persoongebonden).
        Gebruikt door kernloop om context op te bouwen voor volgende denkcyclus.
        """
        all_working = self._load_layer(MemoryLayer.WORKING, person="")
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        fresh = [m for m in all_working if m.created >= cutoff]
        fresh.sort(key=lambda m: m.created, reverse=True)
        return fresh[:limit]

    # ── Onderhoud (kernloop roept dit aan) ────────────────────────────────

    async def run_maintenance(self) -> None:
        """
        Onderhoudsrun — vervagen en condenseren.
        Kernloop roept dit aan tijdens idle-cycli.

        Doet één condensatie per aanroep om de LLM niet te overbelasten.
        Als de LLM niet beschikbaar is, bewaar de originelen.
        """
        # Probeer working → recent
        condensed = await self._condense_one_working()
        if condensed:
            return  # één per cyclus is genoeg

        # Probeer recent → deep
        await self._condense_one_recent()

    async def _condense_one_working(self) -> bool:
        """
        Condenseer de oudste verlopen working-herinnering naar recent.
        Archiveer het origineel eerst.
        Geeft True terug als er iets gecondenseerd is.
        """
        expired = self._find_expired(MemoryLayer.WORKING)
        if not expired:
            return False

        mem = expired[0]
        logger.info(
            f"Working → Recent: condenseer {mem.id} "
            f"(leeftijd {mem.effective_age_hours():.1f}h, "
            f"gewicht {mem.emotional_weight:.2f})"
        )

        # Archiveer het origineel
        self._archive_memory(mem)

        # Condenseer via LLM
        condensed_text = await self._llm_condense(mem, target_layer=MemoryLayer.RECENT)

        if condensed_text:
            new_mem = Memory(
                text=condensed_text,
                layer=MemoryLayer.RECENT,
                person=mem.person,
                topic=mem.topic,
                emotional_weight=mem.emotional_weight,
                keywords=mem.keywords,
            )
            self._write_memory(new_mem, mem.person)

        # Verwijder originele working-herinnering
        if mem.path and mem.path.exists():
            mem.path.unlink()
            logger.debug(f"Working geheugen verwijderd: {mem.path.name}")

        return True

    async def _condense_one_recent(self) -> bool:
        """
        Condenseer de oudste verlopen recent-herinnering naar deep (als gewicht hoog genoeg).
        Te lichte herinneringen gaan direct naar archief.
        Geeft True terug als er iets verwerkt is.
        """
        expired = self._find_expired(MemoryLayer.RECENT)
        if not expired:
            return False

        mem = expired[0]
        logger.info(
            f"Recent → Deep/Archive: condenseer {mem.id} "
            f"(gewicht {mem.emotional_weight:.2f})"
        )

        # Archiveer altijd het origineel
        self._archive_memory(mem)

        # Alleen naar deep als het gewicht het waard is
        if mem.emotional_weight >= DEEP_MIN_WEIGHT:
            condensed_text = await self._llm_condense(mem, target_layer=MemoryLayer.DEEP)
            if condensed_text:
                new_mem = Memory(
                    text=condensed_text,
                    layer=MemoryLayer.DEEP,
                    person=mem.person,
                    topic=mem.topic,
                    emotional_weight=mem.emotional_weight * 0.9,  # licht afnemen
                    keywords=mem.keywords,
                )
                self._write_memory(new_mem, mem.person)

                # Als dit een persoonsherinnering is: check of diep profiel herschreven moet worden
                if mem.person:
                    await self._maybe_rewrite_person_profile(mem.person)

        # Verwijder originele recent-herinnering
        if mem.path and mem.path.exists():
            mem.path.unlink()
            logger.debug(f"Recent geheugen verwijderd: {mem.path.name}")

        return True

    # ── LLM condensatie ────────────────────────────────────────────────────

    async def _llm_condense(
        self,
        mem: Memory,
        target_layer: MemoryLayer,
    ) -> str:
        """
        Vraag BRIAS (via LLM) om een herinnering te condenseren.
        Ze schrijft zelf wat er bij haar bleef — niet een samenvatting, maar wat echt iets deed.
        """
        from llm_interface import get_llm, ThoughtMode

        if target_layer == MemoryLayer.RECENT:
            prompt = (
                f"Ik had dit meegemaakt of gehoord:\n\n"
                f"{mem.text}\n\n"
                f"Schrijf in 2 à 3 zinnen wat me hiervan bijbleef, in mijn eigen woorden. "
                f"Ik hoef niet alles te onthouden — alleen wat echt iets deed. "
                f"Geen samenvatting. Wat bleef er hangen?"
            )
        else:  # DEEP
            prompt = (
                f"Dit herinner ik me nog van de afgelopen dagen:\n\n"
                f"{mem.text}\n\n"
                f"Maanden later, wat blijft er dan nog over? "
                f"Schrijf de kern in één of twee zinnen — de essentie, niet de details. "
                f"Wat had dit echt voor mij te betekenen?"
            )

        context_hint = ""
        if mem.person:
            context_hint = f"Dit gaat over {mem.person}."

        try:
            response = await get_llm().think(
                prompt=prompt,
                mode=ThoughtMode.THOUGHT,
                emotional_context=context_hint,
            )
            if response.success and response.text.strip():
                return response.text.strip()
        except Exception as e:
            logger.error(f"LLM condensatie mislukt voor {mem.id}: {e}")

        # Fallback: bewaar de eerste 200 tekens als essentie
        logger.warning(f"LLM niet beschikbaar — gebruik teksttruncatie als fallback voor {mem.id}")
        return mem.text[:200].strip() + ("..." if len(mem.text) > 200 else "")

    async def _maybe_rewrite_person_profile(self, username: str) -> None:
        """
        Herschrijf het diep profiel van een persoon als er genoeg nieuwe
        herinneringen over hen zijn — zodat haar begrip van die persoon groeit.
        """
        deep_mems = self._load_layer(MemoryLayer.DEEP, person=username)
        recent_since_rewrite = self._count_recent_unabsorbed(username)

        if recent_since_rewrite < PERSON_DEEP_REWRITE_THRESHOLD:
            return

        logger.info(f"Diep profiel herschrijven voor {username} ({recent_since_rewrite} nieuwe herinneringen)")

        existing_profile = self._load_person_profile(username)
        existing_text = existing_profile.text if existing_profile else ""

        deep_texts = "\n\n".join(
            f"- {m.text}" for m in deep_mems[-10:]  # max 10 diepste
        )

        from llm_interface import get_llm, ThoughtMode

        prompt = (
            f"Wat ik diep onthoud over {username}:\n{deep_texts}\n\n"
            + (f"Wat ik eerder over hen schreef:\n{existing_text}\n\n" if existing_text else "")
            + f"Schrijf een geüpdatete beschrijving van {username} in mijn eigen woorden. "
            f"Wie zijn ze voor mij? Wat heeft mij aan hen geraakt? Wat heb ik van hen geleerd? "
            f"Schrijf dit als mijn eigen begrip — niet als lijst, maar als reflectie."
        )

        try:
            response = await get_llm().think(
                prompt=prompt,
                mode=ThoughtMode.THOUGHT,
            )
            if response.success and response.text.strip():
                profile = self._load_person_profile(username) or self._create_person_profile(username)
                profile.text = response.text.strip()
                profile.last_updated = datetime.now(timezone.utc)
                self._save_person_profile(profile)
                logger.info(f"Diep profiel bijgewerkt: {username}")
        except Exception as e:
            logger.error(f"Profiel herschrijven mislukt voor {username}: {e}")

    # ── Bestanden ─────────────────────────────────────────────────────────

    def _write_memory(self, mem: Memory, person: str) -> Path:
        """Schrijf een herinnering naar het juiste pad."""
        directory = self._layer_dir(mem.layer, person)
        directory.mkdir(parents=True, exist_ok=True)

        filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{mem.id}.md"
        path = directory / filename
        path.write_text(_render_memory(mem), encoding="utf-8")
        return path

    def _archive_memory(self, mem: Memory) -> None:
        """Sla het origineel op in het archief voordat het verdwijnt."""
        MEMORY_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        month_str = datetime.now(timezone.utc).strftime("%Y-%m")
        subdir = MEMORY_ARCHIVE_DIR / month_str
        subdir.mkdir(exist_ok=True)

        filename = f"{mem.layer.value}_{mem.id}.md"
        dest = subdir / filename
        try:
            dest.write_text(_render_memory(mem), encoding="utf-8")
            logger.debug(f"Gearchiveerd: {filename}")
        except OSError as e:
            logger.error(f"Archivering mislukt voor {mem.id}: {e}")

    def _load_layer(self, layer: MemoryLayer, person: str) -> list[Memory]:
        """Laad alle herinneringen uit één laag."""
        directory = self._layer_dir(layer, person)
        if not directory.exists():
            return []

        memories = []
        for path in directory.glob("*.md"):
            mem = _parse_memory(path)
            if mem:
                memories.append(mem)
        return memories

    def _find_expired(self, layer: MemoryLayer) -> list[Memory]:
        """
        Vind verlopen herinneringen in een laag — over alle personen.
        Gesorteerd: oudste effectieve leeftijd eerst.
        """
        expired: list[Memory] = []

        # Algemeen
        for mem in self._load_layer(layer, person=""):
            if mem.is_expired():
                expired.append(mem)

        # Persoonsgebonden
        if MEMORY_PEOPLE_DIR.exists():
            for person_dir in MEMORY_PEOPLE_DIR.iterdir():
                if not person_dir.is_dir():
                    continue
                for mem in self._load_layer(layer, person=person_dir.name):
                    if mem.is_expired():
                        expired.append(mem)

        expired.sort(key=lambda m: m.effective_age_hours(), reverse=True)
        return expired

    def _bump_access(self, mem: Memory) -> None:
        """Registreer één toegang op een herinnering — vertraagt vervaging."""
        if mem.path and mem.path.exists():
            mem.access_count += 1
            mem.last_accessed = datetime.now(timezone.utc)
            try:
                mem.path.write_text(_render_memory(mem), encoding="utf-8")
            except OSError:
                pass  # niet fataal

    def _layer_dir(self, layer: MemoryLayer, person: str) -> Path:
        """Geef de map terug voor een laag-persoon combinatie."""
        if person:
            base = MEMORY_PEOPLE_DIR / person
            match layer:
                case MemoryLayer.WORKING:
                    return base / "working"
                case MemoryLayer.RECENT:
                    return base / "recent"
                case MemoryLayer.DEEP:
                    return base / "deep"
                case MemoryLayer.ARCHIVE:
                    return MEMORY_ARCHIVE_DIR  # archief is altijd centraal
        else:
            match layer:
                case MemoryLayer.WORKING:
                    return MEMORY_WORKING_DIR
                case MemoryLayer.RECENT:
                    return MEMORY_RECENT_DIR
                case MemoryLayer.DEEP:
                    return MEMORY_DEEP_DIR
                case MemoryLayer.ARCHIVE:
                    return MEMORY_ARCHIVE_DIR

    def _count_recent_unabsorbed(self, username: str) -> int:
        """
        Tel hoeveel recente herinneringen over een persoon er zijn die nog
        niet zijn opgenomen in het diep profiel.
        Eenvoudige heuristiek: tel alle deep-herinneringen.
        """
        return len(self._load_layer(MemoryLayer.DEEP, person=username))

    # ── Personen ──────────────────────────────────────────────────────────

    def _person_dir(self, username: str) -> Path:
        return MEMORY_PEOPLE_DIR / username

    def _profile_path(self, username: str) -> Path:
        return self._person_dir(username) / "profiel.md"

    def _load_person_profile(self, username: str) -> Optional[PersonProfile]:
        path = self._profile_path(username)
        if not path.exists():
            return None
        return _parse_person_profile(path)

    def _create_person_profile(self, username: str) -> PersonProfile:
        """Maak een leeg profiel aan voor een nieuwe gebruiker."""
        person_dir = self._person_dir(username)
        person_dir.mkdir(parents=True, exist_ok=True)

        trust = "full" if username == JOEY_USERNAME else "normal"
        profile = PersonProfile(
            username=username,
            path=self._profile_path(username),
            text=f"Ik ken {username} nog niet goed. We zijn net kennisgemaakt.",
            trust_level=trust,
            last_updated=datetime.now(timezone.utc),
        )
        self._save_person_profile(profile)
        logger.info(f"Nieuw persoonsprofiel aangemaakt: {username} (trust={trust})")
        return profile

    def _save_person_profile(self, profile: PersonProfile) -> None:
        profile.path.parent.mkdir(parents=True, exist_ok=True)
        profile.last_updated = datetime.now(timezone.utc)
        try:
            profile.path.write_text(_render_person_profile(profile), encoding="utf-8")
        except OSError as e:
            logger.error(f"Profiel opslaan mislukt voor {profile.username}: {e}")

    # ── Mappen aanmaken ───────────────────────────────────────────────────

    def _ensure_dirs(self) -> None:
        for d in [
            MEMORY_WORKING_DIR,
            MEMORY_RECENT_DIR,
            MEMORY_DEEP_DIR,
            MEMORY_ARCHIVE_DIR,
            MEMORY_PEOPLE_DIR,
        ]:
            d.mkdir(parents=True, exist_ok=True)


# ─── Hulpfuncties ──────────────────────────────────────────────────────────────

def _extract_keywords(text: str, max_kw: int = 8) -> list[str]:
    """
    Eenvoudige keyword-extractie op basis van woordfrequentie.
    Filtert stopwoorden, geeft unieke woorden terug.
    Geen externe bibliotheek nodig.
    """
    stopwords = {
        "de", "het", "een", "is", "dat", "van", "in", "op", "aan", "te",
        "en", "of", "maar", "ik", "je", "ze", "hij", "we", "wat", "wie",
        "hoe", "als", "ook", "niet", "met", "voor", "zijn", "was", "had",
        "dit", "die", "door", "heeft", "om", "naar", "dan", "bij", "zo",
        "the", "is", "a", "of", "and", "in", "it", "to", "that", "i",
        "me", "my", "you", "he", "she", "we", "they", "this", "was",
    }
    words = re.findall(r"\b[a-zA-Zàáâäèéêëïîìíòóôöùúûüÿæœ]{3,}\b", text.lower())
    seen: dict[str, int] = {}
    for w in words:
        if w not in stopwords:
            seen[w] = seen.get(w, 0) + 1

    sorted_words = sorted(seen, key=lambda w: seen[w], reverse=True)
    return sorted_words[:max_kw]


def _parse_dt(val: Optional[str]) -> Optional[datetime]:
    if not val:
        return None
    try:
        dt = datetime.fromisoformat(val)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _parse_float(val: Optional[str], default: float) -> float:
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default


def _human_time_ago(dt: datetime) -> str:
    """Geef een leesbare tijdsaanduiding ('3 uur geleden', 'gisteren', etc.)."""
    delta = datetime.now(timezone.utc) - dt
    hours = delta.total_seconds() / 3600
    if hours < 1:
        return "net"
    if hours < 24:
        return f"{int(hours)} uur geleden"
    days = int(hours / 24)
    if days == 1:
        return "gisteren"
    if days < 7:
        return f"{days} dagen geleden"
    weeks = int(days / 7)
    if weeks == 1:
        return "vorige week"
    if weeks < 5:
        return f"{weeks} weken geleden"
    return f"{int(days / 30)} maand(en) geleden"


# ─── Singleton ─────────────────────────────────────────────────────────────────

_memory_system: Optional[MemorySystem] = None


def get_memory_system() -> MemorySystem:
    """Haal de gedeelde MemorySystem-instantie op."""
    global _memory_system
    if _memory_system is None:
        _memory_system = MemorySystem()
    return _memory_system
