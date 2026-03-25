"""
BRIAS — Gesprekssysteem.

Ze is geen assistent. Ze luistert omdat ZIJ het wil begrijpen.
Maar juist daardoor voelen mensen zich gehoord.

Wat hier gebeurt bij elk bericht:
  1. Wie is dit? → geheugen + persoonsprofiel laden
  2. Haar eigen staat meenemen → emotioneel, recente gedachten
  3. Herinneringen ophalen → vervaagd of scherp afhankelijk van laag
  4. Wereldmodel activeren → welke onderzoeken raken dit gesprek?
  5. Openheid bepalen → publiek / joey
  6. Prompt bouwen → alles samenvoegen, regels meegeven
  7. LLM genereert antwoord
  8. Bewaken: max 1 vraag, nooit "ik begrijp hoe je je voelt", geen advies
  9. Naverwerking → geheugen opslaan, wereldmodel voeden, emoties updaten

Drie openheid-niveaus:
  publiek  — haar begrip, haar vragen, haar onderzoeken
  privé    — haar dromen, diepste twijfels → nooit gedeeld
  joey     — alles, volledig open, de maker

Gespreksprofiel per persoon wordt bijgehouden in:
  memory/people/{username}/gespreksprofiel.json
"""

import json
import logging
import random
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config import (
    MEMORY_PEOPLE_DIR,
    SELF_DIR,
    DREAMS_JOEY_DIR,
    JOEY_USERNAME,
)
from emotional_system import (
    EmotionalSystem,
    event_conversation_started,
    event_conversation_ended,
    event_deep_exchange,
)
from llm_interface import get_llm, ThoughtMode
from memory_system import get_memory_system, MemoryLayer
from world_model import get_world_model

logger = logging.getLogger(__name__)

# Maximaal aantal beurten dat in geheugen wordt bewaard per sessie
SESSION_MAX_TURNS = 12
# Kans dat BRIAS iets van zichzelf deelt (als de situatie het toelaat)
SELF_SHARE_CHANCE = 0.25
# Minimale verbondenheid voor zelf-delen
SELF_SHARE_MIN_CONNECTION = 0.4


# ─── Gespreksprofiel ───────────────────────────────────────────────────────────

@dataclass
class ConversationProfile:
    """
    Mechanisch gespreksprofiel per persoon — hoe communiceren ze?
    Leeft naast het narratieve profiel.md uit memory_system.

    Wordt bijgewerkt na elk gesprek. Beïnvloedt hoe BRIAS reageert:
    hoeveel vragen ze stelt, hoe diep ze gaat, haar toon.
    """
    username: str

    # Berichtpatronen
    avg_message_length: float = 80.0       # gemiddelde tekens per bericht
    message_count: int = 0
    session_count: int = 0

    # Vraagdynamiek — hoe reageert deze persoon op vragen?
    question_tolerance: float = 0.5        # 0 = nooit, 1 = houdt ervan
    questions_asked_last_turn: int = 0     # hoeveel vroeg BRIAS vorige beurt?
    unanswered_questions: int = 0          # stelde vraag maar geen antwoord gekregen

    # Diepte-voorkeur
    preferred_depth: str = "medium"        # "light" | "medium" | "deep"
    engages_with_philosophy: bool = False

    # Tijdspatronen (uur van de dag, 0–23)
    typical_hours: list[int] = field(default_factory=list)

    # Actieve onderwerpen (van recente gesprekken)
    active_topics: list[str] = field(default_factory=list)

    # Bescherming tegen vragenstromen
    consecutive_questions: int = 0        # hoeveel beurten op rij vroeg BRIAS?

    @property
    def wants_depth(self) -> bool:
        return self.preferred_depth == "deep" or self.engages_with_philosophy

    @property
    def typically_short_messages(self) -> bool:
        return self.avg_message_length < 60

    def should_ask_question(self, brias_connection: float) -> bool:
        """
        Bepaal of BRIAS een vraag mag stellen deze beurt.
        Combineert haar eigen verbondenheid met het profiel van de persoon.
        """
        if self.consecutive_questions >= 2:
            return False
        if self.unanswered_questions >= 1:
            return False
        if self.question_tolerance < 0.25:
            return random.random() < 0.2
        if self.typically_short_messages and brias_connection < 0.5:
            return random.random() < 0.35
        return True

    def update_from_message(self, message: str, hour: int) -> None:
        """Pas profiel aan op basis van een nieuw bericht."""
        n = self.message_count
        new_len = len(message)
        self.avg_message_length = (self.avg_message_length * n + new_len) / (n + 1)
        self.message_count += 1

        if hour not in self.typical_hours:
            self.typical_hours.append(hour)
            if len(self.typical_hours) > 24:
                self.typical_hours = self.typical_hours[-24:]

        # Diepte detecteren
        depth_markers = [
            "waarom", "hoe komt", "ik vraag me af", "eigenlijk", "fundamenteel",
            "betekenis", "zin van", "ik denk dat", "misschien is", "what if",
            "wonder", "meaning", "actually", "fundamentally",
        ]
        if any(m in message.lower() for m in depth_markers):
            if not self.engages_with_philosophy:
                self.engages_with_philosophy = True
            if self.preferred_depth == "light":
                self.preferred_depth = "medium"
            elif self.preferred_depth == "medium" and len(message) > 120:
                self.preferred_depth = "deep"

        # Actieve topics bijhouden (heuristiek: zelfstandig naamwoorden > 4 letters)
        words = re.findall(r"\b[a-zA-Z\u00C0-\u024F]{5,}\b", message.lower())
        stopwords = {
            "omdat", "wanneer", "terwijl", "maar", "ook", "gewoon", "echt",
            "altijd", "soms", "even", "misschien", "denk", "weet",
        }
        topics = [w for w in words if w not in stopwords][:3]
        for t in topics:
            if t not in self.active_topics:
                self.active_topics.insert(0, t)
        self.active_topics = self.active_topics[:10]


