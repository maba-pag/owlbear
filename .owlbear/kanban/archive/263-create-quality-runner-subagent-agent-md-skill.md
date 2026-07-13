---
id: 263
title: Create Quality-Runner subagent (agent.md + skill)
status: archived
priority: medium
created: 2026-03-30 19:30:52.012916+02:00
updated: 2026-04-04 18:43:24.062687+02:00
started: 2026-04-04 18:43:24.062687+02:00
completed: 2026-04-04 18:43:24.062687+02:00
tags:
- scope:agents
- phase-2
- agent
class: standard
archival_reason: completed
archival_refs: []
---

Create the Quality-Runner utility subagent â€” a mechanical agent that runs pytest, ruff, and coverage, returning structured reports. Design validated in docs/research/quality-runner-subagent-design.md. Decision approved: docs/decisions/resolved/228-esub-utility-subagents.md (Option A).

## Acceptance Criteria

### Agent File: `.github/agents/quality-runner.agent.md`

- [ ] Frontmatter properties:
  - `name: quality-runner`
  - `user-invocable: false`
  - `disable-model-invocation: true`
  - `model: [Claude Haiku 4.5 (copilot), GPT-5.4 mini (copilot)]`
  - `tools: [execute/runInTerminal, execute/getTerminalOutput, execute/awaitTerminal, execute/killTerminal, read/readFile, vscode/memory, read/terminalLastCommand, execute/testFailure]`
  - `agents: []`
- [ ] `<persona>` defines mechanical utility role (run commands, parse output, format report)
- [ ] Agent body embeds these 5 pytest-and-linting pitfalls verbatim as fallback (in case h-pytest-and-linting skill does not auto-load in subagent context):
  1. Never pipe `uv run` output through PS cmdlets
  2. Use bare `--cov` only (no `--cov=module.path`)
  3. Use `isBackground=true` for full-suite runs
  4. File-capture fallback for truncated output (write to docs/scratch/, read_file, delete)
  5. WMI hang mitigation (kill zombie `python*,pytest*` processes)
- [ ] Agent body specifies input contract:
  - `mode`: scoped or full (required)
  - `test_paths`: string[] (required if scoped)
  - `task_id`: string (required, for COVERAGE_FILE isolation)
  - `coverage_modules`: string[] (optional)
  - `lint_paths`: string[] (optional, default: packages/ tests/)
- [ ] Agent body specifies output contract with exactly these sections:
  - Tests: passed count, failed [{name, error}], skipped count
  - Lint: clean bool, violations [{file, line, code, msg}]
  - Coverage: overall_pct, modules [{name, pct}]
  - Exit Codes: pytest exit code, ruff exit code
  - Errors: fatal error messages
- [ ] Agent body instructs retry behavior: max 2 internal retries before reporting failure
- [ ] Agent body instructs timeout behavior: 5 min full suite, 2 min scoped, enforced via execute/killTerminal after elapsed time

### Skill File: `.github/skills/quality-runner/SKILL.md`

- [ ] Documents consumer invocation pattern via runSubagent with example prompt
- [ ] Lists input fields with types and required/optional designators
- [ ] Shows output section format with example
- [ ] Describes fallback: if Quality-Runner is unavailable, callers use direct uv run commands per h-pytest-and-linting skill

## Files to Create

- `.github/agents/quality-runner.agent.md`
- `.github/skills/quality-runner/SKILL.md`

## References

- Design: docs/research/quality-runner-subagent-design.md
- Parent research: docs/research/subagent-nesting-architecture.md S3c
- Decision: docs/decisions/resolved/228-esub-utility-subagents.md (approved: Option A)
- Pitfalls source: h-pytest-and-linting skill
- Pattern reference: .github/agents/code-reader.agent.md (assign-mode utility agent)
- Consumer wiring: #264 (depends on this task)

## Research

Design validated per docs/research/quality-runner-subagent-design.md. Three refinements to #228 design:
1. 8 tools (added read/terminalLastCommand, execute/testFailure)
2. Use disable-model-invocation: true with agents array override
3. Embed top 5 pitfalls in agent body as skill-loading fallback

