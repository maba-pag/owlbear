---
id: 1843
title: 'P2-04: Recall — reserved explore and challenge slots'
status: archived
priority: medium
created: 2026-05-24T19:01:24.850020+02:00
updated: 2026-05-25T04:41:12.548112+02:00
tags:
  - phase-2
  - scope:memory
  - feature
parent: 1839
depends_on:
  - 1840
  - 1841
ac:
  - '`recall_memory` returns `limit` entries (default 20): `max(0, limit - SLOT_EXPLORE
    - SLOT_CHALLENGE)` highest-score in-scope entries, up to SLOT_EXPLORE explore
    slots (lowest total assessment count), up to SLOT_CHALLENGE challenge slots (lowest
    `outstanding_count`). Named constants `SLOT_EXPLORE = 2`, `SLOT_CHALLENGE = 2`.'
  - 'When `limit <= SLOT_EXPLORE + SLOT_CHALLENGE`, regular pool is 0; explore fills
    first (up to limit), challenge fills remainder. Explore metric: `outstanding_count
    + unremarkable_count + didnt_use_count`.'
  - 'Dedup priority: explore > challenge > regular. An entry in explore is excluded
    from challenge and regular pools; an entry in challenge is excluded from regular.
    Fewer in-scope entries than `limit` → return all without padding.'
  - Final returned list sorted by `(state_rank, -score, id)` regardless of pool 
    origin. Callers receive a single ordered list, not categorized blocks.
  - 'Tiebreaker for pool selection: identical qualifying metric → select by lowest
    `id` lexicographically (UUIDv4; not chronological). Guarantees deterministic slot
    assignment.'
  - Recall state filter includes approved, curated, contested; excludes 
    disputed, stale, deleted, pending.
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1839

## Scope

Replace the current recall sort (state_rank, -confidence, id) with score-based sorting and add reserved explore/challenge slot allocation.

### In Scope
- Recall sorted by (state_rank, -score, id)
- Reserved slot allocation: limit-4 regular + 2 explore + 2 challenge
- Explore: lowest total assessment count
- Challenge: lowest outstanding_count
- Dedup across slot categories
- State visibility filtering (uses new states from P2-01)
- Named constants SLOT_EXPLORE=2, SLOT_CHALLENGE=2

### Out of Scope
- Score computation (P2-02)
- State machine definitions (P2-01)
- Assessment tool (P2-07)
- Slot-efficiency check (P2-05)

## Domain
serve/mcp-memory/

[[2026-05-25T01:48:25+02:00]]
## Research
- Research doc: .owlbear/research/memory-recall-explore-challenge-slots.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: T1 implementation — three-pool selection (explore→challenge→regular) in tools.py recall_memory, constants in MCP layer (confidence: 0.92)
- Key findings: fixed-slot allocation is KISS-aligned over probabilistic epsilon-greedy; algorithm is ~30 LOC change; all required model fields already exist from #1840/#1841; limit<4 edge case needs max(0,…) guard
- Challenge: skipped — prescriptive ACs, single implementation path, no alternatives

[[2026-05-25T01:48:30+02:00]]
Research complete. T1 — straightforward algorithmic change to recall_memory in tools.py. Three-pool selection (explore→challenge→regular) with dedup via id sets. All model fields available from completed deps #1840/#1841. No follow-up tasks needed — decomposition already complete in parent #1839.

[[2026-05-25T02:17:21+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Modifies recall selection logic in tools.py only |
| Interface clarity | PASS | ACs specify exact pool formulas, sort keys, dedup rules, and edge cases |
| Dependency correctness | PASS | #1840 (states) and #1841 (model fields) both archived; all required fields confirmed |
| Module layering | PASS | MCP layer (tools.py) reads from owlbear_memory models — correct direction |
| TDD compliance | PASS | proof_bundle=behavioral; test-writer will create tests |
| KISS/YAGNI | PASS | Three-pool selection is minimal for fixed-slot requirement (~30 LOC) |
| Premise challenge | PASS | No existing capability covers this; required by parent Brief design |
| Pattern consistency | PASS | Follows existing tools.py structure (filter → sort → slice) |
| Security surface | PASS | No new system boundaries; internal recall logic only |
| Single domain | PASS | serve/mcp-memory/ only |

### Design Diverge
- Trigger: skipped — single valid approach (fixed-slot allocation vs epsilon-greedy clearly favors deterministic per research)

### Challenge Results
- Challenger: reconsider (confidence 0.57)
- Findings accepted: (1) AC4 false \"oldest entries first\" claim — UUIDs are not chronological; (2) AC1 limit<4 edge case unspecified
- Findings rebutted: (a) Evidence sufficiency — test-writer creates tests before builder, consolidation test #1848 is correctly sequenced; (b) Scope accounting — README updates handled by doc-writer stage
- Architect response: revised ACs to fix both accepted findings, rebutted remaining

### AC Refinements Made
- AC1: Changed to `max(0, limit - SLOT_EXPLORE - SLOT_CHALLENGE)` formula; explicit slot fill behavior
- Added new AC2: Explicit limit <= 4 edge case behavior
- AC4 (now AC5): Removed false \"oldest entries first\" parenthetical; clarified UUIDv4 lexicographic sort
- Split from 5 → 6 ACs for clarity

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined ACs for edge-case completeness and factual accuracy, advanced to todo

[[2026-05-25T02:56:15+02:00]]
test-writer crashed once (empty output); releasing claim before retry

[[2026-05-25T03:10:52+02:00]]
## Test-Writer Notes

**Test file:** `tests/test_recall_slots_1843.py`
**Commit:** `772a694f` — test: recall explore/challenge slot allocation (#1843, test-writer)

### Classes and test counts

| Class | AC | Tests | Category |
|---|---|---|---|
| `TestFromAC_SlotConstants` | AC1 | 5 | happy (constants), slot-pool selection |
| `TestFromAC_LimitEdge` | AC2 | 5 | edge/boundary (limit ≤ SLOT_SUM) |
| `TestFromAC_SlotDedup` | AC3 | 1 | dedup integration (explore→challenge slot freed) |
| `TestFromAC_FinalSort` | AC4 | 3 | sort key (-score not -confidence) |
| `TestFromAC_Tiebreak` | AC5 | 2 | tiebreak (lowest id wins) |
| `TestFromAC_StateFilter` | AC6 | 1 | state filter + slot integration |

**Total: 17 tests — all FAIL ✓ (quality-runner confirmed: 0 pass, 17 fail, ruff clean)**

### AC coverage

| AC | Tests | Status |
|---|---|---|
| AC1: SLOT_EXPLORE=2, SLOT_CHALLENGE=2 constants; pool selection formulas | 5 | FAIL ✓ |
| AC2: limit ≤ 4 → regular=0; explore first; metric = outstanding+unremarkable+didnt_use | 5 | FAIL ✓ |
| AC3: dedup priority explore > challenge > regular | 1 | FAIL ✓ |
| AC4: final sort (state_rank, -score, id) — score not confidence | 3 | FAIL ✓ |
| AC5: pool tiebreak by lowest id | 2 | FAIL ✓ |
| AC6: approved/curated/contested included; excluded states filtered before slots | 1 | FAIL ✓ |

### Test failure modes

- **Constants (AC1):** `ImportError` — `SLOT_EXPLORE` / `SLOT_CHALLENGE` not in `tools.py`.
- **Pool selection / limit edge (AC1–AC3):** Entries are designed with confidence inversely correlated to explore/challenge eligibility; current `-confidence` sort returns the wrong entries.
- **Sort key (AC4):** confidence and score are deliberately divergent; `-confidence` sort produces opposite ordering from `-score`.
- **Tiebreak (AC5):** id-sorted winners have lower confidence than the confidence-sorted winners; current impl returns the wrong entry.
- **State filter + slot (AC6):** contested entry wins explore slot by metric but loses by confidence; current impl returns the high-confidence curated entry.

### AC6 scope note

Stale/deleted/pending exclusion is already covered by regression guards in `test_memory_state_machine_1840.py` (AC3 of that task). A separate stale-exclusion test here passed the current implementation and was omitted per RED-phase instructions. The single AC6 test exercises both state-filter correctness (contested included, disputed excluded) and the new slot logic simultaneously.

[[2026-05-25T03:29:44+02:00]]
## Builder Notes
- Implementation: updated serve/mcp-memory/src/owlbear_mcp_memory/tools.py.
- Files changed: added SLOT_EXPLORE/SLOT_CHALLENGE constants and replaced recall selection logic with three-pool allocation (explore -> challenge -> regular), dedup by priority (explore > challenge > regular), then final unified sort by (state_rank, -score, id).
- Commit: 72c4afd179115db61696eba7874b596e10860bc3

- RED verification (quality-runner): tests/test_recall_slots_1843.py -> 0 passed / 17 failed; ruff clean.
- GREEN verification (quality-runner): tests/test_recall_slots_1843.py -> 17 passed / 0 failed; ruff clean.
- Additional regression check: tests/test_memory_state_machine_1840.py + tests/test_recall_slots_1843.py -> 50 passed / 0 failed; ruff clean.
- Module-level durable baseline observed: tests/test_recall_memory.py has 1 failing test (`TestFromAC_PriorityOrdering::test_sort_then_slice_approved_fills_before_curated`) due pre-slot sort-then-slice expectation conflicting with #1843 reserved-slot semantics.

- Coverage: owlbear_mcp_memory.tools reported 38% on scoped verification set.
- Lint: clean.
- Evidence summary: all #1843 TestFromAC classes now pass with deterministic slot allocation and score-based final ordering; constants exported in tools module as required by AC1.

[[2026-05-25T03:46:30+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1843 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: scoped GREEN proof reports tests/test_recall_slots_1843.py -> 17 passed / 0 failed, additional regression check tests/test_memory_state_machine_1840.py + tests/test_recall_slots_1843.py -> 50 passed / 0 failed, lint clean, and coverage summary present.
- AC evidence map:

| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | serve/mcp-memory/src/owlbear_mcp_memory/tools.py:34-35, 279-296 | tests/test_recall_slots_1843.py:114, 120, 127, 196, 283 | PASS |
| AC2 | serve/mcp-memory/src/owlbear_mcp_memory/tools.py:279-290 | tests/test_recall_slots_1843.py:402, 452, 588 | PASS |
| AC3 | serve/mcp-memory/src/owlbear_mcp_memory/tools.py:286, 289, 293, 295, 298 | tests/test_recall_slots_1843.py:653 | PASS |
| AC4 | serve/mcp-memory/src/owlbear_mcp_memory/tools.py:296, 299 | tests/test_recall_slots_1843.py:795 and companion final-sort assertions in TestFromAC_FinalSort | PASS |
| AC5 | serve/mcp-memory/src/owlbear_mcp_memory/tools.py:285, 290, 296 | tests/test_recall_slots_1843.py:932 and companion explore-tiebreak assertions in TestFromAC_Tiebreak | PASS |
| AC6 | serve/mcp-memory/src/owlbear_mcp_memory/tools.py:271, 299 | tests/test_recall_slots_1843.py:1022, tests/test_recall_memory.py:484, 512, 549, 566 | PASS |
- Challenger cross-check completed for behavioral bundle. Result: reconsidered FAIL; no blocking gap established beyond legacy durable-suite debt.
- Blocking findings: none.

## Observations
- tests/test_recall_memory.py:583 still encodes the pre-slot sort-then-slice expectation and is stale against the #1843 reserved-slot contract implemented in serve/mcp-memory/src/owlbear_mcp_memory/tools.py:279-299. This is non-blocking for the current behavioral bundle because the task-local AC proof is green and the older assertion conflicts with the updated contract rather than exposing an AC miss in the implementation.
- Existing durable recall tests at tests/test_recall_memory.py:484, 512, 549, and 566 still align with the new behavior, so the legacy debt appears isolated to the slice-filling assertion rather than the broader recall contract.

[[2026-05-25T04:07:39+02:00]]
## Docs Gate

### Item 1: README Verification
- Target: `serve/mcp-memory/README.md` (convention: `serve/mcp-memory/src/**`)
- Layer 1 (grep): `SLOT_EXPLORE`, `SLOT_CHALLENGE`, `recall_memory` — constants not referenced in README (expected; they appear only in tool description). Checked Tools table.
- Layer 2 (editorial): `recall_memory` description read "approved before curated; default limit 20" — stale flat-sort language contradicting the three-pool slot allocation implemented in this task.
- **Fix applied:** Updated tool description to "three-pool slot allocation (explore, challenge, regular) with final sort by `(state_rank, -score, id)`; constants `SLOT_EXPLORE=2`, `SLOT_CHALLENGE=2`; default limit 20".
- Commit: `0c1d9a78`
- State Model section (approved/curated/contested included; disputed/stale excluded from recall) — still accurate per implementation filter. No further changes needed.

### Item 2: External Attribution
- `.owlbear/sources/overview.md` already contains `## Recall Explore/Challenge Slots (Task #1843)` section with 6 sources. Up-to-date. N/A — no new attribution needed.

### Item 3: Research Doc
- `.owlbear/research/memory-recall-explore-challenge-slots.md` exists. Linked in task body under `## Research`. ✓

### Item 4: Deletion Detection
- No symbols, tools, or flags were removed. Only additions (SLOT_EXPLORE, SLOT_CHALLENGE) and modified recall selection logic. No orphaned references. ✓

### Scratch Cleanup
- No scratch files with prefix `1843-` exist in `.owlbear/scratch/`. Clean.

### Files Updated
- `serve/mcp-memory/README.md` — corrected `recall_memory` tool description

[[2026-05-25T04:41:12+02:00]]
## Audit
### Regression Detection
- Domain-scoped: 74 passed, 1 failed (known stale durable test test_sort_then_slice_approved_fills_before_curated, documented by builder and reviewer as pre-slot expectation conflict; module-level curation is post-archive per two-tier awareness)
- Task-scoped: 17/17 passed
- No cross-task regressions in memory domain
- Regression verdict: PASS

### Intent Verification
- Scope alignment: PASS (all changes in serve/mcp-memory/ domain; test file in tests/)
- Purpose match: PASS (three-pool slot allocation implemented per stated scope)
- Extraneous scope: none
- Boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 5/5
Specific measurable ACs covering edge cases, challenger invoked with findings incorporated, AC revisions documented. Clean implementation path.

### Commit Integrity
- Upstream commit presence: PASS (72c4afd1 builder, 772a694f test-writer, 0c1d9a78 doc-writer)
- All commits properly scoped to single domain with task reference

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive
