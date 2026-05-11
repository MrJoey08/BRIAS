# BRIAS Gel Button — Implementation Blueprint

Squircle gel button with warm gradient icon. Magnetic spring physics on press, internal warm halo painted onto the gel surface by the icon itself. Designed for BRIAS's dark warm theme.

## Design tokens

| Token | Value | Notes |
|---|---|---|
| Button size | `64 × 64 px` | Adjustable, keep 1:1 |
| Border radius | `20px` (~31% of width) | Squircle — not full circle, not square |
| Icon size | `28px` | Gear stroke `1.6` |
| Warm gradient | `#FFA770 → #FF5A8C` | 135°, orange → pink |
| Surface gradient | `rgba(255,255,255,0.085) → rgba(255,255,255,0.02)` | Top → bottom |
| Border | `0.5px solid rgba(255,255,255,0.20)` | Thin rim-light |

## HTML + SVG

If you have multiple gel buttons, define the gradient **once** in a hidden SVG and reference it with `<use>` per button. Otherwise inline the `<defs>` in each button.

```html
<!-- Define gradient once, near top of <body> -->
<svg style="position:absolute;width:0;height:0" aria-hidden="true">
  <defs>
    <linearGradient id="brias-warm" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#FFA770"/>
      <stop offset="100%" stop-color="#FF5A8C"/>
    </linearGradient>
  </defs>
</svg>

<!-- Use anywhere -->
<button class="gel-btn" aria-label="Settings">
  <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
    <g stroke="url(#brias-warm)" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
      <circle cx="12" cy="12" r="3"/>
    </g>
  </svg>
</button>
```

## CSS

```css
.gel-btn {
  /* shape */
  width: 64px;
  height: 64px;
  border-radius: 20px;

  /* gel surface */
  background: linear-gradient(180deg, rgba(255,255,255,0.085), rgba(255,255,255,0.02));
  border: 0.5px solid rgba(255,255,255,0.20);

  /* CRITICAL: clips the icon glow to the squircle, creating internal halo */
  overflow: hidden;
  position: relative;

  /* layout */
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  cursor: pointer;

  /* spring physics — asymmetric transition is the magic */
  transition:
    transform 600ms cubic-bezier(0.2, 1.8, 0.4, 1),
    box-shadow 300ms ease;
}

/* top specular highlight — the "wet glass" look */
.gel-btn::before {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(255,255,255,0.22), transparent 42%);
  pointer-events: none;
}

/* the icon glow that paints the gel surface from inside */
.gel-btn svg {
  position: relative;
  z-index: 2;
  filter:
    drop-shadow(0 0 5px rgba(255,140,90,0.55))
    drop-shadow(0 0 10px rgba(255,90,140,0.35));
}

/* hover: subtle lift with depth shadow */
.gel-btn:hover {
  transform: translateY(-3px);
  box-shadow:
    0 10px 24px -8px rgba(0, 0, 0, 0.55),
    0 0 0 0.5px rgba(255, 255, 255, 0.08);
}

/* press: deep scale, snappy. Release: spring back via .gel-btn transition */
.gel-btn:active {
  transform: scale(0.82);
  transition: transform 75ms ease-out;
}
```

## Why this works — don't change these without testing

1. **`overflow: hidden`** — clips the icon's `drop-shadow` to the squircle, creating the internal halo on the gel surface. Without this, the glow leaks outside the button and the "lit from inside" effect dies.
2. **Spring curve `cubic-bezier(0.2, 1.8, 0.4, 1)`** — the second control point `1.8` is what creates the overshoot bounce on release.
3. **Asymmetric transition timing** — 600ms spring on default state, 75ms ease-out on `:active`. Press is snappy (responsive), release is bouncy (alive). Symmetric timing kills the feel.
4. **Two stacked `drop-shadow` filters** — short tight orange (5px blur) + wider soft pink (10px blur) = gradient halo, not single-color glow.
5. **`::before` highlight** — the 22%→0% linear gradient at top is the polished-glass specular. Subtle but essential.

## Variants

**Lighter glow (utility buttons / dense bars):**
```css
.gel-btn svg {
  filter:
    drop-shadow(0 0 3px rgba(255,140,90,0.40))
    drop-shadow(0 0 6px rgba(255,90,140,0.22));
}
```

**Less dramatic press (where overshoot feels too much):**
```css
.gel-btn:active { transform: scale(0.92); }
```

**Different size:** scale `width`/`height` and adjust `border-radius` proportionally — keep at ~30% of width for squircle feel. Icon size scales independently.

**Different icon:** replace `<path>` and `<circle>` inside the `<g>`. Keep the `stroke` and gradient ref — that's where the warmth comes from.
