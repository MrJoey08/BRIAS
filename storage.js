/* ═══════════════════════════════════════════════
   BRIAS — storage.js
   LocalStorage abstraction for auth persistence
   ═══════════════════════════════════════════════ */

import { CONFIG } from './config.js';

class StorageService {

  static getToken() {
    return localStorage.getItem(CONFIG.STORAGE_KEYS.TOKEN) || null;
  }

  static setToken(token) {
    localStorage.setItem(CONFIG.STORAGE_KEYS.TOKEN, token);
  }

  static removeToken() {
    localStorage.removeItem(CONFIG.STORAGE_KEYS.TOKEN);
  }

  static getUsername() {
    return localStorage.getItem(CONFIG.STORAGE_KEYS.USERNAME) || null;
  }

  static setUsername(name) {
    localStorage.setItem(CONFIG.STORAGE_KEYS.USERNAME, name);
  }

  static removeUsername() {
    localStorage.removeItem(CONFIG.STORAGE_KEYS.USERNAME);
  }

  static clearAll() {
    this.removeToken();
    this.removeUsername();
  }

  static isAuthenticated() {
    return !!this.getToken();
  }
}

export { StorageService };
