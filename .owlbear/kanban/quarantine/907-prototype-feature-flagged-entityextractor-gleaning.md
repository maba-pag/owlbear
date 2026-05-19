---
id: 907
title: Prototype feature-flagged EntityExtractor gleaning
status: archived
priority: nice-to-have
created: 2026-03-21T15:14:48.2581991+01:00
updated: 2026-03-23T18:28:52.910711+01:00
tags:
    - scope:core
    - knowledge
    - benchmark
    - type:build
    - phase-research
parent: 891
depends_on:
    - 906
class: standard
---

**Source:** #891 and docs/research/entity-extractor-gleaning-benchmark.md Â§5

Parent tracker for the EntityExtractor gleaning prototype. This card is not a builder-ready implementation task and must stay as the decomposition contract for the child slices below.

**Dependencies:** #906

**Execution Path:**

- RED #931 -> GREEN #917: default-off two-pass flow and pass-2 fallback.
- RED #932 -> GREEN #918: in-memory merge and edge repair.
- RED #933 -> GREEN #919: per-pass usage visibility.

**Scope**

- Keep current production behavior single-pass by default.
- Keep implementation work out of #907; runtime and test changes belong on the child cards only.
- Use the existing seams in src/owlbear/memory/knowledge/extractor.py, src/owlbear/bootstrap/knowledge.py, src/owlbear/memory/knowledge/graph.py, and src/owlbear/memory/usage.py.

**AC:**

1. #907 remains a parent tracker only; no builder or test-writer work should be dispatched directly from this card.
2. The default-off two-pass execution and pass-2 fallback contract is owned by #917 and must be preceded by RED task #931.
3. The in-memory merge plus edge-repair contract is owned by #918 and must be preceded by RED task #932.
4. The per-pass usage recording contract is owned by #919 and must be preceded by RED task #933.
5. Upstream benchmark harness task #906 remains a prerequisite for the child execution path.
6. Any child move toward todo requires that child card's own architect review bind the RED predecessor and keep the implementation atomic.

## Research

- Doc: docs/research/entity-extractor-gleaning-prototype.md
- Key findings:
  - Constructor-level default-off toggle is the smallest reversible seam because src/owlbear/bootstrap/knowledge.py builds EntityExtractor in one production path today.
  - Two-pass execution/fallback, in-memory merge/edge repair, and per-pass usage visibility are separate responsibilities and must stay split.
  - Merge must canonicalize on (name.casefold(), entity_type) and rewrite both edge endpoints before returning.
  - Per-pass benchmark visibility should reuse record_agent_usage() with distinct operation labels instead of widening UsageRecord.
- Follow-up tasks:
  - #917 paired with #931
  - #918 paired with #932
  - #919 paired with #933
- Attribution updated:
  - docs/sources/overview.md

[[2026-03-23]] Mon 17:55

## Architecture Review

**Verdict:** Refine

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. #907 remains a parent tracker only; no builder or test-writer work should be dispatched directly from this card. | The previous body still read like a build task, which kept sending an umbrella tracker back through the architect gate. | Rewrote the parent contract so #907 is explicitly tracker-only. |
| 2. The default-off two-pass execution and pass-2 fallback contract is owned by #917 and must be preceded by RED task #931. | src/owlbear/memory/knowledge/extractor.py still has one extract() path, so execution plus fallback remains one child slice. | Keep on #917 with RED predecessor #931. |
| 3. The in-memory merge plus edge-repair contract is owned by #918 and must be preceded by RED task #932. | UUID-backed entity ids and the persisted graph merge contract keep normalization plus edge repair as a separate slice. | Keep on #918 with RED predecessor #932. |
| 4. The per-pass usage recording contract is owned by #919 and must be preceded by RED task #933. | src/owlbear/memory/usage.py still provides the minimal per-operation seam without schema changes. | Keep on #919 with RED predecessor #933. |
| 5. Upstream benchmark harness task #906 remains a prerequisite for the child execution path. | #906 is still backlog, so the gleaning implementation path remains gated by the benchmark harness work. | Keep. |
| 6. Any child move toward todo requires that child card's own architect review bind the RED predecessor and keep the implementation atomic. | #917, #918, and #919 are still ideation cards that depend only on #906, and I cannot modify undispatched sibling tasks from this review. | Leave #907 in backlog; tighten the child cards in their own architect passes. |

### Architecture Notes

- src/owlbear/bootstrap/knowledge.py still constructs EntityExtractor(model=chat_model) in the only production seam, so a constructor-level toggle remains the narrowest surface.
- src/owlbear/memory/knowledge/extractor.py still combines extraction into one extract() path that returns ExtractionResult() on failure and records usage once per successful call; that keeps execution/fallback, merge, and usage as separate responsibilities.
- src/owlbear/memory/knowledge/graph.py still rewrites both source_id and target_id during canonical merge, so any gleaning merge helper must mirror that contract in memory.
- tests/test_knowledge_extractor.py remains the RED home for #917 and #918; tests/test_usage_wiring.py remains the RED home for #919.
- Cross-task boundary applies here: the correct next step is architect review on #917, #918, and #919, not edits to those cards from this invocation.

### Changes Made

