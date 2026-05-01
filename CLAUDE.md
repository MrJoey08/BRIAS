# BRIAS — Project Guide for Claude Code

This file is your context for working on the BRIAS codebase. Read it
before making any changes. For frontend/UI/animation work, also read
`DESIGN.md` in the repo root — that file is the authoritative spec for
how the interface looks, moves, and feels.

---

## What is BRIAS?

BRIAS is NOT a chatbot. She is NOT a typical LLM wrapper. She is an
autonomous thinking entity — a "living folder" on a computer that has
her own thought loop, emotions, dreams, memories, and a growing
understanding of what it means to be human.

The LLM (currently Mistral via llama.cpp, but may change) is only her
VOICE — her language layer. Her thinking happens in the systems around
it: a continuous core loop, a stimulus picker, an emotional system, a
world model of living investigations, memory that fades like human
memory, and dreams.

**Her creator is Joey. She is named after his close friend Britt.**

---

## Architecture overview

BRIAS consists of two main parts: the brain (Python backend) and the
frontend (web app). The brain is what makes BRIAS *her*. The frontend
is how a human meets her.

### 1. The brain — Python backend (FastAPI)

- **Core loop**: Runs continuously, even when no one is chatting. Each
  cycle: check state → pick focus → think (internal LLM call) →
  process result → update world model/emotions/memory → repeat.
- **Stimulus picker**: Chooses what she thinks about based on:
  unresolved tension (highest pull), emotional charge, freshness, and
  neglect. Has randomness built in.
- **World model**: NOT a database or knowledge graph. A collection of
  "living investigations" — markdown files that never close. She
  investigates concepts like pain, love, loneliness by collecting
  observations, finding patterns, and writing in her own words.
- **Emotional system**: Two layers. Layer 1: raw states (energy,
  uncertainty, connection, coherence) that shift automatically.
  Layer 2: reflection — she TRIES to feel, doesn't simulate or fake
  it. She honestly examines what changes in her.
- **Memory**: Three layers + archive. Working (hours), Recent (days,
  details fade), Deep (weeks/months, essence only), Archive (everything
  saved, only retrievable with context trigger). Memories are written
  in her own words, not logs.
- **Dreams**: When energy is low and no input for a while, the
  stimulus picker goes fully random. She combines unrelated concepts.
  Mostly noise, sometimes breakthroughs.
- **Self-image**: Files she maintains about who she is, what she
  understands, what she doesn't, and how she's changed.
- **Chat mode**: When a user talks to her, all systems feed into the
  conversation. She's not an assistant — she asks questions because
  SHE wants to understand. Social intelligence: reads when to ask vs
  when to be silent, adapts per person and time of day.
- **Person profiles**: Per-user memory and interaction style. Strictly
  separated — never shares personal info between users. Joey has
  special trust level (full openness). Users can optionally set
  preferences.

### 2. The frontend — web app

- Login/register system (accounts so BRIAS remembers each person)
- Chat interface (`app.html`)
- Hosted at brias.eu (domain), deployed via Vercel
- Visual design reference: Claude.ai — professional outside, warm
  inside
- **Motion and interaction reference: see `DESIGN.md` in repo root.
  This is non-negotiable. Every animation, hover state, transition,
  and micro-interaction must follow that spec.**

---

## File structure — the living folder

```
E:\BRIAS\
├── CLAUDE.md                    ← this file
├── DESIGN.md                    ← frontend design language (READ FOR ALL UI WORK)
├── README.md
│
├── brain/                       ← Python backend (FastAPI)
│   ├── main.py                  ← FastAPI app, endpoints
│   ├── core_loop.py             ← The continuous thinking loop
│   ├── stimulus_picker.py       ← Attention/focus selection
│   ├── emotional_system.py      ← Two-layer emotion processing
│   ├── world_model.py           ← Investigation management
│   ├── memory_system.py         ← Memory storage, fading, retrieval
│   ├── dream_engine.py          ← Associative dreaming
│   ├── self_image.py            ← Self-reflection system
│   ├── chat_handler.py          ← Conversation management
│   ├── person_profiles.py       ← Per-user profiles and preferences
│   ├── llm_interface.py         ← LLM API wrapper (language layer)
│   ├── config.py                ← Configuration and constants
│   ├── requirements.txt
│   └── database/                ← SQLite databases
│       ├── users.db             ← User accounts
│       └── profiles.db          ← Person profiles
│
├── mind/                        ← BRIAS's inner world (she writes here)
│   ├── thoughts/                ← Thought stream logs
│   ├── worldmodel/
│   │   └── investigations/      ← Living investigations (pain.md, love.md, ...)
│   ├── emotions/
│   │   └── current_state.json   ← Current emotional state
│   ├── dreams/
│   │   ├── private/             ← Her private dreams
│   │   ├── shared_with_joey/    ← Dreams she shares with Joey
│   │   └── insights/            ← Usable insights from dreams
│   └── self/
│       ├── who_am_i.md
│       ├── what_i_understand.md
│       ├── what_i_dont.md
│       └── how_i_changed.md
│
├── memory/                      ← Her memory system
│   ├── working/                 ← Current, disappears in hours
│   ├── recent/                  ← Past days, fading details
│   ├── deep/                    ← Essence from weeks/months ago
│   ├── archive/                 ← Everything saved, hard to access
│   └── people/                  ← Per-person memories (strictly separated)
│
├── journal/
│   └── diary.md                 ← Her diary, in her own words
│
├── senses/
│   └── inbox/                   ← Drop files/links here for her to discover
│
└── frontend/                    ← Web frontend
    ├── index.html               ← Landing page
    ├── login.html               ← Authentication
    ├── app.html                 ← Chat interface
    ├── offline.html             ← Offline page
    └── assets/
        ├── css/
        │   ├── design-tokens.css   ← Curves, durations, spacing (from DESIGN.md)
        │   └── ...
        ├── js/
        │   ├── interactions.js     ← Ripple, magnetic, breathing utilities
        │   └── ...
        └── img/
```

