# BRIAS Side Menu — Fix Brief

The current gel-button implementation in the side menu has conceptual and visual problems. Read this fully before changing anything. The goal is one cohesive warm surface, not "dark panel with some warm icons floating on it."

## What's wrong right now

**1. The buttons are at the wrong level.**
Each menu row (Chat, Journal, Planner, Mindspace) IS a button — the entire row is the tappable area. The 40px squircle next to each title is just an icon container *inside* the row, not a button by itself. Currently the gel treatment is on the small squircle, which means:
- The actual hit-area (the row) has no premium interaction
- On mobile, the user's thumb covers the 40px icon when tapping, so the animation is literally invisible
- Selected/hover states feel disconnected from where the user actually touched

**2. The selected/hover states are grey.**
Tap a row that isn't selected and it goes generic-grey. Grey has no place in this menu. BRIAS is warm — every interactive state needs warm tinting (orange/pink gradients at low opacity), never `rgba(255,255,255,x)` for surface tints.

**3. The bottom settings button is round.**
It should be a squircle. We specified `border-radius: 20px` on a ~56–64px button with the full gel treatment from `brias-gel-button.md`. The profile avatar (the gradient "J" circle) can stay round — avatars are conventionally round and that's fine — but the settings gear next to it must be squircle and use the gel system.

**4. The panel itself reads cold.**
The side menu background is flat dark. It should have a very faint warm vertical gradient underneath everything so the whole surface feels like part of one warm space, not separate elements pasted onto cold neutral.

---

## How to fix it

### Menu rows (Chat / Journal / Planner / Mindspace)

The **row** is the button. Each row should:

```css
.menu-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  border-radius: 16px;
  cursor: pointer;
  position: relative;
  
  /* default — almost invisible warmth */
  background: transparent;
  
  /* smooth ease for hover, spring for press */
  transition:
    background 220ms ease,
    transform 500ms cubic-bezier(0.2, 1.6, 0.4, 1),
    box-shadow 300ms ease;
}

.menu-row:hover {
  background: linear-gradient(90deg,
    rgba(255, 140, 90, 0.07),
    rgba(255, 90, 140, 0.035));
}

.menu-row:active {
  transform: scale(0.99);
  transition: transform 80ms ease-out;
}

.menu-row[aria-current="page"],
.menu-row.is-selected {
  background: linear-gradient(90deg,
    rgba(255, 140, 90, 0.12),
    rgba(255, 90, 140, 0.06));
  box-shadow: 0 4px 24px -10px rgba(255, 140, 90, 0.30);
}

/* selected row's title gets the warm gradient too */
.menu-row.is-selected .row-title {
  background: linear-gradient(135deg, #FFA770, #FF5A8C);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
```

**The 40px icon container stays decorative** — keep its current gel look (warm gradient icon stroke, drop-shadow halo painting the inner gel surface), but remove any hover/press animations on the icon itself. All motion lives on the parent row.

### Bottom settings button

Change from round to squircle. Apply the full gel-button spec from `brias-gel-button.md` — but smaller:

```css
.settings-btn {
  width: 44px;          /* compact for footer */
  height: 44px;
  border-radius: 14px;  /* still ~32% — squircle */
  /* ... rest of .gel-btn styles from brias-gel-button.md ... */
}

.settings-btn svg {
  width: 22px;
  height: 22px;
  /* same filter drop-shadows from brias-gel-button.md */
}
```

This is the only "real" isolated gel button in the side menu — it gets the full spring physics, the internal halo, the works.

### Panel background — the cohesion fix

Add a faint warm gradient to the side panel container:

```css
.side-menu {
  background:
    linear-gradient(180deg,
      rgba(255, 140, 90, 0.018) 0%,
      transparent 35%,
      rgba(255, 90, 140, 0.012) 100%),
    #0e0a0c; /* or whatever the current near-black is */
}
```

So faint you almost can't consciously see it, but the panel stops feeling cold-grey and starts feeling like a warm space. Test by toggling the gradient off — the difference is real even if small.

### Banish grey everywhere

Search the side menu CSS for any:
- `rgba(255, 255, 255, x)` used as a background/hover tint → swap to warm equivalent
- Pure `#xxxxxx` grey hex colors used for interactive states → swap to warm
- Default browser `:active` greys → override explicitly

Warm replacements:
- For orange-leaning surfaces: `rgba(255, 140, 90, x)`
- For pink-leaning surfaces: `rgba(255, 90, 140, x)`
- For neutral warm text/borders: `rgba(255, 230, 215, x)` (warm white)

### Mobile consideration

On mobile, the visible animation needs to happen in the area the thumb is NOT covering:
- Row hover/select background extends across the full row — visible above and to the side of the thumb ✓
- Glow shadow under selected row extends below — visible beyond the touch point ✓
- Title color shift on selected — visible at the right edge of the row ✓

Don't put animation logic that only fires on the small icon (left-aligned) — it'll be obscured.

---

## Done-check

When this is finished, the side menu should:

1. Feel like one warm surface, not a grey panel with warm decorations
2. Have rows that respond *as rows* when tapped, with warm gradient fills and a soft underglow on the selected one
3. Have a squircle gel-button for settings at the bottom (with full gel treatment from `brias-gel-button.md`)
4. Contain zero grey hover/active states
5. Show the selected row clearly even when a finger is covering most of the icon

Don't add new animations beyond what's specified here — the row-level interaction is intentionally subtle (`scale(0.99)`) because the *background fill* is doing the work, not motion. Spectacle stays at the bottom settings button.
