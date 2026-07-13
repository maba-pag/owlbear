---
id: 1322
title: 'P0-06: Content injection guard wiring at ingest pipeline'
status: archived
priority: medium
created: 2026-05-04T05:48:37.792577+00:00
updated: 2026-05-04T12:13:44.541148+00:00
tags:
- phase-0
- scope:knowledge
- knowledge
parent: 1316
depends_on:
- 1321
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.6)

## Acceptance Criteria

- [ ] ContentInjectionGuard wired into ingest_document tool path (O9)
- [ ] All web content passes through guard before being stored as chunks
- [ ] Guard rejects or sanitizes content containing injection markers
- [ ] Pre-guard legacy chunks are not retroactively scanned (D20 — one-time edge case)
- [ ] All #1321 tests pass green

## Scope

- **In scope:** Wire existing ContentInjectionGuard into MCP ingest_document path
- **Out of scope:** Guard at enrichment time (D20), modifying guard implementation itself
[[2026-05-04]]
## Research
- Research doc: .owlbear/research/1322-content-guard-wiring.md
- Sources: 5 studied, 4 high-relevance (all codebase)
- Recommendation: Fast-track to done — all ACs already satisfied by existing code (confidence: 0.95)
- Follow-up tasks created: none
- Decision requests: none

## Key Finding
Implementation is pre-existing. Builder committed guard wiring under #1321 (cd74db6e). ContentInjectionGuard is instantiated in server.py app_lifespan, passed to IngestPipeline, scans every chunk before storage. All 32 tests pass green. No gaps found.
[[2026-05-04]]

## Architecture Review

**Verdict:** APPROVE — all ACs pre-satisfied by code committed under #1321 (cd74db6e).

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Wire guard into ingest path only |
| Interface clarity | PASS | ContentInjectionGuard → IngestPipeline kwarg, scan() per chunk |
| Dependency correctness | PASS | #1321 (test task) archived/done |
| Module layering | PASS | server.py (MCP) → ingest.py (domain) — correct direction |
| TDD compliance | PASS | 32 tests exist in test_content_guard_wiring_1321.py |
| KISS/YAGNI | PASS | Minimal wiring, no over-abstraction |
| Premise challenge | PASS | Code exists, verified in server.py L288 and ingest.py L105-122 |
| Pattern consistency | PASS | Follows lifespan DI pattern used by other server.py services |
| Security surface | PASS | Guard scans ALL chunks, no source_type exemption |
| Single domain | PASS | knowledge domain only |

### AC with Test-Depth
- [ ] ContentInjectionGuard wired into ingest_document tool path (O9) (td:0)
- [ ] All web content passes through guard before being stored as chunks (td:0)
- [ ] Guard rejects or sanitizes content containing injection markers (td:0)
- [ ] Pre-guard legacy chunks are not retroactively scanned (D20) (td:0)
- [ ] All #1321 tests pass green (td:0)

All td:0 — implementation and tests pre-exist. Test-writer: SKIP.

