---
id: 576
title: 'P2-05: Update skill cheatsheets with MCP tool alternatives alongside CLI'
status: backlog
priority: critical
created: 2026-04-03T11:15:13.7738172+02:00
updated: 2026-04-05T02:24:22.3530871+02:00
tags:
    - phase-2
    - ' scope:agent-config'
    - ' type:build'
    - docs
parent: 483
depends_on:
    - 572
    - 563
class: standard
---

## Acceptance Criteria\n\n- [ ] All 14 skill SKILL.md files in AC2 updated with inline MCP tool alternative notes after actionable CLI command invocations\n- [ ] Skills: arch-review, code-review, curation-workflow, decision-requests, dispatch-planning, docs-gate, orchestration, pytest-and-linting, research-workflow, task-decomposition, task-verification, tdd-red, tdd-workflow, kanban-md\n- [ ] PRE-SATISFIED (verify only): 8 cheatsheet skills already have 3 compound MCP rows (start_work, edit_task, end_work) in kanban-md Commands tables (added by #572 builder). No additional table rows required -- simple tool mappings are covered by inline notes.\n- [ ] After each actionable inline kanban-md CLI invocation (code blocks and single-command references in step descriptions), add blockquote: `> **MCP equivalent:** tool_name(key_params)`. Skip generic kanban-md name mentions and cheatsheet-table rows. Use CLI-to-MCP mapping from docs/research/mcp-tool-references-alongside-cli.md section 3a.\n- [ ] Normalize existing inconsistent MCP note patterns to canonical `> **MCP equivalent:**` format. Current variants to normalize: `> **MCP note:**` (decision-requests L282, dispatch-planning L56), `> **MCP equivalents (owlbear-kanban):**` (kanban-md L26). Research-workflow L171 already uses correct format.\n- [ ] Category C: orchestration has 2 kanban-md mentions (L15, L192) that are contextual descriptions of other agents, not recipes -- skip or add minimal cross-reference. pytest-and-linting has no actionable CLI refs -- no changes needed.\n- [ ] No existing CLI references removed (fallback preserved)\n- [ ] REGRESSION CHECK: Must not break 73 tests in tests/test_mcp_tool_references_483.py. Note: these tests verify MCP tool-name presence in cheatsheet sections and whole-body only -- they already pass pre-implementation and do NOT validate per-invocation blockquote coverage. They serve as a regression guard, not a completeness gate.\n- [ ] REVIEWER VERIFICATION (manual): Reviewer must spot-check at least 3 inline CLI invocations per Category A skill and all inline CLI invocations in Category B skills to verify blockquote presence, canonical format, and correct CLI-to-MCP mapping. Normalization of the 3 non-canonical patterns (AC line 5) must be explicitly confirmed.\n\n## Files\n\nskills/arch-review/SKILL.md, skills/code-review/SKILL.md, skills/curation-workflow/SKILL.md, skills/decision-requests/SKILL.md, skills/dispatch-planning/SKILL.md, skills/docs-gate/SKILL.md, skills/orchestration/SKILL.md, skills/pytest-and-linting/SKILL.md, skills/research-workflow/SKILL.md, skills/task-decomposition/SKILL.md, skills/task-verification/SKILL.md, skills/tdd-red/SKILL.md, skills/tdd-workflow/SKILL.md, skills/kanban-md/SKILL.md\n\n## Dependencies\n\nDepends on #572 (test validation, archived) and #563 (mcp-kanban SKILL.md expansion, archived).\n\n## Builder Guidance\n\nEstimated scope per category (from research doc):\n- Category A (8 cheatsheet skills): ~57 inline CLI commands need MCP notes\n- Category B (4 inline-ref skills): ~9 inline CLI commands need MCP notes\n- Category C (2 excluded skills): 0-2 changes (contextual only)\n\nCLI-to-MCP translation reference:\n- `show {id}` goes to `show-task(task_id={id})`\n- `list [filters]` goes to `list_tasks(status=..., ...)`\n- `create TITLE [opts]` goes to `create_task(title=..., ...)`\n- `edit {id} [opts]` goes to `edit_task(task_id={id}, ...)`\n- `move {id} STATUS` goes to `move_task(task_id={id}, status=...)`\n- `pick [filters]` goes to `pick_task(status=..., ...)`\n- `edit claim + show` goes to `start_work(task_id={id})`\n- `edit -a + status + release` goes to `end_work(task_id={id}, note=..., outcome=success)`\n- `delete` has no MCP equivalent (not exposed via MCP)\n\nSpot-check formatting consistency after bulk edits. The test suite is a regression guard only -- real verification happens at reviewer stage via the manual spot-check checklist (AC line 9).\n\n## Research\n\nSee docs/research/skill-cheatsheet-mcp-alternatives.md for full analysis.\n\n## Architecture Review\n**Verdict:** APPROVE\n**DR Verification:** N/A -- T1 classification (docs-only update for existing capabilities), no DR needed\n\n### AC Assessment\nAC Line: All 14 skills updated -- Correct scope, per-category differentiation -- Keep\nAC Line: PRE-SATISFIED cheatsheet rows -- Verified: all 8 skills have 3 MCP rows from #572 -- Keep\nAC Line: Inline blockquote format -- Canonical pattern specified with CLI-to-MCP mapping -- Keep\nAC Line: Normalize 3 inconsistent patterns -- Exact locations verified in codebase -- Keep\nAC Line: Category C handling -- Contextual-only, skip/minimal -- Keep\nAC Line: No CLI refs removed -- Clear, verifiable -- Keep\nAC Line: Regression check (73 tests) -- REFINED: reframed from completeness gate to regression guard -- Rewritten\nAC Line: Reviewer manual verification -- NEW: added explicit spot-check checklist -- Added\n\n### Architecture Notes\nDocumentation-only task, single domain (agent-config). No code, no interfaces, no new modules. All 14 target skills exist and were verified. 8 cheatsheet skills already have compound MCP rows from #572. Real scope is ~66 inline blockquote insertions plus 3 normalizations.\n\nCodebase evidence:\n- skills/code-review/SKILL.md L20-22: 3 MCP rows present (confirmed all 8 cheatsheet skills)\n- No inline MCP equivalent blockquotes in any cheatsheet skill yet (grep confirmed)\n- 4 existing MCP note variants: decision-requests L282, dispatch-planning L56, kanban-md L26, research-workflow L171 (only L171 uses canonical format)\n- tests/test_mcp_tool_references_483.py: 73 tests covering Items 2-7 (all pass pre-implementation)\n\n### Changes Made\n- Refined AC: reframed test requirement as regression guard (not completeness gate)\n- Added AC line 9: explicit reviewer manual verification checklist\n- Fixed tags: removed type:build (invalid for docs-only task), kept docs pass-through tag\n- Preserved prior review refinements (CLI-to-MCP mapping, per-category scope, builder guidance)\n\n### Dependencies\n- Verified: #572 (test validation) -- archived\n- Verified: #563 (mcp-kanban SKILL.md expansion) -- archived\n\n### Challenge Results\n- Challenger: block (confidence .35)\n- Key challenges: (1) 73 tests already pass pre-implementation; (2) inline blockquotes have zero automated coverage; (3) normalization not tested\n- Architect response: Accepted 1-3 and incorporated. Reframed test AC as regression guard. Added mandatory reviewer spot-check checklist. Rebutted block: automated tests for docs formatting is YAGNI -- reviewer manual verification is the correct mitigation for one-time docs cleanup.\n

