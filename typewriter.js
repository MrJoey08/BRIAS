/* ═══════════════════════════════════════════════════════════
   BRIAS — Chat App Logic
   Handles chats, messages, streaming, editing
   ═══════════════════════════════════════════════════════════ */

const API = 'https://api.brias.eu';

let token = localStorage.getItem('brias_token') || null;
let username = localStorage.getItem('brias_username') || null;
let chats = [];
let activeChatId = null;
let isStreaming = false;

/* ── API helper ── */
function api(path, opts = {}) {
  return fetch(API + path, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': 'Bearer ' + token } : {}),
      ...(opts.headers || {})
    }
  });
}

/* ── Escape HTML ── */
function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

/* ── Scroll to bottom ── */
function scrollBottom() {
  const c = document.getElementById('msgContainer');
  setTimeout(() => c.scrollTop = c.scrollHeight, 30);
}

/* ── Auto-resize textarea ── */
function autoResize(el) {
  el.style.height = '24px';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}

/* ── Keyboard ── */
function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleActionBtn();
  }
}

/* ── Toggle sidebar ── */
function toggleSidebar() {
  const sb = document.getElementById('sidebar');
  const btn = document.getElementById('topbarToggle');
  sb.classList.toggle('collapsed');
  btn.style.display = sb.classList.contains('collapsed') ? 'flex' : 'none';
}

/* ── Action button state ── */
function setStopMode(on) {
  const b = document.getElementById('actionBtn');
  document.getElementById('iconSend').style.display = on ? 'none' : 'block';
  document.getElementById('iconStop').style.display = on ? 'block' : 'none';
  b.className = 'action-btn ' + (on ? 'stop' : (document.getElementById('msgInput').value.trim() ? 'send-active' : 'send-inactive'));
}

function updateBtn() {
  if (isStreaming) return;
  document.getElementById('actionBtn').className = 'action-btn ' +
    (document.getElementById('msgInput').value.trim().length > 0 ? 'send-active' : 'send-inactive');
}

function handleActionBtn() {
  if (isStreaming) stopGen();
  else sendMessage();
}

/* ── Stop generation ── */
async function stopGen() {
  if (activeChatId) await api('/api/chats/' + activeChatId + '/abort', { method: 'POST' });
}

/* ── Send message ── */
async function sendMessage() {
  const i = document.getElementById('msgInput');
  const c = i.value.trim();
  if (!c || isStreaming || !activeChatId) return;
  i.value = '';
  autoResize(i);
  updateBtn();
  await sendAsStream(c, activeChatId);
}

/* ── Streaming ── */
async function sendAsStream(content, chatId) {
  isStreaming = true;
  setStopMode(true);

  const welcome = document.getElementById('welcomeScreen');
  if (welcome) welcome.remove();

  const inner = document.getElementById('msgInner');
  const isEdit = !!document.querySelector(`[data-edit-content="${content}"]`);

  if (!isEdit) {
    inner.insertAdjacentHTML('beforeend',
      `<div class="msg user" id="msg-pending"><div class="msg-inner"><div class="msg-avatar"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#9a9a9a" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg></div><div class="msg-body"><div class="msg-bubble">${esc(content)}</div></div></div></div>`
    );
    scrollBottom();
  }

  inner.insertAdjacentHTML('beforeend',
    `<div class="msg assistant" id="typingMsg"><div class="msg-inner"><div class="msg-avatar"><span>B</span></div><div class="msg-body"><div class="msg-bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div></div></div></div>`
  );
  scrollBottom();

  try {
    const resp = await api('/api/chats/' + chatId + '/messages/stream', {
      method: 'POST',
      body: JSON.stringify({ content })
    });
    if (!resp.ok) throw new Error('Server error');

    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let buf = '', sb = null, st = '', gm = false;

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        let msg;
        try { msg = JSON.parse(line.slice(6)); } catch { continue; }

        if (msg.type === 'meta') {
          gm = true;
          const p = document.getElementById('msg-pending');
          if (p) p.outerHTML = msgHtml(msg.user_msg_id, 'user', content);
          document.getElementById('typingMsg')?.remove();
          if (msg.title) {
            const c = chats.find(x => x.id === chatId);
            if (c) { c.title = msg.title; renderChatList(); }
          }
          inner.insertAdjacentHTML('beforeend',
            `<div class="msg assistant" id="streamMsg"><div class="msg-inner"><div class="msg-avatar"><span>B</span></div><div class="msg-body"><div class="msg-bubble" id="streamBubble"><span class="cursor"></span></div></div></div></div>`
          );
          sb = document.getElementById('streamBubble');
          scrollBottom();
        }
        else if (msg.type === 'token') {
          if (!gm) {
            gm = true;
            document.getElementById('typingMsg')?.remove();
            inner.insertAdjacentHTML('beforeend',
              `<div class="msg assistant" id="streamMsg"><div class="msg-inner"><div class="msg-avatar"><span>B</span></div><div class="msg-body"><div class="msg-bubble" id="streamBubble"><span class="cursor"></span></div></div></div></div>`
            );
            sb = document.getElementById('streamBubble');
          }
          st += msg.text;
          sb.innerHTML = esc(st) + '<span class="cursor"></span>';
          scrollBottom();
        }
        else if (msg.type === 'done') {
          if (sb) {
            const fi = 'ai-' + Date.now();
            const se = document.getElementById('streamMsg');
            if (se) se.outerHTML = msgHtml(fi, 'assistant', msg.full_text || st);
          }
        }
        else if (msg.type === 'error') {
          document.getElementById('typingMsg')?.remove();
          inner.insertAdjacentHTML('beforeend', msgHtml('err-' + Date.now(), 'assistant', msg.text));
          scrollBottom();
        }
      }
    }
  } catch {
    document.getElementById('typingMsg')?.remove();
    inner.insertAdjacentHTML('beforeend',
      msgHtml('err-' + Date.now(), 'assistant', 'something went wrong... please try again 💙')
    );
    scrollBottom();
  } finally {
    isStreaming = false;
    setStopMode(false);
    scrollBottom();
  }
}