### Codebase Evidence
- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` L288: `content_guard=ContentInjectionGuard()` passed to IngestPipeline
- `serve/knowledge/src/owlbear_knowledge/ingest.py` L105-122: every chunk scanned, blocked returns early, threat logs warning
- `tests/test_content_guard_wiring_1321.py`: 32 tests covering all ACs

Challenge: SKIP — all td:0, no architectural decision needed.
[[2026-05-04]]
APPROVED — all ACs pre-satisfied by existing implementation (cd74db6e from #1321). Guard wired at server.py L288, scans every chunk at ingest.py L105-122, 32 tests green. All td:0, test-writer SKIP.
[[2026-05-04]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Architect confirmed: implementation pre-exists from #1321 (cd74db6e). 32 tests in `tests/test_content_guard_wiring_1321.py` cover all ACs. No new tests needed.
- Passing through to builder.
[[2026-05-04]]
## Builder Notes
- Implementation: no code changes in this task; AC implementation already present from prior work (#1321 / commit cd74db6e).
- Evidence (fresh run): `tests/test_content_guard_wiring_1321.py` -> 32 passed, 0 failed.
- Lint: `ruff` clean on `serve/knowledge/src/owlbear_knowledge/ingest.py`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`, and `tests/test_content_guard_wiring_1321.py`.
- Coverage (informational for verification run): `owlbear_knowledge.ingest` 52%, `owlbear_mcp_knowledge.server` 44% under the single scoped AC suite.
- AC confirmation:
  - Guard wired into ingest path: verified in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` (`IngestPipeline(..., content_guard=ContentInjectionGuard())`).
  - Web content passes through guard before storage: verified in `serve/knowledge/src/owlbear_knowledge/ingest.py` (scan loop runs before insert/store).
  - Reject/sanitize behavior: verified by passing AC suite.
  - No retroactive scan of pre-guard chunks: verified by passing AC suite search-path coverage.
  - "All #1321 tests pass green": satisfied.
- Approach: non-invasive builder pass-through with fresh GREEN verification evidence only.
[[2026-05-04]]
## Review Evidence
### Test Results
- quality-runner scoped task suite: 32 passed, 0 failed, 0 skipped on `tests/test_content_guard_wiring_1321.py`
- quality-runner adjacent MCP suite: 53 passed, 0 failed, 0 skipped on `serve/mcp-knowledge/tests/test_ingest_graph_tools.py`
- First review cycle: no prior `## Review Evidence` section was present in the live task file

### Lint Results
- `ruff` clean on `serve/knowledge/src/owlbear_knowledge/ingest.py`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`, and `tests/test_content_guard_wiring_1321.py`

### Coverage
- Not run for this td:0 verification task; no task-local diff-scoped coverage gate applied

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| ContentInjectionGuard wired into `ingest_document` tool path (O9) | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:288` instantiates `ContentInjectionGuard()`, `:293` passes it into `IngestPipeline`, `:317` stores that pipeline in `AppContext`, and `:403-415` shows `ingest_document` delegating to `pipeline.ingest_text(...)` | `tests/test_content_guard_wiring_1321.py:155` proves lifespan wiring; `serve/mcp-knowledge/tests/test_ingest_graph_tools.py:165` proves live `ingest_document` delegates to `ingest_text` | PASS |
| All web content passes through guard before being stored as chunks | Scoped brief contract is the MCP `ingest_document` path (`.owlbear/briefs/draft-knowledge-activation/brief.md:113-115`). On that path, `serve/knowledge/src/owlbear_knowledge/ingest.py:110-120` scans/logs before persistence and `:170` stores chunks only after the guard branch | `tests/test_content_guard_wiring_1321.py:451` proves scan-before-store ordering; `:383` proves non-strict threat content reaches `store_chunks()` only after scan | PASS |
| Guard rejects or sanitizes content containing injection markers | Live entrypoint uses `ContentInjectionGuard()` with `strict_mode=True` by default (`serve/knowledge/src/owlbear_knowledge/content_guard.py:107-117`, `:135`), and `ingest_text()` returns blocked before storage on threat (`serve/knowledge/src/owlbear_knowledge/ingest.py:110-111`) | `tests/test_content_guard_wiring_1321.py:280` proves strict blocking; `:366` and `:383` prove the non-strict warning/continue branch separately | PASS |
| Pre-guard legacy chunks are not retroactively scanned (D20) | Brief D20 fixes guard timing to ingest only (`.owlbear/briefs/draft-knowledge-activation/brief.md:115`, `:237`). `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:364-375` shows `search_knowledge` calling `qs.query(...)` directly with no guard hook | `tests/test_content_guard_wiring_1321.py:568` proves search path does not invoke guard scan | PASS |
| All #1321 tests pass green | quality-runner scoped verification on `tests/test_content_guard_wiring_1321.py` reported 32 passed, 0 failed | `tests/test_content_guard_wiring_1321.py` | PASS |

### Test Integrity / Quality
- No weakened or removed `TestFromAC_*` assertions were found in the current inherited suite.
- The current suite now includes the previously missing exact non-strict proofs: `tests/test_content_guard_wiring_1321.py:366` (`status == "ok"`) and `:383` (scan -> store_chunks ordering for non-strict threat content).
- The remaining MCP-entrypoint concern is non-blocking because the adjacent durable suite already covers live `ingest_document` delegation at `serve/mcp-knowledge/tests/test_ingest_graph_tools.py:165`.

