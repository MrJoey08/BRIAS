# BRIAS Design Language

This document is the source of truth for every UI, animation, and
interaction decision in the BRIAS frontend. It is not a style guide —
it is a *behavioral* guide. The visual design (colors, typography,
layout) is owned elsewhere. This one defines how the interface
*moves* and *responds*.

Read this document in full before making any frontend change. When in
doubt about a specific decision, return to the eight principles in
section 4 and ask: *which principle does this serve?* If the answer is
"none", do not make the change.

---

## 1. Why this document exists

BRIAS is a mental support companion. The interface is part of the
support. A surface that feels present, attentive, and warm reduces the
user's sense of isolation before BRIAS has said a single word. This is
not decoration. This is the product.

The hardest thing to copy in software is *how it feels*. Models become
commodities. Features get cloned in weeks. But the *presence* of an
interface — the sense that something is there with you — takes years
to build and is almost impossible to reverse-engineer. This is the
moat. Treat it accordingly.

---

## 2. Core philosophy: presence

The interface should feel like a quiet, attentive presence — never
sterile, never busy. Every element behaves as if it is *aware* it is
being looked at and *responds* when interacted with. Nothing is purely
static. Nothing moves without reason.

Reference points:
- **Apple iOS/macOS** — premium feel, spring physics, restraint
- **Linear** — cursor-aware UI, perfect timing, magnetic interactions
- **Things 3** — organic micro-interactions, warmth, calm
- **Arc browser** — playful presence without being childish

Anti-references (do *not* take inspiration from):
- Material Design — too mechanical, too uniform
- Generic SaaS dashboards — sterile, opacity-fade everything
- Discord, Slack — too busy, too many competing animations
- Most "AI chat" interfaces — flat, lifeless, indistinguishable

---

## 3. Tokens (use ONLY these)

### 3.1 Animation curves

```css
:root {
  /* Smooth — graceful movement, no bounce. Most morphs, reveals, transitions. */
  --ease-smooth: cubic-bezier(0.32, 0.72, 0, 1);

  /* Snappy — small overshoot. UI elements landing, modals appearing, toggles. */
  --ease-snappy: cubic-bezier(0.34, 1.56, 0.64, 1);

  /* Decelerate — for things entering from offscreen or fading in. */
  --ease-decelerate: cubic-bezier(0, 0, 0.2, 1);

  /* Accelerate — for things leaving (always faster than entering). */
  --ease-accelerate: cubic-bezier(0.4, 0, 1, 1);

  /* Spring-soft — for hover responses and idle breathing. */
  --ease-spring-soft: cubic-bezier(0.25, 0.46, 0.45, 0.94);

  /* Bounce-gentle — for celebratory moments only. */
  --ease-bounce-gentle: cubic-bezier(0.34, 1.8, 0.64, 1);
}
```

**NEVER use:** `ease`, `ease-in`, `ease-out`, `ease-in-out`, `linear`.
Exception: `linear` is permitted *only* for opacity-only fades under
200ms where curve choice is imperceptible. These defaults read as
"generic web" and break the premium feel instantly.

### 3.2 Duration scale

```css
:root {
  --duration-instant: 80ms;   /* Tap feedback, ripples, micro-confirmations */
  --duration-quick:   160ms;  /* Hover responses, button states */
  --duration-medium:  280ms;  /* Most transitions, dismissals */
  --duration-slow:    420ms;  /* Modal/sheet appearances, morphs, message arrival */
  --duration-slower:  640ms;  /* Page transitions, hero animations, ripples */
}
```

**Asymmetry rule:** *Leaving is always 20% faster than entering.* A modal
that opens in 420ms closes in 320ms. This matches user expectation
(action wants to feel decisive when reversed) and is one of the most
recognisable Apple patterns.

### 3.3 Motion hierarchy

Not every element gets equal motion budget. Higher tier = more motion.

