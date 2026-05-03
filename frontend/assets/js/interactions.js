'use strict';
/* BRIAS · Interaction Primitives (DESIGN.md §6–§7) */

// Literal easing values matching design-tokens.css (JS cannot read CSS custom properties)
const _EASE_SMOOTH      = 'cubic-bezier(0.32, 0.72, 0, 1)';
const _EASE_SNAPPY      = 'cubic-bezier(0.34, 1.56, 0.64, 1)';
const _EASE_DECELERATE  = 'cubic-bezier(0, 0, 0.2, 1)';
const _EASE_SPRING_SOFT = 'cubic-bezier(0.25, 0.46, 0.45, 0.94)';

// ── §6.1 GPU warm-up ──
function warmUpAnimations() {
  const warmer = document.createElement('div');
  warmer.style.cssText = 'position:fixed;top:0;left:0;width:1px;height:1px;opacity:0;pointer-events:none;will-change:transform,opacity,filter;transform:translateZ(0);contain:strict;';
  document.body.appendChild(warmer);
  warmer.animate(
    [
      { transform: 'translateZ(0) scale(1)',     opacity: 0,     filter: 'blur(0)' },
      { transform: 'translateZ(0) scale(1.001)', opacity: 0.001, filter: 'blur(0.1px)' },
    ],
    { duration: 100, easing: _EASE_SMOOTH }
  ).onfinish = () => warmer.remove();
}

// Pass 6 audit: loaded with `defer` on all pages → executes before DOMContentLoaded fires,
// so this listener always registers in time. Confirmed correct on chat.html, planner.html, journal.html.
document.addEventListener('DOMContentLoaded', warmUpAnimations);

// ── §7.3 Ripple ──
function emitRipple(event, element) {
  const rect = element.getBoundingClientRect();
  // §6.3: all reads before writes
  const x = (event.clientX != null ? event.clientX : rect.left + rect.width  / 2) - rect.left;
  const y = (event.clientY != null ? event.clientY : rect.top  + rect.height / 2) - rect.top;
  const size = Math.max(rect.width, rect.height) * 2;

  requestAnimationFrame(() => {
    element.classList.add('ripple-host');
    const ripple = document.createElement('div');
    ripple.className = 'ripple';
    ripple.style.cssText = `width:${size}px;height:${size}px;left:${x - size / 2}px;top:${y - size / 2}px;`;
    element.appendChild(ripple);

    ripple.animate(
      [
        { transform: 'scale(0)',   opacity: 0 },
        { transform: 'scale(0.5)', opacity: 0.15, offset: 0.2 },
        { transform: 'scale(1)',   opacity: 0 },
      ],
      { duration: 640, easing: _EASE_DECELERATE, fill: 'forwards' }
    ).onfinish = () => ripple.remove();
  });
}

// ── §7.2 Magnetic hover (desktop only) ──
function attachMagnetic(element, options = {}) {
  if (window.matchMedia('(hover: none)').matches) return;

  const { radius = 80, strength = 0.25 } = options;
  let rafId = null;

  function onMove(e) {
    cancelAnimationFrame(rafId);
    rafId = requestAnimationFrame(() => {
      const rect = element.getBoundingClientRect();
      const cx = rect.left + rect.width  / 2;
      const cy = rect.top  + rect.height / 2;
      const dist = Math.hypot(e.clientX - cx, e.clientY - cy);
      if (dist < radius) {
        element.style.transform = `translateZ(0) translate(${(e.clientX - cx) * strength}px,${(e.clientY - cy) * strength}px)`;
      }
    });
  }

  function onLeave() {
    cancelAnimationFrame(rafId);
    element.style.transform = 'translateZ(0) translate(0,0)';
  }

  element.addEventListener('mousemove', onMove,  { passive: true });
  element.addEventListener('mouseleave', onLeave, { passive: true });
}

// ── §7.5 Breathing idle ──
function breathingIdle(element) {
  return element.animate(
    [
      { opacity: 0.92, transform: 'translateZ(0) scale(1)' },
      { opacity: 1.0,  transform: 'translateZ(0) scale(1.015)' },
      { opacity: 0.92, transform: 'translateZ(0) scale(1)' },
    ],
    { duration: 3200, easing: _EASE_SPRING_SOFT, iterations: Infinity }
  );
}

// ── Spring animate wrapper ──
function springAnimate(element, keyframes, options = {}) {
  return element.animate(keyframes, { easing: _EASE_SNAPPY, ...options });
}
