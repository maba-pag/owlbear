---
id: 1841
title: 'P2-02: Model fields — assessment counters and score computation'
status: archived
priority: medium
created: 2026-05-24T19:00:51.563620+02:00
updated: 2026-05-25T01:27:41.693939+02:00
tags:
  - phase-2
  - scope:memory
  - feature
parent: 1839
depends_on: []
ac:
  - 'MemoryEntry has `outstanding_count: int = 0`, `unremarkable_count: int = 0`,
    `didnt_use_count: int = 0`, and `score: float = 0.0` fields (defaults enable backward-compatible
    deserialization of pre-existing entries). Named constants `OUTSTANDING_BOOST =
    0.1`, `UNREMARKABLE_PENALTY = 0.01`, `STALE_THRESHOLD = 50` are defined in the
    memory engine module.'
  - 'Function `compute_score(confidence: float, outstanding_count: int, unremarkable_count:
    int) -> float` returns `confidence + (outstanding_count × OUTSTANDING_BOOST) -
    (unremarkable_count × UNREMARKABLE_PENALTY)`. Exported from owlbear_memory.'
  - MemoryEngine.save() initializes new entries with score = confidence and all 
    three counters = 0. Storage round-trip (write + read) preserves counter and 
    score values in both owlbear_memory and owlbear_mcp_memory packages (model 
    fields, frontmatter serialization, deserialization).
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1839

## Scope

Add assessment counter fields and score computation to the memory model. Define named constants for scoring parameters.

### In Scope
- MemoryEntry fields: outstanding_count, unremarkable_count, didnt_use_count (int, default 0), score (float, default 0.0)
- Named constants: OUTSTANDING_BOOST=0.1, UNREMARKABLE_PENALTY=0.01, STALE_THRESHOLD=50
- compute_score() function
- MemoryEngine.save() initializes score=confidence, counters=0
- Storage serialization/deserialization of new fields

### Out of Scope
- New states (P2-01)
- Recall slot allocation (P2-04)
- Assessment tool (P2-07)
- Migration of existing entries (P2-03)

## Domain
serve/memory/, serve/mcp-memory/

Both packages have duplicated MemoryEntry models and explicit frontmatter serialization. All field additions must be mirrored in both packages.

[[2026-05-24T23:57:07+02:00]]
## Research
- Research doc: .owlbear/research/memory-assessment-counters-score.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: straightforward implementation — field defaults for backward compat, constants + compute_score() in engine.py, dual-package sync (confidence: .90)
- Key findings: 10:1 asymmetric scoring ratio validated against SO/Reddit patterns; Option A (score=0.0 default) safe because migration P2-03 runs before P2-04 recall uses score; 6 files across 2 packages need updating
- Challenge: skipped — prescriptive ACs, trivial implementation, no design alternatives
- No new follow-up tasks — decomposition in #1839 already complete

[[2026-05-25T00:17:04+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: model fields + score computation |
| Interface clarity | PASS | Function signature, formula, defaults all specified |
| Dependency correctness | PASS | Layer 0 task, no deps needed |
| Module layering | PASS | Adds to existing model/engine, no upward imports |
| TDD compliance | PASS | Standard pipeline, test-writer handles RED |
| KISS/YAGNI | PASS | STALE_THRESHOLD forward-looking but Brief-defined constant |
| Premise challenge | PASS | Capability does not exist, Brief approves it |
| Pattern consistency | PASS | Follows existing model field + engine + storage pattern |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Memory domain only (both packages are same domain) |

### AC Refinements Applied
- AC1: Added explicit `= 0.0` default for `score` field to eliminate backward-compat ambiguity
- AC1: Added parenthetical explaining defaults enable pre-existing entry deserialization
- AC3: Expanded to explicitly require both owlbear_memory and owlbear_mcp_memory coverage
- Domain section: Updated from `serve/memory/` to `serve/memory/, serve/mcp-memory/` with dual-package note

### Challenge Results
- Challenger: reconsider (confidence 0.64)
- Findings: (1) AC1 missing model default, (2) dual-package scope mismatch, (3) dep graph ordering gap
- Architect response: accepted findings 1+2 (refined AC/scope), noted finding 3 as parent-level concern (score=0.0 before migration is acceptable — entries sort by id tiebreaker, no worse than pre-feature)

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Design Diverge
- Skipped — no competing approaches; prescriptive AC, single implementation path confirmed by research

### Verdict: APPROVE
### Action Taken: Refined AC for explicit defaults and dual-package scope, advanced to todo

[[2026-05-25T00:28:02+02:00]]
## Test-Writer Notes
- Test file: tests/test_memory_score_fields_1841.py
- Classes: TestFromAC_ModelFields, TestFromAC_ComputeScore, TestFromAC_SaveAndRoundTrip
- Tests per category: happy 18, edge 10, error 5, boundary 4
- Total: 37 tests, all FAIL
- ruff: clean

### AC Coverage
| AC | Tests | Failure mode |
|----|-------|-------------|
| AC1 model fields (owlbear_memory) | 4 default + 1 backward-compat | AttributeError: no attribute 'outstanding_count'/'unremarkable_count'/'didnt_use_count'/'score' |
| AC1 model fields (owlbear_mcp_memory) | 4 default + 1 backward-compat | AttributeError: same |
| AC1 named constants | 6 (3 values + 3 types) | AttributeError: module 'owlbear_memory.engine' has no attribute 'OUTSTANDING_BOOST' etc |
| AC2 compute_score | 8 tests | ImportError: cannot import name 'compute_score' from 'owlbear_memory' |
| AC3 save() init | 5 tests | AttributeError: score/counter fields missing |
| AC3 round-trip owlbear_memory | 4 tests | AttributeError: new fields not on model / not in frontmatter |
| AC3 round-trip owlbear_mcp_memory | 4 tests | AttributeError: new fields not on model / not in frontmatter |

[[2026-05-25T00:48:49+02:00]]
## Builder Notes
- Files changed:
  - serve/memory/src/owlbear_memory/models.py
  - serve/memory/src/owlbear_memory/engine.py
  - serve/memory/src/owlbear_memory/storage.py
  - serve/memory/src/owlbear_memory/__init__.py
  - serve/mcp-memory/src/owlbear_mcp_memory/models.py
  - serve/mcp-memory/src/owlbear_mcp_memory/engine.py
  - serve/mcp-memory/src/owlbear_mcp_memory/tools.py
- Implementation summary:
  - Added `outstanding_count`, `unremarkable_count`, `didnt_use_count` (int, default 0) and `score` (float, default 0.0) to both MemoryEntry models.
  - Added engine constants `OUTSTANDING_BOOST = 0.1`, `UNREMARKABLE_PENALTY = 0.01`, `STALE_THRESHOLD = 50` in owlbear_memory.
  - Added `compute_score(confidence, outstanding_count, unremarkable_count)` and exported it from owlbear_memory.
  - Updated `MemoryEngine.save()` to initialize score to confidence and all three counters to 0.
  - Updated frontmatter serialization/deserialization round-trip coverage by writing new fields in both packages (owlbear_memory storage + owlbear_mcp_memory engine); mirrored MCP dict serialization fields for consistency.
- Quality-runner evidence:
  - RED verification: `tests/test_memory_score_fields_1841.py` -> 0 passed, 37 failed (expected pre-implementation failures for missing fields/constants/compute_score).
  - GREEN verification: `tests/test_memory_score_fields_1841.py` -> 37 passed, 0 failed, 0 skipped.
  - Lint: clean (`ruff` clean on task-scoped lint paths after one __all__ ordering fix).
  - Coverage report (scoped run): overall 41%; touched modules reported (owlbear_memory.models 85%, owlbear_memory.storage 71%, owlbear_memory.engine 37%, owlbear_mcp_memory.models 85%, owlbear_mcp_memory.engine 65%).
- Module-level durable tests:
  - No module-level durable test file exists in `serve/memory/tests/` or `serve/mcp-memory/tests/` for this scope -> skipped per workflow guidance.
- Commit:
  - `b64c6b2e` feat: add memory score counters and compute score (#1841, builder)

[[2026-05-25T01:03:38+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1841 -> docs | AC mapped to code and evidence sufficient.
- AC1 -> code: `MemoryEntry` adds `outstanding_count`, `unremarkable_count`, `didnt_use_count`, and `score` defaults in `serve/memory/src/owlbear_memory/models.py:49-52` and `serve/mcp-memory/src/owlbear_mcp_memory/models.py:53-56`. Engine constants are defined in `serve/memory/src/owlbear_memory/engine.py:17-19`. New fields are written into frontmatter in `serve/memory/src/owlbear_memory/storage.py:75-78` and `serve/mcp-memory/src/owlbear_mcp_memory/engine.py:98-101`.
- AC1 -> tests: defaults and backward-compatible construction without the new fields are asserted in `tests/test_memory_score_fields_1841.py:60-140`; constant values/types are asserted in `tests/test_memory_score_fields_1841.py:144-178`.
- AC2 -> code: `compute_score()` implements the specified formula in `serve/memory/src/owlbear_memory/engine.py:22-25` and is exported from `serve/memory/src/owlbear_memory/__init__.py:5,24`.
- AC2 -> tests: importability and formula behavior are asserted in `tests/test_memory_score_fields_1841.py:189-260`, including zero-counter, boost-only, penalty-only, stale-threshold boundary, and constant-linked formula checks.
- AC3 -> code: `MemoryEngine.save()` initializes all three counters to `0` and `score` to `confidence` in `serve/memory/src/owlbear_memory/engine.py:227-230`. Round-trip persistence is implemented in `serve/memory/src/owlbear_memory/storage.py:58-78` and `serve/mcp-memory/src/owlbear_mcp_memory/engine.py:81-101,150-164`.
- AC3 -> tests: save initialization is asserted in `tests/test_memory_score_fields_1841.py:274-348`; round-trip preservation for all four new fields is asserted in `tests/test_memory_score_fields_1841.py:352-452` across both packages.
- Builder evidence reviewed first: task notes include RED proof (37 expected failures), GREEN proof (`tests/test_memory_score_fields_1841.py` -> 37 passed), scoped `ruff` clean, and coverage summary for touched modules.
- Independent review checks: VS Code diagnostics report no current errors on the changed files or task test file. Challenger review returned `proceed` with no blocking findings.

## Observations
- Non-blocking: AC1 legacy deserialization proof is indirect. The task tests prove missing-field defaults at the model boundary, while both file loaders (`serve/memory/src/owlbear_memory/storage.py:40-48` and `serve/mcp-memory/src/owlbear_mcp_memory/engine.py:150-164`) rely on those defaults. A future durable test could read a legacy markdown file that omits the four new frontmatter keys for a tighter end-to-end proof.
- Non-blocking: `serve/mcp-memory/src/owlbear_mcp_memory/tools.py:92-95` mirrors the new fields into MCP dict serialization. That surface is consistent with the implementation, though it was not required for this task’s ACs.

[[2026-05-25T01:12:54+02:00]]
## Docs Gate

**Verdict:** PASS → done

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| 1. README Verification | UPDATED | `serve/memory/README.md`: added 4 new `MemoryEntry` fields (`outstanding_count`, `unremarkable_count`, `didnt_use_count`, `score`) to model table; added Scoring Constants subsection (`OUTSTANDING_BOOST`, `UNREMARKABLE_PENALTY`, `STALE_THRESHOLD`); added `compute_score()` with formula; updated `save()` row to note counter/score initialization. `serve/mcp-memory/README.md`: added same 4 fields to Entry Schema table. |
| 2. External Attribution | ADDED | Two external prior-art sources (Stack Overflow reputation system, Reddit hot ranking) added to `.owlbear/sources/overview.md` under new Task #1841 section. |
| 3. Research Doc | PASS (N/A to link) | `.owlbear/research/memory-assessment-counters-score.md` exists and is referenced in task body (`[[2026-05-24]]` research section). |
| 4. Deletion Detection | PASS | Task was additive only — no symbols removed, no orphaned references. |

### Files Updated
- `serve/memory/README.md` — +24 lines (model fields + constants + compute_score + save() note)
- `serve/mcp-memory/README.md` — +4 lines (4 new Entry Schema fields)
- `.owlbear/sources/overview.md` — +7 lines (Task #1841 external sources)

### Commit
`6d28f4db` docs: update memory README and sources for score fields (#1841, doc-writer)

### Scratch Cleanup
No `.owlbear/scratch/1841-*` files found — nothing to clean.

[[2026-05-25T01:27:41+02:00]]
## Audit

### Regression Detection
Scoped domain regression (serve/memory/, serve/mcp-memory/, task test): 37 passed, 0 failed, lint clean (ruff exit 0). Broad-suite lint surfaced merge conflict markers in 3 unrelated knowledge-domain test files (background debt, not task-owned).

### Intent Verification
All 7 changed files reside in the memory domain (serve/memory/, serve/mcp-memory/) matching the task's declared scope. No extraneous scope. Implementation direction (assessment counters + score computation) aligns with stated purpose.

### Architect Quality
Score: 5/5 — Extremely prescriptive ACs: field names, types, defaults, constant values, function signature with formula, export location, dual-package coverage requirement. Challenger review refined two gaps (model defaults, dual-package scope). Clean implementation path with no builder improvisation needed.

### Commit Integrity
- test-writer: `06e7718d` test: add failing tests for memory score fields (#1841, test-writer)
- builder: `b64c6b2e` feat: add memory score counters and compute score (#1841, builder)
- doc-writer: `6d28f4db` docs: update memory README and sources for score fields (#1841, doc-writer)

### Deductions
None.

### Confidence: 1.00
### Action: ARCHIVE
