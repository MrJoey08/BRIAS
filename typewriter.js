/* BRIAS — Chat App Logic */

var API = 'https://api.brias.eu';
var token = localStorage.getItem('brias_token') || null;
var username = localStorage.getItem('brias_username') || null;
var chats = [], activeChatId = null, isStreaming = false;

function api(path, opts) {
  opts = opts || {};
  var headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = 'Bearer ' + token;
  if (opts.headers) { for (var k in opts.headers) headers[k] = opts.headers[k]; }
  opts.headers = headers;
  return fetch(API + path, opts);
}

function esc(s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
function scrollBottom() { var c = document.getElementById('msgContainer'); setTimeout(function() { c.scrollTop = c.scrollHeight; }, 30); }
function autoResize(el) { el.style.height = '24px'; el.style.height = Math.min(el.scrollHeight, 140) + 'px'; }
function handleKey(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleActionBtn(); } }

function toggleSidebar() {
  var sb = document.getElementById('sidebar'), btn = document.getElementById('topbarToggle');
  sb.classList.toggle('collapsed');
  btn.style.display = sb.classList.contains('collapsed') ? 'flex' : 'none';
}

function setStopMode(on) {
  var b = document.getElementById('actionBtn');
  document.getElementById('iconSend').style.display = on ? 'none' : 'block';
  document.getElementById('iconStop').style.display = on ? 'block' : 'none';
  b.className = 'action-btn ' + (on ? 'stop' : (document.getElementById('msgInput').value.trim() ? 'send-active' : 'send-inactive'));
}

function updateBtn() {
  if (isStreaming) return;
  document.getElementById('actionBtn').className = 'action-btn ' + (document.getElementById('msgInput').value.trim().length > 0 ? 'send-active' : 'send-inactive');
}

function handleActionBtn() { if (isStreaming) stopGen(); else sendMessage(); }

async function stopGen() { if (activeChatId) await api('/api/chats/' + activeChatId + '/abort', { method: 'POST' }); }

async function sendMessage() {
  var i = document.getElementById('msgInput'), c = i.value.trim();
  if (!c || isStreaming || !activeChatId) return;
  i.value = ''; autoResize(i); updateBtn();
  await sendAsStream(c, activeChatId);
}

async function sendAsStream(content, chatId) {
  isStreaming = true; setStopMode(true);
  var welcome = document.getElementById('welcomeScreen'); if (welcome) welcome.remove();
  var inner = document.getElementById('msgInner');
  var isEdit = !!document.querySelector('[data-edit-content="' + content + '"]');
  if (!isEdit) {
    inner.insertAdjacentHTML('beforeend', '<div class="msg user" id="msg-pending"><div class="msg-inner"><div class="msg-avatar"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#9a9a9a" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg></div><div class="msg-body"><div class="msg-bubble">' + esc(content) + '</div></div></div></div>');
    scrollBottom();
  }
  inner.insertAdjacentHTML('beforeend', '<div class="msg assistant" id="typingMsg"><div class="msg-inner"><div class="msg-avatar"><span>B</span></div><div class="msg-body"><div class="msg-bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div></div></div></div>');
  scrollBottom();

  try {
    var resp = await api('/api/chats/' + chatId + '/messages/stream', { method: 'POST', body: JSON.stringify({ content: content }) });
    if (!resp.ok) throw new Error('Server error');
    var reader = resp.body.getReader(), dec = new TextDecoder();
    var buf = '', sb = null, st = '', gm = false;
    while (true) {
      var result = await reader.read();
      if (result.done) break;
      buf += dec.decode(result.value, { stream: true });
      var lines = buf.split('\n'); buf = lines.pop();
      for (var li = 0; li < lines.length; li++) {
        var line = lines[li];
        if (!line.startsWith('data: ')) continue;
        var msg; try { msg = JSON.parse(line.slice(6)); } catch(e) { continue; }

        if (msg.type === 'meta') {
          gm = true;
          var p = document.getElementById('msg-pending');
          if (p) p.outerHTML = msgHtml(msg.user_msg_id, 'user', content);
          var tm = document.getElementById('typingMsg'); if (tm) tm.remove();
          if (msg.title) { var ch = chats.find(function(x) { return x.id === chatId; }); if (ch) { ch.title = msg.title; renderChatList(); } }
          inner.insertAdjacentHTML('beforeend', '<div class="msg assistant" id="streamMsg"><div class="msg-inner"><div class="msg-avatar"><span>B</span></div><div class="msg-body"><div class="msg-bubble" id="streamBubble"><span class="cursor"></span></div></div></div></div>');
          sb = document.getElementById('streamBubble'); scrollBottom();
        }
        else if (msg.type === 'token') {
          if (!gm) {
            gm = true;
            var tm2 = document.getElementById('typingMsg'); if (tm2) tm2.remove();
            inner.insertAdjacentHTML('beforeend', '<div class="msg assistant" id="streamMsg"><div class="msg-inner"><div class="msg-avatar"><span>B</span></div><div class="msg-body"><div class="msg-bubble" id="streamBubble"><span class="cursor"></span></div></div></div></div>');
            sb = document.getElementById('streamBubble');
          }
          st += msg.text;
          sb.innerHTML = esc(st) + '<span class="cursor"></span>';
          scrollBottom();
        }
        else if (msg.type === 'done') {
          if (sb) {
            var fi = 'ai-' + Date.now(), se = document.getElementById('streamMsg');
            if (se) se.outerHTML = msgHtml(fi, 'assistant', msg.full_text || st);
          }
        }
        else if (msg.type === 'error') {
          var tm3 = document.getElementById('typingMsg'); if (tm3) tm3.remove();
          inner.insertAdjacentHTML('beforeend', msgHtml('err-' + Date.now(), 'assistant', msg.text));
          scrollBottom();
        }
      }
    }
  } catch(e) {
    var tm4 = document.getElementById('typingMsg'); if (tm4) tm4.remove();
    inner.insertAdjacentHTML('beforeend', msgHtml('err-' + Date.now(), 'assistant', 'something went wrong... please try again 💙'));
    scrollBottom();
  } finally {
    isStreaming = false; setStopMode(false); scrollBottom();
  }
}

