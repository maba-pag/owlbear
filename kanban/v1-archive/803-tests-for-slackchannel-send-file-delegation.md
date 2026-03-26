---
id: 803
title: Tests for SlackChannel.send_file delegation
status: archived
priority: nice-to-have
created: 2026-03-14T04:35:03.2011777+01:00
updated: 2026-03-14T11:23:11.713307+01:00
started: 2026-03-14T11:23:05.25338+01:00
completed: 2026-03-14T11:23:05.25338+01:00
tags:
    - channels
    - type:test
class: standard
---

AC:
- [ ] Test file: tests/test_slack_channel.py (extend existing) or tests/test_slack_send_file.py
- [ ] TestFromAC_ naming convention
- [ ] Happy path: send_file(Path('report.pdf'), caption='Report') delegates to send_image
- [ ] Caption forwarding: send_image called with caption='Report'
- [ ] No-caption default: send_file(Path('data.csv')) delegates with caption='data.csv' (path.name)
- [ ] Error fallback: when send_image raises, send_file propagates (no double fallback)
- [ ] Signature match: send_file(self, path: Path, *, caption: str | None = None) -> None
- [ ] All tests FAIL before implementation (RED phase)
- [ ] Ruff clean
Depends on: nothing (test-first)

[[2026-03-14]] Sat 05:05
## Test-Writer Notes
- Test file: tests/test_slack_send_file.py
- Classes: TestFromAC_SendFileDelegation, TestFromAC_SendFileNoCaptionDefault, TestFromAC_SendFileErrorPropagation, TestFromAC_SendFileSignature
- Tests per category: happy 2, edge 3, error 2, boundary 3
- Total: 10 tests, all FAIL
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| Happy path: send_file delegates to send_image | test_send_file_delegates_to_send_image_with_caption | happy |
| Caption forwarding | test_send_file_caption_forwarded_to_send_image | happy |
| No-caption default uses path.name | test_no_caption_uses_path_name, test_no_caption_nested_path_uses_filename_only, test_explicit_none_caption_uses_path_name | edge |
| Error fallback: propagates, no double fallback | test_send_image_error_propagates, test_no_fallback_to_send_on_error | error |
| Signature match: override + params | test_send_file_is_overridden_on_slack_channel, test_send_file_signature_has_path_param, test_send_file_signature_has_keyword_only_caption | boundary |

[[2026-03-14]] Sat 10:16
## Builder Notes
- Files changed: src/owlbear/channels/slack.py (send_file method added, 8 lines)
- Tests: 10 passed (all TestFromAC), 0 failed
- Coverage: send_file fully covered
- Lint: ruff clean
- Commit: 298357a (included in #802 builder commit)
- No TestFromAC classes modified

-t

[[2026-03-14]] Sat 10:46
## Review Evidence

### Test Results
- pytest: 10 passed, 0 failed
- All TestFromAC tests pass

### Lint Results
- ruff: All checks passed!

### Coverage
- slack.py send_file (L190-197): fully covered

### Pass 1 -- CRITICAL

#### Security Review
- No security issues. Thin delegation method.

#### Test Integrity
- Test file: 1 commit only (79e30e1, test-writer). Builder never touched it.
- All 4 TestFromAC classes (10 methods): PRESERVED

#### Test Quality
- Assertion specificity: STRONG
- Negative/error paths: ADEQUATE
- Mutation reasoning: STRONG
- Test independence: STRONG
- Descriptive names: STRONG

#### Data Safety
- No data safety issues.

### Verdict: PASS
### Confidence: .95

-t
