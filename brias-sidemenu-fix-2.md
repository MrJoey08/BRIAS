# BRIAS Side Menu — Round 2 Fix

Two targeted fixes on top of the previous work. Do NOT redo anything else.

## Fix 1 — Revert the active/selected state

The selected row used to look good. The previous fix (`brias-sidemenu-fix.md`) accidentally made it too saturated, and now hover ≈ selected. They need to be clearly different.

**Step 1.** Check git history for the `.menu-row.is-selected` (or whatever class marks the active route) styling that existed BEFORE `brias-sidemenu-fix.md` was applied. Restore it exactly.

**Step 2.** If git history isn't available, use this as the target:

```css
/* hover — barely there, just a hint */
.menu-row:hover {
  background: linear-gradient(90deg,
    rgba(255, 140, 90, 0.035),
    rgba(255, 90, 140, 0.018));
}

/* selected — clearly more prominent than hover, but still subtle */
.menu-row.is-selected,
.menu-row[aria-current="page"] {
  background: linear-gradient(90deg,
    rgba(255, 140, 90, 0.10),
    rgba(255, 90, 140, 0.05));
  box-shadow: 0 4px 20px -12px rgba(255, 140, 90, 0.25);
}

.menu-row.is-selected .row-title {
  background: linear-gradient(135deg, #FFA770, #FF5A8C);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
```

The intensity ratio matters more than exact numbers: **selected should read ~3x more visible than hover**. If hover and selected look comparable when sitting next to each other, the values are wrong.

## Fix 2 — Stop styling the icon containers like gel buttons

The 40px squircles next to each title still read as their own tappable thing because they have all the visual cues of a button: border, top specular highlight, white-tinted surface gradient. They need to feel like a *nook* in the row, not a button *on* the row.

**Remove from the icon container (`.row-icon` or equivalent):**
- The `0.5px solid rgba(255,255,255,...)` border
- The white-tint surface gradient (`linear-gradient(180deg, rgba(255,255,255,0.085), ...)`)
- The `::before` pseudo-element with the top specular highlight

**Keep:**
- Squircle shape via `border-radius`
- The warm-gradient SVG icon
- The `drop-shadow` halo on the SVG (the glow stays)

**Replace surface with a subtle dark inset:**

```css
.row-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  
  /* slightly darker than the row's background — reads as inset, not raised */
  background: rgba(0, 0, 0, 0.25);
  
  /* NO border. NO ::before highlight. NO white tint. */
}

.row-icon svg {
  filter:
    drop-shadow(0 0 4px rgba(255, 140, 90, 0.50))
    drop-shadow(0 0 8px rgba(255, 90, 140, 0.30));
}
```

Why this works: a raised gel surface with rim-light and highlight reads as "I'm a button, press me." A slightly darker inset reads as "I'm a frame for the icon." The warm glowing icon inside both cases is identical — only the container's role changes. Now the row visibly contains the icon instead of carrying the icon as a passenger.

## Fix 3 — Confirm bottom settings is correct

The bottom-right gear button should be the ONLY full gel-button in the side menu (per `brias-gel-button.md`). It should:
- Be squircle (not round) — `border-radius: 14px` on a 44px button
- Have the raised gel surface (the white-tint gradient + ::before highlight + border)
- Have the spring physics on press
- Have the warm icon with drop-shadow halo

If the screenshot shows it as round or missing the gel treatment, apply `brias-gel-button.md` to it.

## Done-check

- Hover vs selected: clearly different intensity, no longer confusable
- Icon containers: no visible border, no white shine on top, just a subtle dark nook with a glowing icon
- Bottom settings button: squircle, with full gel treatment, with spring press
- Nothing in the menu reads grey
- The row, not the icon, is unmistakably the tappable thing