/* Welcome animation BRAIS → BRIAS */
function runWelcomeAnim() {
  var logo = document.getElementById('welcomeLogo');
  if (!logo) return;
  logo.className = 'welcome-logo'; logo.innerHTML = '';
  var cv = document.createElement('canvas'), ctx = cv.getContext('2d');
  ctx.font = "600 72px 'Noto Serif Display',Georgia,serif";
  var g = 72 * .02, w = {};
  'BRAIS'.split('').forEach(function(ch) { w[ch] = ctx.measureText(ch).width + g; });

  function cx(order) {
    var p = {}, x = 0;
    order.split('').forEach(function(ch) { p[ch] = x; x += w[ch]; });
    p._t = x; return p;
  }
  var s = cx('BRAIS'), e = cx('BRIAS');
  logo.style.width = s._t + 'px';
  var sp = {};
  'BRAIS'.split('').forEach(function(ch) {
    var el = document.createElement('span');
    el.className = 'letter letter-' + ch.toLowerCase();
    el.textContent = ch; el.style.left = s[ch] + 'px';
    logo.appendChild(el); sp[ch] = el;
  });

  setTimeout(function() { logo.classList.add('phase1'); }, 800);
  setTimeout(function() {
    logo.classList.remove('phase1'); logo.classList.add('phase2');
    sp.A.style.left = e.A + 'px'; sp.I.style.left = e.I + 'px';
    logo.style.width = e._t + 'px';
  }, 1500);
  setTimeout(function() { logo.className = 'welcome-logo phase3'; }, 2400);
}

/* Chat CRUD */
async function loadChats() {
  chats = await api('/api/chats').then(function(r) { return r.json(); });
  renderChatList();
  if (chats.length > 0 && !activeChatId) selectChat(chats[0].id);
}

async function newChat() {
  var c = await api('/api/chats', { method: 'POST', body: JSON.stringify({ title: 'New chat' }) }).then(function(r) { return r.json(); });
  chats.unshift({ id: c.id, title: c.title, created_at: new Date().toISOString(), updated_at: new Date().toISOString() });
  renderChatList(); selectChat(c.id); runWelcomeAnim();
}

async function deleteChat(id, ev) {
  ev.stopPropagation();
  await api('/api/chats/' + id, { method: 'DELETE' });
  chats = chats.filter(function(c) { return c.id !== id; });
  if (activeChatId === id) { activeChatId = null; chats.length > 0 ? selectChat(chats[0].id) : newChat(); }
  renderChatList();
}

async function selectChat(id) {
  activeChatId = id; renderChatList();
  var msgs = await api('/api/chats/' + id + '/messages').then(function(r) { return r.json(); });
  renderMessages(msgs);
}

