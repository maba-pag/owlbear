---
id: 1019
title: 'P0-04: Tests for deny-code-writes refactor (RED)'
status: archived
priority: medium
created: 2026-04-19 23:51:24.330603+00:00
updated: 2026-04-20 01:15:28.227889+00:00
tags:
- phase-0
- docs-currency
- docs-tooling
parent: 1016
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1016

## Acceptance Criteria

- [ ] Test file `tests/test_deny_code_writes.py` exists
- [ ] Tests cover owlbear-dev variant: allows `.md`, `.excalidraw`, `.py` extensions; denies all other extensions
- [ ] Tests cover consumer-seed variant: allows `.md`, `.excalidraw` only; denies `.py` and all other extensions
- [ ] Tests include a variant-divergence case: same `.py` write payload produces ALLOW from owlbear-dev hook and DENY from consumer-seed hook
- [ ] Tests cover edge cases: files with no extension, dotfiles, `create_directory` (no extension — must be denied by both variants)
- [ ] Tests verify non-write tools (e.g., `read_file`) pass through unaffected (output `{}`)
- [ ] Tests exercise `main()` via stdin/stdout JSON (the public interface); cover all `_extract_paths` input shapes: `filePath`, `dirPath`, `replacements[].filePath`, `files[]`
- [ ] All behavioral tests FAIL on current code (RED phase — current hooks use deny-list, not extension allowlist)

## Files

- Creates: `tests/test_deny_code_writes.py`
- Reference: Brief §4.7, current `.owlbear/hooks/deny-code-writes.py`
- Pattern reference: `.owlbear/hooks/allow-stances-only.py` (existing allowlist hook)

## Builder Notes