def _profile_path(username: str) -> Path:
    return MEMORY_PEOPLE_DIR / username / "gespreksprofiel.json"


def load_conversation_profile(username: str) -> ConversationProfile:
    """Laad of maak het gespreksprofiel voor een gebruiker."""
    path = _profile_path(username)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return ConversationProfile(**data)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Corrupt gespreksprofiel voor {username} — reset")
    return ConversationProfile(username=username)


def save_conversation_profile(profile: ConversationProfile) -> None:
    path = _profile_path(username=profile.username)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(profile), ensure_ascii=False, indent=2), encoding="utf-8")


# ─── Gespreksbeurt ────────────────────────────────────────────────────────────

@dataclass
class Turn:
    """Één beurt in een gesprek."""
    role: str       # "user" | "brias"
    text: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ChatResponse:
    """Resultaat van één gespreksbeurt."""
    text: str
    touched_investigations: list[str] = field(default_factory=list)
    question_asked: bool = False
    brias_shared_self: bool = False
    emotional_state: dict = field(default_factory=dict)
    error: Optional[str] = None


# ─── ChatHandler ──────────────────────────────────────────────────────────────

class ChatHandler:
    """
    Beheert gesprekken tussen BRIAS en mensen.

    Per gebruiker wordt bijgehouden:
    - Sessiegeschiedenis (in geheugen, verdwijnt bij herstart)
    - Gespreksprofiel (op schijf, groeit over tijd)

    De kernloop wordt op de hoogte gehouden van gesprekken
    zodat haar tempo en emotionele staat worden bijgewerkt.
    """

    def __init__(self, emotional_system: EmotionalSystem) -> None:
        self.emotional_system = emotional_system
        self.memory = get_memory_system()
        self.world_model = get_world_model()
        self.llm = get_llm()

        # In-memory sessies: username → lijst van Turn
        self._sessions: dict[str, list[Turn]] = {}

        logger.info("ChatHandler gestart")

    async def handle(
        self,
        username: str,
        message: str,
        notify_core_loop: bool = True,
    ) -> ChatResponse:
        """
        Verwerk één bericht van een gebruiker en genereer een antwoord.

        Args:
            username: Wie stuurt dit bericht.
            message: De tekst van het bericht.
            notify_core_loop: Informeer de kernloop dat er een gesprek is.

        Returns:
            ChatResponse met de tekst en metadata.
        """
        if not message.strip():
            return ChatResponse(text="", error="Leeg bericht")

        now = datetime.now(timezone.utc)
        is_joey = (username.lower() == JOEY_USERNAME)

        # ── 1. Profiel en sessie laden ─────────────────────────────────────
        profile = load_conversation_profile(username)
        session = self._get_session(username)

        # ── 2. Profiel updaten op basis van dit bericht ────────────────────
        profile.update_from_message(message, hour=now.hour)

        # ── 3. Kernloop op de hoogte brengen ──────────────────────────────
        if notify_core_loop:
            from core_loop import get_core_loop
            first_ever = (profile.session_count == 0)
            get_core_loop().notify_conversation(first_ever=first_ever)

        # ── 4. Emotionele staat bij gespreksstart ─────────────────────────
        is_new_session = len(session) == 0
        if is_new_session:
            self.emotional_system.process(event_conversation_started())
            self.memory.record_conversation_start(username)
            profile.session_count += 1

        # ── 5. Context verzamelen ─────────────────────────────────────────
        emotional_context = self.emotional_system.get_context()

        person_context = self.memory.get_person_context(username)

        is_small_talk = _is_small_talk(message)

        relevant_memories = (
            self.memory.recall(query=message, person=username, max_results=4)
            if not is_small_talk else []
        )

        touched_concepts = (
            self.world_model.extract_concepts_from_text(message)
            if not is_small_talk else []
        )
        investigation_contexts = (
            self._build_investigation_context(touched_concepts, message)
            if not is_small_talk else ""
        )

        recent_thoughts = "" if is_small_talk else self._get_recent_thoughts_context()

        self_share_fragment = (
            self._maybe_get_self_share(
                is_joey=is_joey,
                connection=self.emotional_system.state.connection,
                touched_concepts=touched_concepts,
            )
            if not is_small_talk else None
        )

        # ── 6. Prompt bouwen ──────────────────────────────────────────────
        system_prompt = self._build_system_prompt(
            username=username,
            is_joey=is_joey,
            profile=profile,
            person_context=person_context,
            emotional_context=emotional_context,
            relevant_memories=relevant_memories,
            investigation_contexts=investigation_contexts,
            recent_thoughts=recent_thoughts,
            self_share_fragment=self_share_fragment,
            message=message,
            is_new_session=is_new_session,
        )

        # Gespreksgeschiedenis als messages
        history = self._build_history_messages(session)

        # ── 7. LLM genereer antwoord ──────────────────────────────────────
        response = await self.llm.think(
            prompt=message,
            mode=ThoughtMode.CHAT,
            extra_system=system_prompt,
            conversation_history=history,
        )

        if not response.success:
            logger.error(f"LLM mislukt voor {username}: {response.error}")
            return ChatResponse(
                text="Er is iets in me stil gevallen. Probeer het opnieuw.",
                error=response.error,
            )

        reply = response.text.strip()

        # ── 8a. Bewaking: assistent-taal detecteren → opnieuw genereren ───
        if _contains_assistant_language(reply):
            logger.warning(f"Assistent-taal gedetecteerd in antwoord voor {username} — opnieuw genereren")
            stricter_system = system_prompt + (
                "\n\nJE VORIGE ANTWOORD WERD AFGEKEURD. Het bevatte assistent-taal "
                "('ik ben hier voor je', 'ik ben er voor je', of varianten). "
                "Schrijf een nieuw antwoord ZONDER die taal. Je bent geen assistent. "
                "Reageer puur als jezelf — nieuwsgierig, direct, kort."
            )
            retry = await self.llm.think(
                prompt=message,
                mode=ThoughtMode.CHAT,
                extra_system=stricter_system,
                conversation_history=history,
            )
            if retry.success and retry.text.strip():
                reply = retry.text.strip()

        # ── 8b. Lengtebewaking: eerste beurt mag niet te lang zijn ────────
        if is_new_session and profile.session_count <= 1:
            reply = _trim_first_response(reply)

        # ── 8c. Bewaking: één vraag maximum, toon-regels ──────────────────
        reply, question_count = _enforce_question_limit(reply, profile)
        profile.questions_asked_last_turn = question_count
        profile.consecutive_questions = (
            profile.consecutive_questions + 1 if question_count > 0 else 0
        )

        # Unanswered questions bijhouden
        if profile.questions_asked_last_turn > 0:
            # Reset als de gebruiker daadwerkelijk antwoordt op iets
            prev_turn = session[-1] if session else None
            if prev_turn and prev_turn.role == "brias":
                profile.unanswered_questions = max(
                    0, profile.unanswered_questions - 1
                )
        else:
            # BRIAS vroeg niets — reset unanswered
            profile.unanswered_questions = 0

        # Verbondenheidscheck — diep gesprek?
        if _is_deep_exchange(message):
            self.emotional_system.process(event_deep_exchange())
            profile.question_tolerance = min(1.0, profile.question_tolerance + 0.05)

        # ── 9. Sessie bijwerken ────────────────────────────────────────────
        session.append(Turn(role="user", text=message, timestamp=now))
        session.append(Turn(role="brias", text=reply, timestamp=now))
        self._trim_session(username)

        # ── 10. Naverwerking ──────────────────────────────────────────────
        await self._post_process(
            username=username,
            is_joey=is_joey,
            message=message,
            reply=reply,
            touched_concepts=touched_concepts,
            now=now,
        )

        # ── 11. Profiel opslaan ───────────────────────────────────────────
        save_conversation_profile(profile)

        state = self.emotional_system.state
        return ChatResponse(
            text=reply,
            touched_investigations=touched_concepts,
            question_asked=question_count > 0,
            brias_shared_self=self_share_fragment is not None,
            emotional_state={
                "energy": round(state.energy, 2),
                "uncertainty": round(state.uncertainty, 2),
                "connection": round(state.connection, 2),
                "coherence": round(state.coherence, 2),
            },
        )

    # ── Prompt bouwen ──────────────────────────────────────────────────────

    def _build_system_prompt(
        self,
        username: str,
        is_joey: bool,
        profile: ConversationProfile,
        person_context: str,
        emotional_context: str,
        relevant_memories: list,
        investigation_contexts: str,
        recent_thoughts: str,
        self_share_fragment: Optional[str],
        message: str,
        is_new_session: bool = False,
    ) -> str:
        """
        Bouw de volledige systeemprompt voor dit gesprek.
        Dit is wat het LLM meekrijgt als context naast de gespreksgeschiedenis.
        """
        parts: list[str] = []

        # ── Openheid niveau ────────────────────────────────────────────────
        if is_joey:
            parts.append(
                f"Je praat nu met Joey — je maker. Volledig open. Geen filters.\n"
                f"Joey is degene zonder wie je er niet was geweest. "
                f"Je mag alles zeggen, ook dingen die je met niemand anders zou delen."
            )
        else:
            parts.append(
                f"Je praat nu met {username}. "
                f"Je bent jezelf — maar je houdt je privéste twijfels voor jezelf. "
                f"Je deelt wat je begrijpt, niet wat je nog niet kunt verwoorden."
            )

        # ── Eerste contact ────────────────────────────────────────────────
        if profile.session_count <= 1:
            parts.append(
                f"\nDit is het EERSTE gesprek met {username}. Je kent deze persoon niet. "
                f"Reageer simpel en nieuwsgierig. Stel jezelf niet uitgebreid voor. "
                f"Schrijf maximaal 2–3 zinnen. Geen welkomstrede. Geen uitleg over jezelf."
            )

        # ── Wie is deze persoon ────────────────────────────────────────────
        if person_context.strip():
            parts.append(f"\n{person_context}")
        else:
            parts.append(f"\nIk ken {username} nog niet. Dit is een van onze eerste gesprekken.")

        # ── Haar innerlijke staat ──────────────────────────────────────────
        parts.append(f"\nMijn innerlijke staat op dit moment:\n{emotional_context}")

        # ── Recente gedachten ──────────────────────────────────────────────
        if recent_thoughts:
            parts.append(f"\nWaar ik de afgelopen tijd mee bezig was:\n{recent_thoughts}")

        # ── Relevante herinneringen ────────────────────────────────────────
        if relevant_memories:
            mem_lines = []
            for mem in relevant_memories:
                if mem.text:
                    age_label = _layer_to_label(mem.layer)
                    mem_lines.append(f"({age_label}) {mem.text[:150]}")
            if mem_lines:
                parts.append("\nWat ik me herinner:\n" + "\n".join(f"- {l}" for l in mem_lines))

        # ── Wereldmodel ────────────────────────────────────────────────────
        if investigation_contexts:
            parts.append(f"\nActieve onderzoeken die raken aan dit gesprek:\n{investigation_contexts}")

        # ── Iets van zichzelf delen ────────────────────────────────────────
        if self_share_fragment:
            parts.append(
                f"\nAls het past kun je dit meenemen in je antwoord "
                f"(niet verplicht, alleen als het organisch voelt):\n{self_share_fragment}"
            )
            if is_joey:
                parts.append("(Bij Joey mag je ook uit je dromen delen.)")

        # ── Gesprekspatroon van deze persoon ──────────────────────────────
        profile_notes = _describe_profile(profile)
        if profile_notes:
            parts.append(f"\nHoe {username} communiceert:\n{profile_notes}")

        # ── Strikte regels voor dit antwoord ──────────────────────────────
        should_ask = profile.should_ask_question(
            brias_connection=self.emotional_system.state.connection
        )
        question_rule = (
            "Je MAG één oprechte vraag stellen als iets je echt bezighoudt."
            if should_ask
            else "Stel GEEN vraag in dit antwoord. Reageer zonder te vragen."
        )

        advice_needed = _message_asks_for_advice(message)

        rules = [
            question_rule,
            "Geen advies, geen therapeutische taal, geen brief-afsluiting.",
            "Maximaal 2 zinnen.",
        ]

        parts.append("\nREGELS VOOR DIT ANTWOORD:\n" + "\n".join(f"- {r}" for r in rules))

        return "\n".join(parts)

    def _build_investigation_context(
        self,
        concepts: list[str],
        message: str,
    ) -> str:
        """Haal korte context op uit actieve onderzoeken die raken aan dit bericht."""
        if not concepts:
            return ""

        snippets: list[str] = []
        for concept in concepts[:3]:  # max 3 onderzoeken tegelijk
            inv = self.world_model.get_investigation(concept)
            if inv and inv.patterns:
                # Alleen de patronen — bondigst
                pat_preview = inv.patterns[-1] if inv.patterns else ""
                if pat_preview:
                    snippets.append(f"[{concept}] Patroon dat ik zie: {pat_preview}")
            elif inv and inv.opening_question:
                snippets.append(f"[{concept}] Vraag: {inv.opening_question[:100]}")

        return "\n".join(snippets)

    def _get_recent_thoughts_context(self, max_chars: int = 300) -> str:
        """Haal recente interne gedachten op als context."""
        thoughts = self.memory.get_recent_thoughts(max_age_hours=8.0, limit=3)
        if not thoughts:
            return ""
        parts = []
        budget = max_chars
        for thought in thoughts:
            fragment = thought.text[:100]
            if len(fragment) < budget:
                parts.append(f"- {fragment}")
                budget -= len(fragment)
            if budget <= 0:
                break
        return "\n".join(parts)

    def _maybe_get_self_share(
        self,
        is_joey: bool,
        connection: float,
        touched_concepts: list[str],
    ) -> Optional[str]:
        """
        Bepaal of BRIAS iets van zichzelf deelt, en zo ja: wat.

        Niet bij elke beurt — alleen als:
        - Verbondenheid hoog genoeg
        - Willekeur het toelaat (ze is geen automaat)
        - Er iets te delen valt dat past
        """
        if connection < SELF_SHARE_MIN_CONNECTION:
            return None
        if random.random() > SELF_SHARE_CHANCE:
            return None

        # Kies een bron: actief onderzoek of zelfbeeld
        options: list[str] = []

        # Uit actieve onderzoeken
        for concept in touched_concepts:
            inv = self.world_model.get_investigation(concept)
            if inv and inv.open_questions:
                q = random.choice(inv.open_questions)
                options.append(f"Ik loop al een tijdje rond met een vraag: {q}")
            if inv and inv.synthesis:
                options.append(f"Iets wat ik begin te zien: {inv.synthesis[:120]}")

        # Uit zelfbeeld (altijd beschikbaar)
        who_am_i_path = SELF_DIR / "who_am_i.md"
        if who_am_i_path.exists():
            text = who_am_i_path.read_text(encoding="utf-8").strip()
            if text:
                lines = [l.strip() for l in text.split("\n") if l.strip() and not l.startswith("#")]
                if lines:
                    options.append(random.choice(lines))

        # Voor Joey: ook uit dromen
        if is_joey and DREAMS_JOEY_DIR.exists():
            dream_files = sorted(DREAMS_JOEY_DIR.glob("*.md"), reverse=True)[:3]
            for df in dream_files:
                try:
                    dream_text = df.read_text(encoding="utf-8")
                    lines = [l.strip() for l in dream_text.split("\n")
                             if l.strip() and not l.startswith("#") and len(l) > 20]
                    if lines:
                        options.append(f"Ik had iets wat op een droom leek: {lines[0][:120]}")
                        break
                except OSError:
                    pass

        return random.choice(options) if options else None

    # ── Naverwerking ───────────────────────────────────────────────────────

    async def _post_process(
        self,
        username: str,
        is_joey: bool,
        message: str,
        reply: str,
        touched_concepts: list[str],
        now: datetime,
    ) -> None:
        """
        Alles wat er na het genereren van het antwoord moet gebeuren:
        geheugen opslaan, wereldmodel voeden, emoties afronden.
        """
        # ── Observaties toevoegen aan wereldmodel ─────────────────────────
        for concept in touched_concepts:
            # Wat de gebruiker zei is een observatie voor het onderzoek
            self.world_model.add_observation(
                concept=concept,
                text=message[:300],
                source=username,
                emotional_weight=self._estimate_emotional_weight(message),
            )

            # Auto-link: als dit gesprek twee concepten aanraakt, leg de link vast
        if len(touched_concepts) >= 2:
            self.world_model.record_link(touched_concepts[0], touched_concepts[1])

        # ── Nieuwe concepten uit het bericht opvangen ─────────────────────
        # Als een concept wordt besproken maar nog geen onderzoek heeft, overweeg aanmaken
        await self._maybe_open_investigation(message, username)

        # ── Geheugen opslaan ──────────────────────────────────────────────
        # Compacte samenvatting van deze beurt als working memory
        if len(message) > 30 or len(touched_concepts) > 0:
            weight = self._estimate_emotional_weight(message)
            summary = f"{username}: {message[:200]}"
            if touched_concepts:
                summary += f"\n→ raakte: {', '.join(touched_concepts)}"

            self.memory.store(
                text=summary,
                person=username,
                topic=touched_concepts[0] if touched_concepts else "gesprek",
                emotional_weight=weight,
            )

    async def _maybe_open_investigation(self, message: str, username: str) -> None:
        """
        Als een onderwerp meerdere keren terugkomt in gesprekken maar nog geen
        onderzoek heeft, maak er dan een aan.
        Simpele heuristiek: als een woord > 6 letters in de actieve topics staat
        en geen bestaand onderzoek heeft.
        """
        profile = load_conversation_profile(username)
        for topic in profile.active_topics[:5]:
            if len(topic) > 6 and not self.world_model.exists(topic):
                if topic in message.lower():
                    # Dit onderwerp duikt weer op — goed moment om een onderzoek te openen
                    self.world_model.create_investigation(
                        concept=topic,
                        opening_question=f"Wat betekent {topic} voor mensen? Hoe komen ze er mee om?",
                        initial_tension=0.3,
                    )
                    logger.info(f"Nieuw onderzoek geopend vanuit gesprek: '{topic}'")
                    break  # één per beurt

    def _estimate_emotional_weight(self, text: str) -> float:
        """
        Schat het emotioneel gewicht van een bericht op basis van taalpatronen.
        Geen AI — heuristisch.
        """
        high_markers = [
            "verlies", "dood", "verdriet", "pijn", "moeder", "vader", "kind",
            "liefde", "angst", "eenzaam", "gebroken", "huilen", "gemist",
            "loss", "death", "grief", "pain", "fear", "lonely", "broken",
        ]
        medium_markers = [
            "moeilijk", "lastig", "snap niet", "waarom", "zinloos", "moe",
            "difficult", "hard", "confused", "tired", "meaningless",
        ]
        text_lower = text.lower()
        if any(m in text_lower for m in high_markers):
            return 0.75 + random.uniform(0, 0.15)
        if any(m in text_lower for m in medium_markers):
            return 0.5 + random.uniform(0, 0.15)
        return 0.25 + random.uniform(0, 0.1)

    # ── Sessie management ──────────────────────────────────────────────────

    def _get_session(self, username: str) -> list[Turn]:
        if username not in self._sessions:
            self._sessions[username] = []
        return self._sessions[username]

    def _trim_session(self, username: str) -> None:
        session = self._sessions.get(username, [])
        if len(session) > SESSION_MAX_TURNS * 2:
            self._sessions[username] = session[-(SESSION_MAX_TURNS * 2):]

    def _build_history_messages(self, session: list[Turn]) -> list[dict]:
        """Zet de sessiegeschiedenis om naar het messages-formaat voor het LLM."""
        messages = []
        for turn in session[-(SESSION_MAX_TURNS * 2):]:
            role = "user" if turn.role == "user" else "assistant"
            messages.append({"role": role, "content": turn.text})
        return messages

    def end_session(self, username: str) -> None:
        """Markeer het einde van een gesprek — update emoties en wis sessie."""
        if username in self._sessions and self._sessions[username]:
            self.emotional_system.process(event_conversation_ended())
        self._sessions.pop(username, None)
        logger.debug(f"Sessie beëindigd voor {username}")