function renderChatList() {
  document.getElementById('chatList').innerHTML = chats.map(function(c) {
    return '<div class="chat-item ' + (c.id === activeChatId ? 'active' : '') + '" onclick="selectChat(\'' + c.id + '\')">' +
      '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="' + (c.id === activeChatId ? 'var(--orange)' : 'var(--text-dim)') + '" stroke-width="1.5" stroke-linecap="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>' +
      '<span class="ci-title">' + esc(c.title) + '</span>' +
      '<button class="ci-del" onclick="deleteChat(\'' + c.id + '\',event)"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--text-dim)" stroke-width="2" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></button></div>';
  }).join('');
}

function renderMessages(msgs) {
  var inner = document.getElementById('msgInner');
  if (msgs.length === 0) {
    inner.innerHTML = '<div class="welcome" id="welcomeScreen"><div class="welcome-logo" id="welcomeLogo"></div><div class="welcome-sub">What can I help you with?</div></div>';
    runWelcomeAnim(); return;
  }
  inner.innerHTML = msgs.map(function(m) { return msgHtml(m.id, m.role, m.content); }).join('');
  scrollBottom();
}

function msgHtml(id, role, content) {
  var isUser = role === 'user';
  var av = isUser ? '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#9a9a9a" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>' : '<span>B</span>';
  var cp = '<button class="msg-act-btn" onclick="copyMsg(this,\'' + id + '\')" title="Copy"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button>';
  var ed = isUser ? '<button class="msg-act-btn" onclick="startEdit(\'' + id + '\')" title="Edit"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></button>' : '';
  return '<div class="msg ' + role + '" id="msg-' + id + '"><div class="msg-inner"><div class="msg-avatar">' + av + '</div><div class="msg-body"><div class="msg-bubble" id="bubble-' + id + '">' + esc(content) + '</div><div class="msg-actions">' + cp + ed + '</div>' + (isUser ? '<div class="msg-edit-wrap" id="edit-' + id + '"><textarea class="msg-edit-area" id="editarea-' + id + '">' + esc(content) + '</textarea><div class="msg-edit-btns"><button class="edit-cancel-btn" onclick="cancelEdit(\'' + id + '\')">Cancel</button><button class="edit-confirm-btn" onclick="confirmEdit(\'' + id + '\')">Send</button></div></div>' : '') + '</div></div></div>';
}

async function copyMsg(btn, id) {
  var b = document.getElementById('bubble-' + id); if (!b) return;
  await navigator.clipboard.writeText(b.textContent);
  btn.classList.add('copied'); setTimeout(function() { btn.classList.remove('copied'); }, 1500);
}

function startEdit(id) {
  var b = document.getElementById('bubble-' + id), ew = document.getElementById('edit-' + id), ea = document.getElementById('editarea-' + id);
  if (!ew) return;
  ea.value = b.textContent; b.style.display = 'none';
  document.getElementById('msg-' + id).querySelector('.msg-actions').style.display = 'none';
  ew.classList.add('active'); ea.style.height = 'auto'; ea.style.height = ea.scrollHeight + 'px'; ea.focus();
}

function cancelEdit(id) {
  document.getElementById('bubble-' + id).style.display = '';
  document.getElementById('msg-' + id).querySelector('.msg-actions').style.display = '';
  document.getElementById('edit-' + id).classList.remove('active');
}

async function confirmEdit(id) {
  var ea = document.getElementById('editarea-' + id), nc = ea.value.trim();
  if (!nc) return;
  document.getElementById('bubble-' + id).textContent = nc; cancelEdit(id);
  var r = await api('/api/messages/' + id, { method: 'PATCH', body: JSON.stringify({ content: nc }) });
  if (!r.ok) { alert('Edit failed'); return; }
  var d = await r.json();
  var me = document.getElementById('msg-' + id);
  var nx = me.nextElementSibling;
  while (nx) { var n = nx.nextElementSibling; nx.remove(); nx = n; }
  await sendAsStream(nc, d.chat_id);
}

function doLogout() {
  token = null; username = null;
  localStorage.removeItem('brias_token'); localStorage.removeItem('brias_username');
  chats = []; activeChatId = null;
  window.location.href = 'login.html';
}

/* Init */
(async function initApp() {
  if (!token) { window.location.href = 'login.html'; return; }
  try {
    var r = await api('/api/me'); var d = await r.json();
    if (!d.logged_in) { localStorage.removeItem('brias_token'); window.location.href = 'login.html'; return; }
  } catch (e) { /* offline but has token, let them try */ }
  document.getElementById('sfName').textContent = username || '—';
  await loadChats();
  if (chats.length === 0) await newChat(); else runWelcomeAnim();
})();
