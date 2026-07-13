---
id: 1021
title: 'P0-05: deny-code-writes.py refactor (GREEN)'
status: archived
priority: medium
created: 2026-04-19 23:51:49.154972+00:00
updated: 2026-04-20 01:58:19.766303+00:00
tags:
- phase-0
- docs-currency
- docs-tooling
parent: 1016
depends_on:
- 1019
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1016

## Acceptance Criteria

- [ ] `.owlbear/hooks/deny-code-writes.py` refactored from directory deny-list to extension-based allowlist
- [ ] Owlbear-dev variant allows: `.md`, `.excalidraw`, `.py` (for docstring edits)
- [ ] `seed/.owlbear/hooks/deny-code-writes.py` is the strict consumer-seed variant: `.md` + `.excalidraw` only
- [ ] `setup/init.py` updated if hook copy logic changes
- [ ] All P0-04 tests pass (GREEN)
- [ ] No legacy directory deny-list logic remains

## Files

- Modifies: `.owlbear/hooks/deny-code-writes.py`, `seed/.owlbear/hooks/deny-code-writes.py`
- May modify: `setup/init.py`
- Reference: Brief section 4.7
[[2026-04-20]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: refactor deny-list → extension allowlist |
| Interface clarity | PASS | AC specifies both variants, allowed extensions, edge cases |
| Dependency correctness | PASS | Depends on #1019 (RED tests) — archived/done |
| Module layering | PASS | Standalone hook scripts, no cross-package deps |
| TDD compliance | PASS | RED tests exist in `tests/test_deny_code_writes.py` (#1019) |
| KISS/YAGNI | PASS | Minimal scope — allowlist set + extension check |
| Premise challenge | PASS | Refactor serves real need: directory deny-list was brittle |
| Pattern consistency | PASS | Follows existing hook patterns (`deny-src-writes.py`, etc.) |
| Security surface | PASS | This IS a security control; allowlist behavior properly specified |
| Single domain | PASS | docs-tooling only |

### Codebase Analysis

- **Dev hook** (`.owlbear/hooks/deny-code-writes.py`): Already refactored — `_ALLOWED_EXTENSIONS = {".md", ".excalidraw", ".py"}`, no deny-list remnants.
- **Seed hook** (`seed/.owlbear/hooks/deny-code-writes.py`): Already refactored — `_ALLOWED_EXTENSIONS = {".md", ".excalidraw"}`, stricter variant.
- **`setup/init.py`**: Uses generic `shutil.copy2` for non-JSON/YAML seed files (line 289). No hook-specific copy logic — AC4 conditional satisfied (no changes needed).
- **Tests**: 6 test classes in `tests/test_deny_code_writes.py` covering AC1–AC6 with both variants.
- **Other hooks**: `deny-src-writes.py`, `deny-scratch-only-writes.py` — no conflict or overlap.

### Implementation Note

Both hook files already contain the refactored allowlist code. The builder will verify all tests pass GREEN and confirm no further changes are needed. Compressed TDD cycle — implementation was co-delivered with or before RED phase.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: dev hook refactored to allowlist | Verifiable — check `_ALLOWED_EXTENSIONS` set | None |
| AC2: dev allows .md, .excalidraw, .py | Verifiable — test class `TestFromAC_OwlbearDevHook` | None |
| AC3: seed allows .md, .excalidraw only | Verifiable — test class `TestFromAC_ConsumerSeedHook` | None |
| AC4: setup/init.py updated if needed | Conditional — no changes needed (generic copy) | None |
| AC5: all P0-04 tests pass | Verifiable — `pytest tests/test_deny_code_writes.py` | None |
| AC6: no legacy deny-list logic | Verifiable — grep for denied prefixes/dirs | None |

### Challenge Results

- Challenger: reconsider (confidence 0.45)
- C1 (`apply_patch` bypass): **Rebutted** — research doc `.owlbear/research/deny-code-writes-ac-validation-637.md` confirms `apply_patch` uses `tool_input.filePath` (verified by #546 tests). `_extract_paths` handles this.
- C2 (implementation already complete): **Acknowledged** — code is pre-implemented, builder verifies GREEN. Not blocking.
- C3 ("for docstring edits" wording): **Acknowledged** — parenthetical is explanatory, not an enforced constraint. Minor.
- Architect response: C1 rebutted with evidence. C2/C3 accepted as observations. Adjusted confidence: 0.82 → proceed.

### Verdict: APPROVE
### Action Taken: Advanced to todo. All AC lines are precise and verifiable. Implementation appears pre-delivered; builder confirms tests pass GREEN.
[[2026-04-20]]
## Test-Writer Notes
- Compressed TDD cycle: RED tests written in #1019, implementation co-delivered before this task reached todo.
- Test file: `tests/test_deny_code_writes.py`
- Classes: `TestFromAC_OwlbearDevHook`, `TestFromAC_ConsumerSeedHook`, `TestFromAC_VariantDivergence`, `TestFromAC_EdgeCasesExtensionless`, `TestFromAC_NonWritePassthrough`, `TestFromAC_InputShapes`
- Tests per category: happy 5, edge 10, error 6, boundary 10
- Total: 31 tests, **all PASS** (implementation pre-delivered)
- AC coverage: AC1–AC3 → behavioral tests; AC4 → edge cases; AC5 → passthrough (non-write); AC6 → input shape variants
- AC4 (setup/init.py): no changes needed per arch review — generic `shutil.copy2` used; no test required
- AC5 (all P0-04 tests pass GREEN): confirmed — `pytest tests/test_deny_code_writes.py` → 31 passed, 0 failed
- AC6 (no legacy deny-list logic): verifiable by builder via grep; no dedicated test needed
- No new tests written — existing test suite is complete and GREEN; passing through to builder for final GREEN verification and commit.
[[2026-04-20]]
## Builder Notes

### Files Changed
- None — implementation pre-delivered in commit `fac8bc36` (refactor: replace deny-list with extension allowlist in deny-code-writes hooks)
- Tests committed in `eed1b979`

### Verification Evidence
- **RED check skipped** — implementation was pre-delivered before task reached in-progress (per arch review note + test-writer notes). Consistent with compressed TDD cycle acknowledged in both notes.
- **Test results**: `pytest tests/test_deny_code_writes.py -v --tb=short` → **31 passed, 0 failed**
  - `TestFromAC_OwlbearDevHook`: 9 passed
  - `TestFromAC_ConsumerSeedHook`: 7 passed
  - `TestFromAC_VariantDivergence`: 2 passed
  - `TestFromAC_EdgeCasesExtensionless`: 4 passed
  - `TestFromAC_NonWritePassthrough`: 3 passed
  - `TestFromAC_InputShapes`: 6 passed
- **Lint**: `ruff check` → all checks passed, 0 issues
- **AC6 (no legacy logic)**: grep for `DENIED_PREFIXES|denied_prefixes|deny_list|DENY_LIST` in both hook files → no matches

### AC Coverage
- AC1: dev hook uses `_ALLOWED_EXTENSIONS = {".md", ".excalidraw", ".py"}` — PASS
- AC2: seed hook uses `_ALLOWED_EXTENSIONS = {".md", ".excalidraw"}` — PASS
- AC3: variant divergence confirmed by `TestFromAC_VariantDivergence` — PASS
- AC4: `setup/init.py` — no changes needed (generic `shutil.copy2`, confirmed by arch review)
- AC5: all 31 P0-04 tests pass — PASS
- AC6: no legacy deny-list logic found in either hook — PASS
[[2026-04-20]]
## Review Evidence

### Test Results
- pytest: 31 passed, 0 failed (quality-runner independent run)

### Lint
clean — 0 violations

### Coverage
N/A — hook scripts are standalone non-importable Python files; no coverage tooling applies. Not a deduction.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: dev hook refactored to allowlist | `TestFromAC_OwlbearDevHook` (all 9) | Yes — `test_denies_ts_extension` would fail if deny-list logic persisted; `test_allows_md_file_inside_denied_prefix` would fail if extension check missing | COVERED |
| AC2: dev allows .md, .excalidraw, .py | `TestFromAC_OwlbearDevHook::test_allows_py_file_inside_denied_prefix`, `test_allows_md_file_inside_denied_prefix`, `test_allows_excalidraw_inside_denied_prefix` | Yes — each ALLOW test would fail if extension removed from set | COVERED |
| AC3: seed variant .md + .excalidraw only | `TestFromAC_ConsumerSeedHook::test_denies_py_extension`; `TestFromAC_VariantDivergence` (both) | Yes — divergence tests fail if variants match; consumer deny test fails if .py added to seed | COVERED |
| AC4: setup/init.py conditional | No code change required; extensionless/create_directory edge cases covered by `TestFromAC_EdgeCasesExtensionless` (4 tests) | Yes for edge cases — DENY tests would fail if extensionless files allowed | COVERED |
| AC5: all P0-04 tests pass GREEN | All 31 `TestFromAC_*` tests | By definition — quality-runner confirms 31/31 pass | COVERED |
| AC6: no legacy deny-list logic | `TestFromAC_OwlbearDevHook` deny tests exercise paths that old deny-list code would handle differently | Yes — legacy code would pass `.ts` in `share/docs/` which tests expect DENIED | COVERED |

#### Security Review
- No hardcoded secrets
- No injection risk — JSON parsed with `json.loads()`, no interpolation into templates or shell
- No path traversal — `_normalize()` strips `\\`/`./` prefixes; `Path.suffix` used for read-only extension extraction only
- No insecure deserialization — standard library `json` only
- Input validation: all `.get()` with defaults; `isinstance` guards on all path extraction; empty string filtered by `and fp`; malformed JSON returns `{}` (fail-open passthrough, not a regression from prior behavior)
- Hook IS a security control — allowlist correctly enforces write restrictions; no bypass vectors identified
- No security findings

#### Test Integrity (TestFromAC modifications)
Builder made zero code changes (implementation was pre-delivered). No TestFromAC_ methods modified, weakened, or removed.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 31 TestFromAC_* methods | None | PRESERVED |

#### Test Quality
- Assertion specificity: **STRONG** — tests verify exact `{"decision": "block", ...}` dict for DENY and `{}` for ALLOW/passthrough; no lazy `assert result` patterns
- Negative/error paths: covered — DENY tests for every extension type; non-write passthrough for AC5
- Mutation resilience: flipping any extension in `_ALLOWED_EXTENSIONS` would cause at least one test failure per AC; removing allowlist logic entirely would fail all deny tests
- Test independence: no shared mutable state; each test constructs its own JSON payload
- Descriptive names: all test names read as behavioral specs (e.g., `test_allows_py_file_inside_denied_prefix`, `test_py_write_diverges_between_variants`)
- Overall: **STRONG**

#### Data Safety
No shared state, no persistence, no database ops. Clean.

#### Implementation-Aware Test Gap Analysis
Three minor untested paths identified (all low-risk):
1. JSON decode error → gracefully returns `{}` (not an AC requirement; fail-open is pre-existing behavior)
2. Uppercase extension (`.PY`, `.MD`) → handled by `.lower()`, not explicitly tested
3. Empty string path in filePath field → filtered by `and fp`, not explicitly tested
None are significant untested paths per AC scope.

#### Builder Process Quality
Single pass, no retries. CLEAN.

### Pass 2 — INFORMATIONAL
- Minor: uppercase extension normalization not explicitly tested (handled correctly by `.lower()`)
- Minor: double-extension filenames (e.g., `evil.ts.md`) pass the `.md` extension check — inherent limitation of extension-based approach; not introduced by this change; matches behavior of other hooks in codebase

### AC Compliance Table
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: dev hook → allowlist | `_ALLOWED_EXTENSIONS = {".md", ".excalidraw", ".py"}` in `.owlbear/hooks/deny-code-writes.py`; no DENIED_PREFIXES/deny_list vars | `TestFromAC_OwlbearDevHook` | PASS |
| AC2: dev allows .md, .excalidraw, .py | Same file; each extension explicitly in set | `test_allows_py/md/excalidraw_file_inside_denied_prefix` | PASS |
| AC3: seed .md + .excalidraw only | `_ALLOWED_EXTENSIONS = {".md", ".excalidraw"}` in `seed/.owlbear/hooks/deny-code-writes.py`; `.py` absent | `TestFromAC_ConsumerSeedHook::test_denies_py_extension`; `TestFromAC_VariantDivergence` | PASS |
| AC4: setup/init.py (conditional) | Architect confirmed `shutil.copy2` generic copy; no hook-specific logic to change | `TestFromAC_EdgeCasesExtensionless` (extensionless/create_directory) | PASS |
| AC5: all tests GREEN | 31/31 passed (quality-runner independent) | All TestFromAC_* | PASS |
| AC6: no legacy deny-list logic | No `DENIED_PREFIXES`/`denied_prefixes`/`deny_list`/`DENY_LIST` in either hook file | `TestFromAC_OwlbearDevHook` deny tests | PASS |

### Deductions
- None. All Pass 1 criteria met. Minor informational gaps noted but none approach FAIL threshold.

### Verdict
Confidence: .96 → **PASS**
Action: advance to docs
[[2026-04-20]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `.github/copilot-instructions.md` covers Cockpit only — no hook behavior tables. `doc-writer.agent.md` references the hook as a command path only, not its allowed extensions. No documentation describes the allowlist configuration. |
| 2 | Module docstrings | Yes | Verified | Both hook files have accurate module-level docstrings describing their variant and allowed extensions. Dev variant: `.md`, `.excalidraw`, `.py`; seed variant: `.md`, `.excalidraw` only. `_is_denied` has inline docstring. `main()` is a script entry point covered by module docstring. All accurate. |
| 3 | External attribution | No | N/A | Refactor based on prior internal research (#637). `.owlbear/sources/overview.md` already contains attribution entries for all sources used in #637 research. No new external sources introduced by this task. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/deny-code-writes-ac-validation-637.md` exists. Referenced in `## Architecture Review` section of task body (arch review rebuttal C1). Follow-up tasks were not applicable — research was prior work. |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1021-*` files found)
[[2026-04-20]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: dev hook → allowlist | `_ALLOWED_EXTENSIONS = {".md", ".excalidraw", ".py"}` in `.owlbear/hooks/deny-code-writes.py` L33; `_is_denied()` checks suffix against allowlist | PASS |
| AC2: dev allows .md, .excalidraw, .py | Same file L33 — exact set verified by direct read | PASS |
| AC3: seed .md + .excalidraw only | `_ALLOWED_EXTENSIONS = {".md", ".excalidraw"}` in `seed/.owlbear/hooks/deny-code-writes.py` L33; `.py` absent | PASS |
| AC4: setup/init.py conditional | No changes needed — generic `shutil.copy2` (arch review confirmed) | PASS |
| AC5: all tests pass GREEN | quality-runner full suite: 797 passed; 31 task tests in `test_deny_code_writes.py` all pass; 6 failures in mcp-knowledge (unrelated) | PASS |
| AC6: no legacy deny-list logic | grep `DENIED_PREFIXES|denied_prefixes|deny_list|DENY_LIST` → 0 matches in both hook files | PASS |

### Test Results
- pytest: 797 passed, 6 failed (all in `serve/mcp-knowledge/tests/` — unrelated to task scope), 4 skipped
- ruff: clean — 0 violations

### Architect Quality: 4/5
AC lines were specific and independently verifiable. AC4 conditional correctly handled. Minor: AC5 partially redundant with overall GREEN verification. No significant builder improvisation required.

### Deduction Breakdown
- AC lines with no evidence: 0 (all 6 verified)
- Lint violations: 0
- AC quality ≤ 3: N/A (score 4)
- Missing reviewer evidence: 0 (detailed, PASS at .96, security review included)
- Full-suite failures in task scope: 0

### Confidence: 1.00
### Action: archive

### Upstream Commits
- `fac8bc36` — implementation (refactor: replace deny-list with extension allowlist)
- `eed1b979` — tests