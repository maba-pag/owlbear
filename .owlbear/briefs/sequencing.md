# Brief Sequencing & Dependencies

> 10 brief inputs in `.owlbear/briefs/draft-new/input/`.
> Knowledge module activation deferred — separate planning track.

## Brief Inventory

| # | Brief | File | Scope | Effort |
|---|-------|------|-------|--------|
| 1 | AC + proof_bundle as frontmatter | `ac-as-structured-frontmatter.md` | Engine + MCP + cockpit | Medium |
| 2 | Dep-status guidance in start_work | `dep-status-guidance-in-start-work.md` | Engine only | Tiny (~15 LOC) |
| 3 | Body `\n` normalization | `body-newline-normalization.md` | MCP server boundary | Tiny (~5 LOC) |
| 4 | Ideas notebook | `cockpit-ideas-notebook.md` | Backend API + frontend page | Small |
| 5 | Decisions tab | `cockpit-decisions-tab.md` | Backend API + frontend page | Medium |
| 6 | Browser notifications | `cockpit-browser-notifications.md` | Frontend (+ SSE event) | Small |
| 7 | Board grouping & filtering | `cockpit-board-grouping.md` | Frontend only | Medium |
| 8 | Search + cross-references | `cockpit-search-and-cross-refs.md` | Engine + API + frontend | Medium |
| 9 | Memory tab | `cockpit-memory-tab.md` | Backend API + frontend page | Medium |
| 10 | Board visual design | `cockpit-board-visual-design.md` | Frontend CSS only | Medium |

## Dependency Graph

```
(1) AC frontmatter ─────┬──soft──→ (5) Decisions tab (shows AC in DR context)
                        ├──soft──→ (7) Board grouping (AC badges in cards)
                        └──soft──→ (8) Search + cross-refs (AC in results)

(5) Decisions tab ──hard──→ (6) Browser notifications (click target)

(10) Board visual design ──soft──→ (7) Board grouping (visual baseline)
                          ──soft──→ (8) Search + cross-refs (visual baseline)

(2) Dep guidance ──── standalone
(3) \n normalization ── standalone
(4) Ideas notebook ──── standalone
(9) Memory tab ──── standalone
```

**Hard dependencies** (blocked without):
- **(6)** → **(5)**: Notifications need a decisions view to navigate to.

**Soft dependencies** (better-with, not blocked-by):
- **(5), (7), (8)** benefit from **(1)** AC data being in frontmatter.
- **(7), (8)** benefit from **(10)** visual baseline being established first.

## Impact × Risk

| # | Impact | Risk | Notes |
|---|--------|------|-------|
| 1 | **High** | Low | Foundational schema change — enables richer display + dispatch queries |
| 2 | **Medium** | Very low | Pure value, zero risk, independent |
| 3 | **Low** | Very low | Cosmetic fix for archived tasks |
| 4 | **Medium** | Very low | Small scope, independent feel-good feature |
| 5 | **High** | Low | Key workflow visibility — decisions are currently invisible in cockpit |
| 6 | **High** | Low | Blocked by (5) — high value once decisions tab exists |
| 7 | **Medium** | Low | Board usability at scale |
| 8 | **Medium** | Low | Cross-refs are the valuable part |
| 9 | **Medium** | Low | Makes memory visible to user |
| 10 | **High** | Very low | Primary view, first impression — CSS only |

## Execution Waves

### Wave 1 — Foundation + Quick Wins

All parallel, no conflicts.

| # | Brief | Rationale |
|---|-------|-----------|
| 1 | AC + proof_bundle frontmatter | Foundational schema — unblocks richer cockpit display |
| 2 | Dep guidance in start_work | Tiny, independent, immediate value |
| 3 | Body `\n` normalization | Tiny, independent, closes a known defect |

### Wave 2 — Cockpit Expansion

All parallel — different pages/components, no conflicts.

| # | Brief | Rationale |
|---|-------|-----------|
| 10 | Board visual design | Establishes visual baseline before board features |
| 5 | Decisions tab | High-impact new tab, unblocks (6) |
| 4 | Ideas notebook | Small independent tab |
| 9 | Memory tab | Independent tab, mirrors decisions pattern |

### Wave 3 — Board Intelligence

Parallel with each other. Starts after Wave 1 (AC data) and Wave 2 (visual baseline).

| # | Brief | Rationale |
|---|-------|-----------|
| 7 | Board grouping & filtering | Benefits from (1) AC + (10) visual design |
| 8 | Search + cross-references | Benefits from (1) AC data in frontmatter |

### Wave 4 — Polish

Starts after Wave 2 (decisions tab).

| # | Brief | Rationale |
|---|-------|-----------|
| 6 | Browser notifications | Hard dependency on (5) decisions tab |

## Parallelization Rules

- Within each wave, all briefs can be built simultaneously by different agents.
- **Do not** build (7) and (10) simultaneously — both modify board CSS/components.
- Wave boundaries are soft for briefs without dependencies: (4) and (9) could start during Wave 1 if capacity allows.
- Wave 3 should not start until (1) and (10) are at least in review.

## Notes

- Knowledge module activation is a separate planning track — not included in this sequence.
- No ideation needs to wait for implementation — all 10 briefs are concrete enough for task decomposition.
- (7) Board grouping UX ideation benefits from seeing (1) AC badges in the real board first.
