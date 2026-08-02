---
id: 677
title: Add deny-writes hook to read-only agents (auditor, code-reader, challenger)
status: archived
priority: medium
created: 2026-04-08T18:30:31.9568749+02:00
updated: 2026-04-09T00:05:22.5075568+02:00
started: 2026-04-09T00:05:22.5075568+02:00
completed: 2026-04-09T00:05:22.5075568+02:00
tags:
    - scope:agents
    - ' type:safety'
    - ' source:analysis'
class: standard
---

## Context

Analysis synthesis identified that 18 of 23 agents have no hooks. Among these, several are designed to be read-only by convention (prompt instructions) but have no enforcement via PreToolUse hooks.

The existing `deny-writes.ps1` hook (used by reviewer) blocks all write tools. This same hook can be referenced by other read-only agents.

## Agents to add deny-writes hook

| Agent | Current hooks | Rationale |
|-------|--------------|-----------|
| auditor | none | Designed as read-only verifier; should not write code |
| code-reader | none | "Strictly read-only" per agent definition |
| challenger | none | "Strictly read-only; no state mutations" per agent definition |

> quality-runner split to separate task — requires a scratch-only-allow hook, not full deny-writes.

## Acceptance Criteria

- [ ] AC1: `auditor.agent.md` frontmatter contains `hooks:` section with a PreToolUse entry of `type: command` referencing `.owlbear/hooks/deny-writes.ps1` (same format as `reviewer.agent.md`)
- [ ] AC2: `code-reader.agent.md` frontmatter contains `hooks:` section with a PreToolUse entry of `type: command` referencing `.owlbear/hooks/deny-writes.ps1`
- [ ] AC3: `challenger.agent.md` frontmatter contains `hooks:` section with a PreToolUse entry of `type: command` referencing `.owlbear/hooks/deny-writes.ps1`
- [ ] AC4: `deny-writes.ps1` comment header and `permissionDecisionReason` are generalized — must not reference a specific agent name. Use generic phrasing (e.g., "This agent is read-only. File writes are not permitted."). The `seed/.owlbear/hooks/deny-writes.ps1` copy must also be updated to match.
- [ ] AC5: All existing tests in `tests/test_deny_writes_hook_211.py` still pass after the message change (the AC3b test uses OR logic: "reviewer" or "read-only" — generalized message satisfies "read-only")
- [ ] AC6: New test assertions validate each of the 3 agent frontmatter files contains valid YAML with `hooks.PreToolUse` referencing `deny-writes.ps1` (following `TestFromAC_ReviewerAgentHooks` pattern in `tests/test_deny_writes_hook_211.py`)

## Codebase References

- Hook script: `.owlbear/hooks/deny-writes.ps1` (also `seed/.owlbear/hooks/deny-writes.ps1`)
- Reference pattern: `share/agents/reviewer.agent.md` hooks section (lines 11-13)
- Existing tests: `tests/test_deny_writes_hook_211.py` — `TestFromAC_ReviewerAgentHooks` class
- Agent files: `share/agents/auditor.agent.md`, `share/agents/code-reader.agent.md`, `share/agents/challenger.agent.md`

[[2026-04-08]] Wed 20:54
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | After splitting quality-runner to #685, task covers one concern: add deny-writes hook to 3 read-only agents + generalize hook message |
| Interface clarity | PASS | AC specifies exact agent files, hook format (type: command), and reference pattern (reviewer.agent.md lines 11-13) |
| Dependency correctness | PASS | No dependencies — `deny-writes.ps1` already exists at `.owlbear/hooks/deny-writes.ps1` |
| Module layering | PASS | Agent configs (`share/agents/`) reference hooks (`.owlbear/hooks/`) — no layering violation |
| TDD compliance | PASS | AC6 specifies test expectations; test-writer will create frontmatter assertions following `TestFromAC_ReviewerAgentHooks` pattern |
| KISS/YAGNI | PASS | Minimal scope — reuses existing hook, only adds frontmatter references + generalizes one message |
| Premise challenge | PASS | Defense-in-depth is valid — code-reader/challenger have no write tools in allowlist but hook adds platform-level enforcement; auditor has execute tools where hook blocks file-write tools |
| Pattern consistency | PASS | Follows exact pattern from `reviewer.agent.md` (lines 11-13): `hooks: PreToolUse: - type: command, command: powershell -NoProfile -NonInteractive -File .owlbear/hooks/deny-writes.ps1` |
| Security surface | PASS | No new boundaries — reusing existing hook. Known limitation: `run_in_terminal` bypasses PreToolUse hooks (documented in existing tests) |
| Single domain | PASS | Agent configuration domain only |

### AC Refinements Made

| Original AC | Issue | Refined AC |
|---|---|---|
| AC1-3: "references deny-writes.ps1 as PreToolUse hook" | Underspecified format | Now specifies `type: command` and `.owlbear/hooks/` path, references reviewer pattern |
| AC4: "Decide on quality-runner" | Design decision, not testable — separate concern | Split to #685. Replaced with: generalize deny-writes.ps1 message (prereq for sharing hook across agents) |
| AC5: "Existing tests still pass" | OK but needed clarification on AC3b OR logic | Now references specific test file and explains why generalized message passes |
| AC6: "Verify workflows" | Vague, not testable | Now specifies new test assertions for 3 agent frontmatter files following existing test pattern |

