/* ═══════════════════════════════════════════════
   BRIAS — app.js
   Main entry point: bootstraps auth + chat,
   handles routing, global event delegation
   ═══════════════════════════════════════════════ */

import { ApiService } from './api.js';
import { StorageService } from './storage.js';
import { AuthController } from './auth.js';
import { ChatController } from './chat.js';

class BriasApp {
  constructor() {
    this.auth = null;
    this.chat = null;
  }

  async init() {
    // Initialize controllers
    this.chat = new ChatController();
    this.auth = new AuthController(() => this._onAuthenticated());

    // Global event delegation for message actions
    this._bindGlobalEvents();

    // Check existing session
    const online = await ApiService.checkOnline();

    if (StorageService.isAuthenticated() && online) {
      try {
        const data = await ApiService.getMe();
        if (data.logged_in) {
          await this._onAuthenticated();
          return;
        }
      } catch { /* token expired or invalid */ }

      StorageService.clearAll();
    }

    // Show auth
    this.auth.show();
    if (!online) this.auth.setOffline(true);
  }

  async _onAuthenticated() {
    this.auth.hide();
    await this.chat.init();
  }

  _bindGlobalEvents() {
    // Delegated message actions (copy, edit, cancel, confirm)
    document.addEventListener('click', (e) => {
      const actionEl = e.target.closest('[data-action]');
      if (!actionEl) return;

      const action = actionEl.dataset.action;
      const msgId = actionEl.dataset.msgId;

      // Auth actions handled by AuthController
      if (action === 'toggle-auth' || action === 'resend-code') return;

      // Chat message actions
      if (msgId && this.chat) {
        this.chat.handleMessageAction(action, msgId);
      }
    });

    // Sidebar toggle
    document.getElementById('sidebarToggle')?.addEventListener('click', () => this._toggleSidebar());
    document.getElementById('topbarToggle')?.addEventListener('click', () => this._toggleSidebar());

    // New chat
    document.getElementById('newChatBtn')?.addEventListener('click', () => this.chat?.newChat());

    // Logout
    document.getElementById('logoutBtn')?.addEventListener('click', () => {
      this.chat?.logout();
      this.auth?.show();
    });
  }

  _toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const topbarBtn = document.getElementById('topbarToggle');
    sidebar.classList.toggle('collapsed');
    topbarBtn.style.display = sidebar.classList.contains('collapsed') ? 'flex' : 'none';
  }
}

/* ── Bootstrap ── */
const app = new BriasApp();
app.init();
