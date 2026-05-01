# BRIAS Design Language

This document defines the visual and interactive design language for the
BRIAS frontend. Every change to UI, animation, or interaction should be
checked against these principles. When in doubt, choose the option that
feels more *alive*, not the option that is more efficient to build.

BRIAS is a mental support companion. The interface is part of the support.
A surface that feels present, attentive, and warm reduces the user's sense
of isolation before BRIAS even responds. This is not decoration — this is
the product.

## Core philosophy: presence

The interface should feel like a quiet, attentive presence — never sterile,
never busy. Every element behaves as if it is *aware* it is being looked at
and *responds* when interacted with. Nothing is purely static. Nothing
moves without reason.

Reference points:
- Apple iOS/macOS (premium feel, spring physics, restraint)
- Linear (cursor-aware UI, perfect timing)
- Things 3 (organic micro-interactions, warmth)
- NOT: Material Design (too mechanical), generic SaaS (too sterile)

## Animation curves (use ONLY these)

```css
:root {
  /* Smooth — for graceful movement, no bounce. Most morphs and reveals. */
  --ease-smooth: cubic-bezier(0.32, 0.72, 0, 1);

  /* Snappy — small bounce. UI elements landing, modals appearing. */
  --ease-snappy: cubic-bezier(0.34, 1.56, 0.64, 1);

  /* Decelerate — for things sliding in from offscreen or fading in. */
  --ease-decelerate: cubic-bezier(0, 0, 0.2, 1);

  /* Accelerate — for things leaving (always faster than entering). */
  --ease-accelerate: cubic-bezier(0.4, 0, 1, 1);

  /* Spring-soft — for hover responses and idle breathing. */
  --ease-spring-soft: cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
```

NEVER use: `ease`, `ease-in`, `ease-out`, `ease-in-out`, `linear` (except
for opacity-only fades under 200ms). These read as "default web" and break
the premium feel instantly.

## Duration scale

```css
:root {
  --duration-instant: 80ms;   /* Tap feedback, ripples */
  --duration-quick:   160ms;  /* Hover responses, button states */
  --duration-medium:  280ms;  /* Most transitions, dismissals */
  --duration-slow:    420ms;  /* Modal/sheet appearances, morphs */
  --duration-slower:  640ms;  /* Page transitions, hero animations */
}
```

Rule: **leaving is always 20% faster than entering.** A modal that opens
in 420ms closes in 320ms. This matches user expectation and feels right.

## The eight principles

### 1. Causality
Every animation has a *cause*. Elements don't just appear — they appear
*because* something happened. A new message arrives because the user sent
one. A button highlights because the cursor is approaching it. If you
can't articulate the cause, the animation shouldn't exist.

### 2. Anticipation
Before any significant motion, the element "breathes in" by 1-2% scale or
1-2px translation in the *opposite* direction of where it's going. This is
classic Disney animation. On a button press: scale to 0.98 first (anticipation),
then to 0.95 (action), then spring back to 1.02 (overshoot), settle to 1.

### 3. Continuity
Animations never end on a hard stop. Use spring physics or settle curves.
If an element is interrupted mid-animation, the new animation must respect
the current velocity (use `interpolatingSpring`-style logic via Web
Animations API or a spring library — never just snap to a new tween).

### 4. Magnetic attention
Interactive elements respond when the cursor is *near* them, not just on
them. Within ~80px of a button: subtle glow intensifies, scale increases
to 1.01, faint shadow grows. The button feels like it has gravity.
Implementation: track cursor position, calculate distance, apply transforms
proportional to inverse distance.

### 5. Ambient breathing
No element is ever fully static. Idle states have:
- Background glow: slow opacity oscillation 0.95-1.0 over 4-6 seconds
- Cards/surfaces: imperceptible shadow oscillation
- BRIAS avatar/indicator: 4-second breath cycle

This must be at the edge of perception. If a user notices it consciously,
it's too strong.

### 6. Haptic echo (visual)
Every tap/click on a surface emits a faint radial ripple from the contact
point — 1-2px max radius growth, opacity 0 to 0.15 to 0, over 480ms.
Like a drop in water. Subtle enough that it registers in the body, not
the eye.

