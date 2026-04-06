---
id: 591
title: Add PreToolUse path guard hook to doc-writer agent (Phase 5)
status: todo
priority: someday
created: 2026-04-04T07:56:05.2542536+02:00
updated: 2026-04-06T02:19:29.5353409+02:00
tags:
    - scope:agents
    - hooks
    - type:build
depends_on:
    - 589
class: standard
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