| Tier | Element | Motion budget |
|------|---------|---------------|
| 1 | BRIAS indicator, message input, active chat message | High — full breathing, magnetic, ripple, anticipation |
| 2 | Primary CTAs, modal containers, navigation | Medium — hover lift, ripple, smooth transitions |
| 3 | Secondary buttons, toggles, dropdowns | Low — quick hover, subtle press feedback |
| 4 | Static text, icons, dividers, backgrounds | Minimal — ambient breathing only, no interaction motion |

If you find yourself adding motion to a tier-4 element, stop and re-read
principle #8.

---

## 4. The eight principles

These are not guidelines. They are rules. Every animation in the
codebase must serve at least one principle. If you can't name which
principle a motion serves, delete the motion.

### 4.1 Causality
Every animation has a *cause*. Elements don't just appear — they appear
*because* something happened.

- ✅ Right: button glows when cursor enters its magnetic radius
- ❌ Wrong: button glows on a 3-second loop "for visual interest"

### 4.2 Anticipation
Before any significant motion, the element "breathes in" by 1–2% scale
or 1–2px translation in the *opposite* direction of where it's going.
Classic Disney animation. On a button press: scale to 0.98 first
(anticipation), then to 0.95 (action), then spring back to 1.02
(overshoot), settle to 1.

- ✅ Right: button scales 0.98 → 0.95 → 1.02 → 1 on press
- ❌ Wrong: button scales 1 → 0.95 → 1 on press (no anticipation, no overshoot)

### 4.3 Continuity
Animations never end on a hard stop. Use spring physics or settle
curves. If interrupted mid-animation, the new animation must respect
the current velocity — never snap to a new tween.

- ✅ Right: spring-based animation, interruption blends into new spring
- ❌ Wrong: CSS transition that resets to 0 when re-triggered mid-flight

### 4.4 Magnetic attention
Interactive elements respond when the cursor is *near* them, not just
on them. Within ~80px of a tier-1 or tier-2 element: subtle glow
intensifies, scale increases to 1.01, faint shadow grows. The element
feels like it has gravity. Disabled on touch devices (no hovering cursor).

- ✅ Right: send button gains 1px lift when cursor is 60px away
- ❌ Wrong: send button only changes on actual `:hover`

### 4.5 Ambient breathing
No tier-1 element is ever fully static. Idle states have:
- Background glow: slow opacity oscillation 0.95–1.0 over 4–6 seconds
- BRIAS indicator: 4.2-second breath cycle
- Active surfaces: imperceptible shadow oscillation

This must be at the *edge of perception*. If a user consciously
notices it, it's too strong. Test by looking away from the screen for
10 seconds, then back — you should feel like the screen "settled" into
view, not that things are moving.

### 4.6 Haptic echo (visual)
Every click on a tier-1 or tier-2 surface emits a faint radial ripple
from the contact point. Opacity 0 → 0.15 → 0, scale 0 → 20×, over
640ms. Like a drop in water. Subtle enough that it registers in the
body, not the eye.

This is the single most important effect for making the interface feel
*responsive in a physical sense*. Do not skip it.

### 4.7 Sound of motion (no actual sound)
The way things move should *suggest* a sound, even though no audio
plays. A heavy modal sliding in should feel like it has weight. A
toggle should feel like it has a click. A chat message arriving should
feel like a soft puff (gentle blur-in + scale 0.96 → 1).

If you can imagine the sound the animation would make, you've done
it right. If you can't, the motion is probably too generic.

### 4.8 Restraint
The hardest rule. If everything moves, nothing feels alive. Look at
Apple's interfaces: the majority of pixels at any moment are perfectly
still. Motion is *reserved* for what matters.

- ✅ Right: chat message arrives with full settle animation, sidebar items beside it stay perfectly still
- ❌ Wrong: chat message arrives, sidebar items also bounce, header glows, background pulses (chaos)

---

## 5. Moments of stillness

The principles above can be misread as "animate everything beautifully".
They are not. The interface needs moments where *nothing moves* for
the moments where things do move to feel meaningful.

Always still:
- Body text within a message that is already on screen
- Read/sent message timestamps
- Sidebar contents while user is reading a message
- Any element behind a modal (the modal moves; the world freezes)

