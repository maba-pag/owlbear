# Card Visual Treatment — PDS v4 PTag Migration

> **Owning task:** #1615 — P2-05: Card visual treatment
> **Date:** 2026-05-16 **Status:** Complete

## 1. Context and Question

Task #1615 requires migrating card visual elements to PDS v4 components: status chip (PTag with color variant), priority indicator, signal icon (PIcon), tag pills (PTag), and relative timestamp. AC-3 mandates PDS color tokens, not hardcoded hex. Current card uses custom CSS `.card-chip` spans with `--pds-*` tokens (pre-migration).

**Key questions:** (a) How to map status/priority/signal to PTag variants and PIcon names; (b) whether PTag-per-element is feasible at 700-card scale (DOM budget = 6400); (c) how to handle claimed state (no PDS variant equivalent).

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | PDS v4 PTag source (`tag-utils.ts`, `tag.tsx`) | GitHub | 1.0 — variants: primary, secondary, info, info-frosted, warning, warning-frosted, success, success-frosted, error, error-frosted; props: variant, icon, iconSource, compact |
| S2 | PDS v4 PTag examples page | Web (designsystem.porsche.com/v4) | 0.9 — confirmed v4.1.0 API, icon integration pattern |
| S3 | PDS v4 PIcon source (`icon.tsx`, `icon-utils.ts`) | GitHub | 0.9 — colors: primary, contrast-*, success, warning, error, info, inherit; names include information-filled, warning-filled, success-filled, error-filled, disable, user, lock |
| S4 | PDS v4 tag-styles.ts (color maps) | GitHub | 1.0 — colorTextMap, colorBackgroundMap, colorBackgroundHoverMap per variant |
| S5 | `Card.tsx`, `Card.css` | Codebase | 1.0 — current structure: custom .card-chip spans, data-signal border, state cue text |
| S6 | `computeSignal.ts` | Codebase | 1.0 — 6-value signal union: dr-pending, blocked, claimed, deps-unmet, ready, unknown |
| S7 | `KanbanBoard.performance-700.test.tsx` | Codebase | 1.0 — DOM_NODE_BUDGET=6400 for 700 cards; light-DOM querySelectorAll('*') |
| S8 | `TaskFieldsEditor.tsx` | Codebase | 0.8 — existing PTag usage for tag pills (proven import pattern) |
| S9 | `useBoard.ts` | Codebase | 1.0 — Task type: status, priority are strings from API; Board.priorities is dynamic |
| S10 | Prior research: card-css-impl-1546.md | Codebase | 0.7 — established signal-to-border mapping, claimed purple as custom-keep |

## 3. Analysis

### 3.1 Status → PTag Variant Mapping

AC-1 says "status chip (PTag with color variant)." Status = workflow state (research, backlog, todo, etc.), distinct from signal (blocked, claimed). Cards live inside status columns, so status chip is partially redundant — but AC explicitly requires it and it aids scannability during drag/search.

| Status | PTag variant | Rationale |
|--------|-------------|-----------|
| research | info | Informational phase |
| backlog | secondary | Neutral/pending |
| todo | primary | Active, brand-color prominence |
| in-progress | warning | In-flight, attention-drawing |
| review | info | Assessment phase |
| docs | secondary | Low-key |
| done | success | Complete |
| archived | secondary | Muted |
| (unknown) | secondary | Fallback for dynamic values |

Statuses come from Board API (`board.statuses`), not hardcoded (constraint C7). The mapping utility must accept arbitrary strings with a fallback.

### 3.2 Priority → PTag Variant Mapping

| Priority | PTag variant | Rationale |
|----------|-------------|-----------|
| critical | error | Highest urgency |
| important | warning | Elevated attention |
| normal | secondary | Default |
| low | secondary | Muted (compact) |
| (unknown) | secondary | Fallback |

Same dynamic-value concern applies — `board.priorities` is API-provided.

### 3.3 Signal → PIcon Mapping

Current: signal drives left-border color via `data-signal`. AC-1 adds "signal icon."

| Signal | PIcon name | PIcon color | Show? |
|--------|-----------|-------------|-------|
| dr-pending | information-filled | warning | Yes |
| blocked | disable | error | Yes |
| claimed | user | inherit | Yes |
| deps-unmet | lock | contrast-medium | Yes |
| ready | — | — | No (default) |
| unknown | — | — | No |

Keep existing left-border color (visual redundancy is intentional for scannability per AC-2). Signal icon adds a scannable glyph alongside the border color.