### 7. Sound-of-motion (no actual sound)
The way things move should *suggest* a sound. A heavy modal sliding in
should feel like it has weight (slower decelerate). A toggle should feel
like it has a click (sharp snap with overshoot). A chat message arriving
should feel like a soft puff (gentle blur-in + scale 0.96 to 1).

### 8. Restraint
The hardest rule. If everything moves, nothing feels alive. The most
animated apps feel hectic. Pick THE most important element on the screen
and let it have the most personality. Everything else supports.

## Implementation patterns

### Buttons (default)

```css
.btn {
  transition:
    transform var(--duration-quick) var(--ease-spring-soft),
    box-shadow var(--duration-quick) var(--ease-spring-soft),
    background-color var(--duration-quick) var(--ease-spring-soft);
  will-change: transform;
}

.btn:hover {
  transform: scale(1.02) translateY(-1px);
  box-shadow: 0 4px 16px rgba(255, 140, 80, 0.15);
}

.btn:active {
  transform: scale(0.97);
  transition-duration: var(--duration-instant);
}
```

For premium buttons (primary CTAs), add the magnetic effect via JS — see
`magnetic-cursor.js` (to be created).

### Click ripple

Every clickable surface must emit a ripple. Implementation:

```js
function emitRipple(event, element) {
  const rect = element.getBoundingClientRect();
  const ripple = document.createElement('span');
  ripple.className = 'ripple';
  ripple.style.left = `${event.clientX - rect.left}px`;
  ripple.style.top = `${event.clientY - rect.top}px`;
  element.appendChild(ripple);
  ripple.animate(
    [
      { transform: 'translate(-50%, -50%) scale(0)', opacity: 0.15 },
      { transform: 'translate(-50%, -50%) scale(20)', opacity: 0 }
    ],
    { duration: 480, easing: 'cubic-bezier(0, 0, 0.2, 1)' }
  ).onfinish = () => ripple.remove();
}
```

### Message arrival (chat)

New chat messages should not just appear — they should *settle in*:

```css
@keyframes message-arrive {
  0%   { opacity: 0; transform: translateY(8px) scale(0.96); filter: blur(2px); }
  60%  { opacity: 1; filter: blur(0); }
  100% { transform: translateY(0) scale(1); }
}

.message {
  animation: message-arrive 480ms cubic-bezier(0.32, 0.72, 0, 1);
}
```

### Idle breathing on the BRIAS indicator

```css
@keyframes brias-breath {
  0%, 100% { opacity: 0.92; transform: scale(1); }
  50%      { opacity: 1.0;  transform: scale(1.015); }
}

.brias-indicator {
  animation: brias-breath 4.2s ease-in-out infinite;
}
```

Note: 4.2s, not 4s. Prime-ish numbers feel more organic than round ones.

### Modals and sheets

Use the FLIP pattern from the offline-card dismissal animation. Modals
appear with a subtle blur-fade on the background (backdrop-filter:
blur(0px) → blur(20px)) over 420ms, while the modal itself scales from
0.94 to 1 with the snappy curve.

### Scroll-into-view reveals

Elements that scroll into view (history items, settings sections) reveal
with a 16px translateY + opacity fade, staggered by 60ms per item.
NEVER all at once. The stagger creates a feeling of the page "loading
toward you" rather than "appearing at you".

## Forbidden patterns

These break the design language. Do not use:

- `ease`, `ease-in`, `ease-out`, `ease-in-out` (lazy, generic)
- Box shadows that don't move with the element on hover
- Buttons with only color changes on hover (no scale/lift)
- Modals with abrupt appear/disappear
- Hard cuts on state changes (always interpolate)
- Loading spinners (use shimmer/skeleton instead, more refined)
- Multiple competing animations on the same element
- Synchronized animations across the screen (everything moving in lockstep
  feels mechanical — stagger always, even by 30-60ms)
- Scale animations without a transform-origin set (will look wrong)
- Animating width/height/top/left (use FLIP + transform instead)

## Accessibility

Every animation must respect `prefers-reduced-motion: reduce`. When this is
set, replace motion with simple opacity fades under 150ms. Never disable
animations entirely — that feels broken. Just simplify them.

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 150ms !important;
    transition-timing-function: linear !important;
  }
}
```

## When in doubt

Ask: "Does this make BRIAS feel more *present*?" If yes, do it. If it just
looks cool, don't.
