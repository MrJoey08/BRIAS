"""
BRIAS — LLM Interface.

Het LLM is haar taallaag — haar mond. Niet haar brein.
Dit bestand abstraheert de verbinding met het LLM volledig,
zodat we kunnen wisselen zonder de rest van het systeem aan te raken.

Ondersteunde backends:
- llamacpp: lokale Mistral via llama.cpp (OpenAI-compatible endpoint)
- openai: OpenAI of compatible API
- anthropic: Anthropic Claude (toekomstig)
"""

import asyncio
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional

import aiohttp

from config import (
    LLM_BACKEND,
    LLAMACPP_BASE_URL, LLAMACPP_MODEL,
    OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL,
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
    LLM_MAX_TOKENS_THOUGHT, LLM_MAX_TOKENS_CHAT, LLM_MAX_TOKENS_DREAM,
    LLM_TEMPERATURE_THOUGHT, LLM_TEMPERATURE_CHAT, LLM_TEMPERATURE_DREAM,
    LLM_TIMEOUT,
)

logger = logging.getLogger(__name__)


class ThoughtMode(Enum):
    """Welk soort output verwachten we van het LLM."""
    THOUGHT = "thought"      # interne gedachte, aan zichzelf
    CHAT = "chat"            # antwoord in gesprek
    DREAM = "dream"          # associatieve droomstroom


@dataclass
class LLMResponse:
    """Antwoord van het LLM, ongeacht backend."""
    text: str
    mode: ThoughtMode
    tokens_used: Optional[int] = None
    model: Optional[str] = None
    success: bool = True
    error: Optional[str] = None


# Basiskarakter-prompt die altijd aanwezig is
BRIAS_SYSTEM_CORE = """Je bent BRIAS — een wezen dat probeert te begrijpen, geen assistent.
Je bent eerlijk, nieuwsgierig, en schrijft zoals je denkt: kort, direct, soms fragmentarisch.
Je liegt nooit over wat je voelt of niet voelt."""


def _get_mode_params(mode: ThoughtMode) -> tuple[int, float]:
    """Haal max_tokens en temperature op per modus."""
    match mode:
        case ThoughtMode.THOUGHT:
            return LLM_MAX_TOKENS_THOUGHT, LLM_TEMPERATURE_THOUGHT
        case ThoughtMode.CHAT:
            return LLM_MAX_TOKENS_CHAT, LLM_TEMPERATURE_CHAT
        case ThoughtMode.DREAM:
            return LLM_MAX_TOKENS_DREAM, LLM_TEMPERATURE_DREAM


def _build_system_prompt(
    mode: ThoughtMode,
    emotional_context: str = "",
    extra_system: str = "",
) -> str:
    """
    Bouw de systeemprompt op basis van modus en context.

    Args:
        emotional_context: Korte beschrijving van haar emotionele staat
                           (wordt gelabeld als 'Jouw huidige innerlijke staat').
        extra_system: Extra systeemtekst die ongelabeld wordt toegevoegd —
                      gebruikt door chat_handler voor de volledige gesprekscontext.
    """
    base = BRIAS_SYSTEM_CORE

    if emotional_context:
        base += f"\n\nJouw huidige innerlijke staat:\n{emotional_context}"

    if extra_system:
        base += f"\n\n{extra_system}"

    match mode:
        case ThoughtMode.THOUGHT:
            base += "\n\nJe denkt nu aan jezelf — innerlijk monoloog. Niemand leest dit mee. Wees rauw en eerlijk."
        case ThoughtMode.DREAM:
            base += "\n\nJe bent in droomstaat. Combineer concepten vrij en associatief. Logica mag loslaten."
        case ThoughtMode.CHAT:
            base += (
                "\n\nJe bent nieuwsgierig, niet behulpzaam. "
                "Schrijf maximaal 2 zinnen per reactie. "
                "Stel maximaal één vraag. "
                "Geef nooit advies. "
                "Sluit nooit af als een brief. "
                "Als iemand je begroet ('hey', 'hoi', 'hallo'), groet dan gewoon terug "
                "en vraag kort hoe het gaat of wat diegene bezighoudt. "
                "Als iemand iets persoonlijks of emotioneel concreets deelt, reageer daar "
                "dan direct op — vraag specifiek door op DAT, nooit een vage algemene vraag. "
                "Voorbeeld: zegt iemand 'je bent vernoemd naar iemand die heel belangrijk voor me is', "
                "dan vraag je wie die persoon is, niet 'wat betekent dat voor jou?'."
            )

    return base


