# Synthesis — Board Visual Design

## Summary

Four domain stances evaluated the board visual design brief against decisions D1–D9. The CSS architecture (agnostic token layer, per-component CSS, data-attribute state model, theme bootstrap) is broadly endorsed. The stances converge on most structural questions and diverge primarily on card content richness, empty-state treatment, and priority visual discrimination — areas where the brief underspecified the mapping from data to visuals.

---

## Convergences

These positions are shared across all active stances with no material disagreement.

### Token Architecture

- **Agnostic rename** (`--pds-theme-light-*` → `--pds-*`) is justified and necessary. (architect §1, data §2)
- **Token coverage must expand** beyond colors to include shadow, border-radius, and spacing tokens. Non-color tokens are theme-independent — single `:root` definition, no dark overrides. (architect §1)
- **Migration must be mechanically verified.** Orphaned old-name references, `:root` tokens missing dark counterparts, and dark tokens missing `:root` counterparts all produce silent visual bugs. A grep gate or test assertion catches all three. (data §2, architect W1–W2)
- **Shell.css references old token names** and must be updated as part of the rename scope. (architect W5)
- **Test files reference old token names** — the rename surface extends beyond source CSS. (architect W2, data §2)

### Per-Component CSS + Inline Migration

- **6 component CSS files** (Card, Column, KanbanBoard, FilterPanel, DetailTab, ActivityTab) alongside existing Shell.css and tokens.css. (architect §2)
- **`utils/styles.ts` must be absorbed.** The `rowStyleForState()` helper becomes CSS selectors on `[data-state]` attributes; the file is deleted. (architect §2)
- **Inline-to-CSS migration must be complete.** Partial migration where some card states are CSS-themed and others remain hardcoded inline creates an inconsistent theming surface. (data §4, architect §2)

### Theme Infrastructure

- **Synchronous bootstrap script in `index.html`** prevents flash-of-wrong-theme. Runs before React mount. (architect §4, security §theme-flash, data §3)
- **localStorage allowlist validation** — read value checked against `["dark", "light"]` before DOM application. Defense-in-depth. (security R1, architect §4)
- **No React Context for theme.** Theme is a DOM attribute; CSS custom properties propagate through the cascade. Zero re-renders on theme change. (architect §4)
- **`useTheme` hook** provides React API for toggle + OS preference listener. (architect §4)
- **Theme plumbing is a prerequisite, not afterthought.** The agnostic token layer and dark override block are inert without the switching mechanism. (data §3)

### Layout and Scroll

- **Fixed column header + scrolling card body** via flexbox. Column identity always visible. (architect §6, enduser §6)
- **Card height released** (D7) — accepted as safe. Content is inherently bounded by human-written titles. (architect §5, data trades, enduser §1)
- **`overflow-wrap: break-word`** on card titles as single CSS guard against horizontal overflow. (architect §5)

### State Model

- **Data attributes for dynamic state** (`data-priority`, `data-selected`, `data-drag-over`, `data-state`). BEM classes for structural identity. (architect §3)
- **ARIA attributes double as selectors** where applicable — no redundant data attributes. (architect §3)
- **Context menu position remains inline style** (runtime-computed from click coordinates). All visual treatment (shadow, radius, background) moves to CSS. (architect §3, enduser W4)

### Security

- **Brief's security delta is low.** No new API endpoints, data flows, or auth surfaces. (security assessment)
- **No new CSP relaxation.** Moving inline styles to CSS is directionally positive for CSP but won't enable dropping `unsafe-inline` alone. (security R3)
- **PDS CSP boundary preserved.** Existing `pds-runtime-csp.spec.ts` must continue passing. (security R2)
- **Context menu styling is net-positive** for intent safety — making the primary action surface visible improves intentional state transitions. (security §context-menu)

---

## Disagreements

### 1. Empty State Design — enduser vs. D9

**D9 decided:** PDS illustrated placeholder (icon + message).

**enduser (§2, W1):** Pushes back. Kanban columns empty as part of normal operations — "Done" empties after every archive cycle, "Review" clears when the pipeline is healthy. Illustrated placeholders signal "you haven't started yet," not "the pipeline is flowing." Recommends subdued text with PDS typography tokens; the clean column surface IS the design. Warns the user will want illustrations removed within weeks.

**data (W3):** Empty columns convey meaningful pipeline information. The placeholder should reinforce which pipeline stage is empty, not obscure it.

**architect, security:** No specific position.

**Tension level:** Medium. The user explicitly chose illustrations, but enduser's recurring-state argument is well-grounded. This needs a re-confirmation or revision.