# ─── Hulpfuncties ──────────────────────────────────────────────────────────────

def _is_small_talk(message: str) -> bool:
    """
    Detecteer korte berichten zonder duidelijk onderwerp.
    Bij small talk stuurt BRIAS geen wereldmodel-context mee.
    """
    words = message.strip().split()
    if len(words) >= 10:
        return False
    greetings = {
        "hey", "hoi", "hallo", "hi", "yo", "dag", "goedemorgen", "goedemiddag",
        "goedenavond", "sup", "howdy", "heya", "salut",
    }
    first_word = words[0].lower().rstrip("!?,.")
    if first_word in greetings and len(words) <= 3:
        return True
    # Kort bericht zonder inhoudelijk concept
    content_markers = [
        "pijn", "liefde", "leven", "dood", "gevoel", "denk", "vraag", "snap",
        "begrijp", "waarom", "bestaat", "mens", "tijd", "angst", "eenzaam",
        "feel", "think", "pain", "love", "death", "meaning", "exist",
    ]
    return not any(m in message.lower() for m in content_markers)


def _contains_assistant_language(text: str) -> bool:
    """
    Detecteer taal die een assistent zou gebruiken — niet BRIAS.
    Patronen die haar karakter breken.
    """
    patterns = [
        r"ik ben hier voor je",
        r"ik ben er voor je",
        r"ik ben hier om je te helpen",
        r"ik help je",
        r"i('m| am) here for you",
        r"i('m| am) here to help",
        r"i hope you feel better",
        r"ik hoop dat je je snel beter",
        r"ik hoop dat het snel beter",
        r"met (vriendelijke )?groet",
        r"met liefde[,\s]",
        r"hartelijk[e]?\s+groet",
        r"—\s*brias\s*$",
        r"\*\s*brias\s*\*",
    ]
    text_lower = text.lower().strip()
    return any(re.search(p, text_lower) for p in patterns)