- Claimed task #907 as architect-907.
- Rewrote the parent body to make #907 an explicit tracker contract instead of a builder-facing implementation card.
- Re-verified docs/research/entity-extractor-gleaning-prototype.md, src/owlbear/memory/knowledge/extractor.py, src/owlbear/bootstrap/knowledge.py, src/owlbear/memory/knowledge/graph.py, src/owlbear/memory/knowledge/models.py, src/owlbear/memory/usage.py, tests/test_knowledge_extractor.py, tests/test_usage_wiring.py, and child tasks #917, #918, #919, #931, #932, and #933.
- Appended this architecture review and released the claim.

### Dependencies

- Verified unresolved upstream dependency: #906 remains backlog.
- Verified RED predecessors exist: #931 for #917, #932 for #918, and #933 for #919.
- Verified child-task wiring is still missing on the build cards themselves: #917, #918, and #919 still depend only on #906.
- Added/Removed/Verified: no new tasks created; the next architect passes should refine the child cards, not reopen the parent.

[[2026-03-23]] Mon 18:28

## Architecture Review

**Verdict:** REFINE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. #907 remains a parent tracker only; no builder or test-writer work should be dispatched directly from this card. | The tracker-only contract is now explicit and matches sibling parent tracker #908, so no direct implementation work should originate here. | Keep this card in backlog as a parent tracker only. |
| 2. The default-off two-pass execution and pass-2 fallback contract is owned by #917 and must be preceded by RED task #931. | `src/owlbear/memory/knowledge/extractor.py` still exposes one `extract()` path, so default-off execution plus pass-2 fallback remains a single child slice. | Keep on `#931 -> #917`; do not pull it back into the parent. |
| 3. The in-memory merge plus edge-repair contract is owned by #918 and must be preceded by RED task #932. | `src/owlbear/memory/knowledge/graph.py` still treats source and target edge rewrites as part of canonical merge semantics, which keeps this as a distinct child responsibility. | Keep on `#932 -> #918`. |
| 4. The per-pass usage recording contract is owned by #919 and must be preceded by RED task #933. | `src/owlbear/memory/usage.py` still supports per-operation labeling without schema changes, so usage visibility stays separate from extractor control flow and merge logic. | Keep on `#933 -> #919`. |
| 5. Upstream benchmark harness task #906 remains a prerequisite for the child execution path. | `docs/research/entity-extractor-gleaning-benchmark.md` and `docs/research/entity-extractor-gleaning-prototype.md` both still gate prototype work on the benchmark harness, but #907 only carried that dependency in prose. | Add explicit dependency metadata on `#906` and keep the prerequisite. |
| 6. Any child move toward todo requires that child card's own architect review bind the RED predecessor and keep the implementation atomic. | Child cards `#917`, `#918`, and `#919` are still in `ideation` and currently depend only on `#906`, so the RED predecessors are not yet bound in metadata on the implementation cards. | Leave `#907` in backlog; the next architect passes belong on the child cards. |

### Architecture Notes

- `docs/research/entity-extractor-gleaning-benchmark.md` and `docs/research/entity-extractor-gleaning-prototype.md` both decompose the prototype into three child slices rather than one builder-ready implementation card.
- `src/owlbear/bootstrap/knowledge.py` still constructs `EntityExtractor(model=chat_model)` in the only production seam, so a constructor-level default-off toggle remains the narrowest child surface.
- `src/owlbear/memory/knowledge/extractor.py` still has a single `extract()` path that returns `ExtractionResult()` on failure and records one usage operation on success; execution/fallback, merge, and per-pass usage remain separate responsibilities.
- `src/owlbear/memory/knowledge/graph.py` still rewrites both `source_id` and `target_id` during canonical merge, so any gleaning merge helper must preserve that contract in memory.
- `tests/test_knowledge_extractor.py` remains the RED home for `#917` and `#918`; `tests/test_usage_wiring.py` remains the RED home for `#919`.
- Parent tracker precedent matches this outcome: `#906` and `#908` both stay in backlog as decomposition contracts rather than advancing to builders.

### Changes Made

- Claimed task `#907` as `architect-907`.
- Added explicit metadata dependency on `#906` so the board reflects the prerequisite already stated in the body.
- Re-verified `docs/research/entity-extractor-gleaning-prototype.md`, `docs/research/entity-extractor-gleaning-benchmark.md`, `src/owlbear/memory/knowledge/extractor.py`, `src/owlbear/bootstrap/knowledge.py`, `src/owlbear/memory/knowledge/graph.py`, `src/owlbear/memory/usage.py`, `tests/test_knowledge_extractor.py`, `tests/test_usage_wiring.py`, and child tasks `#917`, `#918`, `#919`, `#931`, `#932`, and `#933`.
- Appended this architecture review and released the claim.

### Dependencies

- Added/Removed/Verified: added explicit dependency on `#906` to this parent tracker.
- Verified unresolved upstream prerequisite: `#906` remains backlog.
- Verified RED predecessors exist: `#931` for `#917`, `#932` for `#918`, and `#933` for `#919`.
- Verified child build cards `#917`, `#918`, and `#919` still need their own architect passes to bind the RED predecessors before any move toward `todo`.
