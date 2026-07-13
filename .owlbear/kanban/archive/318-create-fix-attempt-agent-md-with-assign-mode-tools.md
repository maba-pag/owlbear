---
id: 318
title: Create fix-attempt.agent.md with assign-mode tools
status: archived
priority: medium
created: 2026-03-30 20:38:16.829750+02:00
updated: 2026-04-04 19:48:51.749520+02:00
started: 2026-04-04 19:48:51.749520+02:00
completed: 2026-04-04 19:48:51.749520+02:00
tags:
- scope:agents
- phase-2
- agent
class: standard
archival_reason: completed
archival_refs: []
---

AC:
1. agents/fix-attempt.agent.md with persona, tools (assign: 9 tools - builder tools minus kanban), workflow
2. Frontmatter: user-invocable: false, disable-model-invocation: true, agents: [], model: [Claude Sonnet 4.6 (copilot), GPT-5.3-Codex (copilot)]
3. Assigned tools (exactly 9): vscode/memory, execute/runInTerminal, execute/getTerminalOutput, execute/awaitTerminal, execute/killTerminal, read/readFile, edit/editFiles, edit/createFile, search
4. Output contract: FIXED/FAILED + files_changed + evidence (Channel A style)
5. Input contract: task_id, test_file, source_files, retry_hint, error_summary (documented in workflow section)
6. Max 1 internal retry (fix-attempt IS the fresh perspective)
7. Never touches kanban board (enforced by tool exclusion - no owlbear-kanban/*)
8. validate_agents.py passes on the new file
See docs/research/fresh-context-retry-builder.md, docs/research/fix-attempt-agent-design.md
Depends on: decision 228-fresh-context-retry.md approval

[[2026-03-30]] Mon 22:26
## Architecture Review
**Verdict:** Block (pending decision)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Agent file with persona/tools/workflow | Clear, follows pipeline agent pattern | Kept |
| 2. Frontmatter flags + model + agents:[] | Added model spec and agents:[] per research gaps | Refined |
| 3. Explicit 9-tool assign list | Enumerated all 9 tools for precision | Refined |
| 4. Output contract FIXED/FAILED | Aligns with Channel A convention | Kept |
| 5. Input contract with retry_hint | Reflexion-style verbal feedback, well-specified | Kept |
| 6. Max 1 internal retry | Bounded, clear | Kept |
| 7. No kanban tools | Enforced by tool exclusion | Kept |
| 8. validate_agents.py passes | Added: ensures pre-commit hook compatibility | Added |

### Architecture Notes
1. AC is architecturally sound. 9-tool assign set confirmed against builder.agent.md (19 tools minus 10 excluded). Exclusions justified in docs/research/fix-attempt-agent-design.md S3b.
2. Pattern consistency: follows existing pipeline agent convention (DIM true, agents:[], model list, assign tools). Reference: builder.agent.md, reviewer.agent.md.
3. TDD: not applicable for .agent.md files (declarative config). Validated by reviewer against AC plus validate_agents.py. Consistent with #307, #263 precedent.
4. Decision 228-fresh-context-retry.md (approved:false) blocks the feature. Option D (do nothing) would invalidate #318-#320. Consistent with #266 block for same reason.

### Changes Made
- Refined AC: added model spec, agents:[], explicit tool enumeration, validate_agents.py check
- Blocked to ideation pending decision 228 approval

### Dependencies
- Blocking: decision 228-fresh-context-retry.md (approved:false)
- Downstream: #319 (workflow integration), #320 (tests) both at ideation

[[2026-04-04]] Sat 15:50
## Research
- Validation pass on existing docs: docs/research/fix-attempt-agent-design.md, docs/research/fresh-context-retry-builder.md
- Sources: 6 studied (from existing docs), all still relevant
- Decision 228 RESOLVED (approved: Option A - threshold=2, builder first) - blocker cleared
- Minor gap: builder now has 20 tools (not 19) - owlbear-memory/* added post-research. Must be explicitly excluded from fix-attempt (rationale: short-lived repair subagent, memory ops are builder concern). AC still valid at 9 tools.
- Recommendation: proceed to implementation (confidence: .85)
- Follow-up tasks: #319, #320 already exist at ideation - no new tasks needed
- Decision requests: none (228 already resolved)

## Challenge Results
- Challenge: SKIPPED - validation pass on existing research, no new recommendation
- Confidence in original: .85 (unchanged from fix-attempt-agent-design.md S4)
- Key validation checks: decision status, builder tool list, follow-up task existence, AC currency
- Researcher response: findings hold with one minor exclusion-table update needed

[[2026-04-04]] Sat 15:51
Research validation complete. Decision 228 approved (Option A). Existing research docs confirmed current. Blocker cleared — ready for architect/builder.

[[2026-04-04]] Sat 16:20
AC ADDENDUM: 9. PostToolUse hook: hooks.PostToolUse runs lint-changed.ps1 (same as builder.agent.md) to enforce lint discipline on code edits

[[2026-04-04]] Sat 16:21
## Architecture Review (2nd pass)
See docs/scratch/318-architect.md for full evaluation.
Verdict: APPROVE -> todo
Refinements: added AC #9 (PostToolUse lint hook), added agent pass-through tag, fixed #320 deps.

[[2026-04-04]] Sat 16:21
Architecture review 2nd pass complete. AC refined (added #9: PostToolUse lint hook). Agent pass-through tag added. #320 deps fixed to include #319. Challenger accepted on hooks and deps, rebutted on validator scope and other minors. Confidence: .88.

[[2026-04-04]] Sat 16:59
## Test-Writer Notes
- Test file: tests/test_fix_attempt_agent_318.py
- Classes: TestFromAC_FixAttemptFrontmatter, TestFromAC_FixAttemptBody
- Tests per category: happy 0, edge 2, error 0, boundary 0 (contract/structure tests: 27 total)
- Total: 27 tests, all FAIL
- ruff: clean

AC coverage:
| AC | Tests |
|----|-------|
| AC1 file + frontmatter + persona | test_file_exists, test_has_valid_yaml_frontmatter, test_body_has_persona_section |
| AC2 frontmatter flags + model | test_user_invocable_false, test_disable_model_invocation_true, test_agents_is_empty_list, test_model_matches_builder, test_model_contains_claude_sonnet_46, test_model_contains_gpt_codex |
| AC3 exactly 9 tools | test_tools_exactly_9, test_tools_are_correct_set |
| AC4 output contract FIXED/FAILED | test_output_contract_has_fixed_verdict, test_output_contract_has_failed_verdict, test_output_contract_mentions_files_changed, test_output_contract_mentions_evidence |
| AC5 input contract 5 fields | test_input_contract_has_task_id, test_input_contract_has_test_file, test_input_contract_has_source_files, test_input_contract_has_retry_hint, test_input_contract_has_error_summary |
| AC6 max 1 retry | test_body_documents_max_one_retry |
| AC7 no kanban | test_no_kanban_tools_in_frontmatter, test_no_memory_mcp_tools_in_frontmatter, test_body_prohibits_kanban |
| AC8 validate_agents.py | test_validate_agents_passes |
| AC9 PostToolUse hook | test_posttooluse_hook_present, test_posttooluse_hook_references_lint_script |

[[2026-04-04]] Sat 17:51
## Builder Notes

**Files changed:** `.github/agents/fix-attempt.agent.md` (1 new file, 107 lines)

**Test results:** 27 passed (27 TestFromAC_*, 0 TestBuilderDiscovered), 0 failed

**Coverage:** N/A — declarative .agent.md file (no Python code)

**Lint:** ruff clean (no Python files)

**Evidence:**
- Created `.github/agents/fix-attempt.agent.md` with correct frontmatter (user-invocable: false, disable-model-invocation: true, agents: [], model matching builder, exactly 9 tools in assign set)
- PostToolUse hook references lint-changed.ps1 (identical to builder.agent.md pattern)
- Body documents input contract (5 fields), output contract (FIXED/FAILED + files_changed + evidence), max 1 retry, and explicit no-kanban constraint
- validate_agents.py passes (all 9 tools are recognized VS Code built-in or toolset patterns)
- Commit: 02a4207

[[2026-04-04]] Sat 18:20
## Review Evidence

**pytest:** 27 passed, 0 failed (run independently — builder self-report confirmed)
**ruff:** All checks passed
**Coverage:** N/A — declarative `.agent.md` file, no Python code

### TestFromAC Modification Check
Builder commit `02a4207` touched only `.github/agents/fix-attempt.agent.md` (1 new file, 107 lines). Test file (`a5ea509`) was test-writer-only. Zero TestFromAC_* modifications.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: file + frontmatter + persona | `.github/agents/fix-attempt.agent.md` exists; `---` block present; `<persona>` at line 15 | test_file_exists, test_has_valid_yaml_frontmatter, test_body_has_persona_section | PASS |
| AC2: frontmatter flags + model | `user-invocable: false`, `disable-model-invocation: true`, `agents: []`, `model: [Claude Sonnet 4.6 (copilot), GPT-5.3-Codex (copilot)]` — matches builder.agent.md exactly | 6 tests | PASS |
| AC3: exactly 9 tools | `tools: [vscode/memory, execute/runInTerminal, execute/getTerminalOutput, execute/awaitTerminal, execute/killTerminal, read/readFile, edit/editFiles, edit/createFile, search]` — 9 entries, exact set match | test_tools_exactly_9, test_tools_are_correct_set | PASS |
| AC4: output contract FIXED/FAILED + files_changed + evidence | Output Contract table in body; `FIXED #{task_id}` and `FAILED #{task_id}` with `files_changed` and `evidence` columns | 4 tests | PASS |
| AC5: input contract 5 fields | Input Contract table documents: task_id, test_file, source_files, retry_hint, error_summary | 5 tests | PASS |
| AC6: max 1 internal retry | Step 6 header "Retry (max 1)" + body text "max 1 internal retry" + Constraints section | test_body_documents_max_one_retry | PASS |
| AC7: no kanban tools | owlbear-kanban/* absent from tools list; owlbear-memory/* absent; Constraints: "No kanban board access." | 3 tests | PASS |
| AC8: validate_agents.py passes | subprocess.run returncode == 0 confirmed by test execution | test_validate_agents_passes | PASS |
| AC9: PostToolUse hook | `hooks.PostToolUse` block present; command references `lint-changed.ps1` — identical to builder.agent.md | test_posttooluse_hook_present, test_posttooluse_hook_references_lint_script | PASS |

### Pass 1 Findings
- **Security (5.1):** CLEAN — declarative YAML/MD, no code, no injection vectors
- **Test Integrity (5.2):** PRESERVED — builder commit scoped to agent file only
- **Test Quality (5.3):** ADEQUATE — structural verification appropriate for declarative config; 1 LAX note: `test_body_prohibits_kanban` checks presence of "kanban" substring (acceptable — no plausible false positive for this file type)
- **Data Safety (5.4):** N/A
- **Test Gap Analysis (5.5):** Complete — no code paths unexercised
- **Loop Detection (5.7):** CLEAN — 1 Builder Notes section, no retries

### Deductions
None

**Confidence: .97 → PASS**

[[2026-04-04]] Sat 18:37
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | New `.agent.md` file added; copilot-instructions.md lists `.github/agents/` directory only — no individual agent table. No convention changes. No update needed. |
| 2 | Module docstrings | No | N/A | No Python files created or modified — declarative `.agent.md` only. |
| 3 | External attribution | Yes | Verified | `docs/sources/overview.md` § "Fix-Attempt Agent Design Validation (Task #318)" already present (4 sources at lines 396–403). No new entries needed. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `docs/research/fix-attempt-agent-design.md` confirmed on disk. `docs/research/fresh-context-retry-builder.md` linked in task body. Follow-up tasks #319 and #320 exist at ideation. |

### Files Updated
- None

### Scratch Files Cleaned
- `docs/scratch/318-architect.md` — not present on disk (already removed by prior stage)

[[2026-04-04]] Sat 19:48
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: file + frontmatter + persona | fix-attempt.agent.md exists, YAML valid, persona at L15 | PASS |
| AC2: frontmatter flags + model | user-invocable: false, DIM: true, agents: [], model matches builder | PASS |
| AC3: exactly 9 tools | 9 tools in assign set, exact match confirmed | PASS |
| AC4: output contract FIXED/FAILED | Output Contract table with FIXED/FAILED + files_changed + evidence | PASS |
| AC5: input contract 5 fields | Input Contract table: task_id, test_file, source_files, retry_hint, error_summary | PASS |
| AC6: max 1 retry | Step 6 Retry (max 1) + constraints section | PASS |
| AC7: no kanban/memory tools | owlbear-kanban/*, owlbear-memory/* absent from tools and body | PASS |
| AC8: validate_agents.py | test_validate_agents_passes confirms returncode 0 | PASS |
| AC9: PostToolUse hook | hooks.PostToolUse with lint-changed.ps1, matches builder pattern | PASS |

### Test Results
- pytest (task): 27 passed, 0 failed
- pytest (full suite): 593 passed, 143 failed, 1 error (all failures pre-existing from other tasks: #467, #489, #531, #589, etc. Zero in #318 scope)
- ruff: all checks passed

### Architect Quality: 4/5
AC was specific and testable across 9 lines. Builder needed zero improvisation (0 TestBuilderDiscovered). AC9 added on 2nd architect pass (proactive refinement). Minor: initial pass missed PostToolUse hook convention.

### Deduction Breakdown
- AC lines with no evidence: 0 (all 9 mapped) = 0
- Lint violations: 0 = 0
- AC quality score 4/5 (not lte 3) = 0
- Missing reviewer evidence: no (detailed, .97 PASS) = 0
- Full-suite failures in task scope: 0 = 0
Total deductions: 0

### Confidence: 1.00
### Action: archive

### Commit Integrity
- a5ea509: test-writer commit (test file only)
- 02a4207: builder commit (agent file only, 107 lines)
- Scope: clean, no cross-contamination

[[2026-04-04]] Sat 19:48
Audit complete. 9/9 AC lines verified with evidence. 27/27 tests pass. Full suite: 0 regressions in task scope. Architect quality 4/5. Confidence 1.00.
