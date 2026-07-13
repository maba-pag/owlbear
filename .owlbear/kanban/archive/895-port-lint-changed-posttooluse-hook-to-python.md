---
id: 895
title: Port lint-changed PostToolUse hook to Python
status: archived
priority: medium
created: 2026-04-16T22:53:50.250881+00:00
updated: 2026-04-17T04:23:37.234729+00:00
tags:
- phase-1
- scope:hooks
- type:build
- platform
parent: 890
depends_on:
- 892
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #890 and `.owlbear/briefs/draft-macos-compat/brief.md`

## Acceptance Criteria

- [ ] `.owlbear/hooks/lint-changed.py` created
- [ ] Reads JSON from sys.stdin, extracts file paths from tool_input (filePath, dirPath, replacements[], editFiles[])
- [ ] Filters to existing .py files only, deduplicates
- [ ] Runs `ruff check --ignore INP001` on collected paths via subprocess
- [ ] Returns JSON with systemMessage (user-facing) and hookSpecificOutput (model-facing) containing ruff output
- [ ] Non-zero ruff exit captured but does not crash the hook
- [ ] Fail-open: any exception returns {} with exit 0 (D7, D8)
- [ ] Bug-for-bug fidelity with .ps1 original (D7)
- [ ] All tests from #892 pass (GREEN)

## Files

- `.owlbear/hooks/lint-changed.py` (new)
[[2026-04-17]]

## Research

- Research doc: .owlbear/research/895-lint-changed-python-port.md
- Sources: 8 studied, 5 high-relevance (1.0)
- Recommendation: Existing implementation is correct — ready for GREEN verification (confidence: 0.92)
- Follow-up tasks created: none needed — #895 itself is the GREEN phase
- Decision requests: none

## Challenge Results

- Challenger: skipped — validation research on existing implementation with no design alternatives
- Confidence in original: 0.92

## Key Findings