### Architecture Notes

- `deny-writes.ps1` currently hardcodes "The reviewer agent is read-only" in both the comment header (line 1) and `permissionDecisionReason` (line 28). AC4 now requires generalization.
- `seed/.owlbear/hooks/deny-writes.ps1` is already out of sync (missing `editFiles` in write_tools list). AC4 now includes updating the seed copy.
- `deny-writes.ps1` uses case-insensitive `-contains` for tool matching — this is correct (more conservative than `-ccontains`).
- Existing test `test_deny_writes_hook_211.py` line 328: `assert "reviewer" in lower or "read-only" in lower or "read only" in lower` — generalized message with "read-only" satisfies this.

### Challenge Results

- Challenger: FALLBACK — challenger agent not available in current subagent registry
- Architect response: Proceeded without challenge. Confidence high — task reuses proven pattern with minimal changes.

### Verdict: APPROVE (after REFINE + SPLIT)
### Action Taken: Refined AC1-6 for precision, split quality-runner to #685, advanced #677 to todo.

[[2026-04-08]] Wed 21:52
## Test-Writer Notes

**Test file:** `tests/test_deny_writes_hook_677.py`

**Classes:**
- `TestFromAC_AuditorAgentHooks` — 6 tests (AC1 frontmatter contract)
- `TestFromAC_CodeReaderAgentHooks` — 6 tests (AC2 frontmatter contract)
- `TestFromAC_ChallengerAgentHooks` — 6 tests (AC3 frontmatter contract)
- `TestFromAC_GeneralizedHookMessage` — 7 tests (AC4 generalized message)

**Tests per category:**
- Happy path: frontmatter has hooks section, PreToolUse entry, type:command, deny-writes.ps1 reference, .owlbear/hooks/ path (5 per each of 3 agents = 15)
- YAML validity: frontmatter parses as valid YAML with hooks.PreToolUse (AC6, 1 per agent = 3)
- File content: comment header and reason don't reference "reviewer", contain "read-only" (AC4, compound assertions = 4 static + 1 runtime = 5 + 2 = 7)

**Total: 25 tests, all FAIL** (confirmed via pytest: 25 failed, 0 passed)

**AC coverage:**
| AC | Tests |
|---|---|
| AC1 | 6 tests in TestFromAC_AuditorAgentHooks |
| AC2 | 6 tests in TestFromAC_CodeReaderAgentHooks |
| AC3 | 6 tests in TestFromAC_ChallengerAgentHooks |
| AC4 | 7 tests in TestFromAC_GeneralizedHookMessage (static regex + runtime subprocess) |
| AC5 | Covered by existing tests/test_deny_writes_hook_211.py — no new tests needed |
| AC6 | test_frontmatter_is_parseable_yaml_with_pretooluse_hook in each of 3 agent classes |

**Design note:** AC4 `_contains_read_only` tests were initially combined with `_does_not_contain_reviewer` into compound assertions to avoid passing on current code (current message already contains "read-only").

[[2026-04-08]] Wed 22:17
## Builder Notes

**Files changed (5):**
- `share/agents/auditor.agent.md` — added `hooks: PreToolUse: - type: command` block referencing `.owlbear/hooks/deny-writes.ps1`
- `share/agents/code-reader.agent.md` — same hooks block added
- `share/agents/challenger.agent.md` — same hooks block added
- `.owlbear/hooks/deny-writes.ps1` — generalized comment header (removed "reviewer agent") and `permissionDecisionReason` → "This agent is read-only. File writes are not permitted."
- `seed/.owlbear/hooks/deny-writes.ps1` — same message generalization + added missing `editFiles` to write_tools list (seed was out of sync per arch note)

**Test results:** 49 passed (25 new `test_deny_writes_hook_677.py` + 24 existing `test_deny_writes_hook_211.py`), 0 failed
**Lint:** ruff clean — no issues
**Coverage:** config-only changes (no Python logic); test files have full assertion coverage per AC

**AC evidence:**
- AC1-3: frontmatter hooks blocks present, valid YAML, PreToolUse + type:command + `.owlbear/hooks/deny-writes.ps1` path ✓
- AC4: both hook files — comment header and reason generic, no "reviewer" reference ✓
- AC5: `test_deny_writes_hook_211.py` — 24 existing tests still pass ✓
- AC6: `test_frontmatter_is_parseable_yaml_with_pretooluse_hook` passes for all 3 agents ✓

[[2026-04-08]] Wed 23:07
## Review Evidence

### Test Results
pytest: **49 passed, 0 failed** (25 new `test_deny_writes_hook_677.py` + 24 existing `test_deny_writes_hook_211.py`)

### Lint
ruff: **clean** — 0 violations across both test files

