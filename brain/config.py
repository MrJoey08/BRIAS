"""
BRIAS — Configuratie en constanten.
Alle paden, LLM-instellingen, en gedragsparameters op één plek.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Basispaden ---
BASE_DIR = Path(__file__).parent.parent  # E:/BRIAS/
BRAIN_DIR = BASE_DIR / "brain"
MIND_DIR = BASE_DIR / "mind"
MEMORY_DIR = BASE_DIR / "memory"
JOURNAL_DIR = BASE_DIR / "journal"
SENSES_DIR = BASE_DIR / "senses"

# Mind subpaden
THOUGHTS_DIR = MIND_DIR / "thoughts"
WORLDMODEL_DIR = MIND_DIR / "worldmodel" / "investigations"
EMOTIONS_FILE = MIND_DIR / "emotions" / "current_state.json"
DREAMS_PRIVATE_DIR = MIND_DIR / "dreams" / "private"
DREAMS_JOEY_DIR = MIND_DIR / "dreams" / "shared_with_joey"
DREAMS_INSIGHTS_DIR = MIND_DIR / "dreams" / "insights"
SELF_DIR = MIND_DIR / "self"

# Geheugen subpaden
MEMORY_WORKING_DIR = MEMORY_DIR / "working"
MEMORY_RECENT_DIR = MEMORY_DIR / "recent"
MEMORY_DEEP_DIR = MEMORY_DIR / "deep"
MEMORY_ARCHIVE_DIR = MEMORY_DIR / "archive"
MEMORY_PEOPLE_DIR = MEMORY_DIR / "people"

# Senses
INBOX_DIR = SENSES_DIR / "inbox"

# --- LLM Instellingen ---
LLM_BACKEND = os.getenv("LLM_BACKEND", "llamacpp")  # "llamacpp" | "openai" | "anthropic"

# llama.cpp lokaal (OpenAI-compatible endpoint)
LLAMACPP_BASE_URL = os.getenv("LLAMACPP_BASE_URL", "http://localhost:8080/v1")
LLAMACPP_MODEL = os.getenv("LLAMACPP_MODEL", "mistral")

# OpenAI-compatible (ook voor cloud fallback)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Anthropic (toekomstig)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# LLM gedragsparameters
LLM_MAX_TOKENS_THOUGHT = 300       # interne gedachten — bondig
LLM_MAX_TOKENS_CHAT = 600          # gesprekken — meer ruimte
LLM_MAX_TOKENS_DREAM = 400         # dromen — associatief
LLM_TEMPERATURE_THOUGHT = 0.8      # enige variatie in denken
LLM_TEMPERATURE_CHAT = 0.7         # stabiel maar niet robotachtig
LLM_TEMPERATURE_DREAM = 1.1        # dromen — hoog, vrij associatief
LLM_TIMEOUT = 60                   # seconden

# --- Kernloop Tempo (in seconden) ---
TEMPO_ACTIVE = 30          # na intens gesprek — snelle gedachten
TEMPO_NORMAL = 120         # standaard
TEMPO_IDLE = 300           # na lange stilte
TEMPO_DREAM = 600          # droomstaat — langzaam, associatief

# Drempelwaarden voor droomstaat
DREAM_ENERGY_THRESHOLD = 0.25      # onder dit energieniveau → droomstaat mogelijk
DREAM_IDLE_MINUTES = 30            # minuten zonder input voor droomstaat

# --- Emotionele systeem parameters ---
EMOTION_DECAY_RATE = 0.02          # hoe snel emoties vervagen richting neutraal per cyclus
EMOTION_NEUTRAL = {
    "energy": 0.5,
    "uncertainty": 0.5,
    "connection": 0.3,
    "coherence": 0.6,
}

# --- Stimulus picker gewichten ---
STIMULUS_WEIGHT_TENSION = 3.0      # onopgeloste tegenspraak trekt het hardst
STIMULUS_WEIGHT_EMOTION = 2.0      # emotionele lading
STIMULUS_WEIGHT_FRESHNESS = 1.5    # nieuw > oud
STIMULUS_WEIGHT_NEGLECT = 1.0      # lang niet aangeraakt
STIMULUS_RANDOM_CHANCE = 0.15      # kans op willekeurige afwijking (menselijk gedrag)

# --- Gebruikers ---
JOEY_USERNAME = "joey"             # maakt, heeft volledige openheid
JOEY_TRUST_LEVEL = "full"

# --- Database ---
DB_DIR = BRAIN_DIR / "database"
USERS_DB = DB_DIR / "users.db"
PROFILES_DB = DB_DIR / "profiles.db"

# --- Geheugen vervagingsparameters ---
MEMORY_WORKING_HOURS = 4           # werkgeheugen vervalt na X uur
MEMORY_RECENT_DAYS = 7             # recent geheugen details vervagen na X dagen
MEMORY_DEEP_WEEKS = 12             # diep geheugen — essentie, weken

# --- Logging ---
LOG_THOUGHTS = True                # schrijft elke gedachte naar thoughts/
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
