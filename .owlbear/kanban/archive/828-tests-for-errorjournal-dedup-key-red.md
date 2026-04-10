---
id: 828
title: Tests for ErrorJournal dedup_key (RED)
status: archived
priority: someday
created: 2026-03-15T12:48:37.4790518+01:00
updated: 2026-03-15T12:48:37.4790518+01:00
tags:
    - resilience
    - scope:core
    - type:test
depends_on:
    - 567
class: standard
---

TDD RED phase for #567. Write failing tests for dedup_key feature before implementation.\n\n## AC\n- TestDedupKey class: test dedup_key field exists on ErrorEntry with correct sha256[:16] value\n- test_duplicate_suppressed: two identical log() calls within 60s produce single file entry\n- test_window_expiry: log() after window expires produces new entry (mock time.monotonic)\n- test_different_keys: two different errors within window both logged\n- test_cache_eviction: >128 unique errors evict oldest, new dedup still works\n- test_existing_entries_load: JSONL without dedup_key field loads with default empty string\n- test_rotation_compat: dedup + rotation interact correctly\n- test_dedup_window_configurable: custom dedup_window_seconds honored\n- All tests FAIL before implementation (RED phase)\n- See docs/research/error-journal-dedup.md
