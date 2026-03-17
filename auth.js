/* ═══════════════════════════════════════════════
   BRIAS — auth.js
   Authentication controller: login, register,
   verify, profile, offline detection
   ═══════════════════════════════════════════════ */

import { CONFIG } from './config.js';
import { ApiService } from './api.js';
import { StorageService } from './storage.js';
import { GlowBackground } from './glow.js';
import { Typewriter } from './typewriter.js';

class AuthController {
  constructor(onAuthenticated) {
    this.onAuthenticated = onAuthenticated;
    this.mode = 'login'; // 'login' | 'register'
    this.contact = '';
    this.offlineTimer = null;
    this.glow = new GlowBackground('authGlow');
    this.typewriter = new Typewriter('twText');

    this._bindEvents();
  }

  _bindEvents() {
    // Submit buttons
    document.getElementById('authSubmit')?.addEventListener('click', () => this.handleStep1());
    document.getElementById('authStep2')?.querySelector('.auth-submit-btn')?.addEventListener('click', () => this.handleStep2());
    document.getElementById('authStep3')?.querySelector('.auth-submit-btn')?.addEventListener('click', () => this.handleStep3());

    // Enter key on inputs
    document.getElementById('authPass')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') this.handleStep1();
    });
    document.getElementById('authCode')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') this.handleStep2();
    });
    document.getElementById('authAge')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') this.handleStep3();
    });

    // Switch mode
    document.addEventListener('click', (e) => {
      if (e.target.closest('[data-action="toggle-auth"]')) {
        this.toggleMode();
      }
      if (e.target.closest('[data-action="resend-code"]')) {
        this.resendCode();
      }
    });
  }

  /* ── Show / hide ── */

  show() {
    document.getElementById('authScreen').classList.remove('hidden');
    document.getElementById('appScreen').classList.add('hidden');
    requestAnimationFrame(() => this.glow.start());
    this.typewriter.start();
  }

  hide() {
    document.getElementById('authScreen').classList.add('hidden');
    this.typewriter.stop();
  }

  /* ── Steps navigation ── */

  _showStep(n) {
    ['authStep1', 'authStep2', 'authStep3'].forEach(id => {
      document.getElementById(id)?.classList.add('hidden');
    });
    document.getElementById(`authStep${n}`)?.classList.remove('hidden');
  }

  _showError(stepId, message) {
    const el = document.getElementById(stepId);
    if (el) {
      el.textContent = message;
      el.classList.remove('hidden');
    }
  }

  _hideError(stepId) {
    document.getElementById(stepId)?.classList.add('hidden');
  }

  _setLoading(btn, loading) {
    btn?.classList.toggle('is-loading', loading);
  }

  /* ── Toggle login/register ── */

  toggleMode() {
    this.mode = this.mode === 'login' ? 'register' : 'login';
    const submitBtn = document.getElementById('authSubmit');
    const switchEl = document.getElementById('authSwitch');

    submitBtn.textContent = this.mode === 'login' ? 'Log in' : 'Sign up';

    if (this.mode === 'login') {
      switchEl.innerHTML = 'No account? <a data-action="toggle-auth">Sign up</a>';
    } else {
      switchEl.innerHTML = 'Already have an account? <a data-action="toggle-auth">Log in</a>';
    }

    this._hideError('authError');
  }

  /* ── Step 1: Email + Password ── */

  async handleStep1() {
    const contact = document.getElementById('authContact').value.trim();
    const password = document.getElementById('authPass').value;

    if (!contact || !password) {
      this._showError('authError', 'Please fill in all fields');
      return;
    }

    this._hideError('authError');
    const btn = document.getElementById('authSubmit');
    this._setLoading(btn, true);

    try {
      const data = this.mode === 'login'
        ? await ApiService.login(contact, password)
        : await ApiService.register(contact, password);

      if (data.token) {
        // Direct login (no verification needed)
        StorageService.setToken(data.token);
        StorageService.setUsername(data.username);
        this.onAuthenticated();
        return;
      }

      // Need verification
      this.contact = contact;
      document.getElementById('sentTo').textContent = contact;
      this._showStep(2);

    } catch (err) {
      this._showError('authError', err.message || 'Could not connect to server');
    } finally {
      this._setLoading(btn, false);
    }
  }

  /* ── Step 2: Verification code ── */

  async handleStep2() {
    const code = document.getElementById('authCode').value.trim();

    if (!code) {
      this._showError('authError2', 'Please enter the verification code');
      return;
    }

    this._hideError('authError2');

    try {
      const data = await ApiService.verify(this.contact, code);
      StorageService.setToken(data.token);
      StorageService.setUsername(data.username);

      if (this.mode === 'register' && !data.profile_complete) {
        this._showStep(3);
        return;
      }

      this.onAuthenticated();

    } catch (err) {
      this._showError('authError2', err.message || 'Could not connect to server');
    }
  }

  /* ── Step 3: Profile setup ── */

  async handleStep3() {
    const name = document.getElementById('authName').value.trim();
    const age = document.getElementById('authAge').value.trim();

    if (!name) {
      this._showError('authError3', 'We need at least a name');
      return;
    }

    this._hideError('authError3');

    try {
      const data = await ApiService.completeProfile(name, age);
      StorageService.setUsername(data.username || name);
      this.onAuthenticated();

    } catch (err) {
      this._showError('authError3', err.message || 'Could not connect to server');
    }
  }

  /* ── Resend code ── */

  async resendCode() {
    try {
      await ApiService.resendCode(this.contact);
    } catch { /* silently fail */ }
  }

  /* ── Offline detection ── */

  setOffline(isOffline) {
    const el = document.getElementById('authOffline');
    const card = document.querySelector('.auth-card');

    if (isOffline) {
      el?.classList.remove('hidden');
      card?.classList.add('is-offline');

      if (!this.offlineTimer) {
        this.offlineTimer = setInterval(async () => {
          if (await ApiService.checkOnline()) {
            this.setOffline(false);
          }
        }, CONFIG.HEALTH_CHECK_INTERVAL);
      }
    } else {
      el?.classList.add('hidden');
      card?.classList.remove('is-offline');

      if (this.offlineTimer) {
        clearInterval(this.offlineTimer);
        this.offlineTimer = null;
      }
    }
  }
}

export { AuthController };