Stillness is communication. When BRIAS is "thinking" (waiting for a
response), the input area should feel suspended — breathing slowed,
no ripples, the world holding its breath. When the response arrives,
motion returns. The contrast is the meaning.

---

## 6. First-use performance (CRITICAL — read this section twice)

This section exists because the first time a user interacts with an
animation, it must feel as smooth as the hundredth time. Anything less
breaks the premium illusion immediately, especially on mobile.

The most common cause of first-use jank is that the browser hasn't
yet allocated GPU layers, parsed font files, or initialized animation
interpolators when the first animation is requested. The result: the
first 1–3 frames drop, and the animation feels "laggy". By the second
use, everything is cached and it feels instant.

This is unacceptable. Every animation must feel identical on use #1
and use #100.

### 6.1 Mandatory warm-up routine

On every page load, run the warm-up routine *before* any user
interaction is possible. This pre-allocates GPU layers and primes the
animation system.

```js
// In a script that runs on DOMContentLoaded
function warmUpAnimations() {
  const warmer = document.createElement('div');
  warmer.style.cssText = `
    position: fixed;
    top: 0; left: 0;
    width: 1px; height: 1px;
    opacity: 0;
    pointer-events: none;
    will-change: transform, opacity, filter;
    transform: translateZ(0);
    contain: strict;
  `;
  document.body.appendChild(warmer);

  // Run a tiny animation to prime the WAAPI interpolator
  warmer.animate(
    [
      { transform: 'translateZ(0) scale(1)', opacity: 0, filter: 'blur(0)' },
      { transform: 'translateZ(0) scale(1.001)', opacity: 0.001, filter: 'blur(0.1px)' }
    ],
    { duration: 100, easing: 'cubic-bezier(0.32, 0.72, 0, 1)' }
  ).onfinish = () => warmer.remove();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', warmUpAnimations);
} else {
  warmUpAnimations();
}
```

### 6.2 Pre-promote critical elements to GPU layers

Tier-1 and tier-2 elements must be GPU-promoted *before* any
animation starts, not on the animation itself. This eliminates the
"first frame promotion stutter".

```css
.message-input,
.brias-indicator,
.send-button,
.modal-container,
.offline-card {
  transform: translateZ(0);  /* Force GPU layer immediately */
  backface-visibility: hidden;
  will-change: transform;     /* Hint persistent intent */
}
```

Note: leaving `will-change` on permanently is normally bad practice,
but for tier-1 elements that animate on nearly every interaction, the
memory cost is worth the smoothness. For tier-2/3 elements, add
`will-change` *before* animation starts and remove it on `finish`.

### 6.3 Read-before-write rule (eliminates layout thrashing)

The single biggest cause of mobile animation jank: calling
`getBoundingClientRect()`, `offsetTop`, `clientWidth`, etc. *during*
or *just before* an animation. These force a synchronous layout
recalculation, which on mobile takes 16–50ms — guaranteed dropped
frames.

Rule: *all reads happen first, then all writes happen.*

```js
// ❌ WRONG — interleaved reads and writes cause layout thrashing
function dismissCard(card, target) {
  const cardRect = card.getBoundingClientRect();      // READ
  card.style.transform = `translate(${cardRect.left}px, 0)`;  // WRITE
  const targetRect = target.getBoundingClientRect();  // READ — forces relayout!
  card.animate(/* ... */);
}

// ✅ RIGHT — batch reads, then batch writes
function dismissCard(card, target) {
  // Batch all reads first
  const cardRect = card.getBoundingClientRect();
  const targetRect = target.getBoundingClientRect();
  const cardRadius = getComputedStyle(card).borderRadius;
  const targetRadius = getComputedStyle(target).borderRadius;

  // Now all writes — no layout thrash
  requestAnimationFrame(() => {
    card.style.transformOrigin = 'top left';
    card.style.willChange = 'transform, opacity, border-radius, filter';
    card.animate(/* ... */);
    target.animate(/* ... */);
  });
}
```

### 6.4 Font loading must complete before animations involve text