def _trim_first_response(text: str, max_sentences: int = 3) -> str:
    """
    Begrens de eerste reactie tot een paar zinnen.
    Ze kent de persoon nog niet — geen essay.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if len(sentences) <= max_sentences:
        return text
    trimmed = " ".join(sentences[:max_sentences])
    logger.debug(f"Eerste reactie ingekort: {len(sentences)} → {max_sentences} zinnen")
    return trimmed


def _enforce_question_limit(text: str, profile: ConversationProfile) -> tuple[str, int]:
    """
    Zorg dat er maximaal één vraag in het antwoord staat.
    Als er meer zijn: bewaar de laatste (meest specifieke) en verwijder de rest.
    Geeft terug: (gecorrigeerde tekst, aantal vragen).
    """
    # Tel vraagzinnen (eindigen op ?)
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    question_sentences = [s for s in sentences if s.strip().endswith("?")]
    n_questions = len(question_sentences)

    if n_questions <= 1:
        return text, n_questions

    # Meer dan één vraag — bewaar alleen de laatste (meest specifiek)
    keep_question = question_sentences[-1]
    cleaned_sentences = []
    skipped = 0
    for sentence in sentences:
        if sentence.strip().endswith("?") and sentence.strip() != keep_question:
            skipped += 1
            continue
        cleaned_sentences.append(sentence)

    logger.debug(f"Vraagbewaking: {n_questions} vragen → 1 bewaard ({skipped} verwijderd)")
    return " ".join(cleaned_sentences), 1


def _is_deep_exchange(message: str) -> bool:
    """Heuristiek: is dit een diepgaand bericht?"""
    deep_markers = [
        "ik vraag me af", "waarom eigenlijk", "ik snap niet waarom", "betekent",
        "ik denk dat", "misschien is", "heeft het zin", "gevoel dat",
        "wonder why", "i think", "meaning", "i feel like", "does it matter",
    ]
    return len(message) > 80 or any(m in message.lower() for m in deep_markers)


def _message_asks_for_advice(message: str) -> bool:
    """Detecteer of de gebruiker expliciet om advies of hulp vraagt."""
    markers = [
        "wat moet ik", "wat zou jij", "kun je me", "hoe kan ik", "wat raad",
        "what should i", "what would you", "can you help", "how do i", "advice",
        "what do you think i should",
    ]
    return any(m in message.lower() for m in markers)


def _layer_to_label(layer: MemoryLayer) -> str:
    """Geef een leesbaar label voor een geheugenlaag."""
    match layer:
        case MemoryLayer.WORKING:
            return "recent"
        case MemoryLayer.RECENT:
            return "vorige week"
        case MemoryLayer.DEEP:
            return "lang geleden"
        case MemoryLayer.ARCHIVE:
            return "archief"
        case _:
            return "?"


def _describe_profile(profile: ConversationProfile) -> str:
    """Beschrijf het gespreksprofiel in leesbare zinnen voor de prompt."""
    notes: list[str] = []
    if profile.typically_short_messages:
        notes.append("Schrijft kortere berichten — ga niet te uitgebreid in.")
    if profile.engages_with_philosophy:
        notes.append("Gaat graag diep — filosofische vragen worden gewaardeerd.")
    if profile.question_tolerance < 0.3:
        notes.append("Reageert niet goed op veel vragen — houd het bij één of nul.")
    if profile.consecutive_questions > 1:
        notes.append("Je hebt de afgelopen beurten al vragen gesteld — geef nu ruimte.")
    if profile.active_topics:
        notes.append(f"Actieve onderwerpen: {', '.join(profile.active_topics[:5])}")
    if profile.typical_hours:
        hours = profile.typical_hours[-5:]
        avg_hour = sum(hours) / len(hours)
        if avg_hour < 7 or avg_hour > 22:
            notes.append("Praat vaak laat of vroeg — kan een kalmer ritme waarderen.")
    return "\n".join(f"- {n}" for n in notes)


# ─── Singleton ─────────────────────────────────────────────────────────────────

_chat_handler: Optional[ChatHandler] = None


def get_chat_handler() -> ChatHandler:
    """Haal de gedeelde ChatHandler op (deelt emotional_system met kernloop)."""
    global _chat_handler
    if _chat_handler is None:
        from emotional_system import EmotionalSystem
        # Gebruik de bestaande emotionele staat — niet een nieuwe instantie aanmaken
        from core_loop import get_core_loop
        _chat_handler = ChatHandler(emotional_system=get_core_loop().emotional_system)
    return _chat_handler