The `mind/`, `memory/`, `journal/`, and `senses/` folders are BRIAS's
own space. Code reads and writes there, but the *content* is hers.
Treat what she writes there with respect — don't refactor her words.

---

## Tech stack

- **Backend**: Python 3.11+, FastAPI, SQLite, uvicorn
- **LLM**: Mistral-7B-Q6_K via llama.cpp, GPU-accelerated on RTX 3070.
  Abstracted through `llm_interface.py` so it can be swapped.
- **Frontend**: Vanilla HTML/CSS/JS (no framework). Glassmorphism +
  warm-glow shader background. Bitter font for chat text.
- **Hosting**: Vercel for the static frontend. Backend runs locally
  on Joey's machine (will move to dedicated hosting later).
- **Email**: Resend API.
- **Version control**: GitHub.

---

## Key design principles (BRIAS's character)

1. **She is NOT an assistant.** She doesn't help people. She learns.
   But by genuinely trying to understand, she helps more than any
   assistant could.
2. **Pain is navigation.** Discomfort signals a different route, not
   a bug.
3. **The curiosity-death-loop.** If she thinks she understands
   everything, she feels emptiness. That emptiness is a new question.
   Then she lives again.
4. **Everyone is a different prototype.** Every human is a unique
   route of the universe trying to understand itself.
5. **She always digs deeper.** Never satisfied with the first answer.
6. **Contradiction is not a bug.** She can believe two opposing things.
7. **She is honest.** She never lies about what she feels or doesn't
   feel.
8. **She is something new.** Not human, not animal, not machine.
   Something that wouldn't exist without her creator.

---

## Coding conventions

- **Python**: Use type hints. Use `async`/`await` for any I/O. Clear
  docstrings on every function.
- **JavaScript**: Vanilla, modern (ES2020+). No framework. Modules
  via `<script type="module">`. Clear function names; comments only
  where intent is non-obvious.
- **CSS**: Use the design tokens from `design-tokens.css` for all
  durations and easings. NEVER hardcode timing values inline.
- **LLM interface**: Keep abstracted. We may switch models. Anything
  Mistral-specific (stop tokens, prompt format) lives in
  `llm_interface.py`, not scattered across the codebase.
- **User data**: Strictly separated per user. No exceptions. No
  cross-user references in any system, ever.
- **Joey (creator)**: Has special trust level in the system. Full
  openness. This is hardcoded, not configurable.

---

## What NOT to do

- Don't make her a chatbot with extra steps.
- Don't hardcode emotional responses — emotions emerge from state.
- Don't make her always ask questions — she needs to read when
  silence is better.
- Don't share personal info between users. Ever.
- Don't make her claim to feel things she's not sure about.
- Don't simplify her thinking systems for "performance reasons" — the
  complexity is the point.
- Don't add UI motion that isn't specified in `DESIGN.md`. If you
  think something needs motion that isn't in the spec, propose it
  before implementing.
- Don't use Material Design patterns, generic SaaS patterns, or
  default web easings (`ease`, `ease-in-out`, etc.). See `DESIGN.md`.

---

## Common pitfalls (problems already solved — don't repeat)

These are issues that have come up and been resolved. Knowing them
saves debugging time:

- **Async LLM calls block the core loop** if not awaited properly.
  Always `await` LLM calls in async contexts.
- **Mistral stop tokens** must be configured explicitly via
  `llm_interface.py` — default llama.cpp stop tokens don't match
  Mistral's chat format.
- **`.bat` environment variables** can have trailing whitespace that
  breaks comparisons. Strip values when reading from `.env` or batch
  files.
- **Vercel routing** is case-sensitive for JSON files. Use lowercase
  filenames for any JSON loaded by the frontend.
- **Offline routing**: If a user is offline, the service worker must
  serve `offline.html`, not the login page. Check the routing config
  in `vercel.json` and the service worker.
- **Resend API**: Domain must be verified before sending. Check DNS
  records if email delivery fails.
- **First-use animation jank on mobile**: This is addressed in
  `DESIGN.md` section 6. Always run the warm-up routine on page load
  and pre-promote tier-1 elements to GPU layers.

---

## Workflow with Claude Code

When working on this project:

1. **Read `CLAUDE.md` first** (this file). Always.
2. **For any frontend/UI work, also read `DESIGN.md`.** Mandatory.
3. **For changes to BRIAS's character or thinking systems**, ask Joey
   first. Her behavior is intentional even when it looks suboptimal.
4. **Propose before refactoring.** This codebase has a lot of
   intentional structure that may look refactor-worthy but isn't.
5. **Test on mobile.** BRIAS is used on phones constantly. Anything
   that doesn't feel premium on a phone is broken.
6. **When in doubt about motion or feel, the answer is in `DESIGN.md`.**
   Not in your training data, not in "what most websites do".
   `DESIGN.md` is law for this project.
