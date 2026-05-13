# Data Quality Stance — Board Visual Design

## Data Quality Stance

The board visual design is primarily a CSS task, but it creates several data-to-visual contracts that must be explicit. The risks are not in the data model (which is well-typed) but in the **mapping layer** — where typed task fields become visual treatments, and where token architecture must survive a theme migration without silent rendering bugs.

## Schema and Validation Reasoning

### 1. Priority visual discrimination (confidence 0.78)

`important` and `nice-to-have` both map to `notification-info` (blue). The underlying data is not lost — priority is a typed field, exposed as a DOM attribute, and used for in-column sorting. But the visual mapping is **non-injective**: a human scanning the board cannot distinguish these two levels by color alone.

This matters because the board is a scanning tool. If priority is worth encoding visually at all (and the existing `PRIORITY_COLORS` map says it is), the encoding should discriminate all values it covers. A secondary visual channel (border weight, opacity, or a subtle shade variant) would restore discriminability without requiring a new PDS notification tier.

Additional concern: priority is currently a left-border color. When stacked with selection (full-card border + background) or hover/focus states, the priority signal may be occluded. The implementation should verify priority remains visible across all state combinations.

### 2. Token migration completeness (confidence 0.80)

The scope includes renaming `--pds-theme-light-*` vars to theme-agnostic names and adding a `[data-theme="dark"]` override block. This is a three-part migration with distinct failure modes:

- **Rename:** Every consumer of `--pds-theme-light-*` (Shell.css, Card.tsx inline styles, any future CSS) must update to the new names. A missed reference silently resolves to `initial` (transparent/black) — a rendering bug with no error.
- **Dark block parity:** Every token defined in `:root` must also be defined in `[data-theme="dark"]`. A missing dark token silently falls back to the light value — wrong colors, no error.
- **Consumer reference audit:** After migration, no file should reference the old `--pds-theme-light-*` names. A simple `grep` gate in CI or a pre-commit check catches this.

All three are **mechanically verifiable**. The implementation should include a validation step (build script, grep assertion, or test) that catches any of: (a) orphaned old-name references, (b) root tokens without dark counterparts, (c) dark tokens without root counterparts.

### 3. Theme infrastructure gap (confidence 0.82)

D6 decided: auto default (`prefers-color-scheme`) + manual override (`data-theme` attribute + localStorage). Currently **zero** theme-switching infrastructure exists in the frontend. No `data-theme` attribute is set on any element. No `prefers-color-scheme` media query appears in the CSS. No toggle component exists.

This is not a data integrity issue per se, but it's a **delivery risk** for the token architecture. The agnostic token layer and dark override block are inert without the switching mechanism. The brief should treat theme plumbing (attribute setter, media query listener, localStorage persistence) as a prerequisite for dark theme validation, not an afterthought.

### 4. Inline-to-CSS migration (confidence 0.75)

Card.tsx has conditional inline styles (priority border, selection background, height constraints). The brief's CSS-focused approach requires extracting these to CSS rules. The good news: most state hooks already exist — `data-selected`, drag-target attributes, and native `:hover`/`:focus` pseudo-classes are in place. The gap is **completeness of migration**: every inline `style={{}}` that references a PDS token or conditional state must move to CSS to participate in theming.

The risk: partial migration where some states are CSS-themed and others remain inline with hardcoded token references. This creates an inconsistent theming surface — some card states respond to theme changes, others don't.

### 5. Blocked/Claimed styling hooks (confidence 0.73)

`blocked` and `claimed` are typed boolean fields in the task model. The Card renders emoji indicators (`⛔`, `▶`) as child content, but the card root element carries no `data-blocked` or `data-claimed` attributes. CSS cannot style the card differently based on these states without inspecting child text content.

Adding `data-blocked` and `data-claimed` attributes to the card root element gives CSS a proper selector hook. This enables: dimming blocked cards, highlighting claimed cards, or any future state-based visual treatment — all via CSS, all theme-responsive.

## Key Trade-offs

| Decision | Trade-off | Data concern |
|----------|-----------|-------------|
| D7: Release card height | Full content vs. scan density | Correct for data completeness; accept variable heights |
| D4: Ship both themes | Broader QA surface | Token migration must be mechanically verified |
| D6: Auto + manual toggle | More plumbing needed | Theme infrastructure is a prerequisite, not a nice-to-have |
| D5: JSX changes OK | Broader diff surface | Required for inline-to-CSS migration |

## Warnings

1. **Silent failures dominate.** Token rename misses, dark-block omissions, and partial inline migration all produce visual bugs with zero runtime errors. Every validation in this domain must be **proactive** (build-time, grep-based, or test-based), not reactive.

2. **Priority color stacking.** The left-border priority indicator is the narrowest visual channel on the card. Verify it remains visible when selection, hover, focus, and drag states are applied simultaneously.

3. **Empty state is a data signal.** D9 chose PDS illustrated placeholder for empty columns. An empty column conveys meaningful pipeline information ("nothing in review" is actionable). The placeholder design should reinforce, not obscure, which pipeline stage is empty.

## Confidence

**0.78** — Position is grounded in the actual codebase state and brief decisions. The concerns are narrow and mechanically addressable. No fundamental data model issues; the risks are in the mapping and migration layers.
