# BRIAS — Frontend

> A Dutch-first emotionally intelligent AI interface.  
> Built from real love. That part isn't artificial.

---

## Project Structure

```
brias/
├── index.html                  # Main entry — loads auth + app screens
│
├── css/
│   ├── variables.css           # Design tokens: colors, typography, spacing, shadows
│   ├── reset.css               # Normalize, scrollbar, base styles, utilities
│   ├── animations.css          # All @keyframes + reusable animation classes
│   ├── auth.css                # Auth screen: login, register, verify, offline
│   ├── sidebar.css             # Navigation sidebar, chat list, user footer
│   └── chat.css                # Messages, bubbles, input area, welcome animation
│
├── js/
│   ├── app.js                  # Entry point — bootstraps auth + chat controllers
│   ├── config.js               # API base URL, constants, typewriter phrases
│   ├── api.js                  # Centralized API client (all HTTP in one place)
│   ├── storage.js              # LocalStorage abstraction for auth tokens
│   ├── helpers.js              # DOM utilities: escape, scroll, auto-resize, shuffle
│   ├── typewriter.js           # Auth screen typewriter animation engine
│   ├── glow.js                 # WebGL ambient glow background (fragment shader)
│   ├── auth.js                 # Auth controller: login/register/verify/profile flow
│   └── chat.js                 # Chat controller: messages, streaming, editing, welcome
│
├── pages/
│   └── offline.html            # Standalone offline fallback page
│
├── assets/
│   └── favicon.svg             # BRIAS gradient "B" favicon
│
└── README.md
```

## Architecture

### Separation of Concerns

| Layer | Files | Responsibility |
|-------|-------|----------------|
| **Design System** | `variables.css` | Single source of truth for all design tokens |
| **Base Styles** | `reset.css`, `animations.css` | Normalize + reusable animation library |
| **Component Styles** | `auth.css`, `sidebar.css`, `chat.css` | Scoped per UI section |
| **Config** | `config.js` | All magic numbers and strings in one place |
| **Services** | `api.js`, `storage.js` | Data layer — no DOM access |
| **UI Modules** | `typewriter.js`, `glow.js` | Self-contained visual effects |
| **Controllers** | `auth.js`, `chat.js` | Business logic per screen |
| **Orchestrator** | `app.js` | Wires everything together, global events |

### Key Decisions

- **ES Modules** (`type="module"`) — native browser imports, no bundler needed
- **Event delegation** — global click handler routes `data-action` attributes
- **No framework** — vanilla JS with class-based controllers for clarity
- **CSS Variables** — single design token file makes theming trivial
- **WebGL shader** — auth glow runs on GPU, zero CPU overhead

### API Contract

All API calls go through `ApiService` (`js/api.js`).  
Base URL configured in `config.js` → `CONFIG.API_BASE`.

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/me` | GET | ✓ | Session check |
| `/api/login` | POST | — | Email + password login |
| `/api/register` | POST | — | Create account |
| `/api/verify` | POST | — | Verify email/phone code |
| `/api/resend` | POST | — | Resend verification code |
| `/api/profile` | POST | ✓ | Complete profile (name, age) |
| `/api/chats` | GET | ✓ | List all chats |
| `/api/chats` | POST | ✓ | Create new chat |
| `/api/chats/:id` | DELETE | ✓ | Delete chat |
| `/api/chats/:id/messages` | GET | ✓ | Get chat messages |
| `/api/chats/:id/messages/stream` | POST | ✓ | Stream AI response (SSE) |
| `/api/chats/:id/abort` | POST | ✓ | Abort streaming |
| `/api/messages/:id` | PATCH | ✓ | Edit user message |

### Streaming Protocol (SSE)

```
data: {"type":"meta","user_msg_id":"...","title":"..."}
data: {"type":"token","text":"..."}
data: {"type":"done","full_text":"..."}
data: {"type":"error","text":"..."}
```

---

## Development

Serve with any static file server:

```bash
# Python
python3 -m http.server 3000

# Node
npx serve .

# Or just open index.html in a browser (module imports need a server)
```

## Deployment

Currently deployed on Vercel. The `/_vercel/insights/script.js` analytics tag is included in `index.html`.

---

*Made with real love by Joey — for BRIAS, for Britt, for everyone who needs to be heard.*