/* ── Welcome animation (BRAIS → BRIAS) ── */
function runWelcomeAnim() {
  const logo = document.getElementById('welcomeLogo');
  if (!logo) return;
  logo.className = 'welcome-logo';
  logo.innerHTML = '';

  const cv = document.createElement('canvas');
  const ctx = cv.getContext('2d');
  ctx.font = `600 72px 'Noto Serif Display', Georgia, serif`;
  const g = 72 * 0.02;
  const w = {};
  for (const ch of 'BRAIS') w[ch] = ctx.measureText(ch).width + g;

  function cx(order) {
    const p = {};
    let x = 0;
    for (const ch of order) { p[ch] = x; x += w[ch]; }
    p._t = x;
    return p;
  }

  const s = cx('BRAIS');
  const e = cx('BRIAS');
  logo.style.width = s._t + 'px';

  const sp = {};
  for (const ch of 'BRAIS') {
    const el = document.createElement('span');
    el.className = 'letter letter-' + ch.toLowerCase();
    el.textContent = ch;
    el.style.left = s[ch] + 'px';
    logo.appendChild(el);
    sp[ch] = el;
  }

  setTimeout(() => logo.classList.add('phase1'), 800);
  setTimeout(() => {
    logo.classList.remove('phase1');
    logo.classList.add('phase2');
    sp.A.style.left = e.A + 'px';
    sp.I.style.left = e.I + 'px';
    logo.style.width = e._t + 'px';
  }, 1500);
  setTimeout(() => { logo.className = 'welcome-logo phase3'; }, 2400);
}

/* ── Chat CRUD ── */
async function loadChats() {
  chats = await api('/api/chats').then(r => r.json());
  renderChatList();
  if (chats.length > 0 && !activeChatId) selectChat(chats[0].id);
}

async function newChat() {
  const c = await api('/api/chats', {
    method: 'POST',
    body: JSON.stringify({ title: 'New chat' })
  }).then(r => r.json());
  chats.unshift({ ...c, created_at: new Date().toISOString(), updated_at: new Date().toISOString() });
  renderChatList();
  selectChat(c.id);
  runWelcomeAnim();
}

async function deleteChat(id, e) {
  e.stopPropagation();
  await api('/api/chats/' + id, { method: 'DELETE' });
  chats = chats.filter(c => c.id !== id);
  if (activeChatId === id) {
    activeChatId = null;
    chats.length > 0 ? selectChat(chats[0].id) : newChat();
  }
  renderChatList();
}

async function selectChat(id) {
  activeChatId = id;
  renderChatList();
  const msgs = await api('/api/chats/' + id + '/messages').then(r => r.json());
  renderMessages(msgs);
}

function renderChatList() {
  document.getElementById('chatList').innerHTML = chats.map(c =>
    `<div class="chat-item ${c.id === activeChatId ? 'active' : ''}" onclick="selectChat('${c.id}')">` +
      `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="${c.id === activeChatId ? 'var(--orange)' : 'var(--text-dim)'}" stroke-width="1.5" stroke-linecap="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>` +
      `<span class="ci-title">${esc(c.title)}</span>` +
      `<button class="ci-del" onclick="deleteChat('${c.id}',event)"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--text-dim)" stroke-width="2" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></button>` +
    `</div>`
  ).join('');
}

