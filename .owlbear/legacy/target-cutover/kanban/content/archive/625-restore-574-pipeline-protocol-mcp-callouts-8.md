---
id: 625
title: 'Restore #574 pipeline protocol MCP callouts — 8 failing tests'
status: archived
priority: medium
created: 2026-04-05T07:41:30.2992757+02:00
updated: 2026-04-05T17:38:56.4404678+02:00
started: 2026-04-05T17:38:56.4404678+02:00
completed: 2026-04-05T17:38:56.4404678+02:00
tags:
    - phase-2
    - ' scope:agent-config'
    - ' type:fix'
class: standard
---

## Acceptance Criteria

- [ ] All 8 tests in tests/test_mcp_tool_references_574.py pass
- [ ] Inline MCP tool references added to share/skills/r-pipeline-protocol/SKILL.md sections:
  - Channel B: `append_body`, `timestamp` parameter names (in `edit_task` reference)
  - Resolved decision pre-flight: `show_task`
  - Follow-up task quality: `create_task`
  - Blocking convention: `unblock` (as `edit_task(unblock=True)`)
  - Handoff: `edit_task` (with `append_body` parameter)
  - Reading rules: `show_task`
- [ ] Tool references use inline format matching existing patterns in the file (e.g., `start_work` reference at L29, `end_work(outcome="block")` at L176), NOT `> **MCP equivalent:**` blockquotes (removed by #486 DRY consolidation)

## Context

Task #574 (archived) added MCP tool references to the pipeline protocol. During v2 reorganization, the file moved to share/skills/r-pipeline-protocol/SKILL.md but tool references for 6 sections were not carried over. The #574 acceptance tests (8 assertions) now fail.

## Files

share/skills/r-pipeline-protocol/SKILL.md, tests/test_mcp_tool_references_574.py

## Research

From .owlbear/research/575-agent-mcp-lifecycle-audit.md section 3d.

[[2026-04-05]] Sun 11:11
## Research
- Research doc: .owlbear/research/625-restore-pipeline-mcp-callouts.md
- Sources: 4 studied, 3 high-relevance (.95)
- Recommendation: Restore 6 tool reference insertions (confidence: .95)
- Follow-up tasks created: none (task #625 is itself the implementation task)
- Decision requests: none
- Tier: T1 — autonomous (restoration of lost content, no new capability)

## Challenge Results (Research Phase)
- Challenger: FALLBACK — trivial restoration, no recommendation trade-off to challenge
- Confidence in original: .95

## Builder Notes (Architect-refined)
Add inline MCP tool references to 6 sections in `share/skills/r-pipeline-protocol/SKILL.md`.

**Format constraint:** Use inline parenthetical or sentence-level references matching the file's existing patterns:
- L29: `...see the h-mcp-kanban skill (start_work tool: atomic claim + show).`
- L176: `...calls end_work(outcome="block") to release...`

**Do NOT use `> **MCP equivalent:**` blockquotes.** #486 deliberately removed this pattern from all skills as DRY consolidation (audited at 1.00). See .owlbear/research/576-skill-cheatsheet-mcp-superseded.md section 3.

**6 insertions — each adds 1-2 sentences or a parenthetical mentioning the tool name:**
1. **Resolved Decision Pre-flight** (after item 4): `show_task(task_id="{id}")` for reading task body to check for decision sections
2. **Follow-up Task Quality** (after last bullet): `create_task` for creating follow-up tasks at backlog
3. **Channel B — Task Body** (expand existing h-mcp-kanban pointer): add `edit_task(append_body="...", timestamp=True)` parameter syntax
4. **Reading Rules** (after last bullet): `show_task(task_id="{id}")` for reading full task bodies
5. **Blocking Convention** (after end_work mention): `edit_task(block="reason")` / `edit_task(unblock=True)` for setting/clearing block status
6. **Handoff** (after last line): `edit_task(append_body="...")` for appending handoff notes

[[2026-04-05]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One task: add inline tool references to one file |
| Interface clarity | PASS | AC lists all 6 sections and required tool names |
| Dependency correctness | PASS | No dependencies needed; target file and tests exist |
| Module layering | PASS | Documentation edit only, no code module impact |
| TDD compliance | PASS | Tests exist in test_mcp_tool_references_574.py (8 tests, all failing on HEAD) |
| KISS/YAGNI | PASS | Minimal scope: 6 inline insertions of 1-2 lines each |
| Premise challenge | PASS | Content present before (commit 724062e), lost in reorg, tests confirm gap |
| Pattern consistency | REFINE | Builder Notes directed blockquote format removed by #486 DRY consolidation (audited 1.00). Rewritten to require inline style matching start_work (L29) and end_work (L176). |
| Security surface | PASS | No system boundary changes |
| Single domain | PASS | agent-config domain only |

### Key Finding: Format Conflict with #486 DRY Consolidation
Zero `> **MCP equivalent:**` blockquotes in any current skill file (grep verified). Research #576 confirms #486 removed 39 inline MCP blockquotes from 11 skills (audited 1.00). r-pipeline-protocol already uses inline tool refs: `start_work` (L29), `end_work` (L176). Tests check string presence, not blockquote format.

Resolution: AC line 3 rewritten. Builder Notes revised to prohibit blockquotes.

### AC Refinements Applied
- AC line 3: was "Callout format matches existing MCP notes pattern" (ambiguous, no such pattern exists). Now specifies inline format matching start_work/end_work patterns, NOT blockquotes
- Builder Notes: replaced "Restore 6 MCP equivalent blocks" directive with inline format constraint and #486 evidence
- Removed duplicate Channel B entry from AC line 2

### Challenge Results
- Challenger: SKIP (REFINE verdict, mandatory only for APPROVE)
- Post-refinement: all criteria PASS after AC tightening

### Verdict: REFINE then APPROVE
### Action: AC refined for precision, Builder Notes revised to prohibit removed blockquote format, task advanced to todo

[[2026-04-05]] Sun 12:15
Architecture review complete. AC refined: replaced ambiguous format constraint with explicit inline-style requirement (matching existing start_work/end_work patterns). Builder Notes rewritten to prohibit blockquote format removed by #486 DRY consolidation. All 10 criteria pass after refinement.

[[2026-04-05]] Sun 13:09
## Test-Writer Notes

- **Pass-through:** AC targets only `share/skills/r-pipeline-protocol/SKILL.md` (markdown file — no Python interfaces to test).
- **Existing test specification:** `tests/test_mcp_tool_references_574.py` — written during task #574, covers all 6 AC items.
- **8 tests, all FAIL** — verified with pytest on HEAD:
  - `test_channel_b_has_append_body_param` — FAIL
  - `test_channel_b_has_timestamp_param` — FAIL
  - `test_section_has_mcp_tool[resolved-decision->show_task]` — FAIL
  - `test_section_has_mcp_tool[followup-task-quality->create_task]` — FAIL
  - `test_section_has_mcp_tool[channel-b->append_body]` — FAIL
  - `test_section_has_mcp_tool[blocking-convention->unblock]` — FAIL
  - `test_section_has_mcp_tool[handoff->edit_task]` — FAIL
  - `test_section_has_mcp_tool[reading-rules->show_task]` — FAIL
- **AC coverage:** All 6 AC sections mapped to failing tests. No new tests needed.
- **Builder:** Edit `share/skills/r-pipeline-protocol/SKILL.md` — add 6 inline tool references (see Builder Notes). Run `uv run pytest tests/test_mcp_tool_references_574.py -v` to verify all 8 pass.

[[2026-04-05]] Sun 13:24
## Builder Notes

### Files Changed
- `share/skills/r-pipeline-protocol/SKILL.md` — 6 inline MCP tool references added (+10 lines, -2 lines)

### Test Results
- `tests/test_mcp_tool_references_574.py`: **8 passed** (0 failed)
- RED verified: all 8 failed before implementation
- GREEN confirmed: all 8 pass after 6 targeted insertions

### Lint Status
- `ruff check tests/test_mcp_tool_references_574.py`: clean

### Evidence Summary
6 inline tool references added to match existing patterns (`start_work` at L29, `end_work` at L176):
1. **Resolved Decision Pre-flight**: `show_task(task_id="{id}")` after item 4
2. **Follow-up Task Quality**: `create_task(title="...", status="backlog", ...)` after last bullet
3. **Channel B**: expanded to `edit_task(append_body="...", timestamp=True)` inline
4. **Reading Rules**: `show_task(task_id="{id}")` after last bullet
5. **Blocking Convention**: `edit_task(block="reason")` / `edit_task(unblock=True)` after block list
6. **Handoff**: `edit_task(task_id="{id}", append_body="...")` appended inline

### Commit
`d9516ff` — fix(agent-config): restore #574 MCP tool refs to r-pipeline-protocol SKILL.md (#625)

[[2026-04-05]] Sun 15:08
## Review Evidence

### Tests
`uv run pytest tests/test_mcp_tool_references_574.py -v` — **8 passed, 0 failed** (0.08s).
All 8 `TestFromAC_PipelineProtocolMcpPointers` tests pass independently. Builder self-report confirmed.

### Lint
`ruff check tests/test_mcp_tool_references_574.py share/skills/r-pipeline-protocol/SKILL.md` — **clean**.

### Coverage
Pure documentation task (single Markdown file). No Python modules changed; coverage metric not applicable.

### Commit Integrity
`d9516ff` — `fix(agent-config): restore #574 MCP tool refs to r-pipeline-protocol SKILL.md (#625)`.
1 file changed, +10 lines, -2 lines. Matches builder's claim exactly.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| All 8 tests in test_mcp_tool_references_574.py pass | 8 passed, 0 failed (verified independently) | PASS |
| Channel B: `append_body` + `timestamp` parameter names | Diff L114: `edit_task(append_body="...", timestamp=True)` added inline | PASS |
| Resolved decision pre-flight: `show_task` | Diff L47: `show_task(task_id="{id}")` added | PASS |
| Follow-up task quality: `create_task` | Diff L96: `create_task(title="...", status="backlog", ...)` added | PASS |
| Blocking convention: `unblock` | Diff L186: `edit_task(task_id="{id}", unblock=True)` added | PASS |
| Handoff: `edit_task` with `append_body` | Diff L200: `edit_task(task_id="{id}", append_body="...")` added inline | PASS |
| Reading rules: `show_task` | Diff L135: `show_task(task_id="{id}")` added | PASS |
| Inline format (not `> **MCP equivalent:**` blockquotes) | Zero blockquote pattern matches in diff; all 6 are sentence-level or parenthetical inline insertions | PASS |

### TestFromAC Integrity
No `TestFromAC_*` tests modified by the builder. All 8 tests preserved exactly as written by test-writer. PRESERVED.

### Test Quality
ADEQUATE. String-presence assertions within section-scoped extraction are appropriate for documentation tasks. Section isolation prevents false positives from tool names appearing elsewhere. Parametrized IDs are descriptive (`resolved-decision->show_task`, etc.). Would catch misplacement (wrong section) and absence.
**Note:** Tests don't verify format constraint (inline vs. blockquote). A negative assertion like `assert "> **MCP equivalent:**" not in section` would further harden AC 3 — noted for future test writers, not a failing defect since implementation is correct and verified by diff.

### Security
No security surface: pure documentation edit. No system boundary changes, no new dependencies. PASS.

### Deductions
- None (format note is informational only).

### Verdict
Confidence: **.95** → **PASS #625 → docs**

[[2026-04-05]] Sun 15:32
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Pure markdown skill restoration; copilot-instructions.md has no r-pipeline-protocol tool-name entries to update |
| 2 | Module docstrings | No | N/A | Zero Python files changed — single .md file edit only |
| 3 | External attribution | No | N/A | Content sourced from git history (commit 724062e), no external repos or articles |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | .owlbear/research/625-restore-pipeline-mcp-callouts.md exists, linked in task body; follow-up tasks: none required (task is itself the implementation) |

### Files Updated
None — no documentation file changes required.

### Scratch Files
None — no `.owlbear/scratch/625-*` files found.

## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| All 8 tests in test_mcp_tool_references_574.py pass | 8 passed, 0 failed (0.09s) - verified independently | PASS |
| Channel B: append_body + timestamp parameter names | SKILL.md L114: edit_task(append_body=..., timestamp=True) inline | PASS |
| Resolved decision pre-flight: show_task | SKILL.md L47: show_task(task_id={id}) inline | PASS |
| Follow-up task quality: create_task | SKILL.md L96: create_task(title=..., status=backlog, ...) inline | PASS |
| Blocking convention: unblock | SKILL.md L186: edit_task(task_id={id}, unblock=True) inline | PASS |
| Handoff: edit_task with append_body | SKILL.md last line: edit_task(task_id={id}, append_body=...) inline | PASS |
| Reading rules: show_task | SKILL.md L135: show_task(task_id={id}) inline | PASS |
| Inline format (not blockquotes) | Zero blockquote patterns; all 6 are sentence-level inline refs | PASS |

### Test Results
- pytest (task-scoped): 8 passed, 0 failed
- pytest (full suite): 2878 passed, 432 failed (pre-existing systemic), 18 skipped, 0 in task scope
- ruff: All checks passed

### Architect Quality: 5/5
AC specific and verifiable. Format constraint refined mid-process. Zero builder improvisation.

### Deduction Breakdown
- AC lines without evidence: 0
- Lint violations: 0
- AC quality: 5/5 (no deduction)
- Reviewer evidence: present, detailed, PASS at .95
- Full-suite failures in task scope: 0

### Confidence: .98
### Action: archive

[[2026-04-05]] Sun 17:38
8/8 tests pass, full suite 0 failures in scope, ruff clean, AC quality 5/5, confidence .98