### 3.4 Tag Pills

Current: comma-separated text in one `span`, max 3 shown (`TAG_PREVIEW_LIMIT`). AC-1 says "tag pills." Replace with individual `PTag compact variant="secondary"` per tag, preserve the 3-tag limit + overflow indicator.

### 3.5 Performance: DOM Node Budget (CRITICAL)

**Current card DOM nodes (typical, with 3 tags, no cues):** ~8 elements.
**Projected with PTag migration (status + priority + 3 tag pills + signal icon):** ~14 elements.

At 700 cards: ~9,800 nodes vs budget of 6,400. **Exceeds budget by ~53%.**

| Mitigation | DOM impact | Trade-off |
|------------|-----------|-----------|
| A: Increase DOM_NODE_BUDGET to ~10,000 | None — accept higher count | Weakens perf guardrail |
| B: Keep tag pills as text, only PTag status+priority | ~10 nodes/card → 7,000 total | Partial AC compliance for tags |
| C: Use PTag for status only, CSS chips for rest | ~9 nodes/card → 6,300 total | Minimal PDS migration |
| D: Virtualize columns (only render visible cards) | Decouples from budget | Significant arch change (out of scope) |

**Recommendation: A + validate.** Increase budget. The 6,400 budget was set before PDS migration was planned. PDS web components in jsdom render as light-DOM elements (Shadow DOM doesn't inflate querySelectorAll). The real bottleneck is rendering time, not node count — and that should be validated by the builder's test run. If 700-card render time stays acceptable, the higher node count is fine.

### 3.6 Claimed Color Exception

Claimed signal uses custom purple (`--pds-signal-claimed` / `hsl(270 58% 46%)`), documented as a "custom-keep" token with no PDS variant equivalent. PTag has no purple variant.

| Option | Approach | PDS compliance |
|--------|---------|----------------|
| A: CSS variable override on PTag | `style={{ '--p-tag-color': 'var(--signal-claimed)' }}` | Fragile — depends on internal CSS var |
| B: Keep claimed cue as custom chip | Only claimed stays as raw span | Mixed — 1 custom element |
| C: Map claimed to `primary` variant | Dark brand color, loses purple meaning | Full PDS but semantic loss |

**Recommendation: B** — keep claimed as a styled span. It's one edge case, and forcing it into PTag would either require fragile CSS overrides or lose the established purple semantics.

### 3.7 State Cue Text vs Icons

Challenger correctly noted: current card renders explicit text cues ("Blocked", "Claimed", etc.) alongside signal border. The signal icon (§3.3) communicates the dominant signal; the text cues provide detail. **Keep both** — the signal icon is new (compact, at-a-glance), while existing text cues provide explicit labels for accessibility.

## 4. Recommendation

**Approach: PTag for status + priority, PIcon for signal, PTag pills for tags** (confidence: .65)

Challenge: reconsider — original confidence .82 dropped to .65 after challenger identified DOM budget risk (6,400 cap vs ~9,800 projected), claimed-color exception, and API-dynamic mapping contract. Recommendation revised from full PTag-heavy to proceed-with-caveats.

**Implementation guidance for builder:**

1. Create `utils/cardVariants.ts`: status→variant and priority→variant mapping functions with `'secondary'` fallback for unknown values. Accept `board.statuses` / `board.priorities` as input for validation but don't hardcode enums.
2. Status chip: `<PTag variant={statusVariant} compact>{task.status}</PTag>`
3. Priority chip: `<PTag variant={priorityVariant} compact>{task.priority}</PTag>`
4. Signal icon: `{signal !== 'ready' && signal !== 'unknown' && <PIcon name={signalIcon} color={signalColor} size="xs" aria-label={signalLabel} />}`
5. Tag pills: `<PTag variant="secondary" compact>{tag}</PTag>` per tag (preserve TAG_PREVIEW_LIMIT=3).
6. Keep existing state cue text (blocked/claimed/deps/DR spans) — don't replace with icons.
7. Claimed cue: keep as styled custom span (no PTag variant for purple).
8. Update DOM_NODE_BUDGET in performance-700 test — validate actual render time.
9. All colors via PDS component props (PTag variant, PIcon color) — AC-3 satisfied by PDS component internals using `--p-color-*` tokens.
10. Remove `Card.css` custom chip styles that PTag replaces; keep signal-border and cue styles.

## 5. Follow-up Tasks

Task already exists as #1615 (this is its research). No additional follow-up tasks needed — the builder has sufficient guidance above.
