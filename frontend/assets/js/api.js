/* BRIAS — API verbinding */

const API = (() => {
  const BASE = '';   // zelfde origin

  function token() {
    return localStorage.getItem('brias_token') || '';
  }

  function headers(extra = {}) {
    return {
      'Content-Type': 'application/json',
      ...(token() ? { 'Authorization': `Bearer ${token()}` } : {}),
      ...extra,
    };
  }

  async function request(method, path, body) {
    try {
      const res = await fetch(BASE + path, {
        method,
        headers: headers(),
        body: body ? JSON.stringify(body) : undefined,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      return data;
    } catch (e) {
      throw e;
    }
  }

  return {
    get:  (path)       => request('GET',  path),
    post: (path, body) => request('POST', path, body),

    // Auth
    register: (email, name, password) =>
      request('POST', '/api/auth/register', { email, name, password }),
    login: (email, password) =>
      request('POST', '/api/auth/login', { email, password }),
    logout: () =>
      request('POST', '/api/auth/logout'),
    me: () =>
      request('GET', '/api/auth/me'),

    // Staat
    statePublic: () => request('GET', '/api/state/public'),
    state:       () => request('GET', '/api/state'),

    // Chat
    chat: (message) => request('POST', '/api/chat', { message }),

    // Admin
    adminConfig:       () => request('GET',  '/api/admin/config'),
    adminConfigUpdate: (cfg) => request('POST', '/api/admin/config', cfg),
    adminUsers:        () => request('GET',  '/api/admin/users'),
    adminBrain:        () => request('GET',  '/api/admin/brain'),

    // Token opslaan/verwijderen
    saveSession: (token, user, isAdmin) => {
      localStorage.setItem('brias_token', token);
      localStorage.setItem('brias_user',  JSON.stringify(user));
      localStorage.setItem('brias_admin', isAdmin ? '1' : '0');
    },
    clearSession: () => {
      localStorage.removeItem('brias_token');
      localStorage.removeItem('brias_user');
      localStorage.removeItem('brias_admin');
    },
    isLoggedIn:  () => !!localStorage.getItem('brias_token'),
    isAdmin:     () => localStorage.getItem('brias_admin') === '1',
    currentUser: () => {
      try { return JSON.parse(localStorage.getItem('brias_user') || 'null'); }
      catch { return null; }
    },
  };
})();

/* ── Toast notificaties ──────────────────────────────────────────────────── */
function toast(message, type = '') {
  const container = document.getElementById('toast-container')
    || (() => {
      const el = document.createElement('div');
      el.id = 'toast-container';
      document.body.appendChild(el);
      return el;
    })();

  const el = document.createElement('div');
  el.className = `toast${type ? ' toast-' + type : ''}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}