/* ── Render messages ── */
function renderMessages(msgs) {
  const inner = document.getElementById('msgInner');
  if (msgs.length === 0) {
    inner.innerHTML = `<div class="welcome" id="welcomeScreen"><div class="welcome-logo" id="welcomeLogo"></div><div class="welcome-sub">What can I help you with?</div></div>`;
    runWelcomeAnim();
    return;
  }
  inner.innerHTML = msgs.map(m => msgHtml(m.id, m.role, m.content)).join('');
  scrollBottom();
}

function msgHtml(id, role, content) {
  const isUser = role === 'user';
  const av = isUser
    ? `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#9a9a9a" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`
    : `<span>B</span>`;
  const cp = `<button class="msg-act-btn" onclick="copyMsg(this,'${id}')" title="Copy"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button>`;
  const ed = isUser
    ? `<button class="msg-act-btn" onclick="startEdit('${id}')" title="Edit"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></button>`
    : '';

  return `<div class="msg ${role}" id="msg-${id}"><div class="msg-inner"><div class="msg-avatar">${av}</div><div class="msg-body"><div class="msg-bubble" id="bubble-${id}">${esc(content)}</div><div class="msg-actions">${cp}${ed}</div>${isUser ? `<div class="msg-edit-wrap" id="edit-${id}"><textarea class="msg-edit-area" id="editarea-${id}">${esc(content)}</textarea><div class="msg-edit-btns"><button class="edit-cancel-btn" onclick="cancelEdit('${id}')">Cancel</button><button class="edit-confirm-btn" onclick="confirmEdit('${id}')">Send</button></div></div>` : ''}</div></div></div>`;
}

/* ── Message actions ── */
async function copyMsg(btn, id) {
  const b = document.getElementById('bubble-' + id);
  if (!b) return;
  await navigator.clipboard.writeText(b.textContent);
  btn.classList.add('copied');
  setTimeout(() => btn.classList.remove('copied'), 1500);
}

function startEdit(id) {
  const b = document.getElementById('bubble-' + id);
  const ew = document.getElementById('edit-' + id);
  const ea = document.getElementById('editarea-' + id);
  if (!ew) return;
  ea.value = b.textContent;
  b.style.display = 'none';
  document.getElementById('msg-' + id).querySelector('.msg-actions').style.display = 'none';
  ew.classList.add('active');
  ea.style.height = 'auto';
  ea.style.height = ea.scrollHeight + 'px';
  ea.focus();
}

function cancelEdit(id) {
  document.getElementById('bubble-' + id).style.display = '';
  document.getElementById('msg-' + id).querySelector('.msg-actions').style.display = '';
  document.getElementById('edit-' + id).classList.remove('active');
}

async function confirmEdit(id) {
  const ea = document.getElementById('editarea-' + id);
  const nc = ea.value.trim();
  if (!nc) return;
  document.getElementById('bubble-' + id).textContent = nc;
  cancelEdit(id);
  const r = await api('/api/messages/' + id, { method: 'PATCH', body: JSON.stringify({ content: nc }) });
  if (!r.ok) { alert('Edit failed'); return; }
  const d = await r.json();
  const me = document.getElementById('msg-' + id);
  let nx = me.nextElementSibling;
  while (nx) { const n = nx.nextElementSibling; nx.remove(); nx = n; }
  await sendAsStream(nc, d.chat_id);
}

/* ── Logout ── */
function doLogout() {
  token = null;
  username = null;
  localStorage.removeItem('brias_token');
  localStorage.removeItem('brias_username');
  chats = [];
  activeChatId = null;
  window.location.href = 'login.html';
}

/* ── Init ── */
async function initApp() {
  // Guard: must be logged in
  if (!token) {
    window.location.href = 'login.html';
    return;
  }

  // Verify token
  try {
    const r = await api('/api/me');
    const d = await r.json();
    if (!d.logged_in) {
      localStorage.removeItem('brias_token');
      window.location.href = 'login.html';
      return;
    }
  } catch (e) {
    // Offline but has token — let them try
  }

  // Set username in sidebar
  document.getElementById('sfName').textContent = username || '—';

  // Load chats
  await loadChats();
  if (chats.length === 0) await newChat();
  else runWelcomeAnim();
}

initApp();