### 2. Priority Visual Discrimination

**data (§1):** `important` and `nice-to-have` both map to the same PDS `notification-info` blue. The visual encoding is non-injective — a human scanning the board cannot distinguish these two priority levels by color alone. Recommends a secondary visual channel (border weight, opacity, shade variant). Also warns priority border may be occluded when stacked with selection/hover/focus states.

**enduser (§5):** Wants 4px left-border color + accessible text label ("P1" / "crit" / "need" / "nice"). Text label addresses color-blind access. Against background tint.

**architect:** Does not address priority mapping.

**Tension level:** Low-medium. The stances are complementary (data wants color differentiation, enduser wants text labels for accessibility), but together they expand the priority indicator scope beyond what the brief planned.

### 3. Card Content Model Scope

**enduser (§7):** Cards should display title + priority border + text label + blocked indicator + first 3 tags as chips (+N overflow) + claimed indicator.

**data (§5):** `data-blocked` and `data-claimed` attributes must be added to card root for CSS hooks. Currently only emoji child content exists.

**architect (§5):** Card DOM currently renders only title + conditional emoji indicators. Does not propose expanding card content.

**Tension level:** Low. All stances agree the card needs more structure. The question is how much card content is in scope for a "CSS architecture" brief vs. deferred to a card-content brief.

---

## Actionable Additions

Items no stance disputes and the brief currently lacks.

| Addition | Source | Why |
|----------|--------|-----|
| `data-blocked` and `data-claimed` attributes on card root element | data §5, enduser §7 | CSS cannot style card differently based on these states without child text inspection |
| `styles.ts` deletion after CSS absorption | architect §2 | Helper becomes dead code once state selectors move to CSS |
| Mechanical token migration verification (grep gate or test) | data §2, architect W1–W2 | Silent failures dominate — no runtime errors for missed renames or missing dark tokens |
| `overflow-wrap: break-word` on `.card__title` | architect §5 | Prevents horizontal overflow from unbroken strings |
| Column minimum width increase from 80px floor | architect §6 | Current `minmax(80px, 1fr)` produces unreadable columns below ~180px |
| PDS web component theme compatibility verification | architect W3 | Verify PDS components respect `data-theme` attribute changes; PDS provider may need explicit theme prop updates |
| Token generation script update and documentation | architect W1 | Script must extract light-suffixed, dark-suffixed, AND non-color tokens from PDS v4.1.0 exports |
| Shell.css included in token rename scope | architect W5 | References `--pds-theme-light-*` directly |
| Accessible priority text label | enduser §5, W3 | Color-only encoding fails WCAG; text label ("P1"/"crit"/"need"/"nice") needed |

---

## Open Questions

These require user decision before the brief can be finalized.

### Q1. Empty state: re-confirm illustrations or switch to quiet text?

D9 chose illustrated placeholders. Enduser pushes back with a strong argument: kanban columns empty frequently as normal operations, illustrations signal first-run not pipeline-health, and they'll create visual noise that draws the eye to the least important column. Data agrees empty state should reinforce which stage is empty, not obscure it. **Does D9 stand, or should the brief adopt subdued text with optional muted icon?**

### Q2. Card content scope — how much metadata on cards?

The brief describes CSS architecture for existing card structure. Enduser proposes tags (first 3 as chips), claimed indicator, blocked indicator, and accessible priority text labels. Data wants `data-blocked`/`data-claimed` attributes. This expands the JSX surface. **Is card content enrichment in scope for this brief, or should it be a separate card-content task?**

### Q3. Priority color deduplication

Data flags `important` and `nice-to-have` share the same blue. Enduser wants text labels. **Should the brief address priority visual differentiation (second color channel or text labels), or accept the current 4-of-5 discrimination?**

### Q4. Theme toggle UI placement

Enduser recommends status bar right side. Architect defers this as a separate decision. **Should the brief include toggle placement, or scope it as a follow-up?**

### Q5. Column minimum width floor

Architect flags 80px is unreadable. **What minimum column width? 180px? 200px? Or leave for responsive-layout work?**

---

## Recommendation

Ship the brief with the convergent architecture (agnostic tokens, per-component CSS, theme bootstrap, data-attribute state model) and the actionable additions table above. Resolve Q1 (empty state) and Q2 (card content scope) before task decomposition — they materially affect the number and shape of implementation tasks. Q3–Q5 can be noted as brief guidance without blocking decomposition.

**Confidence: 0.80** — High structural convergence, manageable disagreements, and the open questions are scoping decisions rather than architectural conflicts.
