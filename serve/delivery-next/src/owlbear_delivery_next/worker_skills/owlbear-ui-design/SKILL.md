---
name: owlbear-ui-design
description: "Design rules for building or judging a user interface: the brief first, the visitor's mode, the craft floor, typography, colour, layout and states"
user-invocable: false
---

# UI Design

Use when a task changes what a user sees. Adapted from Impeccable (see `NOTICE.md` beside this folder) and OwlBear's
frontend design handbook.

## Context first

- Establish from the repository: product and audience, the visitor's job on this surface, the established
  design system, component library, tokens and supported widths. Never infer a stack or brand without evidence.
- An established design system and the project's conventions outrank everything below.
- **The brief wins.** Honour the aesthetics, fonts, palettes and states it names, even against a rule here.
  Steering a clear brief towards your own taste is a failure.
- **Refinement preserves; redesign replaces.** A refinement keeps the identity, behaviour, copy and everything
  outside its scope. A redesign keeps product truth, content and function and replaces the look. Never split
  the difference into polish on a look the brief discards.

## The visitor's mode

Choose it from the surface, not the product:

| Mode | The visitor | First priority |
| --- | --- | --- |
| Operate | completes a task: app UI, dashboards, settings, tools | scanability, consistency, standard controls, clear state |
| Read | understands something: docs, articles, changelogs | comprehension, wayfinding, a calm reading column |
| Persuade | decides and acts: landing pages, pricing | attention and the action, real evidence |
| Experience | is inside the work: portfolios, galleries | the artifact leads, the interface recedes |

On Operate and Read surfaces the visual world lends only type, palette, density and one signature detail. It
never supplies the layout, the navigation model or the controls; controls are the platform's standard ones.

## Craft floor: verify on the rendered result

- **Contrast:** body and placeholder text at least 4.5:1, large text 3:1, controls, icons and focus indicators
  3:1. On coloured surfaces, tint secondary text from that hue, never plain gray.
- **Spacing:** tight inside a group, generous between groups, more space above a heading than below it.
- **Type:** body measure 45 to 75 characters, a 16px body floor on the web unless a dense role justifies less,
  obvious steps in size and weight between roles, no overflowing text at any supported width.
- **Depth:** shadows have an offset and a soft blur; a zero-offset coloured halo is decoration.
- **Motion:** one purposeful moment rather than effects everywhere; ease out from a visible default; respect
  reduced motion.
- **States:** hover, focus, active, disabled, loading, empty, error and success, with real content and working
  controls. Visible keyboard focus and logical tab order.
- **Browser surfaces:** selection, caret, scrollbars, focus rings, link underlines and tabular numerals are themed,
  not left at browser defaults.
- **Copy:** the product's own words. Controls name their action; errors name the problem and the way out.
- **Coverage:** every brief requirement is present and found within seconds.

## Refuse unless the brief asks for it

- Same-size cards of icon, heading and text as the page structure; nested cards are always wrong.
- The hero-metric template (big number, small label, supporting stats).
- An eyebrow or kicker label above a heading; tiny section numbers that carry no information.
- Gradient text; glass and blur as decoration; a coloured side stripe on cards or alerts; hard offset shadows.
- Purple-to-blue or cyan-on-dark palettes by habit; glowing accents on dark mode.
- Overused default faces (Inter, Roboto, Geist and the like) chosen by habit; a system display face as the voice
  of an own-world page.
- Emoji or glyphs standing in for icons; icons are one library, one stroke, one weight.
- A modal for a task that needs neither interruption nor protected focus.
- Light or dark chosen by category rather than by where and how the product is used.

## Typography

- Use the fewest families and roles that make the hierarchy unmistakable; combine size, weight, space and tone.
- Keep repeated roles identical across screens and states. Name tokens by purpose, not value.
- Tune line height to the face and the measure: wider lines need more leading. Light text on dark needs a little
  more line height, tracking and weight. Tracking never below -0.04em.
- Load only used fonts and weights, with metric-compatible fallbacks; never invisible text while loading.
- Preserve browser zoom and the user's text settings.

## Colour

- Build roles, not swatches: canvas and elevated surfaces, primary and secondary text, action, focus and
  selection, borders, success, warning, error and information, data categories.
- The primary action stays easy to find; never spend its colour on decoration.
- Semantic colours stay consistent; information carried by colour also has text, shape or position.
- Dark mode is designed, not inverted. Prefer explicit colours over chains of translucent layers.

## Layout

- Align to the project's grid and spacing scale, optically as well as mathematically.
- One primary element, two or three secondary ones, everything else quiet.
- No content flush against the viewport edge; nothing clipped, overlapping or unreachable at a supported width.

## Order of fixes

1. Broken or blocked tasks, data loss, misleading state, inaccessible paths.
2. Missing loading, empty, error, success, disabled and permission states.
3. Flow, hierarchy, responsive behaviour and drift from the design system.
4. Visual and motion inconsistencies.
5. Code and asset cleanup.

## Evidence

- Objective blockers (missing focus, placeholder as label, hover-only critical actions, vague errors, overlap or
  clipping, missing states that stop the main task) outrank contextual heuristics (palette, density,
  decoration), which count only where they weaken the intended hierarchy, brand or workflow.
- Match each claim to its evidence: source shows tokens and declared states; rendered pages and screenshots
  show geometry, overlap, hierarchy and contrast. Say which you have.
- The design detector's findings name a rule and a place. They are evidence, not proof: a clean scan is a
  floor, and a finding can be a deliberate choice the brief names.
