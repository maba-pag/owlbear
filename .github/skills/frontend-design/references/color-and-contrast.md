# Color and Contrast Reference

> OwlBear adaptation — see `../NOTICE.md` for attribution.

Color communicates meaning, hierarchy, and brand. Done poorly, it creates
accessibility failures and cognitive overload. Done well, it is nearly invisible.

---

## Modern Color: OKLCH

OKLCH is the recommended color space for design tokens. Unlike HSL, it produces
perceptually uniform steps — equal lightness/chroma changes look equally
different to the human eye.

```css
:root {
  --color-brand:    oklch(55% 0.18 260);   /* L% C H */
  --color-success:  oklch(60% 0.15 145);
  --color-warning:  oklch(75% 0.18 70);
  --color-danger:   oklch(55% 0.20 25);
}
```

Use OKLCH for:
- Generating accessible tint/shade scales without unexpected hue shifts
- Dark-mode variants (lower L, same C and H)
- Palette interpolation (color mixes stay vivid, avoid muddy gray mid-points)

---

## Palette Roles

Define **semantic color tokens**, not raw hex values, in components:

| Role | Token | Use |
|------|-------|-----|
| Brand | `--color-brand` | Primary CTA, active states, accents |
| Surface | `--color-surface-*` | Page, card, overlay backgrounds |
| Content | `--color-content-*` | Body text, headings, icons |
| Feedback | `--color-success/warning/danger` | Status messages, alerts |
| Border | `--color-border-*` | Dividers, input outlines |

This allows systematic dark-mode support by rebinding tokens, not rewriting components.

---

## Contrast

WCAG AA minimums (2.1):

| Scenario | Minimum ratio |
|----------|---------------|
| Body text (< 18pt / < 14pt bold) | 4.5:1 |
| Large text (≥ 18pt / ≥ 14pt bold) | 3:1 |
| UI components and graphics | 3:1 |
| Placeholder text | 4.5:1 |

WCAG AAA (text): 7:1. Target this for long-form reading interfaces.

**Common traps:**
- Gray text on white: `#767676` is the lightest gray that satisfies 4.5:1.
- Colored text on colored background: run every color combination through a
  contrast checker — do not estimate visually.
- Focus indicators: must have at least 3:1 against adjacent colors AND 3:1
  against the non-focused state.

---

## Tinted Neutrals

Pure gray (`hsl(0 0% X%)`) looks cold and clinical. Tint with a small amount
of brand hue to unify the palette:

```css
/* Brand hue 260° (blue-violet), low chroma tint */
--color-surface:      oklch(97% 0.01 260);
--color-surface-alt:  oklch(93% 0.02 260);
--color-border:       oklch(80% 0.03 260);
--color-content-muted: oklch(55% 0.03 260);
```

---

## Dark Mode

Prefer `prefers-color-scheme` media query + CSS custom property rebinding over
class toggles. Keep the same semantic token names:

```css
@media (prefers-color-scheme: dark) {
  :root {
    --color-surface:      oklch(18% 0.02 260);
    --color-content:      oklch(92% 0.02 260);
    --color-border:       oklch(30% 0.03 260);
  }
}
```

Dark mode semantics:
- **Elevation through lightness:** lighter surfaces appear higher (not darker as
  in light mode). Use small lightness steps (3–5%) for layering.
- **Reduce saturation:** vivid brand colors often need their chroma reduced
  (0.15 → 0.12) on dark backgrounds to avoid eye strain.
- **Do not invert blindly:** photos and data visualizations need explicit dark
  variants if inversion would destroy meaning.

---

## Taste Heuristics (not hard rules)

- Default purple/cyan "AI palette": overused, signals no design intent.
- Pure black (`#000000`) text: can feel harsh; `oklch(10% 0.01 260)` is softer.
- Pure white background: `oklch(99% 0.005 260)` adds warmth.

These are suggestions to consider, not policies to enforce.
