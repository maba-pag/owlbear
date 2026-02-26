---
id: 34
title: 'P4-06: Test Copilot OAuth module'
status: ideation
priority: high
created: 2026-02-24T15:16:12.3456482+01:00
updated: 2026-02-26T18:53:06.9248906+01:00
tags:
    - phase-4
    - test
    - auth
depends_on:
    - 31
    - 10
class: standard
---

AC: Create tests/test_auth/__init__.py and tests/test_auth/test_copilot.py. Test cases (minimum 8): (1) request_device_code returns expected fields (mock httpx), (2) poll_for_access_token handles authorization_pending (mock), (3) poll_for_access_token handles slow_down by increasing interval (mock), (4) poll_for_access_token returns token on success (mock), (5) poll_for_access_token raises TimeoutError on expiry (mock), (6) exchange_for_copilot_token returns token dict (mock), (7) derive_base_url parses proxy-ep from token string, (8) derive_base_url returns default when no proxy-ep, (9) token caching: save + load round-trip (tmp_path), (10) token expiry check with 60s safety margin. All tests use unittest.mock for HTTP calls. Mark integration tests with @pytest.mark.api. Files: tests/test_auth/__init__.py, tests/test_auth/test_copilot.py
