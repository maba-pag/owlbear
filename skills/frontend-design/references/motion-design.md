# Motion Design Reference

> OwlBear adaptation — see `../NOTICE.md` for attribution.

Motion communicates state changes, guides attention, and conveys the system's
responsiveness. Poor motion creates distraction, increases perceived latency,
and fails users with vestibular disorders.

---

## Duration Scale

Define motion durations as tokens. Keep them short in interactive UIs:

```css
:root {
  --duration-instant:  50ms;   /* icon swap, state change, no travel */
  --duration-fast:    100ms;   /* hover effects, focus rings */
  --duration-base:    200ms;   /* most enter/exit transitions */
  --duration-slow:    350ms;   /* page-level transitions, large items */
  --duration-crawl:   600ms;   /* progress bars, skeleton loading */
}
```

**Guideline:** For interactive responses (button presses, hover states), use
100–200ms. Users notice latency above 200ms. Decorative or complex transitions
may use up to 500ms.

---

## Easing

Match easing to the nature of the motion:

| Intent | Easing | CSS value |
|--------|--------|-----------|
| Enter screen | Decelerate (fast → slow) | `cubic-bezier(0, 0, 0.2, 1)` |
| Exit screen | Accelerate (slow → fast) | `cubic-bezier(0.4, 0, 1, 1)` |
| Reposition (same level) | Standard | `cubic-bezier(0.4, 0, 0.2, 1)` |
| Bounce/spring (explicit) | Spring-like | `cubic-bezier(0.34, 1.56, 0.64, 1)` |

**Avoid bounce/spring easing as a default** — it reads as playful and can feel
inappropriate in business or utility applications. Use it with explicit design
intent.

---

## Property Constraints

Animate **only `transform` and `opacity`** for smooth, GPU-accelerated motion:

```css
/* Good: composited properties only */
.panel {
  transition: transform var(--duration-base) cubic-bezier(0.4, 0, 0.2, 1),
              opacity  var(--duration-fast)  linear;
}

/* Avoid: triggers layout or paint */
/* transition: width, height, top, left, background-color  ← expensive */
```

For appearing/disappearing elements, gate on `display:none` with a small delay
so the exit animation completes first:

```css
.popover[data-hidden] {
  pointer-events: none;
  opacity: 0;
  transform: translateY(-4px) scale(0.97);
  transition-duration: var(--duration-fast);
}
```

---

## Reduced Motion

Always respect `prefers-reduced-motion: reduce`. This is a **universal blocker**
— never omit it:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration:          0.01ms !important;
    animation-iteration-count:   1      !important;
    transition-duration:         0.01ms !important;
    scroll-behavior:             auto   !important;
  }
}
```

For users who need motion for comprehension (e.g., progress indicators), use
`prefers-reduced-motion: no-preference` as the motion branch:

```css
@media (prefers-reduced-motion: no-preference) {
  .loader { animation: spin 1s linear infinite; }
}
.loader { /* fallback: static state change indicator */ }
```

---

## Perceived Performance

Motion can make slow operations feel faster:

- **Skeleton screens** fake instant response; use `--duration-crawl` shimmer.
- **Optimistic UI**: show the result immediately, roll back on error.
- **Progress indicators**: indeterminate spinner for < 5s; progress bar with
  label for known-length operations.
- **Staggered list entry**: 30–50ms stagger per item, max 5 items staggered.

---

## Taste Heuristics (not hard rules)

- Animated gradients and pulsing backgrounds: high distraction cost, low value.
- Parallax scrolling on decorative elements: fails reduced-motion checks and
  increases scroll jank.
- Excessive microanimation on every hover: fatiguing; reserve for meaningful
  feedback.