If an animation includes text that hasn't finished loading its
custom font, the text re-flows mid-animation. Solution:

```js
async function waitForFonts() {
  if ('fonts' in document) {
    await document.fonts.ready;
  }
}

// Before any text-involving animation:
await waitForFonts();
runAnimation();
```

Also, use `font-display: swap` is FORBIDDEN for tier-1 surfaces. Use
`font-display: optional` instead, or preload fonts in the document
head:

```html
<link rel="preload" href="/fonts/bitter.woff2" as="font" type="font/woff2" crossorigin>
```

### 6.5 First-paint mobile checklist

Before declaring any animation production-ready:

- [ ] Test on a *cold* page load — close the browser tab, reopen, run animation immediately
- [ ] Test on a *throttled* connection (DevTools → Slow 3G) and *throttled CPU* (4× slowdown)
- [ ] Test on a real mobile device, not just DevTools mobile emulation
- [ ] Verify the warm-up routine runs before any interactive element is visible
- [ ] Verify GPU promotion is applied via `transform: translateZ(0)`
- [ ] Verify no `getBoundingClientRect` calls happen mid-animation
- [ ] Verify font loading is complete before text animates
- [ ] Profile in DevTools Performance tab — first run must hit 60fps

If first-use does not feel identical to second-use, the work is not done.

---

## 7. Implementation patterns

### 7.1 Buttons (tier 2 default)

```css
.btn {
  transition:
    transform var(--duration-quick) var(--ease-spring-soft),
    box-shadow var(--duration-quick) var(--ease-spring-soft),
    background-color var(--duration-quick) var(--ease-spring-soft);
  transform: translateZ(0);
  will-change: transform;
  transform-origin: center;
}

.btn:hover {
  transform: translateZ(0) scale(1.02) translateY(-1px);
  box-shadow: 0 4px 16px rgba(255, 140, 80, 0.15);
}

.btn:active {
  transform: translateZ(0) scale(0.97);
  transition-duration: var(--duration-instant);
}
```

For tier-1 buttons, layer on the magnetic effect and ripple via JS.

### 7.2 Magnetic cursor effect (tier 1, desktop only)

```js
function attachMagnetic(element, options = {}) {
  // Disable on touch devices
  if (matchMedia('(hover: none)').matches) return;

  const radius = options.radius ?? 80;
  const strength = options.strength ?? 0.25;
  let rafId = null;
  let pendingEvent = null;

  function update() {
    rafId = null;
    if (!pendingEvent) return;
    const e = pendingEvent;
    pendingEvent = null;

    // Read in a stable rect-cache to avoid forced layout per frame
    const rect = element.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const dx = e.clientX - cx;
    const dy = e.clientY - cy;
    const distance = Math.hypot(dx, dy);

    if (distance < radius) {
      const pull = (1 - distance / radius) * strength;
      element.style.transform =
        `translateZ(0) translate(${dx * pull}px, ${dy * pull}px) scale(${1 + pull * 0.04})`;
    } else if (element.style.transform) {
      element.style.transform = '';
    }
  }

  function onPointerMove(e) {
    pendingEvent = e;
    if (!rafId) rafId = requestAnimationFrame(update);
  }

  function onPointerLeave() {
    element.style.transform = '';
  }

  document.addEventListener('pointermove', onPointerMove, { passive: true });
  element.addEventListener('pointerleave', onPointerLeave);
}
```

### 7.3 Click ripple (tier 1 and tier 2)

```js
function emitRipple(event, element) {
  // Read once
  const rect = element.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;

  // Write
  const ripple = document.createElement('span');
  ripple.className = 'ripple';
  ripple.style.left = `${x}px`;
  ripple.style.top = `${y}px`;
  element.appendChild(ripple);

  ripple.animate(
    [
      { transform: 'translate(-50%, -50%) scale(0)',  opacity: 0.15 },
      { transform: 'translate(-50%, -50%) scale(20)', opacity: 0    }
    ],
    { duration: 640, easing: 'cubic-bezier(0, 0, 0.2, 1)' }
  ).onfinish = () => ripple.remove();
}
```

