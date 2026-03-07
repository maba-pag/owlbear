---
id: 610
title: Auto-skip test files with missing optional dependencies
status: archived
priority: critical
created: 2026-03-07T03:08:55.8043934+01:00
updated: 2026-03-07T18:08:19.3552132+01:00
started: 2026-03-07T04:59:28.4282628+01:00
completed: 2026-03-07T18:08:19.3552132+01:00
tags:
    - test
    - config
    - phase-9
class: standard
---

## Root Cause
5 test files import optional dependencies (numpy, qdrant-client) at module level. When these extras aren't installed, pytest collection crashes with ModuleNotFoundError, poisoning the entire suite:
- test_embedding_idle_timeout.py (numpy)
- test_knowledge_embeddings.py (numpy)
- test_voice_stt.py (numpy)
- test_qdrant_vector_store.py (qdrant-client)
- benchmarks/test_search_benchmark.py (qdrant-client)

This caused runTests (full suite) to report 0 passed / 3223 failed.

## Fix Applied
Added collect_ignore_glob guards in tests/conftest.py that detect missing optional deps at collection time and skip those files gracefully.

## AC
- [ ] uv run pytest tests/ completes without collection errors
- [ ] runTests() (no file filter) returns correct pass/fail counts
- [ ] Skipped files are reported as warnings, not silently dropped
- [ ] conftest.py guards check numpy and qdrant_client
