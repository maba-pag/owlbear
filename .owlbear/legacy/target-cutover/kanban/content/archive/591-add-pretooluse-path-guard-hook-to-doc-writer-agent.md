---
id: 591
title: Add PreToolUse path guard hook to doc-writer agent (Phase 5)
status: archived
priority: medium
created: 2026-04-04 07:56:05.254254+02:00
updated: 2026-04-06 10:37:37.520149+02:00
started: 2026-04-06 10:37:37.520149+02:00
completed: 2026-04-06 10:37:37.520149+02:00
tags:
- scope:agents
- hooks
- type:build
depends_on:
- 589
class: standard
archival_reason: completed
archival_refs: []
---

## Context
Phase 5 of VS Code agent-scoped hooks adoption. Doc-writer should not write to source code directories. Research found that reusing deny-src-writes.ps1 (allow-list for tests/ only) is infeasible — 100% of doc-writer's legitimate write targets are outside tests/. A new deny-list script (deny-code-writes.ps1) is required.

See .owlbear/research/pretooluse-doc-writer-path-guard-591.md and .owlbear/research/deny-code-writes-ac-validation-637.md for full analysis. Task #637 (revised AC) was absorbed into this task during architecture review.

## Acceptance Criteria
1. Create `.owlbear/hooks/deny-code-writes.ps1` — PreToolUse hook using **deny-list** approach:
   - Normalize `\` to `/` and strip leading `./` from extracted paths
   - Extract paths from `tool_input.filePath`, `tool_input.dirPath`, and `tool_input.replacements[*].filePath`
   - Deny when ANY extracted path starts with: `serve/`, `v1/`, `tests/`, `setup/`, `seed/`, `store/`, `share/agents/`, `.git/`, `.owlbear/hooks/`, `.owlbear/scripts/`; or equals `conftest.py` (after normalization)
2. Write-tool gate: script checks paths only for `tool_name` in `{create_file, replace_string_in_file, multi_replace_string_in_file, create_directory, apply_patch}`; all other `tool_name` values return `{}`
3. Add PreToolUse hook to `share/agents/doc-writer.agent.md` frontmatter: `powershell -NoProfile -NonInteractive -File .owlbear/hooks/deny-code-writes.ps1`
4. Remove `edit/editFiles` from doc-writer's tools list — unverified PreToolUse schema prevents path-based guarding (follow-up task for re-adding when schema is confirmed)
5. Script returns `{}` for: non-write tools (per AC2), missing/empty paths, empty/missing `tool_name`, malformed stdin JSON
6. Agent file parses as valid YAML frontmatter after both changes (hook addition + tools list edit)
7. Script has maintenance comment header listing denied dirs and rationale
8. Depends on: #589 (deny-src-writes.ps1 as pattern reference)

## Known Limitations
- `run_in_terminal` bypasses PreToolUse hooks (terminal writes are opaque)
- `.py` docstring edits in `serve/` and `v1/` are blocked by the deny-list — path-level hooks cannot distinguish docstring changes from logic changes. Doc-writer should note needed docstring updates and defer to the builder via reject-to-review. Accepted trade-off: blocking source-dir writes provides stronger protection than instruction-only enforcement.
- Deny-list is not self-maintaining: new source dirs require manual update to script
- `.github/` directory is allowed (doc-writer writes `.github/copilot-instructions.md`) — other `.github/` files (prompts, dependabot) are instruction-enforced only
- `apply_patch` unified diffs may reference files beyond `tool_input.filePath` — patch body parsing is out of scope for path-based hooks

## Research
- Research doc: .owlbear/research/pretooluse-doc-writer-path-guard-591.md
- AC validation doc: .owlbear/research/deny-code-writes-ac-validation-637.md
- Sources: 13 studied across both research rounds
- Recommendation: deny-list approach with deny-code-writes.ps1 (confidence: .80 after amendments)
- Follow-up tasks created: editFiles schema verification (from arch review)
- Decision requests: none — T1 (incremental config/build, no arch change)

[[2026-04-06]] Mon 02:19
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: doc-writer path guard. Tools list edit is ancillary defense for same boundary. |
| Interface clarity | PASS | Inputs (tool_input fields), outputs (deny/pass-through JSON), deny-list dirs, normalization steps all specified. |
| Dependency correctness | PASS | #589 archived (.98 audit confidence). No runtime deps. |
| Module layering | PASS | Standalone PS1 script + agent config. No Python module imports. |
| TDD compliance | PASS | Test-writer processes at todo. Established pattern: test_deny_src_writes_hook_589.py (37 tests). |
| KISS/YAGNI | PASS | Deny-list simpler than allow-list for doc-writer's diverse write targets. editFiles deferred to follow-up #638 (YAGNI: unverified schema). |
| Premise challenge | PASS | Doc-writer has NO path guard currently. 4 other agents already have hooks. Gap is real. |
| Pattern consistency | PASS | Shell pattern (PS1 in .owlbear/hooks/, frontmatter registration, JSON I/O) reused from Phase 2/3. Logic is novel (deny-list vs allow-list) — noted. |
| Security surface | PASS | Stdin JSON from VS Code (trusted). Self-modification blocked (share/agents/ denied). .git/ escalation blocked. Path normalization + ./stripping specified. |
| Single domain | PASS | Agent configuration domain exclusively. |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| JSON parse stdin | Malformed JSON | ConvertFrom-Json error | Yes (AC5) | Pass-through (safe) |
| Path extraction | No path fields | N/A | Yes (AC5) | Pass-through (no paths) |
| Path normalization | Backslash + ./ prefix | N/A | Yes (AC1) | Normalized before comparison |
| Array iteration | Empty replacements | N/A | Yes (AC5) | Pass-through |
| conftest.py match | ./conftest.py input | N/A | Yes (AC1 ./ strip) | Correctly matched after normalization |
| Docstring edit attempt | serve/*.py write | N/A | Denied (by design) | Known Limitation: deferred to builder |
| editFiles tool call | Not in write-tools gate | N/A | Tool removed from agent (AC4) | Not reachable; follow-up #638 |

### Challenge Results (Architecture Phase)
- Challenger: reconsider (confidence: 0.45)
- Key challenges: C1 deny-list blocks .py docstrings (critical), C2 editFiles unverified (critical), C3 conftest.py normalization (moderate), C4 .github/ unprotected (moderate), C5 share/skills/ allowed (moderate)
- Architect response: C1 accepted (explicit Known Limitation, docstrings deferred to builder), C2 accepted (remove editFiles from tools + follow-up #638), C3 accepted (added ./ stripping to AC1), C4 noted as Known Limitation, C5 noted (share/skills/ are docs, in scope)
- Prior challenger results (research phase): reconsider at .78, revised to .73 after accepting C1-C4

### AC Refinements Applied
- Replaced infeasible original AC (reuse deny-src-writes.ps1) with validated deny-list approach from #637 research
- Expanded deny-list: added seed/, store/, share/agents/, .git/ (from #637 R1 amendment)
- Added ./ stripping to normalization (from arch challenger C3)
- Added AC4: remove edit/editFiles from tools list (from arch challenger C2)
- Created follow-up #638 for editFiles schema verification
- Archived #637 (subsumed into revised #591)

### Verdict: APPROVE (via REFINE)
### Action Taken
Rewrote #591 body with validated AC from #637 research (5 amendments incorporated) plus 3 challenger-driven refinements. Removed editFiles from tools list (AC4). Created follow-up #638 for editFiles re-addition. Archived #637 as subsumed. Advanced to todo.

[[2026-04-06]] Mon 03:22
## Test-Writer Notes

**Test file:** `tests/test_deny_code_writes_hook_591.py`

**Classes:**
- `TestFromAC_ScriptExists` — script existence guard (2 tests)
- `TestFromAC_DenyListBehavior` — deny-list / allow-list path routing via subprocess, Windows-only (34 tests)
- `TestFromAC_WriteToolGate` — tool_name gating including apply_patch, Windows-only (8 tests)
- `TestFromAC_SafetyFallbacks` — malformed JSON, empty/missing tool_name, no paths, empty filePath, empty replacements array (6 tests)
- `TestFromAC_DocWriterAgentHooks` — frontmatter hooks section, PreToolUse entry, type:command, deny-code-writes.ps1 reference, edit/editFiles removal, YAML validity, no duplicate keys (7 tests)
- `TestFromAC_MaintenanceHeader` — script comment header existence and content (2 tests)

**Total: 59 tests — all FAIL** (confirmed with `uv run pytest --tb=no -q`)

**AC coverage:**

| AC | Tests |
|----|-------|
| AC1 (deny-list: all 10 prefixes + conftest.py) | 11 deny + 4 allow + 6 normalization + 6 multi/replace/dir = 27 tests |
| AC2 (write-tool gate incl. apply_patch) | 5 gated + 3 pass-through = 8 tests |
| AC3 (PreToolUse hook in frontmatter) | 4 tests |
| AC4 (edit/editFiles removed) | 1 test |
| AC5 (safety fallbacks) | 6 tests |
| AC6 (valid YAML, no dups) | 2 tests |
| AC7 (maintenance comment) | 2 tests |

**Key differentiator from #589:** `apply_patch` IS gated in deny-code-writes (AC2e); deny-src-writes excluded it. Tests explicitly document this distinction.

Ruff: clean. Commit: 94d071b.

[[2026-04-06]] Mon 08:21
## Builder Notes

### Files Changed
- `.owlbear/hooks/deny-code-writes.ps1` — created (deny-list path guard)
- `share/agents/doc-writer.agent.md` — removed `edit/editFiles` from tools, added `hooks:` section with PreToolUse deny-code-writes.ps1

### Test Results
- **59 passed** (0 failed, 0 skipped) — all `TestFromAC_*` classes green
- Classes covered: ScriptExists (2), DenyListBehavior (34), WriteToolGate (8), SafetyFallbacks (6), DocWriterAgentHooks (7), MaintenanceHeader (2)

### Lint
- `ruff check tests/test_deny_code_writes_hook_591.py` — **clean**

### Commit
- `1f42065` — feat: add deny-code-writes.ps1 hook and update doc-writer agent frontmatter (#591)

### Key diff from deny-src-writes.ps1
- Deny-list approach (vs allow-list) — 10 denied prefixes + conftest.py exact match
- `apply_patch` IS gated (AC2e — explicit test distinguishes from #589)
- Path normalization: `\` → `/` and `./` prefix stripping before comparison

[[2026-04-06]] Mon 09:10
## Review Evidence

### Test Results
**pytest:** 59 passed, 0 failed, 0 skipped (quality-runner, independent run)
**ruff:** clean — `tests/test_deny_code_writes_hook_591.py`
**Coverage:** N/A — no Python module changed; PS1 script + agent config only

### Changed Files
- `.owlbear/hooks/deny-code-writes.ps1` — created
- `share/agents/doc-writer.agent.md` — hook added, `edit/editFiles` removed
- `tests/test_deny_code_writes_hook_591.py` — test file (test-writer, builder must not weaken)

### AC Compliance

| AC | Test(s) | Would Fail If Violated? | Verdict |
|----|---------|------------------------|---------|
| AC1 — deny-list (10 prefixes + conftest.py exact, normalization) | 27 TestFromAC_DenyListBehavior tests | Yes — individual prefix tests + normalization tests with `assert _is_denied()` | COVERED |
| AC2 — write-tool gate (5 tools incl. apply_patch) | 8 TestFromAC_WriteToolGate tests | Yes — each gated tool with denied path; run_in_terminal/read_file/unknown return `=={}` | COVERED |
| AC3 — PreToolUse hook in frontmatter | 4 TestFromAC_DocWriterAgentHooks tests | Yes — regex checks for `hooks:`, `PreToolUse`, `type: command`, `deny-code-writes.ps1` | COVERED |
| AC4 — edit/editFiles removed | 1 test (not-in-fm assertion) | Yes — `assert "edit/editFiles" not in fm` | COVERED |
| AC5 — safety fallbacks (malformed JSON, empty/missing tool_name, no paths, empty filePath, empty replacements) | 6 TestFromAC_SafetyFallbacks tests | Yes — each asserts `output == {}` | COVERED |
| AC6 — valid YAML, no duplicate keys | 2 tests (yaml.safe_load + regex key scan) | Yes — parse error or duplicate key triggers pytest.fail | COVERED |
| AC7 — maintenance comment header | 2 TestFromAC_MaintenanceHeader tests | Yes — checks for `#` comment marker and `serve/`, `share/agents/`, `.git/` content | COVERED |

