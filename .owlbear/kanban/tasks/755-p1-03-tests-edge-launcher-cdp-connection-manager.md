---
id: 755
title: 'P1-03: Tests — Edge launcher + CDP connection manager'
status: backlog
priority: critical
created: '2026-04-10T10:55:24.890231+00:00'
updated: '2026-04-10T11:55:46.010090+00:00'
tags:
- phase-1
- type:test
- scope:browser
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
RED phase. Tests for Edge launcher and CDP connection manager:
1. Edge binary discovery (Windows path resolution)
2. CDP launch args (--remote-debugging-port, --remote-allow-origins, 127.0.0.1 binding)
3. Connection lifecycle (connect, disconnect, reconnect)
4. SSO login redirect detection (session expired → fail-fast)

Tests use mocked subprocess/Playwright — no real Edge dependency in CI. All tests fail (RED).

Parent: #751

[[2026-04-10]]
## Research
- Research doc: .owlbear/research/edge-launcher-cdp-tests-755.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: Proceed with RED-phase tests targeting `owlbear_browser.launcher` and `owlbear_browser.cdp` modules in `tests/test_edge_launcher_cdp_755.py`. ~21 tests across 4 classes. (confidence: .85)
- Follow-up tasks created: none (task already has concrete AC, no decomposition needed)
- Decision requests: none (T1 — tests for approved feature)

## Challenge Results
- Challenger: FALLBACK — challenger subagent not available
- Confidence in original: .85
- Key challenges: self-challenge on test placement (root tests/ vs serve/browser/tests/) — resolved: package doesn't exist yet, root is correct per convention
- Researcher response: accepted — consistent with all other RED-phase test files

## Key Findings
1. Module paths: `owlbear_browser.launcher` (Edge discovery + launch), `owlbear_browser.cdp` (connection lifecycle + SSO detection)
2. Chrome 136 compliance is security-critical — ALL launch arg tests must verify `--user-data-dir` is present
3. Security voice HR#4: tests must verify 127.0.0.1 binding only, no wildcards in `--remote-allow-origins`
4. Mock strategy follows test_process_supervisor.py patterns: `_patch_which()`, `_patch_spawn()`, `AsyncMock` for Playwright
5. SSO detection: URL redirect to IdP + login form detection + fail-fast `AuthenticationRequired` error type
6. ~21 tests in 4 TestFromAC classes: EdgeDiscovery, CDPLaunchArgs, ConnectionLifecycle, SSODetection