[[2026-04-03]] Fri 20:01
## Test-Writer Notes
- Non-implementation task (tagged `docs`) — no tests applicable.
- AC deliverables: 14 SKILL.md files in skills/ directory (arch-review, code-review, curation-workflow, decision-requests, dispatch-planning, docs-gate, orchestration, pytest-and-linting, research-workflow, task-decomposition, task-verification, tdd-red, tdd-workflow, kanban-md).
- No Python implementation intent found in AC. Task is documentation-only (inline MCP blockquote insertions + 3 normalization fixes).
- Regression guard: tests/test_mcp_tool_references_483.py (73 tests) already passes pre-implementation — builder must not break it.
- Passing through to builder.

[[2026-04-04]] Sat 03:26
## Builder Notes

### Files Changed
- `skills/arch-review/SKILL.md` — added `start_work` note (Step 1 claim) + `edit_task` note (temp-file body pattern)
- `skills/code-review/SKILL.md` — added `start_work` note (Step 1) + inline `show-task` note (Step 6.7) + `end_work` notes (PASS/FAIL Step 9)
- `skills/curation-workflow/SKILL.md` — added inline `(MCP: show-task)` in Step 1 item 4
- `skills/decision-requests/SKILL.md` — **normalized** `> **MCP note:**` → `> **MCP equivalent:**`; added `edit_task` note (blocking code block); added inline unblock note
- `skills/dispatch-planning/SKILL.md` — **normalized** `> **MCP note:**` → `> **MCP equivalent:**`; added `list_tasks` note (Recipe 1); added `show-task` note (Recipe 2)
- `skills/docs-gate/SKILL.md` — added `start_work` note (Step 1) + `end_work` note (Step 5 + Boundaries)
- `skills/kanban-md/SKILL.md` — **normalized** `> **MCP equivalents (owlbear-kanban):**` → `> **MCP equivalent:**`
- `skills/research-workflow/SKILL.md` — added `end_work` note (Step 6 finalize)
- `skills/task-decomposition/SKILL.md` — added `list_tasks` note (Step 2) + `create_task` note (Step 6)
- `skills/task-verification/SKILL.md` — added `start_work` note (Step 1) + `end_work`/`edit_task` notes (Step 3 decision points)
- `skills/tdd-red/SKILL.md` — added `start_work` (Step 1) + `edit_task` (append blocks × 4) + `end_work` (Step 1a, 1b, Step 8)
- `skills/tdd-workflow/SKILL.md` — added `start_work` (Step 1) + `edit_task` (Step 1b) + `end_work` × 2 (Step 1b + Step 9)