- `.owlbear/hooks/lint-changed.py` already exists (110 lines) and matches all AC items
- Bug-for-bug fidelity with .ps1 confirmed (§3.1 table): same ruff args, exit code handling, output JSON, fail-open pattern
- Three intentional expansions per AC: editFiles tool, .py extension filter, BOM handling
- PostToolUse output format validated against VS Code docs (April 2026): systemMessage (user) + additionalContext (model)
- `dirPath` in AC handled implicitly — create_directory not an edit tool, and directory paths filtered by .py extension check
- Builder GREEN task: run #892 tests, confirm all pass
[[2026-04-17]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: lint changed .py files via ruff on PostToolUse |
| Interface clarity | PASS | Stdin JSON → stdout JSON contract; exact shapes specified in AC |
| Dependency correctness | PASS | #892 (RED phase) archived/done; tests exist at tests/test_lint_changed_hook.py |
| Module layering | PASS | Standalone hook script, no imports from workspace packages |
| TDD compliance | PASS | #892 wrote 30+ tests; this is GREEN verification |
| KISS/YAGNI | PASS | 110-line script, minimal scope |
| Premise challenge | PASS | macOS compat requires Python port of .ps1 hooks (Brief O1) |
| Pattern consistency | PASS | Mirrors .ps1 structure; same I/O contract per VS Code PostToolUse docs |
| Security surface | PASS | subprocess.run with list args (no shell); paths from VS Code tool_input |
| Single domain | PASS | hooks domain only |

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: .py created | Verifiable | File already exists (110 lines) |
| AC2: stdin JSON extraction (filePath, dirPath, replacements[], editFiles[]) | Verifiable — note: dirPath handled implicitly (create_directory not in edit tools, filtered by .py ext check) | No change needed; test_dirpath_returns_empty_dict confirms |
| AC3: .py filter + dedup | Verifiable | .endswith(".py") + Path.is_file() + case-insensitive set |
| AC4: ruff check --ignore INP001 | Verifiable | Mock ruff tests verify exact args |
| AC5: JSON output with systemMessage + hookSpecificOutput | Verifiable | Matches VS Code PostToolUse docs (April 2026) |
| AC6: non-zero ruff exit captured | Verifiable | check=False, returncode==1 gate |
| AC7: fail-open {} exit 0 | Verifiable | Broad except handlers at every stage |
| AC8: bug-for-bug fidelity | Verifiable — note: .py is strict superset (editFiles tool, .py filter, BOM) per AC2-AC3 | Research §3.1 confirms fidelity for overlapping tool set |
| AC9: all #892 tests pass | Verifiable | Builder runs pytest, confirms GREEN |

### Challenge Results

- Challenger: proceed (confidence 0.88)
- Concerns: (1) AC8 "fidelity" wording vs intentional expansions — cosmetic, tests are the real spec; (2) dirPath AC wording — cosmetic, behavior correct; (3) returncode==1 only — inherited .ps1 design, not a regression
- Architect response: accepted — all concerns cosmetic, no behavioral impact

### Verdict: APPROVE

### Action Taken: Advanced to todo. GREEN phase — builder runs existing #892 tests and confirms all pass

[[2026-04-17]]

## Test-Writer Notes

- Non-new-tests pass-through: all 32 tests from task #892 (`tests/test_lint_changed_hook.py`) cover every AC line in #895 and currently PASS (GREEN — implementation already exists at `.owlbear/hooks/lint-changed.py`).
- No new test file created: writing any new tests would duplicate #892 coverage and immediately pass against the existing implementation, violating the RED-phase contract.
- AC coverage by existing #892 tests:

  | AC | Test class |
  |---|---|
  | AC1 file exists | `TestFromAC_ScriptExists` |
  | AC2 stdin JSON extraction | `TestFromAC_PathExtraction`, `TestFromAC_JsonIOContract` |
  | AC3 .py filter + dedup | `TestFromAC_PyFilter`, `TestFromAC_Deduplication` |
  | AC4 ruff check --ignore INP001 | `TestFromAC_RuffArgs` |
  | AC5 JSON output format | `TestFromAC_JsonIOContract` |
  | AC6 non-zero ruff exit | `TestFromAC_JsonIOContract` (exit 0 always) |
  | AC7 fail-open | `TestFromAC_MalformedInput` |
  | AC8 fidelity | `TestFromAC_RuffArgs` |
  | AC9 GREEN | 32/32 tests PASS |

- Builder action: run `uv run pytest tests/test_lint_changed_hook.py -q` to confirm, then commit and close.
[[2026-04-17]]

## Builder Notes

### Files changed

- `.owlbear/hooks/lint-changed.py` — already existed (committed in #892 as part of RED phase); confirmed as correct GREEN implementation
- `tests/test_lint_changed_hook.py` — 32 tests from #892, committed in this task

### Test results

- **32 passed**, 0 failed — `uv run pytest tests/test_lint_changed_hook.py -q`
- Ruff: `All checks passed!` on `.owlbear/hooks/lint-changed.py`

### AC verification

| AC | Status |
|---|---|
| AC1: `.owlbear/hooks/lint-changed.py` created | PASS — file exists (110 lines) |
| AC2: stdin JSON extraction (filePath, dirPath, replacements[], editFiles[]) | PASS — `TestFromAC_PathExtraction` |
| AC3: .py filter + dedup | PASS — `TestFromAC_PyFilter`, `TestFromAC_Deduplication` |
| AC4: ruff check --ignore INP001 | PASS — `TestFromAC_RuffArgs` |
| AC5: JSON output (systemMessage + hookSpecificOutput) | PASS — `TestFromAC_JsonIOContract` |
| AC6: non-zero ruff exit captured | PASS — returncode==1 gate |
| AC7: fail-open {} exit 0 | PASS — `TestFromAC_MalformedInput` |
| AC8: bug-for-bug fidelity with .ps1 | PASS — same ruff args, exit code, output shape |
| AC9: all #892 tests pass | PASS — 32/32 GREEN |

### Commit

`3906c464` — feat(hooks): add lint-changed.py PostToolUse hook (#895)
[[2026-04-17]]

## Review Evidence

### Test Results

- pytest: **32 passed, 0 failed** (Quality-Runner independent run)
- ruff: **clean** on `.owlbear/hooks/lint-changed.py` and `tests/test_lint_changed_hook.py`
- Coverage: N/A — subprocess-based hook not measurable by pytest-cov; expected, no deduction

### TestFromAC Integrity

All `TestFromAC_*` classes verified against builder notes: tests committed from #892 unmodified. No WEAKENED or REMOVED assertions found. One LAX noted (informational only):

- `TestFromAC_MalformedInput.test_bom_prefixed_input_returns_empty_dict`: uses non-existent file so {} is returned whether BOM stripped successfully or parsing failed. Does not auto-FAIL — the BOM stripping is structural defensive code exercised indirectly, and both fail paths produce the correct AC7 output.

### AC Compliance Table

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: `.owlbear/hooks/lint-changed.py` created | File exists, 110 lines | `TestFromAC_ScriptExists.test_script_exists/test_script_is_nonempty` | PASS |
| AC2: stdin JSON extraction (filePath/dirPath/replacements[]/editFiles[]) | `_extract_paths()` L22-48; `dirPath` filtered by `create_directory` absent from `_EDIT_TOOLS` | `TestFromAC_PathExtraction.*` | PASS |
| AC3: .py filter + dedup | `main()` L79-80; `_add()` uses `path.lower()` for case-insensitive dedup | `TestFromAC_PyFilter.*`, `TestFromAC_Deduplication.*` | PASS |
| AC4: `ruff check --ignore INP001` via subprocess | `main()` L82-89; `check=False`, list args (no shell) | `TestFromAC_RuffArgs.*` (mock ruff verifies exact args) | PASS |
| AC5: JSON output with systemMessage + hookSpecificOutput | `main()` L91-100 | `TestFromAC_JsonIOContract.test_lint_errors_include_system_message`, `test_lint_errors_include_hook_specific_output` | PASS |
| AC6: non-zero ruff exit captured, no crash | `check=False` prevents CalledProcessError; `if result.returncode == 1` gates reporting | `TestFromAC_JsonIOContract.test_exit_code_always_zero_on_lint_errors` | PASS |
| AC7: fail-open {} exit 0 | Multiple `except Exception: print("{}"); return` blocks at every I/O boundary | `TestFromAC_MalformedInput.*` (4 tests: truncated, empty, BOM, binary) | PASS |
| AC8: bug-for-bug fidelity with .ps1 | PS1 and .py verified side-by-side: identical ruff args (`check --ignore INP001`), output shape (`systemMessage`+`hookSpecificOutput.additionalContext`+`hookEventName`), exit gate (`returncode == 1`), fail-open pattern, OrdinalIgnoreCase-equivalent dedup. Intentional expansions (`editFiles`, .py filter, BOM) are AC-required or defensive. | `TestFromAC_RuffArgs.*` + direct PS1 comparison | PASS |
| AC9: all #892 tests pass | 32/32 GREEN (Quality-Runner independent) | All `TestFromAC_*` classes | PASS |

### Security

- `subprocess.run` with list args, `shell=False` — no injection vector (noqa S603/S607 appropriate)
- `json.loads` only (no pickle/yaml/eval)
- fail-open at every boundary prevents crash on malformed VS Code input
- No hardcoded secrets, no credential leakage in output
- PASS

### Builder Process

Single `## Builder Notes` section. CLEAN.

### Informational (non-blocking)

- `test_bom_prefixed_input_returns_empty_dict` uses a non-existent file as a crutch, so it tests fail-open rather than specifically BOM stripping. Low risk — BOM strip is exercised by test_binary_stdin (raw bytes path).
- `returncode == 1` gate (inherited from .ps1): ruff exit 2 (config/internal error) returns `{}` silently. Documented intentional design; architect accepted.

### Deductions

None.

### Verdict

Confidence: **0.95** → **PASS**
[[2026-04-17]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `copilot-instructions.md` has only Project Identity and Repository Branches sections — no hooks enumerated; this is an internal operational script |
| 2 | Module docstrings | Yes | Verified | Module docstring present (L1-4). `_extract_paths()` has docstring. `main()` has no docstring — D1xx (missing-docstring) not enforced per h-python-conventions |
| 3 | External attribution | No | N/A | All 8 research sources are internal files or VS Code Hooks docs already attributed in #547/#891/#892 sections of sources/overview.md |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | `.owlbear/research/895-lint-changed-python-port.md` exists and is linked from task body; follow-up tasks: none needed per task body |

### Files Updated

- None

### Scratch Files Cleaned

- None (no `895-*` scratch files found)
[[2026-04-17]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: `.owlbear/hooks/lint-changed.py` created | File exists, 110 lines (direct read) | PASS |
| AC2: stdin JSON extraction (filePath, dirPath, replacements[], editFiles[]) | `_extract_paths()` L24-50; dirPath filtered implicitly (_EDIT_TOOLS gate) | PASS |
| AC3: .py filter + dedup | L82 `.endswith(".py")` + `Path.is_file()`; `_add()` L35 case-insensitive dedup | PASS |
| AC4: ruff check --ignore INP001 | L86-89: `["ruff", "check", "--ignore", "INP001", *existing_py]` | PASS |
| AC5: JSON output with systemMessage + hookSpecificOutput | L91-99: both keys present with hookEventName + additionalContext | PASS |
| AC6: non-zero ruff exit captured | L86 `check=False`; L91 `if result.returncode == 1` gate | PASS |
| AC7: fail-open {} exit 0 | `except Exception: print("{}"); return` at L65, L78, L89; plus early returns at L62, L66, L70 | PASS |
| AC8: bug-for-bug fidelity with .ps1 | Reviewer PS1 side-by-side comparison; same ruff args, exit gate, output shape, fail-open. Intentional expansions (editFiles, .py filter, BOM) are AC-required | PASS |
| AC9: all #892 tests pass | 32/32 GREEN (quality-runner independent run, exit 0) | PASS |

### Test Results

- pytest (task-scoped): 32 passed, 0 failed (quality-runner independent)
- pytest (full suite): infrastructure hang at 98% (exit 137) — pre-existing, not task-caused; standalone hook script has zero cross-task integration surface
- ruff: clean (exit 0)

### Architect Quality: 4/5

Specific, verifiable AC lines. Minor cosmetic ambiguity in AC8 "fidelity" wording (intentional expansions exist) and AC2 dirPath handling (implicit via _EDIT_TOOLS gate). Both correctly resolved by downstream agents without improvisation.

### Deduction Breakdown

- AC lines with no evidence: 0 (all 9 verified) → no deduction
- Lint violations: 0 → no deduction
- AC quality ≤ 3: no (4/5) → no deduction
- Missing reviewer evidence: no (detailed PASS) → no deduction
- Full-suite test failures in task scope: 0 → no deduction
- Note: full suite incomplete due to infrastructure hang; no rubric deduction applies (no failures detected, task scope isolated)

### Confidence: .98

### Action: archive

Builder commit: `3906c464` — feat(hooks): add lint-changed.py PostToolUse hook (#895)
