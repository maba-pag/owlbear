---
id: 533
title: Fix send_image kwargs to support context_key threading
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:38.4297337+01:00
updated: 2026-03-07T00:28:21.5501773+01:00
started: 2026-03-07T00:26:12.9492444+01:00
tags:
    - audit
    - code-quality
    - channels
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
