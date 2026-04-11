// ===== BRIAS · Auth Logic =====

const API = 'https://api.brias.eu';

let authMode = 'login';
let authContact = '';
let _authRetryTimer = null;
let _authRetryDelay = 3000;

function api(path, opts = {}) {
  const token = localStorage.getItem('brias_token');
  return fetch(API + path, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': 'Bearer ' + token } : {}),
      ...(opts.headers || {})
    }
  });
}

async function checkOnline() {
  try {
    await fetch(API + '/api/me', { method: 'GET', signal: AbortSignal.timeout(3000) });
    return true;
  } catch(e) { return false; }
}

function setOffline(off) {
  const el = document.getElementById('authOffline');
  const card = document.getElementById('authCard');
  if (off) {
    el.classList.remove('hidden');
    if (card) card.classList.add('is-offline');
    if (!_authRetryTimer) {
      _authRetryDelay = 3000;
      _scheduleAuthRetry();
    }
  } else {
    el.classList.add('hidden');
    if (card) card.classList.remove('is-offline');
    _authRetryDelay = 3000;
    if (_authRetryTimer) { clearTimeout(_authRetryTimer); _authRetryTimer = null; }
  }
}

function _scheduleAuthRetry() {
  _authRetryTimer = setTimeout(async () => {
    _authRetryTimer = null;
    if (await checkOnline()) {
      setOffline(false);
    } else {
      // Exponential backoff: 3s → 6s → 12s → 24s → max 30s
      _authRetryDelay = Math.min(_authRetryDelay * 2, 30000);
      _scheduleAuthRetry();
    }
  }, _authRetryDelay);
}

function showStep(n) {
  ['authStep1', 'authStep2', 'authStep3'].forEach(s => document.getElementById(s)?.classList.add('hidden'));
  document.getElementById('authStep' + n)?.classList.remove('hidden');
}

function toggleAuth() {
  authMode = authMode === 'login' ? 'register' : 'login';
  document.getElementById('authSubmit').textContent = authMode === 'login' ? 'Log in' : 'Sign up';
  document.getElementById('authSwitch').innerHTML = authMode === 'login'
    ? 'No account? <a onclick="toggleAuth()">Sign up</a>'
    : 'Already have an account? <a onclick="toggleAuth()">Log in</a>';
  document.getElementById('authError').classList.add('hidden');
}

async function doAuthStep1() {
  const c = document.getElementById('authContact').value.trim();
  const p = document.getElementById('authPass').value;
  const e = document.getElementById('authError');
  if (!c || !p) { e.textContent = 'Please fill in all fields'; e.classList.remove('hidden'); return; }
  e.classList.add('hidden');
  authContact = c;
  try {
    const r = await api(authMode === 'login' ? '/api/login' : '/api/register', {
      method: 'POST', body: JSON.stringify({ contact: c, password: p })
    });
    const d = await r.json();
    if (!r.ok) { e.textContent = d.detail || 'Something went wrong'; e.classList.remove('hidden'); return; }
    if (d.token) {
      localStorage.setItem('brias_token', d.token);
      localStorage.setItem('brias_username', d.username);
      window.location.href = 'app.html';
      return;
    }
    document.getElementById('sentTo').textContent = c;
    showStep(2);
  } catch(err) {
    e.textContent = 'Could not connect to server';
    e.classList.remove('hidden');
  }
}

async function doAuthStep2() {
  const code = document.getElementById('authCode').value.trim();
  const e = document.getElementById('authError2');
  if (!code) { e.textContent = 'Please enter the verification code'; e.classList.remove('hidden'); return; }
  e.classList.add('hidden');
  try {
    const r = await api('/api/verify', { method: 'POST', body: JSON.stringify({ contact: authContact, code }) });
    const d = await r.json();
    if (!r.ok) { e.textContent = d.detail || 'Invalid code'; e.classList.remove('hidden'); return; }
    localStorage.setItem('brias_token', d.token);
    localStorage.setItem('brias_username', d.username);
    if (authMode === 'register' && !d.profile_complete) { showStep(3); return; }
    window.location.href = 'app.html';
  } catch(err) {
    e.textContent = 'Could not connect to server';
    e.classList.remove('hidden');
  }
}

async function resendCode() {
  try { await api('/api/resend', { method: 'POST', body: JSON.stringify({ contact: authContact }) }); } catch(e) {}
}

async function doAuthStep3() {
  const name = document.getElementById('authName').value.trim();
  const age = document.getElementById('authAge').value.trim();
  const e = document.getElementById('authError3');
  if (!name) { e.textContent = 'We need at least a name'; e.classList.remove('hidden'); return; }
  e.classList.add('hidden');
  try {
    const r = await api('/api/profile', { method: 'POST', body: JSON.stringify({ display_name: name, age: age ? parseInt(age) : null }) });
    const d = await r.json();
    if (!r.ok) { e.textContent = d.detail || 'Something went wrong'; e.classList.remove('hidden'); return; }
    localStorage.setItem('brias_username', d.username || name);
    window.location.href = 'app.html';
  } catch(err) {
    e.textContent = 'Could not connect to server';
    e.classList.remove('hidden');
  }
}

// Init: check if already logged in, check if offline
(async function init() {
  const token = localStorage.getItem('brias_token');
  const online = await checkOnline();

  if (!online) {
    setOffline(true);
    return;
  }

  if (token) {
    try {
      const r = await api('/api/me');
      const d = await r.json();
      if (d.logged_in) { window.location.href = 'app.html'; return; }
    } catch(e) {}
    localStorage.removeItem('brias_token');
    localStorage.removeItem('brias_username');
  }
})();
