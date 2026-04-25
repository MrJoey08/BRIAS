// ===== BRIAS · Shell =====
// Gedeelde drawer, settings en profile modal voor alle pagina's.
// Gebruik: voeg <script src="shell.js"></script> toe aan elke pagina,
// samen met <link rel="stylesheet" href="shell.css">.
// Roep SHELL.init() aan nadat je meData hebt opgehaald.

const SHELL = (() => {

  // ── Welke pagina is actief (voor de nav highlight) ──────────────────────
  // Detecteer automatisch op basis van de URL. Of overschrijf via SHELL.activePage.
  const PAGE_MAP = {
    'app.html':     'chat',
    'diary.html':   'journal',
    'planner.html': 'planner',
  };
  const _filename = location.pathname.split('/').pop() || 'app.html';
  let activePage = PAGE_MAP[_filename] || 'chat';

  // ── HTML injecteren ──────────────────────────────────────────────────────
  function _inject() {
    // Voeg drawer + settings + modal toe aan de body als ze er nog niet zijn
    if (!document.getElementById('shellDrawer')) {
      document.body.insertAdjacentHTML('beforeend', _drawerHTML());
    }
    if (!document.getElementById('shellSettings')) {
      document.body.insertAdjacentHTML('beforeend', _settingsHTML());
    }
    if (!document.getElementById('shellProfileModal')) {
      document.body.insertAdjacentHTML('beforeend', _profileModalHTML());
    }

    // Escape sluit settings/modal
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') {
        if (document.getElementById('shellProfileModal')?.classList.contains('open')) {
          closeProfileModal();
        } else if (document.getElementById('shellSettings')?.classList.contains('open')) {
          closeSettings();
        } else {
          closeDrawer();
        }
      }
      if (e.key === 'Enter') {
        if (document.getElementById('shellProfileModal')?.classList.contains('open')) {
          e.preventDefault(); submitProfileModal();
        }
      }
    });
  }

  // ── Drawer HTML ──────────────────────────────────────────────────────────
  function _drawerHTML() {
    const nav = [
      {
        id: 'chat',
        href: 'app.html',
        label: 'Chat',
        sub: 'Your conversation with BRIAS',
        icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round">
          <defs><linearGradient id="shellNg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#e8764a"/><stop offset="100%" stop-color="#d44a7a"/></linearGradient></defs>
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" stroke="url(#shellNg)"/>
        </svg>`,
        activeIcon: true,
      },
      {
        id: 'journal',
        href: 'diary.html',
        label: 'Journal',
        sub: 'You and BRIAS write here together',
        icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgba(228,224,227,.25)" stroke-width="1.8" stroke-linecap="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>`,
      },
      {
        id: 'planner',
        href: 'planner.html',
        label: 'Planner',
        sub: 'Keep track of mental steps',
        icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgba(228,224,227,.25)" stroke-width="1.8" stroke-linecap="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>`,
      },
      {
        id: 'mindspace',
        href: null,
        label: 'Mindspace',
        sub: 'Dump it here, sort later',
        soon: true,
        icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgba(228,224,227,.25)" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg>`,
      },
    ];

    const navItems = nav.map(n => {
      const isActive = n.id === activePage;
      const onclick = n.href
        ? (isActive ? `SHELL.closeDrawer()` : `window.location.href='${n.href}'`)
        : '';
      return `<button class="nav-item${isActive ? ' active' : ''}"${onclick ? ` onclick="${onclick}"` : ''}>
        <div class="nav-icon">${n.icon}</div>
        <div class="nav-texts">
          <div class="nav-name">${n.label}${n.soon ? ' <span class="soon-badge">soon</span>' : ''}</div>
          <div class="nav-sub">${n.sub}</div>
        </div>
      </button>`;
    }).join('');

    return `
<div class="drawer" id="shellDrawer">
  <div class="drawer-backdrop" onclick="SHELL.closeDrawer()"></div>
  <div class="drawer-panel">
    <div class="drawer-top"><div class="drawer-logo">BRIAS</div></div>
    <div class="drawer-nav">
      <div class="nav-section-label">Spaces</div>
      ${navItems}
    </div>
    <div class="drawer-divider"></div>
    <div class="drawer-footer">
      <div class="footer-av"><span id="shellDrawerInitial">—</span></div>
      <div class="footer-info">
        <div class="footer-name" id="shellDrawerName">—</div>
        <div class="footer-handle" id="shellDrawerHandle">—</div>
      </div>
      <button class="drawer-settings-btn" onclick="SHELL.openSettings();SHELL.closeDrawer();" title="Settings">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="rgba(228,224,227,.3)" stroke-width="1.5" stroke-linecap="round">
          <circle cx="12" cy="12" r="3"/>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l-.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
        </svg>
      </button>
    </div>
  </div>
</div>`;
  }

  // ── Settings HTML ────────────────────────────────────────────────────────
  function _settingsHTML() {
    return `
<div class="settings-overlay" id="shellSettings">
  <div class="settings-header">
    <div class="settings-title">Settings</div>
    <button class="settings-close-btn" onclick="SHELL.closeSettings()">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="rgba(228,224,227,.5)" stroke-width="2.5" stroke-linecap="round">
        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
      </svg>
    </button>
  </div>
  <div class="settings-tabs" id="shellSettingsTabs">
    <button class="stab active" onclick="SHELL.switchTab(0)">Profile</button>
    <button class="stab" onclick="SHELL.switchTab(1)">Plan</button>
    <button class="stab" onclick="SHELL.switchTab(2)">Permissions</button>
    <button class="stab" onclick="SHELL.switchTab(3)">Customise</button>
    <button class="stab" onclick="SHELL.switchTab(4)">About</button>
  </div>
  <div class="settings-content">
    <div class="settings-body" id="shellSettingsBody"></div>
  </div>
</div>`;
  }

  // ── Profile modal HTML ───────────────────────────────────────────────────
  function _profileModalHTML() {
    return `
<div class="pmodal" id="shellProfileModal">
  <div class="pmodal-card">
    <div class="pmodal-title" id="shellPmTitle">Edit</div>
    <div class="pmodal-sub" id="shellPmSub"></div>
    <input class="pmodal-input" id="shellPmInput" />
    <div class="pmodal-err" id="shellPmErr"></div>
    <div class="pmodal-actions">
      <button class="pmodal-btn pmodal-cancel" onclick="SHELL.closeProfileModal()">Cancel</button>
      <button class="pmodal-btn pmodal-save" id="shellPmSaveBtn" onclick="SHELL.submitProfileModal()">Save</button>
    </div>
  </div>
</div>`;
  }

  // ── Settings tabs content ────────────────────────────────────────────────
  const _tabs = [
    // 0 — Profile
    () => `
      <div class="s-section">
        <div class="s-section-title">Profile</div>
        <div class="s-row"><div class="s-row-left"><div class="s-row-label">Name</div></div><button class="s-btn" onclick="SHELL.editName()">${_esc(_meData?.display_name || 'Set name')}</button></div>
        <div class="s-row"><div class="s-row-left"><div class="s-row-label">Age</div></div><button class="s-btn" onclick="SHELL.editAge()">${_esc(_meData?.age == null ? 'Set age' : String(_meData.age))}</button></div>
        <div class="s-row"><div class="s-row-left"><div class="s-row-label">Email</div></div><div class="s-row-val">${_esc(_meData?.email || '—')}</div></div>
      </div>
      <div class="s-section">
        <div class="s-section-title">Manage</div>
        <div class="s-row"><div class="s-row-left"><div class="s-row-label">Password</div></div><button class="s-btn">Change</button></div>
        <div class="s-row"><div class="s-row-left"><div class="s-row-label">Sign out</div></div><button class="s-btn" onclick="SHELL.logout()">Sign out</button></div>
        <div class="s-row"><div class="s-row-left"><div class="s-row-label">Delete account</div></div><button class="s-btn danger">Delete</button></div>
      </div>`,
    // 1 — Plan
    () => `
      <p class="sub-intro"></p>
      <div class="sub-cards">
        <div class="sub-card"><div class="sub-card-name">Standard</div><div class="sub-card-price">€— <span>/ month</span></div><ul class="sub-card-perks"><li></li><li></li><li></li></ul></div>
        <div class="sub-card"><div class="sub-card-name">Supportive</div><div class="sub-card-price">€— <span>/ month</span></div><ul class="sub-card-perks"><li></li><li></li><li></li></ul></div>
        <div class="sub-card"><div class="sub-card-name">Advanced</div><div class="sub-card-price">€— <span>/ month</span></div><ul class="sub-card-perks"><li></li><li></li><li></li></ul></div>
      </div>`,
    // 2 — Permissions
    () => `
      <div class="s-section">
        <div class="s-section-title">Device</div>
        <div class="s-row"><div class="s-row-left"><div class="s-row-label">Notifications</div><div class="s-row-sub">Let BRIAS check in on you</div></div><button class="toggle" onclick="this.classList.toggle('on')"></button></div>
        <div class="s-row"><div class="s-row-left"><div class="s-row-label">Microphone</div><div class="s-row-sub">For voice messages</div></div><button class="toggle" onclick="this.classList.toggle('on')"></button></div>
      </div>
      <div class="s-section">
        <div class="s-section-title">Data</div>
        <div class="s-row"><div class="s-row-left"><div class="s-row-label">Save conversations</div><div class="s-row-sub">Keep your chat history</div></div><button class="toggle on" onclick="this.classList.toggle('on')"></button></div>
        <div class="s-row"><div class="s-row-left"><div class="s-row-label">Save journal</div><div class="s-row-sub">Stored locally on your device</div></div><button class="toggle on" onclick="this.classList.toggle('on')"></button></div>
      </div>`,
    // 3 — Customise
    () => `
      <div class="s-section">
        <div class="s-section-title">Appearance</div>
        <div class="s-row">
          <div class="s-row-left"><div class="s-row-label">Theme</div><div class="s-row-sub">Choose what feels right for you</div></div>
          <div class="theme-toggle${document.body.classList.contains('light') ? ' pill-right' : ''}" id="shellThemeToggle">
            <div class="theme-toggle-pill"></div>
            <button class="theme-opt${!document.body.classList.contains('light') ? ' active' : ''}" onclick="SHELL.setTheme('dark')">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
              <span>Dark</span>
            </button>
            <button class="theme-opt${document.body.classList.contains('light') ? ' active' : ''}" onclick="SHELL.setTheme('light')">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
              <span>Light</span>
            </button>
          </div>
        </div>
      </div>`,
    // 4 — About
    () => `<span class="about-logo">BRIAS</span>`,
  ];

  // ── State ────────────────────────────────────────────────────────────────
  let _meData = null;
  let _apiBase = 'https://api.brias.eu';
  let _token = localStorage.getItem('brias_token');
  let _pmField = null;
  let _logoutFn = null;

  function _api(path, opts = {}) {
    return fetch(_apiBase + path, {
      ...opts,
      headers: {
        'Content-Type': 'application/json',
        ...(_token ? { 'Authorization': 'Bearer ' + _token } : {}),
        ...(opts.headers || {}),
      },
    });
  }

  function _esc(s) {
    const d = document.createElement('div');
    d.textContent = String(s ?? '');
    return d.innerHTML;
  }

  // ── Public: init ─────────────────────────────────────────────────────────
  // Roep aan na het ophalen van meData in je pagina-script.
  // meData: het object van /api/me
  // options.logout: optionele override voor de logout functie
  // options.apiBase: optionele override voor de API url
  function init(meData, options = {}) {
    _meData = meData;
    if (options.apiBase) _apiBase = options.apiBase;
    if (options.logout) _logoutFn = options.logout;

    // Pas theme toe vanuit localStorage
    if (localStorage.getItem('brias_theme') === 'light') {
      document.body.classList.add('light');
    }

    _inject();
    _updateDrawerUser();
  }

  // ── Public: updateUser ───────────────────────────────────────────────────
  // Roep aan na een /api/me refresh om de drawer bij te werken.
  function updateUser(meData) {
    _meData = meData;
    _updateDrawerUser();
  }

  function _updateDrawerUser() {
    if (!_meData) return;
    const name = _meData.display_name || _meData.username || localStorage.getItem('brias_username') || '—';
    const el = id => document.getElementById(id);
    if (el('shellDrawerName')) el('shellDrawerName').textContent = name;
    if (el('shellDrawerHandle')) el('shellDrawerHandle').textContent = _meData.email || _meData.username || '—';
    if (el('shellDrawerInitial')) el('shellDrawerInitial').textContent = (name.charAt(0) || '?').toUpperCase();
  }

  // ── Drawer ───────────────────────────────────────────────────────────────
  function toggleDrawer() {
    const d = document.getElementById('shellDrawer');
    d?.classList.contains('open') ? closeDrawer() : openDrawer();
  }

  function openDrawer() {
    document.getElementById('shellDrawer')?.classList.add('open');
    document.getElementById('menuBtn')?.classList.add('open');
  }

  function closeDrawer() {
    document.getElementById('shellDrawer')?.classList.remove('open');
    document.getElementById('menuBtn')?.classList.remove('open');
  }

  // ── Settings ─────────────────────────────────────────────────────────────
  function openSettings() {
    document.getElementById('shellSettings')?.classList.add('open');
    switchTab(0);
    _refreshMe();
  }

  function closeSettings() {
    document.getElementById('shellSettings')?.classList.remove('open');
  }

  function switchTab(i) {
    document.querySelectorAll('#shellSettingsTabs .stab').forEach((t, j) => t.classList.toggle('active', j === i));
    const body = document.getElementById('shellSettingsBody');
    if (body) body.innerHTML = _tabs[i]();
  }

  function setTheme(mode) {
    if (mode === 'light') document.body.classList.add('light');
    else document.body.classList.remove('light');
    localStorage.setItem('brias_theme', mode);
    const toggle = document.getElementById('shellThemeToggle');
    if (toggle) toggle.classList.toggle('pill-right', mode === 'light');
    document.querySelectorAll('.theme-opt').forEach(btn => {
      const isDark = btn.getAttribute('onclick').includes('dark');
      btn.classList.toggle('active', mode === 'dark' ? isDark : !isDark);
    });
  }

  async function _refreshMe() {
    try {
      const r = await _api('/api/me');
      if (!r.ok) return;
      const d = await r.json();
      if (!d.logged_in) return;
      _meData = d;
      _updateDrawerUser();
      // herlaad actieve tab
      const active = document.querySelector('#shellSettingsTabs .stab.active');
      if (active) {
        const i = Array.from(document.querySelectorAll('#shellSettingsTabs .stab')).indexOf(active);
        if (i >= 0) switchTab(i);
      }
    } catch {}
  }

  // ── Profile modal ────────────────────────────────────────────────────────
  function editName() { _openProfileModal('name'); }
  function editAge() { _openProfileModal('age'); }

  function _openProfileModal(field) {
    _pmField = field;
    const err = document.getElementById('shellPmErr');
    err.textContent = ''; err.classList.remove('visible');
    const input = document.getElementById('shellPmInput');
    if (field === 'name') {
      document.getElementById('shellPmTitle').textContent = 'Your name';
      document.getElementById('shellPmSub').textContent = 'What should BRIAS call you?';
      input.type = 'text'; input.placeholder = 'Name';
      input.removeAttribute('min'); input.removeAttribute('max');
      input.value = _meData?.display_name || '';
    } else {
      document.getElementById('shellPmTitle').textContent = 'Your age';
      document.getElementById('shellPmSub').textContent = 'Optional. Helps BRIAS understand context.';
      input.type = 'number'; input.min = '10'; input.max = '120'; input.placeholder = 'Age';
      input.value = _meData?.age == null ? '' : String(_meData.age);
    }
    document.getElementById('shellProfileModal')?.classList.add('open');
    setTimeout(() => { input.focus(); input.select?.(); }, 80);
  }

  function closeProfileModal() {
    document.getElementById('shellProfileModal')?.classList.remove('open');
    _pmField = null;
  }

  async function submitProfileModal() {
    const input = document.getElementById('shellPmInput');
    const err = document.getElementById('shellPmErr');
    const btn = document.getElementById('shellPmSaveBtn');
    const v = input.value.trim();
    err.textContent = ''; err.classList.remove('visible');

    if (_pmField === 'name') {
      if (!v) { err.textContent = 'Please enter a name.'; err.classList.add('visible'); return; }
    } else {
      if (!_meData?.display_name) { err.textContent = 'Please set your name first.'; err.classList.add('visible'); return; }
      if (v && (!/^\d+$/.test(v) || parseInt(v) < 10 || parseInt(v) > 120)) {
        err.textContent = 'Please enter a number between 10 and 120.'; err.classList.add('visible'); return;
      }
    }

    btn.disabled = true; btn.textContent = 'Saving…';
    const res = _pmField === 'name'
      ? await _saveProfile(v, _meData?.age ?? null)
      : await _saveProfile(_meData.display_name, v === '' ? null : v);
    btn.disabled = false; btn.textContent = 'Save';
    if (res.ok) { closeProfileModal(); }
    else { err.textContent = res.error || 'Could not save. Try again.'; err.classList.add('visible'); }
  }

  async function _saveProfile(display_name, age) {
    try {
      const r = await _api('/api/profile', {
        method: 'POST',
        body: JSON.stringify({ display_name, age: age === '' || age == null ? null : parseInt(age) }),
      });
      if (!r.ok) {
        let detail = '';
        try { const d = await r.json(); detail = d.detail || ''; } catch {}
        return { ok: false, error: detail || `Could not save (HTTP ${r.status}).` };
      }
      await _refreshMe();
      return { ok: true };
    } catch {
      return { ok: false, error: 'Network error — could not reach BRIAS.' };
    }
  }

  // ── Logout ───────────────────────────────────────────────────────────────
  function logout() {
    if (_logoutFn) { _logoutFn(); return; }
    localStorage.removeItem('brias_token');
    localStorage.removeItem('brias_username');
    window.location.href = 'auth.html';
  }

  // ── Public API ───────────────────────────────────────────────────────────
  return {
    init,
    updateUser,
    // drawer
    toggleDrawer,
    openDrawer,
    closeDrawer,
    // settings
    openSettings,
    closeSettings,
    switchTab,
    setTheme,
    // profile modal
    editName,
    editAge,
    closeProfileModal,
    submitProfileModal,
    // logout
    logout,
    // activePage (leesbaar, ook instelbaar)
    get activePage() { return activePage; },
    set activePage(v) { activePage = v; },
  };

})();
