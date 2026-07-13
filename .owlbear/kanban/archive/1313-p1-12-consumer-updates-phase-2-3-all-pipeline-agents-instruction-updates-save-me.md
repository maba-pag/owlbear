---
id: 1313
title: 'P1-12: Consumer updates Phase 2-3 — All pipeline agents + instruction updates
  (save_memory, recall_memory rollout)'
status: archived
priority: medium
created: 2026-05-04T01:32:27.397472+00:00
updated: 2026-05-05T17:21:09.833521+00:00
tags:
- phase-2
- scope:agents
- memory
- mcp
parent: 1301
depends_on:
- 1312
- 1308
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1301

## Acceptance Criteria

- [ ] Pipeline agents (researcher, architect, builder, reviewer, auditor, doc-writer, orchestrator, planner, test-writer, test-curator): `vscode/memory` replaced with `ob-memory/save_memory, ob-memory/recall_memory` in tools: array (td:0)
- [ ] test-writer and test-curator: `'ob-memory/*'` wildcard narrowed to explicit `ob-memory/save_memory, ob-memory/recall_memory` (td:0)
- [ ] Subagents (challenger, code-reader, quality-runner): `vscode/memory` removed, no ob-memory tools added (td:0)
- [ ] r-pipeline-protocol/SKILL.md Knowledge Pre-flight (~L40-50): `query_memory()` → `recall_memory(agent="{agent_name}")` (td:0)
- [ ] r-pipeline-protocol/SKILL.md Post-task Reflection (~L248-264): `store_learning` with `scope_agents` → `save_memory` with `source_agent`; remove dual-write/fallback framing, keep single-path `save_memory` call (td:0)
- [ ] Negative grep over the 13 in-scope agent files + r-pipeline-protocol/SKILL.md only: none references `query_memory`, `store_learning`, `add_memory`, `update_entry`, `delete_entry`, `scope_agents`, `vscode/memory`, or `'ob-memory/*'` (td:1)

## Scope