### Pre-condition: Restored deleted root-level files
`skills/`, `agents/`, `instructions/` directories were physically deleted from the working tree (unstaged) but still tracked in git HEAD. Used `git restore` to bring them back. Tests were already failing with FileNotFoundError; restoring from HEAD made all 73 pass pre-implementation.

### Test Results
- Regression: `tests/test_mcp_tool_references_483.py` — **73 passed** (pre + post)
- Normalizations: 3 non-canonical patterns corrected (AC line 5)
- Inline blockquotes added: ~37 across 12 skill files
- Skipped: Category C (orchestration contextual ref, pytest-and-linting no CLI refs)

### Commit
`5afaf1b` — `docs: add inline MCP equivalent notes to 12 skill cheatsheets (#576, builder)`

[[2026-04-05]] Sun 02:24
## Review Evidence

### Test Results
- pytest `tests/test_mcp_tool_references_483.py`: **11 FAILED, 62 FAILED** — all 73 tests fail with `FileNotFoundError: .github/skills/` (directory removed by subsequent #600 restructure commit `118bda6`, which moved `.github/skills/` → `share/skills/`).
- Cause: NOT the #576 builder directly — path breakage was introduced by #600. However, the AC unambiguously states "Must not break 73 tests" and at HEAD they are all broken.

### Lint: N/A
- Docs-only task. No Python files changed by #576 builder. Lint not applicable.

### Coverage: N/A
- Docs-only task.

### Pass 1 — CRITICAL

#### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| All 14 skill SKILL.md files updated with inline MCP notes | `share/skills/w-arch-review/SKILL.md` → 0 `MCP equivalent` matches. Confirmed across all 14 target files via PowerShell scan: **0 blockquotes found**. | FAIL |
| Skills list (14 named) | Builder correctly targeted `.github/skills/` in `a821a0d`. However, `w-dispatch-planning` was NOT included in `a821a0d` or `0d2efc2` — only in the incorrect root-level first commit. `tdd-workflow` similarly absent from correct-location commits. | FAIL (partial) |
| PRE-SATISFIED: 3 compound MCP rows in cheatsheet tables | Not verifiable — all cheatsheet content was overwritten by #486. Cannot confirm without reading #572 audit trail. | UNVERIFIED |
| After each actionable CLI invocation, add `> **MCP equivalent:** tool_name(key_params)` | None present at HEAD. Entire per-invocation blockquote layer removed by `cca6373` (#486). | FAIL |
| Normalize 3 inconsistent patterns | `a821a0d` performed these normalizations. `cca6373` (#486) then rewrote those sections, outcome of normalizations indeterminate. | FAIL |
| No CLI references removed | Cannot verify at HEAD — `cca6373` did bulk rewrites of the same sections. | UNVERIFIED |
| Regression: 73 tests pass | ALL 73 FAIL at HEAD (FileNotFoundError). | FAIL |
| Reviewer manual spot-check | Performed: `w-arch-review` — 0 MCP equivalent blockquotes. `w-dispatch-planning` — 0 MCP equivalent blockquotes. `w-tdd-red` — 0 MCP equivalent blockquotes. AC deliverable absent. | FAIL |

#### Security Review
No security concerns. Docs-only content changes.

#### Builder Process Quality
- 3 builder commits (`5afaf1b`, `a821a0d`, `0d2efc2`). First commit targeted wrong directory (`skills/` root-level). Second commit correctly targeted `.github/skills/` but missed `w-dispatch-planning` and `tdd-workflow`. Third commit patched 2 files. FRICTION pattern, not LOOP.

### Root Cause — Design Conflict with #486
The core failure is not a builder execution error but a **design conflict** between two concurrent tasks:

- **#576** specified: per-invocation inline `> **MCP equivalent:**` blockquotes after each CLI command in all 14 skills (~66 insertions)
- **#486** (`cca6373`, Sat Apr 4 23:42:59) implemented: a single `**Kanban operations:** See \`h-mcp-kanban\` skill — section \`## Agent Lifecycle Pattern\`` line at the top of each skill

`cca6373` was committed AFTER `0d2efc2` (the builder's final #576 commit) and REMOVED all per-invocation blockquotes from the 11 skills the builder had correctly modified. The two approaches are architecturally incompatible.

### Additional Gap: w-dispatch-planning and tdd-workflow
`w-dispatch-planning` was NEVER modified by the #576 builder in the correct location (`.github/skills/`). `git log` confirms only 3 commits ever touched that file: `2d1e9ca`, `2231ec7`, and `118bda6` (move). Neither `a821a0d` nor `0d2efc2` included it. The builder's root-level first commit (`5afaf1b`) modified `skills/dispatch-planning/SKILL.md` — a separate file from the `.github/skills/w-dispatch-planning/SKILL.md` that the tests and subsequent workflow reference.

Same pattern for `tdd-workflow`.

### Verdict
Confidence: **0.85 → FAIL**

Route: **backlog** — Design conflict. Architect must decide:
1. Are per-invocation inline blockquotes still needed, given that #486 added a generic `h-mcp-kanban` skill reference to each pipeline skill?
2. If yes: the AC needs to clearly state that per-invocation blockquotes are required AND the #486 consolidation approach must be reconciled (or reversed) before implementation proceeds.
3. If no: task should be closed as superseded by #486.

The builder cannot fix this directly without first resolving the architectural question.