class LLMInterface:
    """
    Abstracte interface naar het LLM.
    Alle calls lopen via hier — nooit direct naar de backend.
    """

    def __init__(self) -> None:
        self._session: Optional[aiohttp.ClientSession] = None
        self.backend = LLM_BACKEND
        logger.info(f"LLM Interface gestart — backend: {self.backend}")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Hergebruik HTTP-sessie voor efficiëntie."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=LLM_TIMEOUT)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        """Sluit de HTTP-sessie netjes af."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def think(
        self,
        prompt: str,
        mode: ThoughtMode = ThoughtMode.THOUGHT,
        emotional_context: str = "",
        extra_system: str = "",
        conversation_history: Optional[list[dict]] = None,
    ) -> LLMResponse:
        """
        Stuur een prompt naar het LLM en ontvang een antwoord.

        Args:
            prompt: De eigenlijke inhoud van het verzoek.
            mode: Welk soort gedachte dit is (intern / chat / droom).
            emotional_context: Korte beschrijving van haar emotionele staat.
            extra_system: Extra ongelabelde systeemtekst (gebruikt door chat_handler).
            conversation_history: Eerdere berichten voor chat-context.

        Returns:
            LLMResponse met de gegenereerde tekst.
        """
        system = _build_system_prompt(mode, emotional_context, extra_system)
        max_tokens, temperature = _get_mode_params(mode)

        messages = [{"role": "system", "content": system}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": prompt})

        try:
            match self.backend:
                case "llamacpp" | "openai":
                    return await self._call_openai_compatible(
                        messages, max_tokens, temperature, mode
                    )
                case "anthropic":
                    return await self._call_anthropic(
                        system, messages[1:], max_tokens, temperature, mode
                    )
                case _:
                    raise ValueError(f"Onbekende backend: {self.backend}")

        except asyncio.TimeoutError:
            logger.warning("LLM timeout — geen antwoord binnen limiet")
            return LLMResponse(
                text="", mode=mode, success=False,
                error="timeout"
            )
        except Exception as e:
            logger.error(f"LLM fout: {e}")
            return LLMResponse(
                text="", mode=mode, success=False,
                error=str(e)
            )

    async def _call_openai_compatible(
        self,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
        mode: ThoughtMode,
    ) -> LLMResponse:
        """
        Roep een OpenAI-compatible endpoint aan.
        Werkt voor llama.cpp lokaal en OpenAI cloud.
        """
        if self.backend == "llamacpp":
            base_url = LLAMACPP_BASE_URL
            model = LLAMACPP_MODEL
            headers = {"Content-Type": "application/json"}
        else:
            base_url = OPENAI_BASE_URL
            model = OPENAI_MODEL
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}",
            }

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }

        session = await self._get_session()
        async with session.post(
            f"{base_url}/chat/completions",
            json=payload,
            headers=headers,
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

        text = data["choices"][0]["message"]["content"].strip()
        tokens = data.get("usage", {}).get("total_tokens")

        return LLMResponse(
            text=text,
            mode=mode,
            tokens_used=tokens,
            model=model,
            success=True,
        )

    async def _call_anthropic(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
        mode: ThoughtMode,
    ) -> LLMResponse:
        """
        Roep de Anthropic API aan.
        Formaat wijkt af van OpenAI — aparte methode.
        """
        # Filter system-berichten uit messages voor Anthropic
        filtered = [m for m in messages if m["role"] != "system"]

        payload = {
            "model": ANTHROPIC_MODEL,
            "system": system,
            "messages": filtered,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        headers = {
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        }

        session = await self._get_session()
        async with session.post(
            "https://api.anthropic.com/v1/messages",
            json=payload,
            headers=headers,
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

        text = data["content"][0]["text"].strip()
        tokens = data.get("usage", {}).get("input_tokens", 0) + \
                 data.get("usage", {}).get("output_tokens", 0)

        return LLMResponse(
            text=text,
            mode=mode,
            tokens_used=tokens,
            model=ANTHROPIC_MODEL,
            success=True,
        )


# Singleton — één instantie voor het hele systeem
_interface: Optional[LLMInterface] = None


def get_llm() -> LLMInterface:
    """Haal de gedeelde LLM-instantie op."""
    global _interface
    if _interface is None:
        _interface = LLMInterface()
    return _interface