- In: 13 agent.md files (10 pipeline + 3 subagents listed above), r-pipeline-protocol/SKILL.md
- Out: ideation agents (10+, retain vscode/memory, separate follow-up), memory-curator (done in #1312), review prompt (#1314), MCP server code, h-memory-structure/SKILL.md (tracks broader migration state — separate update)

## Builder Guidance

- `save_memory` signature: `title` (str), `content` (str), `categories` (list[MemoryCategory]), `confidence` (float), `source_agent` (str) — all required
- `recall_memory` signature: `agent` (str, required), `categories` (optional), `limit` (optional, default 20)
- Post-task Reflection rewrite: replace dual-write block with single `save_memory(source_agent="{agent_name}", ...)` pattern; remove file-based fallback to `/memories/repo/inbox/`
- `h-memory-structure/SKILL.md` still references dual-write — that's intentionally OUT OF SCOPE (tracks broader migration state)
- Ideation agents in the same directory retain `vscode/memory` — do NOT touch them

## Research

Research doc: `.owlbear/research/consumer-updates-memory-rollout.md`

**Key findings:**
- 13 agent files need editing: 10 pipeline agents (swap `vscode/memory` → `ob-memory/save_memory, ob-memory/recall_memory`) + 3 subagents (remove `vscode/memory`, don't add ob-memory)
- test-writer and test-curator: narrow `'ob-memory/*'` wildcard to explicit pair (minimal privilege)
- `agent-common.instructions.md` doesn't exist — AC items target `r-pipeline-protocol/SKILL.md` directly
- Two stale tool names in r-pipeline-protocol: `query_memory()` → `recall_memory(agent=...)`, `store_learning` → `save_memory`
- `save_memory` takes `source_agent` (str), not `scope_agents` (list)
- T1 Autonomous — mechanical rollout, confidence .92
[[2026-05-05]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One job: roll out save_memory/recall_memory to pipeline consumers |
| Interface clarity | PASS | AC specifies exact files, tool names, signatures in Builder Guidance |
| Dependency correctness | PASS | #1312, #1308 archived (complete); MCP tools exist |
| Module layering | PASS | No code changes — agent config + skill text only |
| TDD compliance | PASS | td:1 regression test for negative grep assertion |
| KISS/YAGNI | PASS | Minimal mechanical replacement |
| Premise challenge | PASS | Required to complete Brief-driven memory MCP migration (D32, D37) |
| Pattern consistency | PASS | Follows existing tools: array format conventions |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | Memory tooling domain only |

### Challenge Results
- Challenger: reconsider (confidence 0.38)
- Issues raised: (1) AC 6 grep scope contradicted exclusion of ideation agents, (2) missing ob-memory/* in banned patterns, (3) semantic mismatch concern re: store_learning→save_memory, (4) h-memory-structure still documents dual-write
- Architect response: Accepted items 1-2 (fixed AC 6 scope + added ob-memory/* to grep). Rebutted item 3 — migration is Brief-decided (D32/D37), not an accidental rename; protocol text update is the documented next step. Rebutted item 4 — h-memory-structure tracks broader migration state, explicitly out of scope with follow-up noted.

### Test Depth
- Max depth: 1 (AC 6 only)
- Test-writer: PROCEED (write single scanning test for negative grep assertion)

### Verdict: APPROVE
### Action Taken: Refined AC from 6 vague items to 6 precise items with exact file lists, tool signatures, scoping boundary, and builder guidance. Fixed grep scope contradiction. Advanced to todo.
[[2026-05-05]]
## Test-Writer Notes
- Test file: tests/test_memory_tool_rollout_1313.py
- Classes: TestFromAC_MemoryToolMigration
- Tests per category: happy 0, edge 0, error 0, boundary 0 (td:1 — single regression smoke test)
- Total: 1 test, all FAIL
- ruff: clean

AC coverage:
| AC | Term | Test |
|----|------|------|
| AC1 (td:0) | vscode/memory → save_memory/recall_memory in pipeline agents | skipped |
| AC2 (td:0) | test-writer/test-curator ob-memory/* narrowed | skipped |
| AC3 (td:0) | Subagents: vscode/memory removed, no ob-memory added | skipped |
| AC4 (td:0) | r-pipeline-protocol Knowledge Pre-flight: query_memory→recall_memory | skipped |
| AC5 (td:0) | r-pipeline-protocol Post-task Reflection: store_learning→save_memory | skipped |
| AC6 (td:1) | Negative grep: no banned terms in 14 in-scope files | test_no_banned_terms_in_in_scope_files |

Failure evidence: 13 agent files contain `vscode/memory`; test-writer.agent.md and test-curator.agent.md also contain `'ob-memory/*'`; r-pipeline-protocol/SKILL.md contains `query_memory`, `store_learning`, `scope_agents`. All violations surface in the assertion message.
[[2026-05-05]]
## Builder Notes
- Implementation: updated 13 in-scope agent files and `share/skills/r-pipeline-protocol/SKILL.md` to complete memory rollout.
- Tool migration applied:
  - Pipeline agents (10): replaced `vscode/memory` with `ob-memory/save_memory` and `ob-memory/recall_memory`.
  - test-writer + test-curator: removed wildcard `'ob-memory/*'` and kept explicit pair only.
  - Subagents (3): removed `vscode/memory` and did not add ob-memory tools.
- Protocol updates applied in `share/skills/r-pipeline-protocol/SKILL.md`:
  - Knowledge Pre-flight now uses `recall_memory(agent="{agent_name}")`.
  - Post-task Reflection now uses single-path `save_memory(..., source_agent="{agent_name}")` guidance; dual-write/fallback wording removed.
- Tests: quality-runner scoped run passed `1` / failed `0` (`tests/test_memory_tool_rollout_1313.py::TestFromAC_MemoryToolMigration::test_no_banned_terms_in_in_scope_files`).
- ruff: clean on scoped lint path (`tests/test_memory_tool_rollout_1313.py`).
- Coverage: not requested for this td:1 smoke regression task.
- Commit: `3b15bcf0` — `feat: migrate pipeline memory tools to save/recall APIs (#1313, builder)`.

Post-task reflection:
- Problem faced: broad workspace had unrelated modified kanban files; staging had to be tightly scoped.
- Workaround: staged exact file list and verified with `git diff --cached --name-only` before commit.
- Pattern discovered: memory migration required both tool-list updates and protocol text changes to satisfy grep-based guard tests.
- Quality gap: `start_work` response did not reflect claim state (`claimed: false`) despite no error; proceeded with caution under existing protocol behavior.
[[2026-05-05]]
## Review Evidence
### Test Results
- quality-runner scoped pass: pytest `1 passed, 0 failed` on `tests/test_memory_tool_rollout_1313.py`.
- quality-runner lint pass: `ruff clean` on `tests/test_memory_tool_rollout_1313.py`.
- Coverage: `N/A` for this task. The changed surface is agent/skill markdown, and the task owns no runtime module to measure.
- AC6 proof is discriminating: banned terms are enumerated at `tests/test_memory_tool_rollout_1313.py:47`, the exact in-scope file list is built at `tests/test_memory_tool_rollout_1313.py:59`, and the assertion scans every file/term pair at `tests/test_memory_tool_rollout_1313.py:80-102`.

### Scope / Provenance Evidence
- Builder commit existence confirmed from reflogs: `.git/logs/refs/heads/dev:1849` and `.git/logs/HEAD:2009` both record `3b15bcf025c1e2f1d98728f9ded351cfcbb7cd61` with subject `feat: migrate pipeline memory tools to save/recall APIs (#1313, builder)`.
- Prior task test commit exists at `.git/logs/refs/heads/dev:1848` and `.git/logs/HEAD:2007` with subject `test: add failing tests for memory tool rollout (#1313, test-writer)`.
- Review scope reconstructed from AC + builder notes + live file inspection: 10 pipeline agent files, 3 subagent files, and `share/skills/r-pipeline-protocol/SKILL.md`.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Pipeline agents replace `vscode/memory` with `ob-memory/save_memory, ob-memory/recall_memory` | `share/agents/researcher.agent.md:8`, `share/agents/architect.agent.md:8`, `share/agents/builder.agent.md:9`, `share/agents/reviewer.agent.md:9`, `share/agents/auditor.agent.md:8`, `share/agents/doc-writer.agent.md:9`, `share/agents/orchestrator.agent.md:7`, `share/agents/planner.agent.md:8`, `share/agents/test-writer.agent.md:9`, `share/agents/test-curator.agent.md:9` all contain the explicit pair; exact-file banned-term greps over those 10 files returned no `vscode/memory` matches | td:0 direct review | PASS |
| test-writer and test-curator narrow `'ob-memory/*'` to the explicit pair | `share/agents/test-writer.agent.md:9` and `share/agents/test-curator.agent.md:9` contain only `ob-memory/save_memory` and `ob-memory/recall_memory`; exact-file banned-term greps returned no `'ob-memory/*'` matches | td:0 direct review | PASS |
| Subagents remove `vscode/memory` and add no ob-memory tools | `share/agents/challenger.agent.md:8`, `share/agents/code-reader.agent.md:8`, and `share/agents/quality-runner.agent.md:8` show tool arrays with no memory tools; exact-file banned-term greps returned no `vscode/memory` matches in those files | td:0 direct review | PASS |
| `r-pipeline-protocol` Knowledge Pre-flight uses `recall_memory(agent="{agent_name}")` | `share/skills/r-pipeline-protocol/SKILL.md:44` contains `recall_memory(agent="{agent_name}")`; exact-file banned-term grep returned no `query_memory` matches | td:0 direct review | PASS |
| `r-pipeline-protocol` Post-task Reflection uses single-path `save_memory` with `source_agent`; dual-write / fallback framing removed | `share/skills/r-pipeline-protocol/SKILL.md:252` contains `save_memory` with `source_agent="{agent_name}"`; live read of `share/skills/r-pipeline-protocol/SKILL.md:248-256` shows only single-path guidance in the section and no dual-write wording | td:0 direct review | PASS |
| Negative grep over 13 in-scope agent files + `r-pipeline-protocol/SKILL.md` contains none of the banned terms | quality-runner: `1 passed, 0 failed`; test implementation at `tests/test_memory_tool_rollout_1313.py:47`, `:59`, and `:80-102` scans the exact 14-file scope for `query_memory`, `store_learning`, `add_memory`, `update_entry`, `delete_entry`, `scope_agents`, `vscode/memory`, and `'ob-memory/*'`; reviewer exact-file greps found no matches in any in-scope file | `tests/test_memory_tool_rollout_1313.py::TestFromAC_MemoryToolMigration::test_no_banned_terms_in_in_scope_files` | PASS |

### Critical Checks
- Test-writer audit: PASS. AC6 has a discriminating assertion that would fail on any remaining banned term. AC1-AC5 are `td:0` and are directly satisfied by file inspection.
- Test integrity: PASS with deduction. No evidence in the live task test of weakened or removed `TestFromAC` assertions. Separate test-writer and builder commits are present in reflogs, but per-commit file diff was unavailable during review.
- Test quality: ADEQUATE. The task test uses exact file enumeration, exact banned-term enumeration, and enumerated violation output; no lazy assertions.
- Security review: PASS. Scope is agent/skill markdown configuration only; no new runtime boundary, dependency, or secret-handling change observed.
- Data safety: PASS. No persistence, concurrency, or unbounded-input logic changed.
- Necessity check: N/A. No new dependency/integration/tool added.
- Builder process quality: CLEAN. One builder section; no prior `## Review Evidence` section present in the task body.

### Deductions
- `-0.03` Could not complete an independent git diff / dirty-tree contamination check because the git-audit subagent failed with a service disruption error.
- `-0.02` TestFromAC immutability verification is slightly lower-confidence without direct per-commit file ownership evidence.

### Verdict
- PASS
- Confidence: `0.93`

### Action
- Advance to docs.
[[2026-05-05]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | All changed files are agent-executable (`.agent.md`, `SKILL.md`) — OUT of scope. No IN-scope prose doc (README, setup guide, share/README) references the tool array details changed. |
| 2 | Module docstrings | No | N/A | No `.py` files modified. |
| 3 | External attribution | No | N/A | Task is a mechanical migration within the existing MCP tool framework; no new external patterns sourced. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/consumer-updates-memory-rollout.md` exists and is linked from task body. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/pipeline.excalidraw` — `describes: share/skills/r-pipeline-protocol/**, share/agents/*.agent.md` — matched. Updated footer from `c7aa298c` → `89641691`. `share/diagrams/project-overview.excalidraw` — `describes: share/**` — matched. Updated footer from `09e060d4` → `89641691`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. No IN-scope orphaned docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| share/agents/*.agent.md (×13) | OUT | Agent-executable — no edit |
| share/skills/r-pipeline-protocol/SKILL.md | OUT | Agent-executable SKILL.md — no edit |
| tests/test_memory_tool_rollout_1313.py | OUT | Test file — no edit |
| share/diagrams/pipeline.excalidraw | IN | Footer updated |
| share/diagrams/project-overview.excalidraw | IN | Footer updated |
| .owlbear/research/consumer-updates-memory-rollout.md | IN | Verified (exists, linked) |

### Files Updated
- share/diagrams/pipeline.excalidraw (footer: c7aa298c → 89641691)
- share/diagrams/project-overview.excalidraw (footer: 09e060d4 → 89641691)

### Commit
`7fd18c70` — docs: update diagram footers for memory tool rollout (#1313, doc-writer)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found (no `.owlbear/scratch/1313-*` files existed)
[[2026-05-05]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Pipeline agents swap vscode/memory to ob-memory pair | researcher.agent.md:8, challenger confirmed no memory tools; reviewer mapped all 10 files | PASS |
| AC2: test-writer/test-curator narrow ob-memory/* to explicit pair | test-writer.agent.md:9, test-curator.agent.md:9 confirmed explicit pair only | PASS |
| AC3: Subagents remove vscode/memory, no ob-memory added | challenger.agent.md:8 tools array has no memory tools | PASS |
| AC4: Knowledge Pre-flight uses recall_memory(agent=...) | r-pipeline-protocol/SKILL.md:44 confirmed | PASS |
| AC5: Post-task Reflection uses save_memory with source_agent, no dual-write | r-pipeline-protocol/SKILL.md:252 confirmed single-path save_memory | PASS |
| AC6: Negative grep clean over 14 in-scope files | test_memory_tool_rollout_1313.py PASSED (1 passed, 0 failed) | PASS |

### Test Results
- pytest full suite: 198 failed, 4605 passed, 4 skipped (34.05s)
- Task-scoped test: 1 passed, 0 failed
- All 198 failures are in unrelated modules (kanban engine, memory engine, MCP servers, cockpit). Task changed only .agent.md and SKILL.md markdown; no Python source modified.
- ruff: N/A (no Python source in task scope; reviewer confirmed clean on test file)

### Commit Integrity
- Builder: 3b15bcf0 feat: migrate pipeline memory tools to save/recall APIs (#1313, builder)
- Doc-writer: 7fd18c70 docs: update diagram footers for memory tool rollout (#1313, doc-writer)
- Both confirmed via git log --oneline

### Architect Quality: 4/5
Precise AC with exact file lists, tool signatures, and grep patterns. Minor initial scope contradiction in AC6 caught and fixed by challenger during arch review. Builder Guidance comprehensive with parameter signatures. Final AC was specific and verifiable.

### Deduction Breakdown
- AC lines without evidence: 0 (all 6 verified)
- Lint violations: 0 (N/A, no Python source)
- AC quality <=3: NO (score 4)
- Missing reviewer evidence: NO (detailed, 6 AC lines mapped)
- Full-suite failures in task scope: 0

### Confidence: .98
### Action: archive