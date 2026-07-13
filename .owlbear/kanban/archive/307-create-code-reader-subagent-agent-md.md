---
id: 307
title: Create Code-Reader subagent (agent.md)
status: archived
priority: medium
created: 2026-03-30 20:29:35.258911+02:00
updated: 2026-03-31 05:52:00.474638+02:00
started: 2026-03-31 05:51:37.424203+02:00
completed: 2026-03-31 05:51:37.424203+02:00
tags:
- scope:agents
- phase-2
class: standard
archival_reason: completed
archival_refs: []
---

Create the Code-Reader read-only analysis subagent per docs/research/reviewer-parallel-fan-out.md S3b and docs/research/code-reader-subagent-design.md. Assign-mode agent with read+search tools only.

## Acceptance Criteria

- [ ] agents/code-reader.agent.md exists with valid YAML frontmatter
- [ ] name: code-reader
- [ ] user-invocable: false
- [ ] disable-model-invocation: true
- [ ] agents: []
- [ ] model: [Claude Sonnet 4.6 (copilot), GPT-5.4 (copilot)] (matches reviewer)
- [ ] tools (assign mode, exactly 5): read/readFile, read/viewImage, read/problems, search, vscode/memory
- [ ] No execute/*, edit/*, agent, web, browser, or MCP tools in tools array
- [ ] Agent body contains procedures for code-review skill steps 6.0-6.6 (critical checks) and 7.1-7.4 (informational checks)
- [ ] Agent body documents input contract: task_id (string), ac_lines (string[]), changed_files (string[]), test_files (string[])
- [ ] Agent body defines 8-section output contract: test_writer_audit, security_review, test_integrity, test_quality, data_safety, test_gaps, necessity_check, informational
- [ ] Agent body includes persona establishing read-only adversarial analysis role

## Architecture Notes

- Reference: docs/research/code-reader-subagent-design.md
- Reference: docs/research/reviewer-parallel-fan-out.md S3b
- Depends on: decision 228-parallel-fan-out (pending, agent buildable independently per research; wiring is #265 scope)
- TDD: not applicable, agent .md file with no Python code. Validated by reviewer against AC plus validate_agents.py
- Pattern: follows existing pipeline agent frontmatter convention (reviewer, builder, etc.)
- Assign mode enforces read-only boundary architecturally, not just by instruction

## Research
See docs/research/code-reader-subagent-design.md for full validation.

Key findings (.90 confidence):
- Assign mode with 5 tools: read/readFile, read/viewImage, read/problems, search, vscode/memory
- Model: same as reviewer (Sonnet 4.6 / GPT-5.4)
- Leaf worker: agents [], disable-model-invocation: true
- Decision 228 pending but Code-Reader can be built independently

[[2026-03-30]] Mon 22:21
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| agent.md exists with valid frontmatter | Clear, verifiable | Kept |
| name: code-reader | Verifiable from frontmatter | Added (was implicit) |
| user-invocable: false | Verifiable from frontmatter | Kept |
| disable-model-invocation: true | Verifiable from frontmatter | Merged from research |
| agents: [] | Verifiable from frontmatter | Merged from research |
| model matches reviewer | Verifiable from frontmatter | Merged from research |
| tools exactly 5 (listed) | Verifiable from frontmatter | Tightened (was vague assign-mode) |
| No execute/edit/agent/web/MCP tools | Verifiable from frontmatter | Added negative constraint |
| Body covers skill steps 6.0-6.6, 7.1-7.4 | Verifiable by reading body | Kept |
| Input contract documented | Verifiable by reading body | Tightened (4 fields listed) |
| 8-section output contract | Verifiable by reading body | Tightened (sections listed) |
| Read-only adversarial persona | Verifiable by reading body | Added |

### Architecture Notes
Codebase search confirmed: all 12 pipeline agents use the same frontmatter pattern (explicit tools array, DIM true, agents []). Code-Reader follows this convention exactly. Assign mode with 5 tools enforces the read-only boundary at the tooling layer, not just by instruction. Reviewer agent.md (agents/reviewer.agent.md) is the reference template for model selection.

TDD not applicable: .agent.md files are declarative configuration validated by the reviewer against AC and scripts/validate_agents.py. No existing agent creation task has a preceding test task. Consistent with #263 pattern.

Decision 228-parallel-fan-out is pending (approved: false) but the agent file is buildable independently. Wiring into the reviewer is #265 scope. Risk of dead code is low (decision auto-resolves to Option A in 5 days).

### Changes Made
- Refined AC from 4+3 lines to 12 precise, mechanically verifiable lines
- Inlined tool names, input contract fields, output section names (no external references needed for verification)
- Added negative constraint (no execute/edit/agent/web/MCP tools)
- Preserved research section and architecture notes

### Dependencies
- Verified: decision 228-parallel-fan-out pending but non-blocking for agent file creation
- Verified: #265 (reviewer wiring) is separate scope
- No new dependencies added

[[2026-03-30]] Mon 22:21
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| agent.md exists with valid frontmatter | Clear, verifiable | Kept |
| name: code-reader | Verifiable from frontmatter | Added (was implicit) |
| user-invocable: false | Verifiable from frontmatter | Kept |
| disable-model-invocation: true | Verifiable from frontmatter | Merged from research |
| agents: [] | Verifiable from frontmatter | Merged from research |
| model matches reviewer | Verifiable from frontmatter | Merged from research |
| tools exactly 5 (listed) | Verifiable from frontmatter | Tightened (was vague assign-mode) |
| No execute/edit/agent/web/MCP tools | Verifiable from frontmatter | Added negative constraint |
| Body covers skill steps 6.0-6.6, 7.1-7.4 | Verifiable by reading body | Kept |
| Input contract documented | Verifiable by reading body | Tightened (4 fields listed) |
| 8-section output contract | Verifiable by reading body | Tightened (sections listed) |
| Read-only adversarial persona | Verifiable by reading body | Added |

### Architecture Notes
Codebase search confirmed: all 12 pipeline agents use the same frontmatter pattern (explicit tools array, DIM true, agents []). Code-Reader follows this convention exactly. Assign mode with 5 tools enforces the read-only boundary at the tooling layer, not just by instruction. Reviewer agent.md (agents/reviewer.agent.md) is the reference template for model selection.

TDD not applicable: .agent.md files are declarative configuration validated by the reviewer against AC and scripts/validate_agents.py. No existing agent creation task has a preceding test task. Consistent with #263 pattern.

Decision 228-parallel-fan-out is pending (approved: false) but the agent file is buildable independently. Wiring into the reviewer is #265 scope. Risk of dead code is low (decision auto-resolves to Option A in 5 days).

### Changes Made
- Refined AC from 4+3 lines to 12 precise, mechanically verifiable lines
- Inlined tool names, input contract fields, output section names (no external references needed for verification)
- Added negative constraint (no execute/edit/agent/web/MCP tools)
- Preserved research section and architecture notes

### Dependencies
- Verified: decision 228-parallel-fan-out pending but non-blocking for agent file creation
- Verified: #265 (reviewer wiring) is separate scope
- No new dependencies added

[[2026-03-31]] Tue 04:01
## Test-Writer Notes
- Test file: tests/test_code_reader_agent_307.py
- Classes: TestFromAC_CodeReaderFrontmatter, TestFromAC_CodeReaderBody
- Tests per category: happy 0, edge 4, error 0, boundary 0 (all structural/contract checks)
- Total: 38 tests, all FAIL ✓
- ruff: clean
- AC coverage:
  AC1: test_file_exists, test_has_valid_yaml_frontmatter
  AC2: test_name_is_code_reader
  AC3: test_user_invocable_false
  AC4: test_disable_model_invocation_true
  AC5: test_agents_is_empty_list
  AC6: test_model_matches_reviewer
  AC7: test_tools_exactly_5, test_tools_are_correct_set
  AC8: test_no_execute_tools, test_no_edit_tools, test_no_forbidden_standalone_tools, test_no_mcp_glob_tools
  AC9: test_body_covers_critical_step_6_0..6.6, test_body_covers_informational_step_7_1..7.4
  AC10: test_body_input_contract_has_task_id/ac_lines/changed_files/test_files
  AC11: test_body_output_contract_test_writer_audit/security_review/test_integrity/test_quality/data_safety/test_gaps/necessity_check/informational
  AC12: test_body_has_readonly_persona, test_body_has_adversarial_persona

[[2026-03-31]] Tue 04:21
## Builder Notes
- Files changed: agents/code-reader.agent.md (created)
- Tests: 38 passed, all TestFromAC_ checks green
- Lint: ruff clean (agents/code-reader.agent.md + tests/test_code_reader_agent_307.py)
- Evidence: 38 passed in 0.11s; uv run ruff check All checks passed!
- Fixes applied: None -- agent file was pre-built with correct frontmatter and body content; builder verified all 38 AC tests pass and lint is clean, then advanced to review

-t

[[2026-03-31]] Tue 04:23
## Builder Notes
- Files changed: agents/code-reader.agent.md (created)
- Tests: 38 passed, all TestFromAC_ checks green
- Lint: ruff clean
- Evidence: 38 passed in 0.11s; ruff All checks passed!
- Fixes applied: None -- agent file pre-built correctly; builder verified all 38 AC tests pass and lint clean

[[2026-03-31]] Tue 05:19
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | code-reader is a leaf subagent, not a pipeline stage; no behavior/convention change |
| 2 | Docstrings | No | N/A | Only .agent.md + test file created; no Python modules |
| 3 | docs/sources/overview.md | No | N/A | No new external code pattern adopted |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/code-reader-subagent-design.md exists and linked in task body |
| 6 | agents/README.md | Yes | Updated | Count updated 11-to-12; code-reader identified as leaf subagent |

### Files Updated
- agents/README.md

### Scratch Files Cleaned
- None (no docs/scratch/307-* files existed)

[[2026-03-31]] Tue 05:52
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 8dac007 | chore | kanban/tasks/307-*.md | #307 |
