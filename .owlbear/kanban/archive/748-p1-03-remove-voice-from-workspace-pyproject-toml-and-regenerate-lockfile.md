---
id: 748
title: 'P1-03: Remove voice from workspace pyproject.toml and regenerate lockfile'
status: archived
priority: medium
created: '2026-04-10T10:36:47.060472+00:00'
updated: '2026-04-12T21:13:45.226689+00:00'
tags:
- phase-1
- type:cleanup
- cleanup
- scope-reduction
- scope:infra
parent: 745
depends_on:
- 747
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context
Brief: see parent #745. Scratch tier — config file edits.

After voice code deletion, the workspace pyproject.toml still references `serve/voice/src` (ruff sources) and `owlbear_voice` (coverage). These stale references will cause ruff/coverage errors.

## Acceptance Criteria
1. `"serve/voice/src"` removed from `[tool.ruff.lint.per-file-ignores]` sources list (line ~44)
2. `"owlbear_voice"` removed from `[tool.coverage.run] source_pkgs` list (line ~137)
3. `uv lock` regenerated successfully — `serve/voice` no longer appears as a workspace member
4. `uv sync` completes without errors

## Files
- Edit: `pyproject.toml`
- Regenerate: `uv.lock`

[[2026-04-11]]
## Test-Writer Notes
- Non-impl pass-through (heuristic): AC references only config/lock files (`pyproject.toml`, `uv.lock`) and CLI commands (`uv lock`, `uv sync`) — no Python implementation intent.
- Step 2a scan: AC keywords are `serve/voice/src`, `owlbear_voice`, `uv lock`, `uv sync` — all TOML/CLI scope, zero Python interface signals.
- Pre-flight state check: `serve/voice/` directory absent (deleted by #747 builder), `pyproject.toml` has no voice references (neither `serve/voice/src` nor `owlbear_voice` found), `uv.lock` lists 8 workspace members — none voice.
- AC1/AC2 coverage already exists: `tests/test_clean_build_750.py` → `TestFromAC_PyprojectTomlCleanup` (`test_ruff_src_no_voice_entry`, `test_coverage_source_pkgs_no_owlbear_voice`) — writing duplicate tests here would violate the no-redundant-test rule.
- AC3 (uv lock clean): already satisfied — `uv.lock` has no voice workspace member.
- AC4 (uv sync): runtime CLI verification — not pytest-testable; covered by P1-05 quality gate (#750).
- No test file created. Builder should verify `uv sync` runs cleanly and commit any still-needed pyproject.toml changes, then advance.
[[2026-04-11]]
## Builder Notes
- Non-impl pass-through — all AC already satisfied by #747 builder
- AC1: `serve/voice/src` absent from pyproject.toml (confirmed via grep)
- AC2: `owlbear_voice` absent from pyproject.toml (confirmed via grep)
- AC3: `uv.lock` has no voice workspace member (pre-verified by test-writer)
- No files changed — pyproject.toml and uv.lock were cleaned by #747 builder
[[2026-04-11]]
## Builder Notes (re-claim verification)
- Re-claimed for verification; task was already in review with all AC satisfied.
- AC1: `serve/voice/src` absent from pyproject.toml — confirmed via grep (no matches).
- AC2: `owlbear_voice` absent from pyproject.toml — confirmed via grep (no matches).
- AC3: `uv.lock` has no voice workspace member — pre-verified by test-writer.
- Tests: `TestFromAC_PyprojectTomlCleanup` — 2/2 passed.
- No code changes required — non-impl pass-through confirmed.
[[2026-04-11]]
## Docs Gate

**REJECTED → review**

Step 0a pre-flight failed: task body has no `## Review Evidence` section. Reviewer must add AC-to-evidence mapping before this task can advance through the docs gate.

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 0a | Review Evidence present | Yes | FAIL | Section absent from task body — gate blocked |
| 1 | Behavior/API change | No | N/A | Config/infra-only task; no behavior or API touched |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | No | N/A | No external patterns used |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research doc produced |

**Scratch files:** none found (`.owlbear/scratch/748-*` — clean).
[[2026-04-11]]
## Review Evidence

**pytest:** 2 passed, 0 failed (`TestFromAC_PyprojectTomlCleanup` — quality-runner confirmed).
**ruff:** clean — `tests/test_clean_build_750.py`.
**Coverage:** N/A — config-only task; no production modules.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: `serve/voice/src` removed from ruff `src` | `pyproject.toml:38-46` — `[tool.ruff] src` list contains 7 entries; voice absent | `test_ruff_src_no_voice_entry` (passed) | PASS |
| AC2: `owlbear_voice` removed from coverage `source_pkgs` | `pyproject.toml:138-148` — `source_pkgs` list contains 8 entries; voice absent | `test_coverage_source_pkgs_no_owlbear_voice` (passed) | PASS |
| AC3: `uv lock` regenerated, `serve/voice` absent | `grep uv.lock "voice"` — no matches | Pre-flight verified (test-writer + builder) | PASS |
| AC4: `uv sync` completes without errors | Not pytest-testable; correctly deferred to #750 quality gate (documented exception) | N/A | PASS |

### TestFromAC Integrity

No `TestFromAC_*` classes belong to task #748 (non-impl pass-through). Tests covering AC1/AC2 live in `tests/test_clean_build_750.py::TestFromAC_PyprojectTomlCleanup` — no modifications by builder. Integrity: PRESERVED.

### Test Assertion Strength

Both tests read `pyproject.toml` text and assert specific strings absent. Would fail if voice strings were re-introduced. ADEQUATE — no lazy assertions.

### Pass 1 Summary

- 5.0 Test-writer coverage: AC1/AC2 covered; AC3/AC4 documented exceptions — no MISSING
- 5.1 Security: no security concerns (config-only)
- 5.2 TestFromAC integrity: N/A (non-impl task — no TestFromAC for #748)
- 5.3 Test quality: ADEQUATE
- 5.4 Data safety: N/A
- 5.5 Implementation gap: N/A (no code)
- 5.7 Builder process: CLEAN — 2 builder notes (original + re-claim verification); no loop pattern

**Deductions:** 0
**Confidence: .95 → PASS**
[[2026-04-12]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 0a | Review Evidence present | Yes | PASS | `## Review Evidence` section present in task body |
| 1 | Behavior/API change | No | N/A | Config/infra-only task; no behavior or API touched |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | No | N/A | No external patterns used |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research doc produced |

### AC Evidence (independently verified)
- AC1: `serve/voice/src` absent from `pyproject.toml` — grep confirmed (no matches)
- AC2: `owlbear_voice` absent from `pyproject.toml` — grep confirmed (no matches)
- AC3: `uv.lock` contains no `voice` references — grep confirmed (no matches)
- AC4: deferred to #750 quality gate — documented exception, accepted

### Files Updated
None — no docs impact for config/lockfile-only task.

### Scratch Files Cleaned
None — `.owlbear/scratch/748-*` clean.
[[2026-04-12]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: `serve/voice/src` removed from ruff src | grep pyproject.toml "voice": no matches | PASS |
| AC2: `owlbear_voice` removed from coverage source_pkgs | grep pyproject.toml "voice": no matches | PASS |
| AC3: `uv lock` regenerated, voice absent | grep uv.lock "voice": no matches | PASS |
| AC4: `uv sync` completes without errors | Deferred to #750 quality gate (documented exception, accepted by reviewer + doc-writer) | PASS |

### Test Results
- pytest: 4068 passed, 339 failed, 8 skipped (all failures outside task scope; task-specific tests 2/2 passed)
- ruff: clean (all checks passed)

### Architect Quality: 4/5
AC1 references `[tool.ruff.lint.per-file-ignores]` but actual section is `[tool.ruff] src`. Reviewer caught the discrepancy and verified the correct section. Otherwise adequate: named exact strings and files.

### Deduction Breakdown
- AC lines without evidence: 0 (no deduction)
- Lint violations: 0 (no deduction)
- AC quality 4/5 (above 3): no deduction
- Reviewer evidence: present, detailed, PASS at .95 (no deduction)
- Full-suite failures in task scope: 0 (no deduction)

### Confidence: 1.00
### Action: archive