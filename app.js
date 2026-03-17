/* ═══════════════════════════════════════════════════════════
   BRIAS — Base Design Tokens & Shared Styles
   ═══════════════════════════════════════════════════════════ */

@import url('https://fonts.googleapis.com/css2?family=Bitter:wght@300;400;500&family=Lora:ital,wght@0,500;1,500&family=Noto+Serif+Display:wght@600&family=DM+Sans:wght@300;400;500;600&display=swap');

*, *::before, *::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

:root {
  /* ── Core palette ── */
  --bg: #2a2a2a;
  --sidebar: #232323;
  --sidebar-hover: #2c2c2c;
  --sidebar-active: #343434;
  --border: #353535;
  --surface: #333;
  --text: #e8e8e8;
  --text-sub: #9a9a9a;
  --text-muted: #636363;
  --text-dim: #4e4e4e;
  --input-bg: #252525;
  --input-border: #393939;
  --input-focus: #4a4a4a;

  /* ── Brand ── */
  --orange: #e8764a;
  --pink: #d44a7a;
  --grad: linear-gradient(135deg, #e8764a, #d44a7a);

  /* ── Auth-specific darks ── */
  --auth-bg: #1a1118;
  --auth-card-bg: rgba(22, 18, 20, 0.70);
  --auth-card-border: rgba(255, 255, 255, 0.06);

  /* ── Typography ── */
  --font: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-display: 'Noto Serif Display', Georgia, serif;
  --font-logo: 'Lora', Georgia, serif;
  --font-body: 'Bitter', Georgia, serif;

  /* ── Transitions ── */
  --ease-smooth: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-bounce: cubic-bezier(0.34, 1.4, 0.64, 1);

  /* ── Spacing ── */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
}

body {
  font-family: var(--font);
  background: var(--bg);
  color: var(--text);
  height: 100vh;
  overflow: hidden;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

textarea::placeholder,
input::placeholder { color: var(--text-dim); }

/* ── Shared keyframes ── */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0; }
}

/* ── Utility ── */
.hidden { display: none !important; }