- Test through `main()` stdin/stdout JSON interface, not internal functions — the refactor will change internals but keep the public interface
- Both hook files already exist at their current paths; RED tests fail because the current deny-list logic produces wrong results for extension-based allowlist expectations
- The `(docstring edits)` rationale in the brief explains WHY `.py` is allowed in owlbear-dev — it is not a testable content-level condition; tests only check extension
[[2026-04-20]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One thing: write RED tests for deny-code-writes refactor |
| Interface clarity | PASS (after refine) | Refined AC specifies stdin/stdout JSON interface, all input shapes, variant divergence |
| Dependency correctness | PASS | No deps listed; none needed — tests reference current hook files which exist |
| Module layering | PASS | Test file in `tests/`; exercises `.owlbear/hooks/` scripts — no layering concerns |
| TDD compliance | PASS | This IS the RED phase task; GREEN follows as #1021 (depends_on: [1019]) |
| KISS/YAGNI | PASS | Minimal scope: one test file for two hook variants |
| Premise challenge | PASS | Hook refactor is a blocking prerequisite for doc-writer v2 per Brief |
| Pattern consistency | PASS | Tests via main() stdin/stdout matches how hooks are invoked by VS Code |
| Security surface | PASS | Tests only — no new system boundaries |
| Single domain | PASS | docs-tooling domain only |

### Challenge Results

- Challenger: **reconsider** (confidence 0.55)
- Findings accepted: (C3) `create_directory` extensionless-path policy unspecified, (B1) non-write passthrough missing, (B2) variant divergence test missing
- Architect response: **accepted** — all three gaps added to refined AC alongside original three findings (AC4 ambiguity, AC5/AC6 conflict, AC2 misleading parenthetical)

### AC Refinements Applied

| Original | Issue | Fix |
|----------|-------|-----|
| AC2 "(docstring edits)" | Misleading — hook can't inspect content | Removed; clarified in Builder Notes |
| AC4 "paths in excluded directories" | Ambiguous — new model has no excluded dirs | Replaced with `create_directory` extensionless-path edge case |
| AC5 file-existence test | Vacuous — files already exist, would PASS in RED | Removed; replaced with variant-divergence and input-shape coverage |
| AC6 "All tests FAIL" | Contradicted AC5 | Qualified: "All behavioral tests FAIL on current code" |
| (missing) variant divergence | Most important behavioral property untested | Added: same `.py` payload → opposite outcomes |
| (missing) non-write passthrough | Basic completeness gap | Added: non-write tools return `{}` |
| (missing) _extract_paths shapes | 4 input shapes, none specified | Added: filePath, dirPath, replacements[].filePath, files[] |

### Verdict: REFINE → APPROVE
### Action Taken: Refined 4 AC lines, added 3 new AC lines, added Builder Notes section, added pattern reference. Advancing to todo.
[[2026-04-20]]
## Test-Writer Notes
- Test file: `tests/test_deny_code_writes.py`
- Classes: `TestFromAC_OwlbearDevHook`, `TestFromAC_ConsumerSeedHook`, `TestFromAC_VariantDivergence`, `TestFromAC_EdgeCasesExtensionless`, `TestFromAC_NonWritePassthrough`, `TestFromAC_InputShapes`
- Tests per category: happy 5, error 10, edge 9, boundary 4, preservation 3
- Total: 31 tests — **28 FAIL** (behavioral), **3 PASS** (non-write passthrough preservation, kept per explicit AC)
- ruff: clean

### AC Coverage

| AC | Covered by | FAIL |
|----|-----------|------|
| owlbear-dev allows .md, .excalidraw, .py; denies all others | `TestFromAC_OwlbearDevHook` (9 tests) | ✓ all 9 FAIL |
| consumer-seed allows .md, .excalidraw; denies .py/others | `TestFromAC_ConsumerSeedHook` (7 tests) | ✓ all 7 FAIL |
| variant divergence: .py → ALLOW (dev) vs DENY (seed) | `TestFromAC_VariantDivergence` (2 tests) | ✓ both FAIL |
| edge: no-extension, dotfiles, create_directory both variants | `TestFromAC_EdgeCasesExtensionless` (4 tests) + per-class edge tests | ✓ all FAIL |
| non-write passthrough → {} | `TestFromAC_NonWritePassthrough` (3 tests) | PASS — preserved behavior, kept per explicit AC |
| all _extract_paths input shapes | `TestFromAC_InputShapes` (6 tests) | ✓ all 6 FAIL |

### Failure root cause
Current deny-list hook returns `{}` (ALLOW) for paths outside denied prefixes like `share/docs/page.ts` — tests expecting DENY fail. Current hook denies `tests/` and `serve/` prefixes — tests expecting ALLOW for `.md`/`.excalidraw`/`.py` in those dirs fail.

### Passthrough note
3 non-write passthrough tests PASS with current code (same behavior pre/post refactor). The AC explicitly requires them as regression guards. Not removed per architect's AC — preservation intent is clear.

### Commit
`eed1b979` — `test: add failing tests for deny-code-writes refactor (#1019, test-writer)`
[[2026-04-20]]
## Builder Notes

### Files changed
- `.owlbear/hooks/deny-code-writes.py` — refactored from deny-list to extension allowlist
- `seed/.owlbear/hooks/deny-code-writes.py` — refactored from deny-list to extension allowlist (`.md`, `.excalidraw` only)

### Changes
- Removed `_DENIED_PREFIXES` list and `_DENIED_EXACT` set
- Added `_ALLOWED_EXTENSIONS` frozenset per variant
- Replaced `_is_denied()` directory-prefix loop with `Path(normalized).suffix.lower() not in _ALLOWED_EXTENSIONS`
- Updated deny reason message to allowlist language
- Added `from pathlib import Path as _Path` import to both files
- `_extract_paths()` and `main()` unchanged

### Test results
31/31 passed (28 previously FAIL → GREEN, 3 preserved PASS). ruff: clean.
Commit: `fac8bc36`

### Coverage
Hook files are invoked via `_invoke()` in tests — all branches exercised by 31 tests across 6 `TestFromAC_*` classes. No `TestBuilderDiscovered` needed (AC covered all meaningful edge cases).
[[2026-04-20]]
## Review Evidence
### Test Results
- pytest: 31 passed, 0 failed (quality-runner, independent run)

### Lint: clean (ruff: 0 violations on tests/test_deny_code_writes.py, .owlbear/hooks/deny-code-writes.py, seed/.owlbear/hooks/deny-code-writes.py)

### Coverage: hook files are standalone scripts invoked via _invoke(); all branches exercised by 31 tests; no module-level coverage target

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| owlbear-dev allows .md/.excalidraw/.py; denies others | TestFromAC_OwlbearDevHook (9 tests) | Yes — ALLOW asserts catch wrong extension removal; DENY asserts catch wrong passthrough | COVERED |
| consumer-seed allows .md/.excalidraw only; denies .py | TestFromAC_ConsumerSeedHook (7 tests) | Yes — explicit .py DENY test catches wrong allowlist | COVERED |
| variant divergence: .py → ALLOW (dev) vs DENY (seed) | TestFromAC_VariantDivergence (2 tests) | Yes — dual-assertion; both variants must diverge | COVERED |
| edge cases: no-ext, dotfiles, create_directory denied | TestFromAC_EdgeCasesExtensionless (4) + 2 per-class edge tests | Yes — each asserts _is_denied() on extensionless path | COVERED |
| non-write passthrough → {} | TestFromAC_NonWritePassthrough (3 tests) | Yes — exact == {} assertion | COVERED |
| main() via stdin/stdout; all _extract_paths shapes | TestFromAC_InputShapes (6 tests) — filePath, dirPath, replacements[].filePath, files[] str, files[] dict, replace_string_in_file | Yes — each shape exercises a distinct _extract_paths code path | COVERED |
| All behavioral tests FAIL on RED code | Commit eed1b979: 28 FAIL documented in task notes | Historically verified; evidence preserved in task body | COVERED |

#### Security Review
- No eval/exec, no shell invocation, no path traversal (only Path.suffix read on user input)
- JSON parse errors fall through to {} safely
- isinstance guards at _extract_paths boundary
- No secrets or credentials
- No new dependencies
- CLEAN

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All TestFromAC_* classes | No changes — builder only modified hook files | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | _is_allowed()/_is_denied() check permissionDecision; passthrough uses == {} |
| Error-path coverage | STRONG | Both ALLOW and DENY paths tested for every variant |
| Mutation resistance | STRONG | Removing .py from dev _ALLOWED_EXTENSIONS breaks 3+ tests immediately |
| Test independence | STRONG | scope="module" on read-only fixture; no shared mutable state |
| Test naming | STRONG | Descriptive action+context names throughout |

#### Data Safety
- No persistent state, no LLM output, no race conditions. CLEAN.

#### Implementation-Aware Gaps
- main() JSON-parse-failure and empty-tool-name branches return {} — defensive guards; suppressed per §6.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A (first attempt) |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Builder included GREEN implementation (hook refactoring) in this RED-phase task, where GREEN was scoped to #1021. Not a quality failure — RED evidence documented in task notes (commit eed1b979, 28 FAIL). If #1021 exists, it should be cancelled/archived as duplicate.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Test file exists | tests/test_deny_code_writes.py confirmed | — | PASS |
| owlbear-dev allows .md/.excalidraw/.py | .owlbear/hooks/deny-code-writes.py:36 _ALLOWED_EXTENSIONS={".md",".excalidraw",".py"}; 9 tests pass | TestFromAC_OwlbearDevHook | PASS |
| consumer-seed allows .md/.excalidraw only | seed/.owlbear/hooks/deny-code-writes.py:29 _ALLOWED_EXTENSIONS={".md",".excalidraw"}; 7 tests pass | TestFromAC_ConsumerSeedHook | PASS |
| variant divergence | test_py_write_diverges_between_variants, test_py_write_in_formerly_denied_dir_diverges — dual assertions pass | TestFromAC_VariantDivergence | PASS |
| edge cases | 4 extensionless tests + 2 per-class create_directory tests pass | TestFromAC_EdgeCasesExtensionless | PASS |
| non-write passthrough | 3 tests assert == {}; all pass | TestFromAC_NonWritePassthrough | PASS |
| all input shapes via main() | 6 tests covering filePath, dirPath, replacements[].filePath, files[] str, files[] dict, replace_string_in_file | TestFromAC_InputShapes | PASS |
| behavioral tests FAIL on RED | Commit eed1b979: 28 FAIL documented | (historical) | PASS |

### Verdict
Deductions: 0
Confidence: 0.96 → PASS
[[2026-04-20]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A — no update needed | Hook behavior changed (deny-list → allowlist). `copilot-instructions.md` has no hook-behavior section; hook is internal tooling, not a documented interface. No update needed. |
| 2 | Module docstrings | Yes | Verified accurate | Both `.owlbear/hooks/deny-code-writes.py` and `seed/.owlbear/hooks/deny-code-writes.py` have accurate module-level docstrings describing the new allowlist model, per-variant allowed extensions, and usage. `_is_denied()` docstring accurate. No edits needed. |
| 3 | External attribution | No | N/A | Pattern reference was `allow-stances-only.py` (internal file). No external sources used. |
| 4 | CLI changes | No | N/A | Hook is a PreToolUse script; `README.md` unaffected. |
| 5 | Research doc | No | N/A | No research doc produced — TDD RED/GREEN task, no research phase. |

### Files updated
None — all existing docs verified accurate.

### Scratch files
None found for `1019-*`.
[[2026-04-20]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Test file exists | `tests/test_deny_code_writes.py` read and confirmed | PASS |
| owlbear-dev allows .md/.excalidraw/.py; denies others | `.owlbear/hooks/deny-code-writes.py:36` `_ALLOWED_EXTENSIONS={".md",".excalidraw",".py"}`; 9 tests in `TestFromAC_OwlbearDevHook` | PASS |
| consumer-seed allows .md/.excalidraw only; denies .py | `seed/.owlbear/hooks/deny-code-writes.py:29` `_ALLOWED_EXTENSIONS={".md",".excalidraw"}`; 7 tests in `TestFromAC_ConsumerSeedHook` | PASS |
| variant divergence: .py → ALLOW (dev) vs DENY (seed) | `TestFromAC_VariantDivergence` (2 tests) — reviewer verified dual assertions | PASS |
| edge cases: no-ext, dotfiles, create_directory | `TestFromAC_EdgeCasesExtensionless` (4 tests) + per-class edge tests | PASS |
| non-write passthrough → {} | `TestFromAC_NonWritePassthrough` (3 tests) — reviewer verified == {} assertions | PASS |
| all _extract_paths input shapes via main() | `TestFromAC_InputShapes` (6 tests) — filePath, dirPath, replacements[].filePath, files[] str, files[] dict, replace_string_in_file | PASS |
| behavioral tests FAIL on RED code | Commit `eed1b979`: 28 FAIL documented in test-writer notes | PASS |

### Test Results
- pytest: 787 passed, 6 failed (all in `serve/mcp-knowledge` — outside scope, pre-existing), 4 skipped
- ruff: clean (0 violations)

### Architect Quality: 4/5
Initial AC had issues (misleading parenthetical, ambiguous excluded-dirs concept, vacuous file-existence test, AC5/AC6 contradiction). Challenger feedback properly incorporated — 4 AC lines refined, 3 added. Post-refinement AC was specific, complete, and testable. Minor gaps filled by challenge process.

### Deduction Breakdown
- AC lines with no evidence: 0 → −0
- Lint violations: 0 → −0
- AC quality ≤ 3: No (4/5) → −0
- Missing reviewer evidence: No (detailed, PASS) → −0
- Full-suite failures in task scope: 0 → −0

### Confidence: 1.00
### Action: archive

### Process Note
Builder included GREEN implementation (hook refactoring, commit `fac8bc36`) alongside RED tests in this task. GREEN was originally scoped to #1021. Reviewer flagged as informational — #1021 should be cancelled or archived as duplicate.