### Informational / Residual Risk
- The sibling `IngestPipeline.ingest()` path still persists before scan at `serve/knowledge/src/owlbear_knowledge/ingest.py:281-288`, but the current brief and task scope narrow #1322 to the MCP `ingest_document` / `ingest_text` path, so this was not used as a gate here.

### Deductions
- `-0.03` dirty-tree contamination and inherited-test immutability could not be fully proven because this tool surface cannot run `git status --porcelain` or `git show`; commit presence was only confirmed via `.git/logs/HEAD:1789` and `.git/logs/refs/heads/dev:1639`
- `-0.02` the task-local AC suite is component-focused rather than a full MCP integration suite, but the adjacent durable `ingest_document` suite closes the delegation gap

### Verdict
- PASS
- Confidence: 0.92
- Action: advance to `docs`

### Reflection
- Verification-only child tasks need adjacent durable suites as evidence, not just inherited task-local tests.
- When direct git inspection is unavailable, `.git/logs/**` can confirm commit presence but not full diff cleanliness.
- The brief scope at `.owlbear/briefs/draft-knowledge-activation/brief.md:113-115` was necessary to keep the sibling `ingest()` path from being over-read into this task.
[[2026-05-04]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No code changes in this task; serve/mcp-knowledge/README.md and serve/knowledge/README.md do not reference ContentInjectionGuard internals |
| 2 | Module docstrings | No | N/A | No modules created or modified in this task (pass-through verification only) |
| 3 | External attribution | No | N/A | Research doc cites OWASP LLM01:2025; already attributed at .owlbear/sources/overview.md:3881 (prior task #834) |
| 4 | Research doc | Yes | Verified | .owlbear/research/1322-content-guard-wiring.md exists and is linked from task body |
| 5 | Diagram maintenance (describes match) | No | N/A | mcp-topology.excalidraw describes serve/mcp-*/src/** and serve/knowledge/src/**, but no files were changed in this task — footer update not warranted |
| 6 | Explicit diagram creation | No | N/A | Not requested |
| 7 | Deletion detection | No | N/A | No deleted files |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py | IN (docstrings) | N/A — referenced for evidence only, not changed in this task |
| serve/knowledge/src/owlbear_knowledge/ingest.py | IN (docstrings) | N/A — referenced for evidence only, not changed in this task |
| tests/test_content_guard_wiring_1321.py | OUT | N/A |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None
[[2026-05-04]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| ContentInjectionGuard wired into ingest_document tool path (O9) | server.py L288: `ContentInjectionGuard()` instantiated, L290-293: passed to `IngestPipeline` | PASS |
| All web content passes through guard before being stored as chunks | ingest.py L108-125: guard scans every chunk before storage (L128+) | PASS |
| Guard rejects or sanitizes content containing injection markers | ingest.py L110-111: `check.blocked` returns early; L120-125: threat logs warning | PASS |
| Pre-guard legacy chunks are not retroactively scanned (D20) | Reviewer confirmed search_knowledge has no guard hook; brief D20 scopes to ingest only | PASS |
| All #1321 tests pass green | 32 passed, 0 failed | PASS |

### Test Results
- Scoped: 32 passed, 0 failed (tests/test_content_guard_wiring_1321.py)
- Full Python suite: 1175 passed, 68 failed (all in kanban/mcp-memory domains — none in knowledge scope)
- Full frontend suite: 950 passed, 13 failed (ActivityTab component — unrelated)
- Background failures are pre-existing tech debt in other domains

### Lint
- Scoped (ingest.py, server.py, test file): clean
- Full ruff: 1 violation in copilot_auth.py (T201 print — unrelated)
- ESLint: 1 rule definition issue in usePolling.ts (unrelated)

### Commit Integrity
- cd74db6e confirmed: `feat: wire ingest guard at lifespan/text path (#1321, builder)`
- Research doc exists: .owlbear/research/1322-content-guard-wiring.md

### AC Quality Score: 4/5
AC lines were specific and verifiable. Task was purely verification of pre-existing work (all td:0). No gaps requiring builder improvisation.

### Deductions
- -.01 background failures in other domains (process awareness)

### Confidence: 0.99
### Action: ARCHIVE