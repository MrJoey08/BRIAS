/* ═══════════════════════════════════════════════
   BRIAS — typewriter.js
   Auth screen typewriter animation
   ═══════════════════════════════════════════════ */

import { CONFIG, TYPEWRITER_PHRASES } from './config.js';
import { shuffleArray } from './helpers.js';

class Typewriter {
  constructor(elementId) {
    this.el = document.getElementById(elementId);
    this.queue = [...TYPEWRITER_PHRASES];
    shuffleArray(this.queue);
    this.queueIndex = 0;
    this.charIndex = 0;
    this.isDeleting = false;
    this.isRunning = false;
  }

  start() {
    if (!this.el || this.isRunning) return;
    this.isRunning = true;
    setTimeout(() => this._tick(), CONFIG.TYPEWRITER.INITIAL_DELAY);
  }

  stop() {
    this.isRunning = false;
  }

  _tick() {
    if (!this.isRunning) return;

    const phrase = this.queue[this.queueIndex];
    const tw = CONFIG.TYPEWRITER;

    if (!this.isDeleting) {
      // Typing forward
      this.el.textContent = phrase.slice(0, this.charIndex + 1);
      this.charIndex++;

      if (this.charIndex >= phrase.length) {
        // Pause then start deleting
        setTimeout(() => {
          this.isDeleting = true;
          this._tick();
        }, tw.PAUSE_AFTER_TYPE);
        return;
      }

      setTimeout(() => this._tick(), tw.TYPE_SPEED_MIN + Math.random() * tw.TYPE_SPEED_VAR);
    } else {
      // Deleting
      this.el.textContent = phrase.slice(0, this.charIndex);
      this.charIndex--;

      if (this.charIndex < 0) {
        this.isDeleting = false;
        this.charIndex = 0;
        this.queueIndex++;

        if (this.queueIndex >= this.queue.length) {
          this.queue = [...TYPEWRITER_PHRASES];
          shuffleArray(this.queue);
          this.queueIndex = 0;
        }

        setTimeout(() => this._tick(), tw.PAUSE_AFTER_DELETE);
        return;
      }

      setTimeout(() => this._tick(), tw.DELETE_SPEED_MIN + Math.random() * tw.DELETE_SPEED_VAR);
    }
  }
}

export { Typewriter };