Required CSS:

```css
.ripple {
  position: absolute;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  pointer-events: none;
  transform: translate(-50%, -50%) scale(0);
  will-change: transform, opacity;
}

/* Parent must have: */
.ripple-host {
  position: relative;
  overflow: hidden;
}
```

### 7.4 Message arrival (chat)

```css
@keyframes message-arrive {
  0%   { opacity: 0; transform: translateY(8px) scale(0.96); filter: blur(2px); }
  60%  { opacity: 1;                                          filter: blur(0);  }
  100% { opacity: 1; transform: translateY(0)   scale(1);                       }
}

.message {
  animation: message-arrive 480ms var(--ease-smooth);
  transform-origin: bottom left;  /* sender side; flip for receiver */
  will-change: transform, opacity, filter;
}

/* Remove will-change after animation */
.message.arrived {
  will-change: auto;
}
```

The blur is critical. Without it the motion reads as "fade and slide".
With it, the message *materialises*.

### 7.5 BRIAS indicator breathing

```css
@keyframes brias-breath {
  0%, 100% { opacity: 0.92; transform: translateZ(0) scale(1);     }
  50%      { opacity: 1.0;  transform: translateZ(0) scale(1.015); }
}

.brias-indicator {
  animation: brias-breath 4.2s var(--ease-spring-soft) infinite;
  will-change: transform, opacity;
}
```

4.2s, not 4s. Prime-ish numbers feel more organic because they don't
sync with anything else on the page.

### 7.6 FLIP-based morph (modals, sheets, the offline-card pattern)

Used when an element transforms from one position/size to another,
*including* visually being absorbed into another element.

Reference implementation: offline card → typing bar dismissal in
`chat.html`.

Key requirements for any FLIP morph:
- Animate `transform` and `opacity` only — never `width`/`height`/`top`/`left`
- Animate `border-radius` if start and end have different corner shapes
- Add `filter: blur(2px)` near the end of the morph (offset 0.85+) for
  the "absorbed" feel — this is what makes it feel Apple-grade
- The receiving element must respond with a subtle squish (e.g.
  `scale(1.02, 0.96)` then settle) starting ~80ms *after* the morph
  begins, not simultaneously
- `transform-origin: top left` for predictable scale math
- All `getBoundingClientRect()` reads happen *before* any writes
- Set `will-change` before the animation, remove it on `finish`
- On mobile, run a warm-up animation on this element on page load
  (see section 6.1)

### 7.7 Modals and sheets

- Background: `backdrop-filter: blur(0px)` → `blur(20px)`, opacity
  0 → 1, over 420ms with `--ease-smooth`
- Modal container: `scale(0.94)` → `scale(1)`, `opacity 0 → 1`, over
  420ms with `--ease-snappy`
- Dismissal: 320ms (asymmetry rule) with `--ease-accelerate`
- World behind modal: must freeze (no breathing) while modal is open

### 7.8 Scroll-into-view reveals

Elements that scroll into view (settings sections, history items)
reveal with 16px `translateY` + opacity fade. Always staggered.

**Stagger formula:** `delay = base * sqrt(index)` where `base = 60ms`.
Square-root staggering feels more organic than linear because the gap
between item N and N+1 shrinks as N grows — matching how natural
sequences (footsteps, raindrops) feel.

```js
items.forEach((item, i) => {
  item.style.animationDelay = `${60 * Math.sqrt(i)}ms`;
});
```

### 7.9 Typography in motion

Text has different motion rules than UI elements:
- Headings entering a view: 12px `translateY` + opacity, 480ms
  `--ease-smooth`. Slightly slower than UI because text needs time to
  be read as it lands.
- Body text changing in place: cross-fade with 4px `translateY`, 220ms
  `--ease-decelerate`. Never instant.
- Numbers changing (counters, timers): roll-up animation if the number
  is meaningful; instant change if it's just a clock.
- *Never* animate individual letters of body text. That's a portfolio
  trick, not a product pattern.

---

