# Typography Reference

> OwlBear adaptation — see `../NOTICE.md` for attribution.

Good typography creates hierarchy, improves readability, and communicates brand
personality before the user reads a single word.

---

## Type Scale

Use a **modular scale** (ratio 1.25 or 1.333) rather than arbitrary sizes. Define
tokens in CSS custom properties and apply them consistently:

```css
--text-xs:   0.75rem;   /* 12px — captions, labels */
--text-sm:   0.875rem;  /* 14px — secondary body */
--text-base: 1rem;      /* 16px — primary body */
--text-lg:   1.125rem;  /* 18px — large body, card leads */
--text-xl:   1.25rem;   /* 20px — section sub-heads */
--text-2xl:  1.5rem;    /* 24px — section heads */
--text-3xl:  1.875rem;  /* 30px — page titles */
--text-4xl:  2.25rem;   /* 36px — hero headings */
```

Fluid type (`clamp()`) between two scale stops smooths the transition across
viewport widths:

```css
--text-display: clamp(2rem, 5vw, 3.5rem);
```

---

## Vertical Rhythm

Line height should be 1.4–1.6 for body copy, 1.1–1.3 for headings. Paragraph
spacing of `1em` creates comfortable breathing room without double spacing.

```css
body {
  line-height: 1.5;
}

h1, h2, h3 {
  line-height: 1.2;
  letter-spacing: -0.01em;  /* tighten large headings slightly */
}
```

---

## Font Pairing

Choose fonts with intention:

- **One type family is enough** for most UIs — use weight and size variation to
  create hierarchy, not different typefaces.
- For a pairing (serif + sans, or display + body), ensure the x-heights are
  compatible.
- Pick a **variable font** where possible: one file, full weight/width range, no
  FOUT on weight transitions.

**Avoid:** Defaulting to Inter, Roboto, or system-ui as a stylistic choice just
because they are "safe." They signal no design intent. When that neutrality is
intentional, document it.

---

## Font Loading

Prevent flash of unstyled text (FOUT) and layout shift (CLS):

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preload" as="font" type="font/woff2" crossorigin href="/fonts/my-font.woff2">
```

```css
@font-face {
  font-family: 'MyFont';
  font-display: swap;  /* show fallback immediately, swap when loaded */
  src: url('/fonts/my-font.woff2') format('woff2');
}
```

Define a **metric-compatible fallback** to minimize CLS:

```css
@font-face {
  font-family: 'MyFont-fallback';
  src: local('Arial');
  size-adjust: 98%;
  ascent-override: 95%;
}
```

---

## Accessibility

- Minimum **16px** for body copy; 14px only for non-critical secondary text.
- Avoid using font weight below 300 for small text — thin text fails contrast.
- Do not rely on italics alone to distinguish meaning; add an additional visual cue.
- Respect `prefers-reduced-data` by loading lighter font variants when possible.

---

## OpenType Features

Enable contextual features for polished editorial text (not required for UI):

```css
font-feature-settings: 'kern' 1, 'liga' 1, 'calt' 1, 'zero' 1;
```

Numerals in tables always use tabular and lining numerals:

```css
font-variant-numeric: tabular-nums lining-nums;
```
