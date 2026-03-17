/* ═══════════════════════════════════════════════════════════
   BRIAS — Offline Page Styles
   ═══════════════════════════════════════════════════════════ */

.offline-screen {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: var(--auth-bg);
  overflow: hidden;
}

.offline-content {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  padding: 0 24px;
  animation: fadeUp 0.6s var(--ease-smooth) both;
}

/* ── Animated pulse ring ── */
.offline-pulse {
  position: relative;
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.offline-pulse::before,
.offline-pulse::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 1px solid rgba(232, 118, 74, 0.15);
  animation: pulseRing 3s ease-in-out infinite;
}

.offline-pulse::after {
  animation-delay: 1.5s;
}

@keyframes pulseRing {
  0%   { transform: scale(0.8); opacity: 0.6; }
  50%  { transform: scale(1.6); opacity: 0; }
  100% { transform: scale(0.8); opacity: 0; }
}

.offline-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--grad);
  animation: offlineDotPulse 2s ease-in-out infinite;
}

@keyframes offlineDotPulse {
  0%, 100% { opacity: 0.4; transform: scale(0.9); }
  50%      { opacity: 1; transform: scale(1.1); }
}

.offline-title {
  font-family: var(--font-display);
  font-size: clamp(42px, 10vw, 64px);
  font-weight: 600;
  letter-spacing: 0.03em;
  background: var(--grad);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  opacity: 0.3;
}

.offline-heading {
  font-family: var(--font);
  font-size: 18px;
  font-weight: 600;
  color: var(--text-sub);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.offline-message {
  font-family: var(--font-body);
  font-size: 15px;
  color: var(--text-muted);
  text-align: center;
  line-height: 1.6;
  max-width: 340px;
}

.offline-retry-btn {
  margin-top: 12px;
  padding: 12px 32px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-sub);
  font-family: var(--font);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 0.02em;
}

.offline-retry-btn:hover {
  border-color: rgba(232, 118, 74, 0.3);
  background: rgba(232, 118, 74, 0.06);
  color: var(--orange);
}

.offline-retry-btn:active {
  transform: scale(0.97);
}

.offline-retry-btn.is-checking {
  pointer-events: none;
  opacity: 0.5;
}

.offline-footer {
  position: absolute;
  bottom: 24px;
  left: 0;
  right: 0;
  text-align: center;
  z-index: 2;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.08);
  letter-spacing: 0.1em;
  font-weight: 300;
}
