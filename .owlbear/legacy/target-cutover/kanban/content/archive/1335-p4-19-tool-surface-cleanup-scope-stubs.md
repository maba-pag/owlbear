---
id: 1335
title: 'P4-19: Tool surface cleanup + scope stubs'
status: archived
priority: medium
created: 2026-05-04T05:48:50.199644+00:00
updated: 2026-05-07T15:28:26.229593+00:00
tags:
- phase-4
- scope:mcp-knowledge
- knowledge
parent: 1316
depends_on:
- 1334
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.9)

## Acceptance Criteria

- [ ] Only 8 active tools registered: search_knowledge, list_sources, get_stats, ingest_document, refresh_source, get_next_batch, get_consolidation_candidates, store_enrichment (O7)
- [ ] Removed from registration: list_entities, bookmark_source, list_bookmarks, update_bookmark_tags, consolidate_knowledge
- [ ] 4 scope stubs registered internally: import_scope, export_scope, sync_from_global, sync_to_global (D12, D16)
- [ ] Scope stubs not exposed to agents — registered but excluded from tool discovery
- [ ] All #1334 tests pass green

## Scope

- **In scope:** MCP tool registration cleanup, scope stub creation
- **Out of scope:** Scope stub implementation (D12, D16), delete_source tool (D19)
[[2026-05-07]]
## Research

All 5 ACs already satisfied by current codebase. Implementation delivered in commit `430ccbdd` ("feat: reduce mcp-knowledge tool surface to 8 active tools (#1334, builder)"). The builder who implemented #1334's tests also made server changes GREEN in the same pass.

Verification: `uv run pytest tests/test_mcp_knowledge_tool_surface_1334.py` → 4/4 pass.

No follow-up tasks needed. Doc: `.owlbear/research/1335-tool-surface-cleanup.md`. Confidence: 0.95.
[[2026-05-07]]

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tool registry cleanup + scope stubs are one coherent MCP surface concern |
| Interface clarity | PASS | Exact tool names and counts specified in AC |
| Dependency correctness | PASS | #1334 done/archived; its tests pass green |
| Module layering | PASS | All changes within serve/mcp-knowledge, no upward imports |
| TDD compliance | PASS | tests/test_mcp_knowledge_tool_surface_1334.py covers all 5 ACs |
| KISS/YAGNI | PASS | Straightforward removal + stub retention pattern |
| Premise challenge | PASS | Work already shipped in #1334 builder pass; task documents final state |
| Pattern consistency | PASS | Follows FastMCP post-def registration pattern for batch tools |
| Security surface | PASS | No new boundaries — removed tools, stubs not agent-facing |
| Single domain | PASS | mcp-knowledge only |

### Test Depth
- AC1: Only 8 active tools registered (td:0) — verified via existing test
- AC2: Removed from registration (td:0) — verified via existing test
- AC3: 4 scope stubs registered internally (td:0) — verified via existing test
- AC4: Scope stubs not exposed to agents (td:0) — verified via existing test
- AC5: All #1334 tests pass green (td:0) — verification-only
- Max depth: 0
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — all td:0
- Architect response: N/A

### Verdict: APPROVE
### Action Taken: Approved to todo. All ACs already satisfied by current codebase (commit 430ccbdd). Builder confirms green, no new code needed.
[[2026-05-07]]
Architecture review complete. All 10 criteria PASS. All ACs verified against live codebase — 8 active MCP tools, 5 removed, 4 scope stubs as plain functions in __all__ but not in tool registry. Tests exist and pass (4/4). All td:0 → Test-writer: SKIP.
[[2026-05-07]]
## Test-Writer Notes
- All AC lines annotated td:0 — architect verdict: Test-writer: SKIP.
- All 5 ACs already satisfied by existing code (commit 430ccbdd) and covered by tests/test_mcp_knowledge_tool_surface_1334.py (4/4 pass).
- No new tests needed. Passing through to builder.
[[2026-05-07]]
## Builder Notes
- Implementation: no source changes required; AC state already satisfied in existing code.
- Evidence: `tests/test_mcp_knowledge_tool_surface_1334.py` passed 4/4 (failed: []).
- Lint: clean on `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` and `tests/test_mcp_knowledge_tool_surface_1334.py`.
- Coverage: scoped run reported `owlbear_mcp_knowledge.server` at 29.54% (verification-only pass; no touched modules in this task).
- Approach: verification-only builder pass-through based on td:0 architecture verdict and existing implementation from prior task.

