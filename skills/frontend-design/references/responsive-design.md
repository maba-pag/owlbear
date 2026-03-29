# Responsive Design Reference

> OwlBear adaptation — see `../NOTICE.md` for attribution.

Responsive design means the UI works across the full range of devices a user
might realistically use — not just "it doesn't break on mobile."

---

## Mobile-First

Write baseline styles for small viewports, then layer on enhancements for larger
ones:

```css
/* Baseline: mobile single column */
.card-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-4);
}

/* Medium and up: two columns */
@media (min-width: 640px) {
  .card-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* Large and up: three columns */
@media (min-width: 1024px) {
  .card-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

Mobile-first means **lower specificity baseline** — overrides only add, they do
not undo.

---

## Breakpoints

Define breakpoints as design tokens, not magic numbers:

```css
:root {
  --bp-sm:  640px;   /* Large phone landscape, small tablet */
  --bp-md:  768px;   /* Tablet portrait */
  --bp-lg:  1024px;  /* Tablet landscape, small desktop */
  --bp-xl:  1280px;  /* Standard desktop */
  --bp-2xl: 1536px;  /* Wide desktop */
}
```

**Prefer container queries over viewport breakpoints** for component-level
behavior (see [spatial-design.md](spatial-design.md)). Viewport breakpoints are
for page-level layout shifts.

---

## Pointer and Hover Queries

Not all devices with large screens have a mouse. Use interaction media features:

```css
/* Touch-primary: no reliable hover */
@media (hover: none) and (pointer: coarse) {
  .tooltip-trigger::after { display: none; }  /* no hover tooltips */
  .nav-item { min-height: 48px; }             /* larger touch targets */
}

/* Mouse: hover works reliably */
@media (hover: hover) and (pointer: fine) {
  .card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-raised);
  }
}
```

Critical actions must not rely exclusively on hover — this is a **universal blocker**.

---

## Safe Areas (Mobile Devices)

Account for device notches, home indicators, and status bars:

```css
body {
  padding-top:    env(safe-area-inset-top);
  padding-bottom: env(safe-area-inset-bottom);
  padding-left:   env(safe-area-inset-left);
  padding-right:  env(safe-area-inset-right);
}
```

Fixed-position elements (bottom sheet, sticky nav) need explicit safe-area offsets:

```css
.bottom-nav {
  padding-bottom: calc(var(--space-2) + env(safe-area-inset-bottom));
}
```

---

## Responsive Images

```html
<img
  srcset="hero-480.webp 480w, hero-960.webp 960w, hero-1440.webp 1440w"
  sizes="(max-width: 640px) 100vw, (max-width: 1024px) 75vw, 50vw"
  src="hero-960.webp"
  alt="..."
  loading="lazy"
  decoding="async"
>
```

Use `aspect-ratio` to prevent layout shift before images load:

```css
.hero-image {
  aspect-ratio: 16 / 9;
  width: 100%;
  object-fit: cover;
}
```

---

## Real-Device Testing

Emulators miss:
- Touch event coalescing and scroll behaviour
- Rubber-band scroll elasticity
- On-screen keyboard interactions (viewport resizing, input scrolling)
- Battery-saving GPU throttling
- Network speed perception under congestion

Test on real devices for launch-critical flows. BrowserStack/LambdaTest covers
the gaps for device configurations you don't own.

---

## Typography Responsiveness

Use `clamp()` for fluid headings instead of breakpoint-based overrides:

```css
h1 { font-size: clamp(1.75rem, 4vw + 1rem, 3rem); }
h2 { font-size: clamp(1.25rem, 3vw + 0.75rem, 2rem); }
```

Keep body text at a fixed size (16px minimum) — do not scale it with viewport.
