/* ═══════════════════════════════════════════════
   BRIAS — api.js
   Centralized API client with auth headers,
   error handling, and typed endpoints
   ═══════════════════════════════════════════════ */

import { CONFIG } from './config.js';
import { StorageService } from './storage.js';

class ApiService {

  /**
   * Base fetch wrapper — attaches auth token + JSON headers
   */
  static async request(path, opts = {}) {
    const token = StorageService.getToken();
    const headers = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.headers || {}),
    };

    return fetch(`${CONFIG.API_BASE}${path}`, {
      ...opts,
      headers,
    });
  }

  /* ── Health ── */

  static async checkOnline() {
    try {
      await fetch(`${CONFIG.API_BASE}/api/me`, {
        method: 'GET',
        signal: AbortSignal.timeout(CONFIG.HEALTH_CHECK_TIMEOUT),
      });
      return true;
    } catch {
      return false;
    }
  }

  /* ── Auth ── */

  static async login(contact, password) {
    const res = await this.request('/api/login', {
      method: 'POST',
      body: JSON.stringify({ contact, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Login failed');
    return data;
  }

  static async register(contact, password) {
    const res = await this.request('/api/register', {
      method: 'POST',
      body: JSON.stringify({ contact, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Registration failed');
    return data;
  }

  static async verify(contact, code) {
    const res = await this.request('/api/verify', {
      method: 'POST',
      body: JSON.stringify({ contact, code }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Invalid code');
    return data;
  }

  static async resendCode(contact) {
    await this.request('/api/resend', {
      method: 'POST',
      body: JSON.stringify({ contact }),
    });
  }

  static async completeProfile(displayName, age) {
    const res = await this.request('/api/profile', {
      method: 'POST',
      body: JSON.stringify({
        display_name: displayName,
        age: age ? parseInt(age) : null,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Profile update failed');
    return data;
  }

  static async getMe() {
    const res = await this.request('/api/me');
    return res.json();
  }

  /* ── Chats ── */

  static async getChats() {
    const res = await this.request('/api/chats');
    return res.json();
  }

  static async createChat(title = 'New chat') {
    const res = await this.request('/api/chats', {
      method: 'POST',
      body: JSON.stringify({ title }),
    });
    return res.json();
  }

  static async deleteChat(chatId) {
    await this.request(`/api/chats/${chatId}`, { method: 'DELETE' });
  }

  /* ── Messages ── */

  static async getMessages(chatId) {
    const res = await this.request(`/api/chats/${chatId}/messages`);
    return res.json();
  }

  static async streamMessage(chatId, content) {
    const res = await this.request(`/api/chats/${chatId}/messages/stream`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
    if (!res.ok) throw new Error('Server error');
    return res;
  }

  static async abortStream(chatId) {
    await this.request(`/api/chats/${chatId}/abort`, { method: 'POST' });
  }

  static async editMessage(messageId, content) {
    const res = await this.request(`/api/messages/${messageId}`, {
      method: 'PATCH',
      body: JSON.stringify({ content }),
    });
    if (!res.ok) throw new Error('Edit failed');
    return res.json();
  }
}

export { ApiService };
