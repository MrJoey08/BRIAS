/* ═══════════════════════════════════════════════
   BRIAS — chat.js
   Chat controller: message list, streaming,
   editing, copy, welcome animation
   ═══════════════════════════════════════════════ */

import { CONFIG } from './config.js';
import { ApiService } from './api.js';
import { StorageService } from './storage.js';
import { esc, scrollBottom, autoResize } from './helpers.js';

class ChatController {
  constructor() {
    this.chats = [];
    this.activeChatId = null;
    this.isStreaming = false;

    this._bindEvents();
  }

  _bindEvents() {
    const input = document.getElementById('msgInput');
    const actionBtn = document.getElementById('actionBtn');

    input?.addEventListener('input', () => {
      autoResize(input);
      this._updateButton();
    });

    input?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this._handleAction();
      }
    });

    actionBtn?.addEventListener('click', () => this._handleAction());
  }

  /* ── Initialize app view ── */

  async init() {
    document.getElementById('authScreen').classList.add('hidden');
    document.getElementById('appScreen').classList.remove('hidden');
    document.getElementById('sfName').textContent = StorageService.getUsername() || '—';

    await this.loadChats();

    if (this.chats.length === 0) {
      await this.newChat();
    } else {
      this._runWelcomeAnim();
    }
  }

  /* ── Chats CRUD ── */

  async loadChats() {
    this.chats = await ApiService.getChats();
    this._renderChatList();

    if (this.chats.length > 0 && !this.activeChatId) {
      await this.selectChat(this.chats[0].id);
    }
  }

  async newChat() {
    const chat = await ApiService.createChat();
    this.chats.unshift({
      ...chat,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
    this._renderChatList();
    await this.selectChat(chat.id);
    this._runWelcomeAnim();
  }

  async deleteChat(id, event) {
    event?.stopPropagation();
    await ApiService.deleteChat(id);
    this.chats = this.chats.filter(c => c.id !== id);

    if (this.activeChatId === id) {
      this.activeChatId = null;
      if (this.chats.length > 0) {
        await this.selectChat(this.chats[0].id);
      } else {
        await this.newChat();
      }
    }

    this._renderChatList();
  }

  async selectChat(id) {
    this.activeChatId = id;
    this._renderChatList();

    const messages = await ApiService.getMessages(id);
    this._renderMessages(messages);
  }

  /* ── Render chat list ── */

  _renderChatList() {
    const el = document.getElementById('chatList');
    if (!el) return;

    el.innerHTML = this.chats.map(c => `
      <div class="chat-item ${c.id === this.activeChatId ? 'active' : ''}"
           data-chat-id="${c.id}">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
             stroke="${c.id === this.activeChatId ? 'var(--orange)' : 'var(--text-dim)'}"
             stroke-width="1.5" stroke-linecap="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        </svg>
        <span class="ci-title">${esc(c.title)}</span>
        <button class="ci-del" data-delete-chat="${c.id}">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
               stroke="var(--text-dim)" stroke-width="2" stroke-linecap="round">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
        </button>
      </div>
    `).join('');

    // Bind events via delegation
    el.querySelectorAll('[data-chat-id]').forEach(item => {
      item.addEventListener('click', (e) => {
        if (!e.target.closest('[data-delete-chat]')) {
          this.selectChat(item.dataset.chatId);
        }
      });
    });

    el.querySelectorAll('[data-delete-chat]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.deleteChat(btn.dataset.deleteChat, e);
      });
    });
  }

  /* ── Render messages ── */

  _renderMessages(msgs) {
    const inner = document.getElementById('msgInner');

    if (msgs.length === 0) {
      inner.innerHTML = `
        <div class="welcome" id="welcomeScreen">
          <div class="welcome-logo" id="welcomeLogo"></div>
          <div class="welcome-sub">What can I help you with?</div>
        </div>`;
      this._runWelcomeAnim();
      return;
    }

    inner.innerHTML = msgs.map(m => this._msgHtml(m.id, m.role, m.content)).join('');
    scrollBottom();
  }

  _msgHtml(id, role, content) {
    const isUser = role === 'user';

    const avatar = isUser
      ? `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#9a9a9a" stroke-width="2">
           <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
         </svg>`
      : `<span>B</span>`;

    const copyBtn = `
      <button class="msg-act-btn" data-action="copy" data-msg-id="${id}" title="Copy">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <rect x="9" y="9" width="13" height="13" rx="2"/>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
        </svg>
      </button>`;

    const editBtn = isUser
      ? `<button class="msg-act-btn" data-action="edit" data-msg-id="${id}" title="Edit">
           <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
             <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
             <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
           </svg>
         </button>`
      : '';

    const editWrap = isUser
      ? `<div class="msg-edit-wrap" id="edit-${id}">
           <textarea class="msg-edit-area" id="editarea-${id}">${esc(content)}</textarea>
           <div class="msg-edit-btns">
             <button class="edit-cancel-btn" data-action="cancel-edit" data-msg-id="${id}">Cancel</button>
             <button class="edit-confirm-btn" data-action="confirm-edit" data-msg-id="${id}">Send</button>
           </div>
         </div>`
      : '';

    return `
      <div class="msg ${role}" id="msg-${id}">
        <div class="msg-inner">
          <div class="msg-avatar">${avatar}</div>
          <div class="msg-body">
            <div class="msg-bubble" id="bubble-${id}">${esc(content)}</div>
            <div class="msg-actions">${copyBtn}${editBtn}</div>
            ${editWrap}
          </div>
        </div>
      </div>`;
  }

  /* ── Message actions (delegated) ── */

  handleMessageAction(action, msgId) {
    switch (action) {
      case 'copy':     return this._copyMessage(msgId);
      case 'edit':     return this._startEdit(msgId);
      case 'cancel-edit':  return this._cancelEdit(msgId);
      case 'confirm-edit': return this._confirmEdit(msgId);
    }
  }

  async _copyMessage(id) {
    const bubble = document.getElementById(`bubble-${id}`);
    if (!bubble) return;

    await navigator.clipboard.writeText(bubble.textContent);

    const btn = document.querySelector(`[data-action="copy"][data-msg-id="${id}"]`);
    btn?.classList.add('copied');
    setTimeout(() => btn?.classList.remove('copied'), 1500);
  }

  _startEdit(id) {
    const bubble = document.getElementById(`bubble-${id}`);
    const editWrap = document.getElementById(`edit-${id}`);
    const editArea = document.getElementById(`editarea-${id}`);
    if (!editWrap) return;

    editArea.value = bubble.textContent;
    bubble.style.display = 'none';
    document.getElementById(`msg-${id}`).querySelector('.msg-actions').style.display = 'none';
    editWrap.classList.add('active');
    editArea.style.height = 'auto';
    editArea.style.height = editArea.scrollHeight + 'px';
    editArea.focus();
  }

  _cancelEdit(id) {
    document.getElementById(`bubble-${id}`).style.display = '';
    document.getElementById(`msg-${id}`).querySelector('.msg-actions').style.display = '';
    document.getElementById(`edit-${id}`).classList.remove('active');
  }

  async _confirmEdit(id) {
    const editArea = document.getElementById(`editarea-${id}`);
    const newContent = editArea.value.trim();
    if (!newContent) return;

    document.getElementById(`bubble-${id}`).textContent = newContent;
    this._cancelEdit(id);

    try {
      const data = await ApiService.editMessage(id, newContent);
      // Remove all messages after this one
      const msgEl = document.getElementById(`msg-${id}`);
      let next = msgEl.nextElementSibling;
      while (next) {
        const n = next.nextElementSibling;
        next.remove();
        next = n;
      }
      // Re-stream
      await this._streamMessage(newContent, data.chat_id);
    } catch {
      alert('Edit failed');
    }
  }

  /* ── Send / Stop ── */

  _handleAction() {
    if (this.isStreaming) {
      this._stopStream();
    } else {
      this._sendMessage();
    }
  }

  async _sendMessage() {
    const input = document.getElementById('msgInput');
    const content = input.value.trim();
    if (!content || this.isStreaming || !this.activeChatId) return;

    input.value = '';
    autoResize(input);
    this._updateButton();

    await this._streamMessage(content, this.activeChatId);
  }

  async _stopStream() {
    if (this.activeChatId) {
      await ApiService.abortStream(this.activeChatId);
    }
  }

  /* ── Streaming ── */

  async _streamMessage(content, chatId) {
    this.isStreaming = true;
    this._setStopMode(true);

    const welcome = document.getElementById('welcomeScreen');
    if (welcome) welcome.remove();

    const inner = document.getElementById('msgInner');

    // Add user message
    const isEdit = !!document.querySelector(`[data-edit-content="${content}"]`);
    if (!isEdit) {
      inner.insertAdjacentHTML('beforeend', `
        <div class="msg user" id="msg-pending">
          <div class="msg-inner">
            <div class="msg-avatar">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#9a9a9a" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
              </svg>
            </div>
            <div class="msg-body"><div class="msg-bubble">${esc(content)}</div></div>
          </div>
        </div>`);
      scrollBottom();
    }

    // Typing indicator
    inner.insertAdjacentHTML('beforeend', `
      <div class="msg assistant" id="typingMsg">
        <div class="msg-inner">
          <div class="msg-avatar"><span>B</span></div>
          <div class="msg-body">
            <div class="msg-bubble">
              <div class="typing-dots"><span></span><span></span><span></span></div>
            </div>
          </div>
        </div>
      </div>`);
    scrollBottom();

    try {
      const resp = await ApiService.streamMessage(chatId, content);
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = '', streamBubble = null, streamText = '', gotMeta = false;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buf += decoder.decode(value, { stream: true });
        const lines = buf.split('\n');
        buf = lines.pop();

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;

          let msg;
          try { msg = JSON.parse(line.slice(6)); } catch { continue; }

          if (msg.type === 'meta') {
            gotMeta = true;
            // Replace pending user message with real one
            const pending = document.getElementById('msg-pending');
            if (pending) pending.outerHTML = this._msgHtml(msg.user_msg_id, 'user', content);

            document.getElementById('typingMsg')?.remove();

            // Update chat title
            if (msg.title) {
              const chat = this.chats.find(c => c.id === chatId);
              if (chat) {
                chat.title = msg.title;
                this._renderChatList();
              }
            }

            // Create stream bubble
            inner.insertAdjacentHTML('beforeend', `
              <div class="msg assistant" id="streamMsg">
                <div class="msg-inner">
                  <div class="msg-avatar"><span>B</span></div>
                  <div class="msg-body">
                    <div class="msg-bubble" id="streamBubble"><span class="cursor"></span></div>
                  </div>
                </div>
              </div>`);
            streamBubble = document.getElementById('streamBubble');
            scrollBottom();
          }

          else if (msg.type === 'token') {
            if (!gotMeta) {
              gotMeta = true;
              document.getElementById('typingMsg')?.remove();
              inner.insertAdjacentHTML('beforeend', `
                <div class="msg assistant" id="streamMsg">
                  <div class="msg-inner">
                    <div class="msg-avatar"><span>B</span></div>
                    <div class="msg-body">
                      <div class="msg-bubble" id="streamBubble"><span class="cursor"></span></div>
                    </div>
                  </div>
                </div>`);
              streamBubble = document.getElementById('streamBubble');
            }
            streamText += msg.text;
            streamBubble.innerHTML = esc(streamText) + '<span class="cursor"></span>';
            scrollBottom();
          }

          else if (msg.type === 'done') {
            if (streamBubble) {
              const finalId = 'ai-' + Date.now();
              const streamMsg = document.getElementById('streamMsg');
              if (streamMsg) {
                streamMsg.outerHTML = this._msgHtml(finalId, 'assistant', msg.full_text || streamText);
              }
            }
          }

          else if (msg.type === 'error') {
            document.getElementById('typingMsg')?.remove();
            inner.insertAdjacentHTML('beforeend',
              this._msgHtml('err-' + Date.now(), 'assistant', msg.text));
            scrollBottom();
          }
        }
      }

    } catch {
      document.getElementById('typingMsg')?.remove();
      const inner = document.getElementById('msgInner');
      inner.insertAdjacentHTML('beforeend',
        this._msgHtml('err-' + Date.now(), 'assistant', 'something went wrong... please try again 💙'));
      scrollBottom();
    } finally {
      this.isStreaming = false;
      this._setStopMode(false);
      scrollBottom();
    }
  }

  /* ── Button state ── */

  _updateButton() {
    if (this.isStreaming) return;
    const input = document.getElementById('msgInput');
    const btn = document.getElementById('actionBtn');
    btn.className = 'action-btn ' + (input.value.trim().length > 0 ? 'send-active' : 'send-inactive');
  }

  _setStopMode(on) {
    const btn = document.getElementById('actionBtn');
    document.getElementById('iconSend').style.display = on ? 'none' : 'block';
    document.getElementById('iconStop').style.display = on ? 'block' : 'none';
    btn.className = 'action-btn ' + (on
      ? 'stop'
      : (document.getElementById('msgInput').value.trim() ? 'send-active' : 'send-inactive'));
  }

  /* ── Welcome animation (BRAIS → BRIAS) ── */

  _runWelcomeAnim() {
    const logo = document.getElementById('welcomeLogo');
    if (!logo) return;

    logo.className = 'welcome-logo';
    logo.innerHTML = '';

    // Measure character widths
    const cv = document.createElement('canvas');
    const ctx = cv.getContext('2d');
    ctx.font = `600 72px 'Noto Serif Display', Georgia, serif`;

    const gap = 72 * 0.02;
    const widths = {};
    for (const ch of 'BRAIS') {
      widths[ch] = ctx.measureText(ch).width + gap;
    }

    function calcPositions(order) {
      const pos = {};
      let x = 0;
      for (const ch of order) {
        pos[ch] = x;
        x += widths[ch];
      }
      pos._total = x;
      return pos;
    }

    const startPos = calcPositions('BRAIS');
    const endPos = calcPositions('BRIAS');

    logo.style.width = startPos._total + 'px';

    const spans = {};
    for (const ch of 'BRAIS') {
      const el = document.createElement('span');
      el.className = `letter letter-${ch.toLowerCase()}`;
      el.textContent = ch;
      el.style.left = startPos[ch] + 'px';
      logo.appendChild(el);
      spans[ch] = el;
    }

    const delays = CONFIG.WELCOME_ANIM;

    setTimeout(() => logo.classList.add('phase1'), delays.PHASE1_DELAY);

    setTimeout(() => {
      logo.classList.remove('phase1');
      logo.classList.add('phase2');
      spans.A.style.left = endPos.A + 'px';
      spans.I.style.left = endPos.I + 'px';
      logo.style.width = endPos._total + 'px';
    }, delays.PHASE2_DELAY);

    setTimeout(() => {
      logo.className = 'welcome-logo phase3';
    }, delays.PHASE3_DELAY);
  }

  /* ── Logout ── */

  logout() {
    StorageService.clearAll();
    this.chats = [];
    this.activeChatId = null;
  }
}

export { ChatController };