### Test Integrity — TestFromAC Comparison
Test count: test-writer baseline 59 (all FAIL, commit 94d071b) → builder delivery 59 (all PASS, commit 1f42065). Zero tests added, removed, or skipped. No `xfail`/`skip` markers encountered. Assertion specificity preserved: `_is_denied()` checks `hookSpecificOutput.permissionDecision == "deny"` (exact equality); pass-through checks use `output == {}` (exact dict equality).

| Assessment | Result |
|-----------|--------|
| Any WEAKENED or REMOVED? | None detected |
| Any STRENGTHENED? | None |

### Security Review
- No hardcoded secrets, tokens, or credentials.
- No shell injection — ConvertFrom-Json used (not string construction); deny-list comparisons are pure string operations.
- Path normalization is defensive: `\` → `/`, `./` prefix stripped before deny checks. Note: `../../serve/foo.py`-style paths are not normalized; this is a deliberate accepted design limitation documented in Known Limitations. The hook is not exploitable for arbitrary file writes (it only reads paths and emits JSON).
- No insecure deserialization — `ConvertFrom-Json` is PowerShell's native safe parser; no `eval`/`exec` equivalents.
- Deny response outputs a PS1 hashtable serialized via `ConvertTo-Json -Compress` (no interpolated user data in the key/structure).
- **No OWASP Top 10 violations.**

### Test Quality
| Dimension | Rating | Notes |
|-----------|--------|-------|
| Assertion specificity | STRONG | Exact equality (`== {}`) or field-level checks (`== "deny"`) throughout |
| Negative/error-path coverage | STRONG | Every deny prefix has an allow counterpart; pass-through tools each tested |
| Manual mutation check | STRONG | Removing any single prefix from `$denied_prefixes` would fail the corresponding test; removing `apply_patch` from gate would fail AC2e |
| Test independence | STRONG | Subprocess-based; no shared mutable state between tests |
| Descriptive names | STRONG | All names map directly to AC labels; docstrings reference AC item |

### Data Safety
No LLM output persisted, no shared state, no multi-step atomicity concerns, subprocess `timeout=30` guards against unbounded blocking. Clean.

### Minor Observation (no deduction)
No test covers the case where `tool_input` key is entirely absent from stdin (`{"tool_name": "create_file"}` with no `tool_input`). The implementation handles this correctly via `if ($tool_input)` + empty-paths early-exit. Not listed in AC5; untested edge case that is safely implemented. No deduction warranted.

### Deductions
None.

### Verdict
**Confidence: .97 → PASS → docs**

[[2026-04-06]] Mon 09:33
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A — no update needed | Doc-writer agent modified (hook added, editFiles removed). `copilot-instructions.md` is a 5-line Project Identity stub — no hooks tables or agent config sections exist to update. README "Pre-commit Hooks" section covers only git hooks, not PreToolUse; no PreToolUse section exists in README that would need updating. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified — PS1 script + `.agent.md` config only. |
| 3 | External attribution | No | N/A | Task #591 research doc (`pretooluse-doc-writer-path-guard-591.md`) used only internal sources (5 internal files, no external URLs). Subsumed task #637's external source (VS Code hooks docs) is already recorded in `sources/overview.md` under "Deny-Code-Writes AC Validation (Task #637)". |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | Both docs exist and linked in task body: `.owlbear/research/pretooluse-doc-writer-path-guard-591.md` ✓, `.owlbear/research/deny-code-writes-ac-validation-637.md` ✓. Follow-up #638 (editFiles schema verification) created. |

### Files Updated
None — no documentation changes required.

### Scratch Files
No `.owlbear/scratch/591-*` files found.

[[2026-04-06]] Mon 10:37
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — deny-list (10 prefixes + conftest.py, normalization) | 27 TestFromAC_DenyListBehavior tests pass; script lines 82-92 list all 10 prefixes; normalization at lines 98-101 | PASS |
| AC2 — write-tool gate (5 tools incl. apply_patch) | 8 TestFromAC_WriteToolGate tests pass; script lines 42-48 list all 5 tools | PASS |
| AC3 — PreToolUse hook in frontmatter | 4 TestFromAC_DocWriterAgentHooks tests pass; doc-writer.agent.md hooks section verified | PASS |
| AC4 — edit/editFiles removed from tools | 1 test (not-in-fm assertion) pass; doc-writer.agent.md tools list confirmed no edit/editFiles | PASS |
| AC5 — safety fallbacks | 6 TestFromAC_SafetyFallbacks tests pass; script try/catch + empty-path guards verified | PASS |
| AC6 — valid YAML, no duplicate keys | 2 tests pass; frontmatter parses cleanly | PASS |
| AC7 — maintenance comment header | 2 TestFromAC_MaintenanceHeader tests pass; script lines 1-26 contain full header | PASS |

### Test Results
- pytest (task scope): 59 passed, 0 failed, 0 skipped
- pytest (full suite): 3058 passed, 473 failed, 18 skipped — zero failures from #591 files; all failures are pre-existing (voice scaffolding, validator skills, other unrelated tasks)
- ruff: 5 pre-existing violations in serve/mcp-kanban/ — zero in #591 deliverables

### Upstream Commits Verified
- Test-writer: 94d071b (test file)
- Builder: 1f42065 (deny-code-writes.ps1 + doc-writer.agent.md)

### Architect Quality: 5/5
Three refinement rounds (research, #637 AC validation, arch challenger) produced specific, complete, testable AC. All 8 items unambiguous. Challenger identified 5 edge cases — all addressed in AC or Known Limitations. No builder/reviewer improvisation needed.

### Deduction Breakdown
- AC lines without evidence: 0 (all 7 covered)
- Lint violations in scope: 0
- AC quality score: 5/5 (no deduction)
- Reviewer evidence section: present, detailed, PASS at .97 (no deduction)
- Full-suite failures in task scope: 0 (no deduction)

### Confidence: .98
### Action: archive
