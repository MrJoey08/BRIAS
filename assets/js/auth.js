/* BRIAS — Auth Logic */

var API = 'https://api.brias.eu';
var authMode = 'login';
var authContact = '';

function api(path, opts) {
  opts = opts || {};
  var token = localStorage.getItem('brias_token');
  var headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = 'Bearer ' + token;
  if (opts.headers) { for (var k in opts.headers) headers[k] = opts.headers[k]; }
  opts.headers = headers;
  return fetch(API + path, opts);
}

async function checkOnline() {
  try { await fetch(API + '/api/me', { method: 'GET', signal: AbortSignal.timeout(3000) }); return true; }
  catch (e) { return false; }
}

function showStep(n) {
  ['authStep1','authStep2','authStep3'].forEach(function(s) { document.getElementById(s).classList.add('hidden'); });
  document.getElementById('authStep' + n).classList.remove('hidden');
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
  var c = document.getElementById('authContact').value.trim();
  var p = document.getElementById('authPass').value;
  var e = document.getElementById('authError');
  var btn = document.getElementById('authSubmit');
  if (!c || !p) { e.textContent = 'Please fill in all fields'; e.classList.remove('hidden'); return; }
  e.classList.add('hidden');
  authContact = c;
  btn.classList.add('is-loading');
  try {
    var r = await api(authMode === 'login' ? '/api/login' : '/api/register', { method: 'POST', body: JSON.stringify({ contact: c, password: p }) });
    var d = await r.json();
    if (!r.ok) { e.textContent = d.detail || 'Something went wrong'; e.classList.remove('hidden'); return; }
    if (d.token) { localStorage.setItem('brias_token', d.token); localStorage.setItem('brias_username', d.username); window.location.href = 'app.html'; return; }
    document.getElementById('sentTo').textContent = c;
    showStep(2);
  } catch (err) {
    window.location.href = 'offline.html';
  }
  finally { btn.classList.remove('is-loading'); }
}

async function doAuthStep2() {
  var code = document.getElementById('authCode').value.trim();
  var e = document.getElementById('authError2');
  if (!code) { e.textContent = 'Please enter the verification code'; e.classList.remove('hidden'); return; }
  e.classList.add('hidden');
  try {
    var r = await api('/api/verify', { method: 'POST', body: JSON.stringify({ contact: authContact, code: code }) });
    var d = await r.json();
    if (!r.ok) { e.textContent = d.detail || 'Invalid code'; e.classList.remove('hidden'); return; }
    localStorage.setItem('brias_token', d.token);
    localStorage.setItem('brias_username', d.username);
    if (authMode === 'register' && !d.profile_complete) { showStep(3); return; }
    window.location.href = 'app.html';
  } catch (err) { window.location.href = 'offline.html'; }
}

async function resendCode() {
  try { await api('/api/resend', { method: 'POST', body: JSON.stringify({ contact: authContact }) }); } catch (err) {}
}

async function doAuthStep3() {
  var name = document.getElementById('authName').value.trim();
  var age = document.getElementById('authAge').value.trim();
  var e = document.getElementById('authError3');
  if (!name) { e.textContent = 'We need at least a name'; e.classList.remove('hidden'); return; }
  e.classList.add('hidden');
  try {
    var r = await api('/api/profile', { method: 'POST', body: JSON.stringify({ display_name: name, age: age ? parseInt(age) : null }) });
    var d = await r.json();
    if (!r.ok) { e.textContent = d.detail || 'Something went wrong'; e.classList.remove('hidden'); return; }
    localStorage.setItem('brias_username', d.username || name);
    window.location.href = 'app.html';
  } catch (err) { window.location.href = 'offline.html'; }
}

/* ── Init ──
   Page starts with visibility:hidden on #authScreen.
   We check online FIRST. If offline → redirect to offline.html.
   User never sees the login page flash. */
(async function initAuth() {
  var token = localStorage.getItem('brias_token');
  var online = await checkOnline();

  /* Server down → straight to offline. Login page never becomes visible. */
  if (!online) {
    window.location.replace('offline.html');
    return;
  }

  /* Already logged in → straight to app. Login page never becomes visible. */
  if (token) {
    try {
      var r = await api('/api/me');
      var d = await r.json();
      if (d.logged_in) { window.location.replace('app.html'); return; }
    } catch (e) {}
    localStorage.removeItem('brias_token');
  }

  /* Server online + not logged in → NOW reveal the login page */
  document.getElementById('authScreen').style.visibility = 'visible';
  initGlow('authGlow');
  initTypewriter('twText');
})();
