---
id: 533
title: Fix send_image kwargs to support context_key threading
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:38.4297337+01:00
updated: 2026-03-22T19:17:38.4515853+01:00
started: 2026-03-07T00:26:12.9492444+01:00
completed: 2026-03-22T19:17:38.4515853+01:00
tags:
    - audit
    - code-quality
    - channels
blocked: true
block_reason: 'Superseded by archived #794; src/owlbear/channels/slack.py and tests/test_slack_interactive.py already satisfy the AC'
class: standard
---

F-23: Slack send_image handles thread_ts but ignores context_key, breaking thread auto-creation for images.

**Research:** N/A - trivial parameter addition following existing pattern in send/send_blocks.

**Current state:**
- send (L101): accepts context_key, resolves via _thread_registry, registers new threads.
- send_blocks (L132): accepts both thread_ts and context_key with priority to thread_ts. Registers new threads.
- send_image (L178): accepts only thread_ts. No context_key. No registry lookup or registration.

**Fix (src/owlbear/channels/slack.py, send_image method):**
1. Add context_key: str | None = None kwarg.
2. If explicit thread_ts given, use it (existing). Else if context_key given, look up _thread_registry.
3. After successful upload, register response ts to _thread_registry if context_key set and not yet registered.
4. Note: files_upload_v2 returns different structure than chat_postMessage - extract ts from response['file']['shares'].
5. Error fallback send() call should forward context_key.

**AC:**
- [ ] send_image accepts context_key parameter
- [ ] context_key resolves thread_ts from _thread_registry
- [ ] Successful upload registers ts in _thread_registry when context_key provided
- [ ] Explicit thread_ts takes precedence over context_key
- [ ] Error fallback forwards context_key to send()
- [ ] 4+ new tests covering above scenarios

See docs/code-quality-audit.md F-23.

[[2026-03-21]] Sat 04:47
## Architecture Review
**Verdict:** Refine (stale duplicate; blocked in backlog)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| send_image accepts context_key parameter | Already satisfied in src/owlbear/channels/slack.py:208; the current task description is stale relative to repo state. | Do not route to builder. |
| context_key resolves thread_ts from _thread_registry | Already satisfied in src/owlbear/channels/slack.py:241-244 and exercised by tests/test_slack_interactive.py:540. | Treat as already implemented. |
| Successful upload registers ts in _thread_registry when context_key provided | Already satisfied in src/owlbear/channels/slack.py:256-260 via _extract_upload_ts() and covered by tests/test_slack_interactive.py:563 plus extraction-failure cases at :677 onward. | No new implementation task needed. |
| Explicit thread_ts takes precedence over context_key | Already satisfied in src/owlbear/channels/slack.py:239-244 and verified by tests/test_slack_interactive.py:586. | No new implementation task needed. |
| Error fallback forwards context_key to send() | Already satisfied in src/owlbear/channels/slack.py:253 and verified by tests/test_slack_interactive.py:615. | No new implementation task needed. |
| 4+ new tests covering above scenarios | Already exceeded: archived task #794 added 6 tests in tests/test_slack_interactive.py:523-668, then reviewer and auditor verified them. | Treat #533 as superseded by the archived execution path. |

### Architecture Notes
- Single-domain check: yes. This is strictly a Slack channels/thread-registry concern.
- Pattern check: current implementation follows the existing send()/send_blocks() thread registry contract in src/owlbear/channels/slack.py, so no architectural mismatch remains.
- TDD check: already satisfied through archived test task #794, which contains RED notes, builder notes (commit 5cfc403), review evidence, and audit verification for this exact behavior.
- Origin: docs/code-quality-audit.md:282 recorded a valid recommendation, but the repository now satisfies it. Routing #533 into todo would duplicate completed work.
- Decision: keep the task out of builder flow and block it for board cleanup/closure instead of approving a second implementation pass.

### Changes Made
- Claimed task #533 as fern-ivory.
- Appended this Architecture Review section.
- Added an explicit block reason so planners do not redispatch already-completed work.

### Dependencies
- Verified: archived task #794 is the executable TDD/audit trail for this behavior.
- Verified: current repo state in src/owlbear/channels/slack.py and tests/test_slack_interactive.py satisfies the AC.
- Added/Removed: none.