### Coverage
Config-only changes (YAML frontmatter + PowerShell comments) — no Python logic; N/A

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 | `auditor.agent.md` lines 12–16: `hooks: PreToolUse: - type: command, command: powershell -NoProfile -NonInteractive -File .owlbear/hooks/deny-writes.ps1` | PASS |
| AC2 | `code-reader.agent.md` lines 9–13: identical structure | PASS |
| AC3 | `challenger.agent.md` lines 9–13: identical structure | PASS |
| AC4 | Both `.owlbear/hooks/deny-writes.ps1` and `seed/.owlbear/hooks/deny-writes.ps1` byte-identical. Comment header: "deny-writes.ps1 — PreToolUse hook for read-only agents." permissionDecisionReason: "This agent is read-only. File writes are not permitted." — no "reviewer" reference, "read-only" present. `editFiles` present in seed write_tools list | PASS |
| AC5 | `test_deny_writes_hook_211.py` line 230 OR assertion: `"reviewer" in lower or "read-only" in lower or "read only" in lower` — generalized message satisfies "read-only" condition; all 24 existing tests pass | PASS |
| AC6 | `test_frontmatter_is_parseable_yaml_with_pretooluse_hook` in each of 3 agent classes parses YAML and validates `hooks.PreToolUse` structure | PASS |

### TestFromAC Integrity
All `TestFromAC_*` classes unmodified by builder. 4 classes present: AuditorAgentHooks, CodeReaderAgentHooks, ChallengerAgentHooks, GeneralizedHookMessage. No WEAKENED or REMOVED tests detected.

### Test Quality
STRONG — regex assertions on specific frontmatter fields, compound absence/presence checks for AC4 (must not contain "reviewer" AND must contain "read-only"), runtime subprocess test verifies actual PowerShell hook execution. No lazy assertions.

### Security
Config-only changes. No injection vectors, no secrets, no new dependencies. No OWASP concerns.

### Builder Process
1 Builder Notes section — CLEAN. No loop patterns.

### Deductions
0

### Verdict
Confidence: **0.97 → PASS**

[[2026-04-08]] Wed 23:13
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | YAML frontmatter additions + PowerShell comment generalization; `copilot-instructions.md` is 14 lines with no hooks/agent tables — nothing to update |
| 2 | Module docstrings | No | N/A | Zero Python modules touched — config-only changeset (3 `.agent.md` files + 2 `.ps1` files) |
| 3 | External attribution | No | N/A | No external repos, articles, or docs referenced in task body or review evidence |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | No | N/A | No `.owlbear/research/677-*` file; task originated from analysis synthesis, no research phase doc |

### Files Updated
None — no documentation impact.

### Scratch Files
No `.owlbear/scratch/677-*` files found.

### Verification
- `auditor.agent.md` lines 12–16: `hooks: PreToolUse: - type: command, command: powershell ... deny-writes.ps1` ✓
- `code-reader.agent.md` lines 9–13: identical structure ✓
- `challenger.agent.md` lines 9–13: identical structure ✓
- Both `deny-writes.ps1` copies byte-identical: generic header + `permissionDecisionReason: 'This agent is read-only. File writes are not permitted.'` ✓

[[2026-04-09]] Thu 00:05
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 | `auditor.agent.md` lines 12–14: hooks.PreToolUse with type:command referencing `.owlbear/hooks/deny-writes.ps1` | PASS |
| AC2 | `code-reader.agent.md` lines 9–11: identical structure | PASS |
| AC3 | `challenger.agent.md` lines 9–11: identical structure | PASS |
| AC4 | Both `.owlbear/hooks/deny-writes.ps1` and `seed/` copy: comment header "read-only agents" (no "reviewer"), reason "This agent is read-only. File writes are not permitted." — byte-identical | PASS |
| AC5 | `test_deny_writes_hook_211.py`: 24 existing tests pass — OR logic at line 230 satisfied by "read-only" | PASS |
| AC6 | `test_frontmatter_is_parseable_yaml_with_pretooluse_hook` passes for Auditor, CodeReader, Challenger classes | PASS |

### Test Results
- pytest (task-scoped): 49 passed, 0 failed (25 new + 24 existing)
- pytest (full suite): 3707 passed, 376 failed — failures pre-existing, unrelated to #677 (config-only changes, zero Python source)
- ruff: 5 warnings in `serve/mcp-kanban/` — unrelated to #677

### Architect Quality: 5/5
AC lines specific with exact file paths, frontmatter format, reference patterns, and test expectations. Architecture notes (OR logic, seed sync, editFiles gap) were helpful and accurate. No improvisation required by builder.

### Deduction Breakdown
- AC evidence: 0 (all 6 AC lines verified with file evidence + test assertions)
- Lint: 0 (no violations in task scope)
- AC quality: 0 (score 5/5)
- Reviewer evidence: 0 (present and detailed, PASS verdict)
- Full-suite in scope: 0 (no task-scope failures)
- Commit integrity: -.02 (builder + doc-writer failed to commit deliverables; auditor committed leftovers)

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 8ea9b27 | test | tests/test_deny_writes_hook_677.py | #677 |
| aa23908 | feat | 6 files (3 agent.md, 2 deny-writes.ps1, test file) | #677 |