[[2026-05-07]]
## Review Evidence
### Test Results
- Quality-runner executed `uv run pytest tests/test_mcp_knowledge_tool_surface_1334.py -v --tb=short`.
- Result: 4 passed, 0 failed, 1.28s, exit code 0.
- Passing tests:
  - `tests/test_mcp_knowledge_tool_surface_1334.py::TestFromAC_ToolSurfaceValidation::test_exactly_eight_tools_registered`
  - `tests/test_mcp_knowledge_tool_surface_1334.py::TestFromAC_ToolSurfaceValidation::test_all_active_tools_present`
  - `tests/test_mcp_knowledge_tool_surface_1334.py::TestFromAC_ToolSurfaceValidation::test_removed_tools_not_registered`
  - `tests/test_mcp_knowledge_tool_surface_1334.py::TestFromAC_ToolSurfaceValidation::test_scope_stubs_are_callable_and_not_registered_as_tools`

### Lint Results
- Quality-runner executed `uv run ruff check serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py tests/test_mcp_knowledge_tool_surface_1334.py`.
- Result: clean, 0 issues, exit code 0.

### Coverage
- Not run.
- Reason: verification-only surface task; no changed-module coverage gate needed for review confidence.

### Test-Writer Audit
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| Only 8 active tools registered | `test_exactly_eight_tools_registered` (`tests/test_mcp_knowledge_tool_surface_1334.py:105`) | Yes. Exact `len(tool_names) == 8` fails on any extra or missing registered tool. | COVERED |
| Removed tools absent from registration | `test_removed_tools_not_registered` (`tests/test_mcp_knowledge_tool_surface_1334.py:139`) | Yes. Set intersection fails if any removed tool remains registered. | COVERED |
| 4 scope stubs exist and are internal-only | `test_scope_stubs_are_callable_and_not_registered_as_tools` (`tests/test_mcp_knowledge_tool_surface_1334.py:157`) | Yes. Fails if any stub is missing, non-callable, or appears in the MCP tool list. | COVERED |
| All #1334 tests pass green | Full scoped pytest run above | Yes. Any failing task test would break the AC directly. | COVERED |

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Only 8 active tools registered: `search_knowledge`, `list_sources`, `get_stats`, `ingest_document`, `refresh_source`, `get_next_batch`, `get_consolidation_candidates`, `store_enrichment` | MCP registrations present at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:792`, `:795`, `:798`, `:829`, `:864`, `:879`, `:941`, `:1194`; independent pass from `tests/test_mcp_knowledge_tool_surface_1334.py:105` | `test_exactly_eight_tools_registered` | PASS |
| Removed from registration: `list_entities`, `bookmark_source`, `list_bookmarks`, `update_bookmark_tags`, `consolidate_knowledge` | Plain function defs remain at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:909`, `:1005`, `:1027`, `:1049`, `:1240`; independent absence proof from `tests/test_mcp_knowledge_tool_surface_1334.py:139` | `test_removed_tools_not_registered` | PASS |
| 4 scope stubs registered internally: `import_scope`, `export_scope`, `sync_from_global`, `sync_to_global` | Current code exposes internal stubs at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1074`, `:1096`, `:1115`, `:1153`; module export list includes them at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:802`; brief refines contract to deferred internal stubs at `.owlbear/briefs/draft-knowledge-activation/brief.md:24` and `:164` | `test_scope_stubs_are_callable_and_not_registered_as_tools` | PASS |
| Scope stubs not exposed to agents | Brief says scope stubs “exist but are not exposed” at `.owlbear/briefs/draft-knowledge-activation/brief.md:24`; current MCP registrations are limited to the 8 active tools above, and task test at `tests/test_mcp_knowledge_tool_surface_1334.py:157` confirms the 4 stub names are absent from the tool list | `test_scope_stubs_are_callable_and_not_registered_as_tools` | PASS |
| All #1334 tests pass green | Quality-runner pytest result: 4/4 passed, 0 failed | Full scoped pytest run | PASS |

