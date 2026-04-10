---
id: 794
title: 'Tests: send_image context_key threading'
status: archived
priority: nice-to-have
created: 2026-03-14T02:16:48.8992947+01:00
updated: 2026-03-14T03:53:24.2588491+01:00
started: 2026-03-14T03:53:19.5639905+01:00
completed: 2026-03-14T03:53:19.5639905+01:00
tags:
    - test
    - channels
class: standard
---

Write failing tests for send_image context_key support (#533).

**File:** tests/test_channels.py or tests/test_slack_interactive.py (co-locate with TestThreadRegistryIntegration)

**AC:**
- [ ] Test: send_image accepts context_key kwarg (verify signature)
- [ ] Test: send_image with context_key resolves thread_ts from _thread_registry
- [ ] Test: first send_image with context_key registers ts in _thread_registry (mock files_upload_v2 response)
- [ ] Test: explicit thread_ts takes precedence over context_key
- [ ] Test: error fallback forwards context_key to send()
- [ ] Test: send_image without context_key works as before (regression)
- [ ] All tests FAIL (RED phase  feature not implemented yet)
- [ ] ruff clean

**Pattern:** Follow existing TestThreadRegistryIntegration in test_slack_interactive.py

depends_on: none

[[2026-03-14]] Sat 02:43
## Test-Writer Notes
- Test file: tests/test_slack_interactive.py
- Classes: TestFromAC_SendImageContextKey
- Tests per category: happy 3, edge 1, error 1, boundary 1
- Total: 6 tests, all FAIL
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| send_image accepts context_key kwarg | test_send_image_accepts_context_key_kwarg | happy |
| context_key resolves thread_ts from registry | test_send_image_context_key_resolves_thread_ts | happy |
| first send_image registers ts | test_send_image_first_call_registers_ts | happy |
| explicit thread_ts takes precedence | test_explicit_thread_ts_takes_precedence | boundary |
| error fallback forwards context_key to send() | test_error_fallback_forwards_context_key | error |
| without context_key works as before | test_send_image_without_context_key_regression | edge |

[[2026-03-14]] Sat 02:53
## Builder Notes
- Files changed: src/owlbear/channels/slack.py
- Tests: 30 passed (6 TestFromAC_SendImageContextKey + 24 existing), 0 failed
- Coverage: slack.py 77% (misses are pre-existing unrelated code: receive, connect, disconnect)
- Lint: ruff clean
- Implementation: added context_key param to send_image, thread registry lookup with explicit thread_ts precedence, ts extraction from files_upload_v2 response via _extract_upload_ts helper, context_key forwarding to send() fallback
- Commit: 5cfc403

[[2026-03-14]] Sat 03:14
## Review Evidence
### Test Results
- pytest test_slack_interactive.py: 30/30 passed

### Lint Results
- ruff: All checks passed (slack.py + test_slack_interactive.py)

### Coverage
- slack.py: 77% (128 stmts, 30 miss -- misses are pre-existing: receive, connect, disconnect)

### Pass 1 CRITICAL
#### Security Review
No issues. Placeholders in tests, dict ops + Slack API only, no injection/traversal/deser/PII.

#### TestFromAC Comparison
git diff d4e1013..5cfc403: empty. All 6 TestFromAC tests PRESERVED.

#### Test Quality
Assertion specificity: ADEQUATE, Negative/error-path: ADEQUATE, Mutation reasoning: STRONG, Independence: STRONG, Names: STRONG. No WEAK.

#### Data Safety
No concerns.

### AC Compliance
All 8 AC lines PASS with specific evidence (see task body notes above).

### Verdict: PASS (confidence .93)

[[2026-03-14]] Sat 03:14
## Review Evidence
PASS .93 | 30/30 tests, ruff clean, slack.py 77% (pre-existing misses), all 6 TestFromAC PRESERVED (zero diff d4e1013..5cfc403), security clean, test quality ADEQUATE+, all 8 AC lines satisfied.

[[2026-03-14]] Sat 03:33
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Slack-specific param addition to send_image; no protocol/convention change |
| 2 | Docstrings complete | Yes | Pass | send_image (L187) has full Parameters section documenting thread_ts + context_key; _extract_upload_ts (L241) has docstring |
| 3 | sources/overview.md | No | N/A | No external patterns; uses existing Slack SDK files_upload_v2 API |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | No | N/A | No research phase; test task derived from parent #533 |
| 6 | No impact | -- | -- | Items 1,3,4,5 N/A; item 2 already correct |

### Files Updated
- None

### Scratch Files Cleaned
- Deleted docs/scratch/794-cov.txt

[[2026-03-14]] Sat 03:53
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. send_image accepts context_key kwarg | test_send_image_accepts_context_key_kwarg L520: inspect.signature check | PASS |
| 2. context_key resolves thread_ts from registry | test_send_image_context_key_resolves_thread_ts L537: pre-populates registry, asserts thread_ts | PASS |
| 3. first send_image registers ts | test_send_image_first_call_registers_ts L561: checks registry populated from response | PASS |
| 4. explicit thread_ts takes precedence | test_explicit_thread_ts_takes_precedence L584: sends with both, asserts explicit wins | PASS |
| 5. error fallback forwards context_key | test_error_fallback_forwards_context_key L609: upload raises, send() called, context_key registered | PASS |
| 6. without context_key regression | test_send_image_without_context_key_regression L634: default=None, no thread_ts, empty registry | PASS |
| 7. All tests FAIL (RED phase) | test-writer notes confirm RED; builder made GREEN in 5cfc403 (normal TDD) | PASS |
| 8. ruff clean | ruff check: All checks passed (slack.py + test_slack_interactive.py) | PASS |

### Test Results
- pytest test_slack_interactive.py: 30/30 passed
- Full suite: 5 pre-existing regex collection errors (trafilatura), no new failures
- ruff: clean

### Commits Verified
- d4e1013: test-writer (tests only, 157 lines added)
- 5cfc403: builder (slack.py only, 32 lines added)

### Confidence: .96
### Action: archive
