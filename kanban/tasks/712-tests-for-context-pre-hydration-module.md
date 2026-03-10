---
id: 712
title: Tests for context pre-hydration module
status: archived
priority: important
created: 2026-03-09T15:30:48.2246205+01:00
updated: 2026-03-10T03:03:02.2868496+01:00
started: 2026-03-10T02:29:15.0188591+01:00
completed: 2026-03-10T03:03:02.2868496+01:00
tags:
    - phase-research
    - scope:core
    - test
    - agent
claimed_by: writer
claimed_at: 2026-03-10T02:29:15.0188591+01:00
class: standard
---

RED-phase tests for context pre-hydration (#703). Tests must exist and fail before implementation begins.

Reference: #703 AC defines the module interface (function signatures, types, error behavior).

AC:
- [ ] Test URL extraction from task body text (http/https links, markdown links)
- [ ] Test file path extraction from task body text (absolute, relative, workspace-scoped)
- [ ] Test URL fetching with httpx+trafilatura (mock HTTP, success + timeout + error)
- [ ] Test file reading (existing file, missing file, path-escape attempt blocked)
- [ ] Test URL safety guard integration (blocked URL rejected, allowed URL passes)
- [ ] Test workspace confinement (paths outside workspace rejected)
- [ ] Test max_content_bytes budget truncation (content exceeding budget is trimmed)
- [ ] Test full hydrate() pipeline returns HydrationResult with urls, files, errors
- [ ] All tests fail (RED phase) prior to implementation

Module under test: owlbear.core.context_hydration
Test file: tests/test_context_hydration.py

[[2026-03-09]] Mon 17:05
## Architecture Review
**Verdict:** APPROVED (after refinement)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Test URL extraction | Clear: input text, output list[str]. Well-scoped | Keep |
| Test file path extraction | Clear: uses sandbox_path from paths.py | Keep |
| Test URL fetching (mock) | Clear: mock httpx + trafilatura, 3 scenarios | Keep |
| Test file reading | Clear: existing/missing/escape | Keep |
| Test URL safety guard | Clear: url_checker callable DI | Keep |
| Test workspace confinement | Clear: PermissionError from sandbox_path | Keep |
| Test max_tokens budget | WRONG NAME: #703 uses max_content_bytes, not max_tokens | Renamed to max_content_bytes |
| Test config toggle | MISPLACED: config toggle is in OwlBearSettings, checked at daemon/bootstrap layer. Module hydrate() has no config param | Removed |
| Test hydrate() pipeline | Clear: HydrationResult with urls, files, errors | Keep |
| All tests fail (RED) | Standard RED phase constraint | Keep |

### Architecture Notes
- **Circular dependency fixed:** #712 had depends_on:[703] but #703 already depends_on:[712]. Removed from #712.
- **Config toggle removed:** prehydration_enabled lives in OwlBearSettings (config.py). The daemon/bootstrap layer checks it before calling hydrate(). The context_hydration module itself is config-unaware -- pure functions. Config integration testing belongs in #703's daemon integration tests.
- **Parameter naming:** Corrected max_tokens -> max_content_bytes to match #703's interface spec (max_content_bytes: int = 50_000).
- **Module layering:** Tests import from owlbear.core.context_hydration (valid). Module imports only owlbear.paths (leaf). No layering violations.
- **Patterns to follow:** sandbox_path() for confinement (src/owlbear/paths.py L14-36). trafilatura.extract(output_format='markdown', include_links=True) per content_extractor.py and web_search.py. url_checker is Callable[[str], None] raising ValueError on reject.

### Changes Made
- Removed depends_on:[703] from #712 (circular dependency fix)
- Rewrote body: renamed max_tokens -> max_content_bytes, removed config toggle AC, added reference to #703 for interface spec
- Moved to todo

### Dependencies
- Removed: #703 (was circular -- #703 already depends on #712)
- Verified: #703 has depends_on:[712] (correct direction: impl waits for tests)
- Verified: sandbox_path in paths.py (leaf module, exists)
- Verified: trafilatura patterns in content_extractor.py and web_search.py

[[2026-03-09]] Mon 17:32
## Test-Writer Notes
- Test file: tests/test_context_hydration.py
- Classes: TestFromACExtractUrls, TestFromACExtractFilePaths, TestFromACFetchUrl, TestFromACReadFileSafe, TestFromACWorkspaceConfinement, TestFromACMaxContentBytesBudget, TestFromACHydratePipeline
- Tests per category: happy 20, edge 7, error 7, boundary 5
- Total: 39 tests, all FAIL (ImportError)
- ruff: clean

[[2026-03-09]] Mon 17:58
## Builder Notes
- Files changed: src/owlbear/core/context_hydration.py (NEW), tests/test_context_hydration.py (added TestBuilderDiscovered + import fix)
- Tests: 44 passed, 1 failed (test_relative_path fixture bug)
- Coverage: 95% on context_hydration.py
- Lint: ruff clean
- Evidence: 38/39 TestFromAC pass; 6 TestBuilderDiscovered pass
- Fixture bug: test_relative_path calls (tmp_path/src/module.py).mkdir() creating a directory named module.py, then .write_text() fails with PermissionError. Fix: should be (tmp_path/src).mkdir().

-t

[[2026-03-09]] Mon 19:47
## Review Evidence
See docs/scratch/712-reviewer.md for full evidence.

[[2026-03-09]] Mon 19:47
## Review Evidence

[[2026-03-09]] Mon 19:47
## Review Evidence
See docs/scratch/712-reviewer.md for full evidence.

[[2026-03-09]] Mon 22:59
## Test-Writer Notes (repair pass)
Fixed fixture bug at line 98: (tmp_path / src / module.py).mkdir() created a directory named module.py instead of a file. Now correctly creates src/ directory then writes module.py file.
Removed TestBuilderDiscovered class (builder's responsibility).
- Test file: tests/test_context_hydration.py
- Classes: TestFromACExtractUrls, TestFromACExtractFilePaths, TestFromACFetchUrl, TestFromACReadFileSafe, TestFromACWorkspaceConfinement, TestFromACMaxContentBytesBudget, TestFromACHydratePipeline
- Tests: 39 total, ruff clean
- Note: implementation module exists (untracked) from prior rejected round -- tests pass against it. Original RED phase verified all 39 fail (ImportError) in first round.

[[2026-03-10]] Tue 01:33
## Builder Notes (round 2)
- Files changed: tests/test_context_hydration.py (added TestBuilderDiscovered + httpx import)
- src/owlbear/core/context_hydration.py: UNCHANGED from prior round
- Tests: 45 passed (39 TestFromAC + 6 TestBuilderDiscovered), coverage 95% on context_hydration.py
- Lint: ruff clean
- TestFromAC not modified
- Round 2 fixes: added 6 builder-discovered tests covering generic HTTPError, hydrate URL success path, url_checker ValueError in pipeline, file/URL budget exhaustion, URL content truncation

[[2026-03-10]] Tue 02:29
## Review Evidence (round 2)

### Test Results
- N/A  documentation-only task, no .py files changed

### Lint Results
- N/A  no .py files changed (confirmed via git diff --name-only: only SECURITY.md and .github/copilot-instructions.md)

### Coverage
- N/A  no .py files changed

### Security Review
- SECURITY.md itself is a documentation file. No code changes. No secrets, injection, or vulnerability concerns.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| (1) SECURITY.md Shell Execution section | SECURITY.md L1-L33: 'Shell Execution' section documents create_subprocess_shell by design (L9-10), CommandSafetyGuard as defense-in-depth not security boundary (L18-20), approval gate referenced as primary (L9, detailed in Mitigations L40-48), 4 bypass vectors listed (L24-28: base64, alt tools, chaining, env var expansion). Note: AC says 'double-spacing' but doc lists 'env var expansion'  same substitution accepted in round 1 as a more realistic vector. | PASS |
| (2) SECURITY.md Mitigations section | SECURITY.md L35-L79: layered defense with 3 numbered subsections  (1) Approval gate L40-52, (2) CommandSafetyGuard L54-67, (3) Workspace confinement L69-82. All three controls documented with implementation details. | PASS |
| (3) SECURITY.md Future Considerations | SECURITY.md L84-L105: allowlist mode evaluated with 3 pros (fail-closed, harder to bypass, per-project), 4 cons (limits autonomy, maintenance, shell features, frustration), decision (not implemented, reconsider for multi-user). | PASS |
| (4) copilot-instructions.md Safety row refs SECURITY.md | copilot-instructions.md L54: Safety row now ends with '. See `SECURITY.md`'. Confirmed via git diff: single-line change appending the reference. **Previously FAILED in round 1  now fixed.** | PASS |
| (5) ruff clean on changed .py files | No .py files changed  N/A. | PASS |

### Verdict: PASS confidence .93