## 8. Forbidden patterns

These break the design language. Treat any of them as a bug:

- `ease`, `ease-in`, `ease-out`, `ease-in-out` (lazy, generic)
- `linear` outside of opacity-only fades under 200ms
- Box shadows that don't move with the element on hover
- Buttons with only color changes on hover (no scale/lift)
- Modals with abrupt appear/disappear
- Hard cuts on state changes (always interpolate)
- Loading spinners (use shimmer/skeleton instead — more refined)
- Multiple competing animations on the same element
- Synchronised animations across the screen (always stagger)
- Scale animations without explicit `transform-origin`
- Animating `width`/`height`/`top`/`left` (use FLIP + transform)
- "Bouncy" easings on text reveals (text should feel calm, not playful)
- Hover states that don't release on `pointerleave` (sticky hover)
- Animations that block user input while playing (always interruptible)
- `getBoundingClientRect()` calls during animations (causes jank)
- `font-display: swap` on tier-1 surfaces (causes text reflow)
- Adding `will-change` only on `:hover` (too late — causes first-frame jank)

---

## 9. Accessibility

Every animation must respect `prefers-reduced-motion: reduce`. When
this is set, replace motion with simple opacity fades. Never disable
animations entirely — that feels broken. Just simplify them.

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 1ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 150ms !important;
    /* Keep timing functions intact — for opacity-only fades the curve
       is barely perceptible and this preserves design intent for users
       who can still benefit from subtle smoothing. */
  }

  /* Idle breathing animations have no functional purpose — disable them */
  .brias-indicator,
  .ambient-glow {
    animation: none !important;
  }
}
```

---

## 10. Performance requirements

Every animation must:
- Run at solid 60fps on a mid-range mobile device (target: iPhone 11, Galaxy A52)
- Run at solid 60fps on the *first* use, not just subsequent uses (see section 6)
- Use only GPU-friendly properties: `transform`, `opacity`, `filter`
- Be interruptible (user input always wins over animation completion)

Test method:
1. Chrome DevTools → Performance tab → CPU throttle 4× → record while interacting
2. Verify zero red bars (dropped frames) on the *first* run after page load
3. Repeat on a real mobile device, not emulation

Mobile-specific:
- Disable magnetic cursor on touch devices via `matchMedia('(hover: none)')`
- Reduce blur radius on filters (mobile GPUs handle blur poorly above 8px)
- Avoid animating more than 3 properties simultaneously on tier-1 elements
- Use `passive: true` on all scroll/pointer event listeners

---

## 11. The decision filter

Before adding, removing, or modifying any motion, ask in order:

1. **Which principle does this serve?** If none, stop.
2. **Which tier is this element?** Match motion budget accordingly.
3. **Is something else nearby already moving?** If yes, this should
   stay still or stagger.
4. **Will the first-use experience be identical to the hundredth?**
   If unclear, follow section 6 strictly.
5. **Does this make BRIAS feel more *present*?** If no, stop.
6. **Would I notice this if I weren't looking for it?** If yes, it's
   probably too strong.

If all six answers are good, ship it. If any one fails, redesign or
delete.

---

## 12. When to break these rules

Almost never. But four legitimate exceptions:

- **Celebratory moments** (first message sent, milestone reached) may
  use `--ease-bounce-gentle` and brief tier-elevation for an element.
  Use sparingly — once per session at most.
- **Error states** may use a single sharp shake (3 oscillations,
  240ms total) to signal something failed. Nothing else should shake.
- **The first 500ms of a new user's first session** may use slightly
  more pronounced motion to communicate "this thing is alive". After
  that, return to normal restraint.
- **Toggle components** may use tighter overshoot curves (1.2–1.4
  range) than `--ease-snappy` when the standard curve feels too bouncy
  for the click metaphor. The toggle knob (`cubic-bezier(0.34,1.4,0.6,1)`)
  and theme-switch pill (`cubic-bezier(0.34,1.2,0.6,1)`) are the only
  current instances. Do not extend this to other components.

If you're considering a fifth exception, the answer is no.