[[2026-04-04]] Sat 15:57
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One deliverable: Quality-Runner agent + companion skill |
| Interface clarity | PASS (refined) | Original 5 vague AC lines expanded to 11 precise lines with exact tools, pitfalls, I/O contract |
| Dependency correctness | PASS | No code deps. Decision 228-esub-utility-subagents resolved (approved). #264 depends on this. |
| Module layering | N/A | Agent config files, not Python modules |
| TDD compliance | PASS | Non-impl task, `agent` tag added. Test-writer processes with pass-through note. |
| KISS/YAGNI | PASS | 8 tools justified by research. Assign mode limits scope. No speculative features. |
| Premise challenge | PASS | No built-in alternative. 4 agents handle pytest/ruff independently with repeated pitfalls. |
| Pattern consistency | PASS | Follows code-reader.agent.md: assign mode, disable-model-invocation, structured I/O |
| Security surface | PASS | Execute tools are internal (pytest, ruff). Assign mode limits blast radius to 8 tools. |
| Single domain | PASS | agent-config domain only |

### Challenge Results

- Challenger: reconsider (confidence: 0.60)
- Accepted: (C1) restored user-invocable and model as explicit AC; (C2) clarified timeout enforcement via killTerminal; (C4) enumerated all 5 pitfalls; (SKILL.md scope) added 4 AC lines for skill content
- Noted: C3 (execute/testFailure kept, builder already uses it); C5 (handled by REFINE process)
- Architect response: accepted (4 of 6 actionable items incorporated)

### AC Changes from Original

- 5 vague AC lines expanded to 11 precise lines across 2 file sections
- Added exact 8-tool list, model priority, all 5 embedded pitfalls
- Added I/O contract fields and output section structure
- Added SKILL.md content requirements (4 AC lines)
- Removed stale blocked-by text (decision resolved)

### Verdict: APPROVED (after REFINE)
### Action Taken: Body rewritten with precise AC, agent tag added, advancing to todo

[[2026-04-04]] Sat 15:59
AC refined from 5 vague lines to 11 precise lines. Challenger invoked (reconsider, 0.60), 4 of 6 items incorporated. Decision 228 resolved. Agent tag added. Advancing to todo.

[[2026-04-04]] Sat 16:22
Non-implementation task (tagged `agent`) — no tests applicable. Passing through to builder.

[[2026-04-04]] Sat 16:58
## Builder Notes

**Files created:**
- `.github/agents/quality-runner.agent.md` — frontmatter (8 tools, disable-model-invocation, Haiku/GPT-5.4-mini models, agents: []), persona (mechanical instrument framing), embedded 5 pitfalls, input/output contracts, retry (max 2) and timeout (5 min full / 2 min scoped) behavior
- `.github/skills/quality-runner/SKILL.md` — runSubagent invocation pattern with scoped and full examples, input field table (types + required/optional), output format with working example, fallback to h-pytest-and-linting direct commands

**Validation:** `validate_agents.py` and `validate_skills.py` both pass (no output = success)

**Test results:** Non-implementation task (agent config files) — no tests applicable. Passed through from test-writer.

**Lint:** N/A (markdown files)

**Coverage:** N/A

**All 11 AC lines satisfied.**

[[2026-04-04]] Sat 17:53
## Review Evidence

### Test Results
- pytest: N/A — non-implementation task (agent config files only, `agent` tag). No TestFromAC_* classes. Test-writer pass-through confirmed in task body.

### Lint: N/A (markdown files)

### Coverage: N/A

### Validation Scripts (independently run)
- `validate_agents.py .github/agents/quality-runner.agent.md` → no output = PASS
- `validate_skills.py .github/skills/quality-runner` → no output = PASS

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
Conditional skipped — no TestFromAC_* classes exist (agent-config-only task).

#### Security Review
- No hardcoded secrets, tokens, or passwords in either file
- No injection vectors (YAML frontmatter + markdown content only)
- No path traversal or deserialization risks
- `disable-model-invocation: true` design is good security practice (limits blast radius)
- No new Python dependencies
- **No issues**

#### Test Integrity
Conditional skipped — no TestFromAC_* classes exist.

#### Test Quality
Conditional skipped — no executable tests in scope for an agent-config task.

#### Data Safety
- Config files only; no shared mutable state or data persistence
- **No issues**