### Additional Review Notes
- Brief/refined contract check: the child AC wording says “registered internally,” but the binding brief language is “4 deferred scope stubs” that “exist but are not exposed” (`.owlbear/briefs/draft-knowledge-activation/brief.md:24`, `:164`, `:198`). Current code and tests satisfy that refined contract.
- Commit presence check: builder commit `430ccbdd` is present in local git logs at `.git/logs/HEAD:2184` and `.git/logs/refs/heads/dev:2010`.
- Test integrity: current `TestFromAC_*` assertions are discriminating. I could not obtain a direct `git show`/`git status` diff in this tool surface, so immutability/dirty-tree checks are lower-confidence than ideal.
- No security or data-safety issue was found in the reviewed scope. This task narrows MCP exposure rather than broadening it.

### Deductions
- `-0.03` Could not perform terminal-backed dirty-tree contamination check (`git status --porcelain`) from the available tool surface.
- `-0.02` Could not perform direct commit diff / TestFromAC immutability proof; commit presence was verified via `.git/logs/*` instead.
- `-0.02` Child AC text is slightly stale/ambiguous versus the parent brief’s refined wording for deferred scope stubs.

### Verdict
- PASS
- Confidence: 0.93

### Action
- Advance to docs.

### Post-task Reflection
- Verification-only child tasks can carry stale wording from a parent brief; review should anchor to the latest binding brief text, not the child shorthand alone.
- When direct git diff access is unavailable, `.git/logs/*` is still useful to prove commit presence, but it does not fully replace dirty-tree or immutability evidence.
- The current `TestFromAC_*` suite is strong enough to prove the narrowed 8-tool MCP surface without needing broader module coverage for this task.
[[2026-05-07]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | N/A — accurate | `serve/mcp-knowledge/README.md` `### Tools` lists exactly the 8 active tools; removed tools (`list_entities`, `bookmark_source`, `list_bookmarks`, `update_bookmark_tags`, `consolidate_knowledge`) and scope stubs never appeared there |
| 2 | Module docstrings | Yes | N/A — accurate | Builder pass was verification-only; scope stubs (`import_scope`, `export_scope`, `sync_from_global`, `sync_to_global`) added in prior commit 430ccbdd all have accurate docstrings verified at `server.py:1074`–`:1175` |
| 3 | External attribution | No | N/A | Task body and research doc confirm no external patterns used |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1335-tool-surface-cleanup.md` exists and is linked from task body; follow-up section: "None required" |
| 5 | Diagram maintenance | No | N/A | Doc-index contains no `describes` entries for any diagram matching `mcp-knowledge` files |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | 5 removed tools remain as plain function defs in `server.py`; no IN-scope doc references them as active MCP tools; no orphaned docs |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | IN (docstrings) | Verified — accurate, no edits needed |
| `tests/test_mcp_knowledge_tool_surface_1334.py` | OUT (test file) | No action |
| `.owlbear/research/1335-tool-surface-cleanup.md` | IN (research doc) | Verified — exists, linked, accurate |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1335-*` files existed)
[[2026-05-07]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Only 8 active tools registered | `test_exactly_eight_tools_registered` PASS; commit 430ccbdd; registrations at server.py:792-1194 | PASS |
| Removed from registration (5 tools) | `test_removed_tools_not_registered` PASS; plain function defs remain but no @mcp decorators | PASS |
| 4 scope stubs registered internally | `test_scope_stubs_are_callable_and_not_registered_as_tools` PASS; stubs at server.py:1074-1153 | PASS |
| Scope stubs not exposed to agents | Same test confirms stub names absent from MCP tool list | PASS |
| All 1334 tests pass green | 4/4 passed, exit 0, 1.29s | PASS |

### Test Results
- pytest (task-scoped): 4 passed, 0 failed
- pytest (full suite): 4783 passed, 226 failed (none in task scope; mcp-knowledge failure is pre-existing test_outputschema_541 about schema rendering, unrelated to tool registration)
- ruff: 12 violations, all outside task scope (serve/tools/, serve/knowledge/)

### Commit Integrity
- Commit 430ccbdd present in git log for server.py
- Working tree clean (git status --porcelain: no changes in scope)

### Architect Quality: 4/5
AC lines are specific and verifiable with exact tool names and counts. Minor wording variance between child AC ("registered internally") and parent brief ("exist but are not exposed") had no verification impact.

### Deduction Breakdown
- AC lines without evidence: 0 (all 5 covered) = 0
- Lint violations in scope: 0 = 0
- AC quality score 4 (above 3): 0
- Reviewer evidence section: present and detailed = 0
- Full-suite failures in task scope: 0 = 0

### Confidence: 1.00
### Action: archive