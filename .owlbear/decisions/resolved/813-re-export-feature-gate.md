---
# >> Your action: set response to approved, needs-info, or rejected
response: approved
decision: "A: Do not add re-exports — close #813 and #815 as won't-do"
notes: ""
# >> Agent metadata (do not edit)
task_id: 813
agent: researcher
created: 2026-03-15
urgency: blocking
decision_type: feature-gate
---

# Decision: Should OwlBear add `__init__.py` re-exports to non-library packages?

## Context

Two research docs for parent #549 reached opposite conclusions on adding re-exports:

- `init-reexports.md` (.85): DO NOT add — 0/66 consumers use them, YAGNI
- `init-re-exports.md` (.90): ADD — matches library patterns like PydanticAI

Three subsequent research rounds resolved the contradiction. All empirical evidence
confirms zero demand: 0/26+ consumers in `src/`, 0/167 browser-specific imports use
package-level paths. OwlBear is a standalone daemon, not a library.

Blocked tasks: #813 (5 packages), #815 (browser), #812 (remove existing from core).
See `docs/research/re-export-contradiction.md` and `docs/research/browser-re-exports.md`.

## Options

### A: Do not add re-exports — close #813 and #815 as won't-do <- recommended

- Effort: 0 (tasks closed, no code changes)
- Trade-off: unblocks #812/#822 to remove existing unused re-exports from core
- Risk: none — 0 consumers affected
- Evidence: 3 independent grep counts, all zero. KISS/YAGNI/DRY aligned.

### B: Add re-exports to all packages per init-re-exports.md

- Effort: ~2 days, 2 tasks (#813 + #815)
- Trade-off: +72 LOC across 6 `__init__.py` files, ongoing sync cost
- Risk: dual import paths complicate refactoring; WebCrawler needs lazy-import hack
- Evidence: 0 consumers would benefit today

### C: Defer — keep tasks blocked, decide later

- Effort: 0
- Trade-off: 5 tasks remain parked on the board
- Risk: board clutter, no resolution

## Recommendation

.95 confidence — **Option A.** Five independent research rounds and architect review
all agree. Zero consumers use package-level imports. OwlBear is an application, not
a library. Adding re-exports violates KISS, YAGNI, and DRY.

## Impact of Deferral

Tasks #812, #813, #815, #822, #823 remain blocked/parked. If no decision is made
within 5 days, the planner will auto-resolve with the recommended option (A).