#### Implementation-Aware Gaps
- Config files have no code paths to exercise
- **No untested paths**

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
None.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `name: quality-runner` | agent.md line 2 | N/A | PASS |
| `user-invocable: false` | agent.md line 7 | N/A | PASS |
| `disable-model-invocation: true` | agent.md line 8 | N/A | PASS |
| `model: [Claude Haiku 4.5 (copilot), GPT-5.4 mini (copilot)]` | agent.md line 9 | N/A | PASS |
| `tools: [8 tools]` | agent.md line 10 — all 8 tools present | N/A | PASS |
| `agents: []` | agent.md line 11 | N/A | PASS |
| `<persona>` mechanical utility role | agent.md persona block — diagnostic instrument, mechanical precision, no kanban/file edits | N/A | PASS |
| 5 pitfalls embedded | agent.md Embedded Pitfalls section — all 5 present (no-pipe, bare --cov, isBackground, file-capture, WMI) | N/A | PASS |
| Input contract (5 fields) | agent.md Input Contract table — mode, test_paths, task_id, coverage_modules, lint_paths | N/A | PASS |
| Output contract (5 sections) | agent.md Output Contract — Tests/Lint/Coverage/Exit Codes/Errors all present with correct shapes | N/A | PASS |
| Retry max 2 | agent.md critical_rules + Retry logic section | N/A | PASS |
| Timeout 5min full / 2min scoped via killTerminal | agent.md Execution Protocol — 2min scoped, 5min full, killTerminal enforcement | N/A | PASS |
| SKILL: runSubagent invocation example | SKILL.md Consumer Invocation Pattern — scoped + full examples | N/A | PASS |
| SKILL: input fields with types + required/optional | SKILL.md Input Fields table | N/A | PASS |
| SKILL: output format with example | SKILL.md Output Format with fully populated example | N/A | PASS |
| SKILL: fallback to h-pytest-and-linting | SKILL.md Fallback section | N/A | PASS |

### Confidence: .97
### Verdict: PASS

[[2026-04-04]] Sat 17:59
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Agent config files only; copilot-instructions.md references `.agent.md` generically — no per-agent listing table to update |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | Yes | Verified | `docs/sources/overview.md` already contains "Quality-Runner Subagent Design (Task #263)" section with S1 (VS Code Built-in Tools Reference), S2 (VS Code Subagents Guide), S3 (VS Code Custom Agents docs) — all CC-BY-4.0 |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | `docs/research/quality-runner-subagent-design.md` exists; linked from task body under References |

### Files Updated
- None — all docs already in order (attribution pre-populated in sources/overview.md)

### Scratch Files Cleaned
- None (no `docs/scratch/263-*` files found)

[[2026-04-04]] Sat 18:43
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| name: quality-runner | agent.md L2 | PASS |
| user-invocable: false | agent.md L5 | PASS |
| disable-model-invocation: true | agent.md L6 | PASS |
| model: [Haiku 4.5, GPT-5.4 mini] | agent.md L7 | PASS |
| tools: 8 tools | agent.md L8: all 8 present | PASS |
| agents: [] | agent.md L9 | PASS |
| persona mechanical utility | agent.md persona block: diagnostic instrument | PASS |
| 5 pitfalls embedded | agent.md Embedded Pitfalls: all 5 | PASS |
| Input contract (5 fields) | agent.md Input Contract table | PASS |
| Output contract (5 sections) | agent.md Output Contract | PASS |
| Retry max 2 | agent.md critical_rules + Retry logic | PASS |
| Timeout 5min/2min killTerminal | agent.md Execution Protocol | PASS |
| SKILL: runSubagent invocation | SKILL.md Consumer Invocation Pattern | PASS |
| SKILL: input fields table | SKILL.md Input Fields table | PASS |
| SKILL: output format example | SKILL.md Output Format section | PASS |
| SKILL: fallback | SKILL.md Fallback section | PASS |

### Test Results
- pytest: 2813 passed, 408 failed, 8 skipped (all failures pre-existing, unrelated to agent-config task)
- validate_agents.py: PASS
- validate_skills.py: PASS

### Architect Quality: 4/5
Refined from 5 vague to 11 precise AC lines after REFINE + challenger.

### Deduction Breakdown
- Uncommitted deliverables (builder missed commit): -.02

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| c5aee17 | feat | quality-runner.agent.md, SKILL.md | #263 |
