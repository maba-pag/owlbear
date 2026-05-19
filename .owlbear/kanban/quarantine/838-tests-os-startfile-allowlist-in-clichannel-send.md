---
id: 838
title: 'Tests: os.startfile allowlist in CLIChannel.send_file'
status: archived
priority: nice-to-have
created: 2026-03-16T12:36:36.7215574+01:00
updated: 2026-03-16T21:43:05.0958779+01:00
started: 2026-03-16T21:41:52.1360793+01:00
completed: 2026-03-16T21:41:52.1360793+01:00
tags:
    - test
    - security
    - scope:cli
depends_on:
    - 527
class: standard
---

TDD RED tests for #527. Test the os.startfile extension allowlist in CLIChannel.send_file. See docs/research/startfile-allowlist.md for context.

AC:

- Test safe extension (.png) calls os.startfile on Windows
- Test unsafe extension (.exe) does NOT call os.startfile
- Test unsafe extension still prints path to output (graceful degradation)
- Test unsafe extension logs warning with blocked suffix
- Test case-insensitive check (.PNG same as .png)
- Test no-extension file is blocked
- Test send_image(Path) inherits the allowlist guard (delegates to send_file)

Target file: tests/test_channels.py (extend existing TestCLIChannelSendFile class or add new class)
Impl file: src/owlbear/channels/cli.py

[[2026-03-16]] Mon 14:42

## Test-Writer Notes\n- Test file: tests/test_channels.py\n- Class: TestFromAC_StartfileAllowlist\n- Total: 8 tests, all FAIL (ImportError or AssertionError) checked\n- ruff: clean\n- AC coverage: safe ext constant (2 tests), unsafe no-startfile, unsafe prints path, warning logged, case-insensitive, no-ext blocked, send_image guard

[[2026-03-16]] Mon 20:27

## Builder Notes

- Files changed: src/owlbear/channels/cli.py
- Tests: 47 passed in tests/test_channels.py (includes 8/8 TestFromAC_StartfileAllowlist)
- Coverage: 100% on src/owlbear/channels/cli.py (scoped run with bare --cov)
- Lint: ruff check src/owlbear/channels/cli.py tests/test_channels.py passed
- Evidence: RED before implementation: 8 failed (ImportError for SAFE_EXTENSIONS + allowlist behavior assertions). GREEN after implementation: 47 passed.
- Fixes applied: Added SAFE_EXTENSIONS allowlist and guarded Windows os.startfile behind case-insensitive suffix check; blocked extensions now log WARNING including the suffix and still print path.
- Notes: Full-repo ruff check currently has unrelated pre-existing violations outside this task scope.

[[2026-03-16]] Mon 20:42

## Review Evidence

See full review in task body (already appended).

[[2026-03-16]] Mon 20:55

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Internal security fix to CLIChannel, not a daemon capability change |
| 2 | Docstrings complete | Yes | Pass | All public methods in cli.py have docstrings; send_file documents Windows/allowlist behavior; SAFE_EXTENSIONS exposed with clear name |
| 3 | sources/overview.md | No | N/A | Research attribution already added during #527 research phase (Python docs, OWASP guidance) |
| 4 | README.md | No | N/A | Not a CLI or user-facing feature; internal channel security fix |
| 5 | Research doc linked | Yes | Pass | docs/research/startfile-allowlist.md referenced in task body |

### Files Updated

- None  docstrings were already present and complete

### Scratch Files Cleaned

- None  no scratch files created

### Summary

Task #838 adds TDD RED tests for the os.startfile allowlist security feature (#527). All 8 tests pass, covering safe/unsafe extensions, case-insensitivity, graceful degradation, warning logging, and send_image delegation. Docstrings in cli.py are complete. No documentation updates needed  this is an internal security fix with comprehensive coverage.

[[2026-03-16]] Mon 21:42

## Audit

### AC: 7/7 PASS  Confidence: .98  Action: archived
