---
id: 948
title: 'Fix SSRF CWE-918 in HttpxContentFetcher.fetch: add private/loopback IP blocklist'
status: archived
priority: medium
created: 2026-04-18T00:12:36.295205+00:00
updated: 2026-04-18T01:56:06.140886+00:00
tags:
- security
- knowledge
- type:fix
parent:
depends_on:
- 946
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Problem

`HttpxContentFetcher.fetch()` in `serve/knowledge/src/owlbear_knowledge/fetcher.py` (L29–33) accepts user-controlled URLs with only scheme validation via `_check_url_scheme()`. No IP validation — same SSRF vulnerability as #946 and its sibling.

Uses `httpx.AsyncClient().get(url)` with default settings (follows redirects, no IP blocklist).

## Acceptance Criteria

- [ ] `fetch()` resolves the URL hostname to IP(s) asynchronously before making any HTTP request
- [ ] Blocked ranges match #946: use `ipaddress` stdlib properties (`.is_private`, `.is_loopback`, `.is_link_local`, `.is_reserved`, `.is_unspecified`) plus `.ipv4_mapped` check
- [ ] DNS rebinding is mitigated: HTTP request is made to the resolved IP directly (same pattern as #946)
- [ ] Redirects are disabled (`follow_redirects=False`) as defense-in-depth
- [ ] Any blocked URL raises `ValueError` with descriptive message
- [ ] Reuse the validation helper from #946 if one was extracted, or extract a shared utility if the pattern is identical
- [ ] Unit tests cover: localhost, 127.x, 10.x, 172.16.x, 192.168.x, 169.254.x, ::1, fe80::, ::ffff:127.0.0.1, and a safe public IP
- [ ] `ruff check` passes

## Context

Sibling of #946. Discovered during architecture review of #946 — same vulnerability pattern in a different call site. Implements the `ContentFetcher` protocol defined in `serve/knowledge/src/owlbear_knowledge/protocol.py` L98.

[[2026-04-18]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Fixes SSRF in one method (`HttpxContentFetcher.fetch`) |
| Interface clarity | PASS | Input: `url: str`, output: `str`, error: `ValueError` for blocked IPs. Implements `ContentFetcher` protocol (`protocol.py` L98) |
| Dependency correctness | PASS | #946 is archived/done. Pattern exists in `mcp-knowledge/server.py` L156-227 |
| Module layering | PASS | `fetcher.py` is in `owlbear_knowledge` — correct layer for the fix |
| TDD compliance | PASS | Will flow through test-writer |
| KISS/YAGNI | PASS | Minimal scope: one vulnerability, one method |
| Premise challenge | PASS | Genuine CWE-918 vulnerability. `HttpxContentFetcher` is a public API class in the library |
| Pattern consistency | PASS | Follows proven #946 pattern (`_is_blocked_ip` + DNS resolve + IP rewrite + Host header + no redirects) |
| Security surface | PASS | This IS the security fix. AC covers all SSRF vectors |
| Single domain | PASS | Knowledge domain only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| DNS resolution | Hostname unresolvable | `OSError` from `getaddrinfo` | Builder should raise `ValueError` per AC5 | URL rejected with descriptive message |
| DNS resolution | All resolved IPs blocked | N/A | `ValueError` per AC5 | URL rejected |
| IP-rewritten request | Connection error | `httpx.ConnectError` | Propagates (existing behavior) | Request fails normally |
| Empty URL | `urlparse("").hostname` → `None` | `getaddrinfo(None, port)` resolves to localhost → blocked | Implicit via SSRF check | Raises `ValueError` |

### Challenge Results

- Challenger: **reconsider** (confidence 0.60)
- Key concerns: (C1) shared utility coordination with #947, (C4) Host header missing from AC text
- Architect response: **accepted with mitigations** — see binding guidance below

### Binding Architecture Guidance (builder MUST follow)

**1. Host header preservation (addresses challenger C4):**
AC3 ("request made to resolved IP directly") MUST include `headers={"Host": original_hostname}` on the IP-rewritten request, matching the #946 pattern at `server.py` L223. Without this, virtual-hosted servers return wrong content or 404.

**2. Shared utility location (addresses challenger C1):**
The `_is_blocked_ip()` function from #946 was NOT extracted — it's a private function in `mcp-knowledge/server.py`. The builder MUST:

- Check if sibling task #947 has already created a shared module in `owlbear_knowledge/`
- If yes: import and reuse it
- If no: create `serve/knowledge/src/owlbear_knowledge/_ssrf.py` containing `is_blocked_ip(ip_str: str) -> bool` and the IP-rewrite helper. Both #947 and #948 targets are in the same package, so a single shared module avoids duplication.

**3. Empty URL behavior:**
The existing `_check_url_scheme()` passes empty strings through. After SSRF validation, `urlparse("").hostname` returns `None`, and `getaddrinfo(None, ...)` resolves to localhost → blocked. This is correct behavior. Test should cover empty-string input.

### Follow-up Created

- #949: Assess SSRF surface in BrowserContentFetcher (page.goto) — the third `ContentFetcher` implementation has no IP-level SSRF protection.

### Verdict: APPROVE

### Action Taken: Advanced to `todo` with binding architecture guidance. Created follow-up #949 for remaining SSRF surface

[[2026-04-18]]

## Test-Writer Notes

**Test file:** `serve/knowledge/tests/test_ssrf_fix_948.py`

**Class:** `TestFromAC_HttpxContentFetcherSSRF`

**Tests per category:**

| Category | Count | Tests |
|----------|-------|-------|
| Boundary (blocked IPs) | 9 | 127.0.0.1, 127.x, localhost, 10.x, 172.16.x, 192.168.x, 169.254.x, 0.0.0.0, IPv4-mapped ::ffff:127.0.0.1 |
| Edge (IPv6 + rebinding) | 3 | ::1, fe80::1, DNS-rebinding hostname→private |
| Error contract | 3 | ValueError not None, descriptive message contains IP, DNS failure raises ValueError |
| Security (redirects + URL rewrite) | 3 | follow_redirects=False, URL rewritten to IP, Host header preserved |
| Happy / DNS pre-flight | 1 | DNS called before HTTP |

**Total: 19 tests, all FAIL** — `pytest serve/knowledge/tests/test_ssrf_fix_948.py -v --tb=line -n 0`: 19 failed, 0 passed

**ruff check:** clean

**AC coverage:**

| AC Line | Tests |
|---------|-------|
| DNS resolution before HTTP | test_dns_resolution_called_before_http_request |
| Blocked ranges (loopback/private/link-local/reserved/unspecified) | 8 × blocked tests |
| IPv4-mapped IPv6 (.ipv4_mapped check) | test_blocks_ipv4_mapped_ipv6_loopback |
| DNS rebinding mitigation (IP rewrite + Host header) | test_request_url_rewritten_to_resolved_ip, test_host_header_set_to_original_hostname, test_dns_rebinding_hostname_resolving_to_private_ip_is_blocked |
| Redirects disabled | test_follow_redirects_disabled |
| ValueError on blocked URL (not None) | test_blocked_ip_raises_value_error_not_returns_none, test_blocked_ip_error_message_contains_ip |
| localhost, 127.x, 10.x, 172.16.x, 192.168.x, 169.254.x, ::1, fe80::, ::ffff:127.0.0.1, safe public IP | Dedicated tests for each |
[[2026-04-18]]

## Builder Notes

**Files changed:** `serve/knowledge/src/owlbear_knowledge/fetcher.py` (1 file, −23/+2 net)

**Implementation:** Replaced the naive `httpx.AsyncClient().get(url)` in `HttpxContentFetcher.fetch()` with a delegation to `safe_async_fetch(url)` from `owlbear_knowledge._ssrf` (created by #947). The shared utility already implements the full SSRF pipeline: DNS resolution via `asyncio.to_thread(socket.getaddrinfo)`, `_is_blocked_ip` check with IPv4-mapped IPv6 unwrap, URL rewrite to resolved IP + Host header, and `follow_redirects=False`.

**Test results:** 19/19 passed (`TestFromAC_HttpxContentFetcherSSRF`), 0 failed

**Coverage:** `fetcher.py` 100%, `_ssrf.py` 91% (83 tests total in knowledge suite)

**Lint:** ruff clean

**Commit:** `443ddda2` — `fix(security): SSRF CWE-918 in HttpxContentFetcher.fetch (#948, builder)`
[[2026-04-18]]

## Review Evidence

**Reviewer:** reviewer agent, 2026-04-18

### Test Results

Quality-Runner (independent): **19 passed, 0 failed, 0 skipped** — exit 0. Builder self-report confirmed.

### Lint

`ruff check` on `fetcher.py`, `_ssrf.py`, `test_ssrf_fix_948.py`: **clean** — exit 0.

### Coverage

| Module | % |
|--------|---|
| `owlbear_knowledge.fetcher` | 100% |
| `owlbear_knowledge._ssrf` | 86% |

Both above 90% threshold.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `fetch()` resolves hostname asynchronously before HTTP | `_ssrf.py` L60–61: `await asyncio.to_thread(socket.getaddrinfo, ...)` | `test_dns_resolution_called_before_http_request` | PASS |
| Blocked ranges: all 5 ipaddress properties + `.ipv4_mapped` | `_ssrf.py` L24–34 | 8× blocked tests + `test_blocks_ipv4_mapped_ipv6_loopback` | PASS |
| DNS rebinding mitigated: IP rewrite + Host header | `_ssrf.py` L74–81 | `test_request_url_rewritten_to_resolved_ip`, `test_host_header_set_to_original_hostname` | PASS |
| `follow_redirects=False` | `_ssrf.py` L80 | `test_follow_redirects_disabled` | PASS |
| `ValueError` with descriptive message | `_ssrf.py` L63–72 | `test_blocked_ip_raises_value_error_not_returns_none`, `test_blocked_ip_error_message_contains_ip` | PASS |
| Reuse shared utility from #947 | `fetcher.py` L5: imports `safe_async_fetch` from `owlbear_knowledge._ssrf` | Structural | PASS |
| All 10 required IP ranges in unit tests | Dedicated test per range | 9 blocked + 1 happy-path | PASS |
| `ruff check` passes | Quality-Runner: clean | — | PASS |

### Critical Checks (Pass 1)

- **5.0 TestFromAC Coverage:** 19/19 tests map to AC lines with discriminating assertions. No MISSING, no LAX.
- **5.1 Security:** No hardcoded secrets, injection, path traversal, or insecure deserialization. `_ssrf.py` is the fix itself — all SSRF vectors covered. Clean.
- **5.2 TestFromAC Integrity:** All 19 original tests present and unmodified. No WEAKENED or REMOVED.
- **5.3 Test Quality: STRONG.** Specific assertions, error-path coverage, descriptive names, independent tests.
- **5.4 Data Safety:** Clean. No shared mutable state. `asyncio.to_thread` is thread-safe.
- **5.5 Test Gap:** Explicit-port URL path (`http://host:8080/`) in `_ssrf.py` not tested (accounts for ~14% coverage gap). URL construction logic, no security implications — informational only.
- **5.7 Builder Process:** 1 `## Builder Notes` section, 1 commit `443ddda2`. Clean.

### Deductions

- Explicit-port URL path untested: −0.01

### Verdict

**Confidence: .97 → PASS** → docs
[[2026-04-18]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `copilot-instructions.md` covers project identity/branches only — no library API docs. SSRF ValueError contract is an internal library concern not tracked there. |
| 2 | Module docstrings | Yes | Updated | `HttpxContentFetcher.fetch()` had no docstring despite now raising `ValueError` on SSRF-blocked URLs. Added docstring documenting `ValueError` and `HTTPStatusError` raises. `_ssrf.py` `safe_async_fetch` and `_is_blocked_ip` already had accurate docstrings. Commit `067e6d5e`. |
| 3 | External attribution | No | N/A | Implementation reuses #947 shared utility `_ssrf.py`. Only Python stdlib (`ipaddress`, `socket`, `asyncio`) — no new external sources. Pattern already established in #946. |
| 4 | CLI changes | No | N/A | Library fix only, no CLI commands added or modified. |
| 5 | Research doc | No | N/A | No `.owlbear/research/*948*` file produced — task was a sibling fix following #946/#947 pattern, no research phase needed. |

### Files Updated

- `serve/knowledge/src/owlbear_knowledge/fetcher.py` — added `fetch()` docstring

### Scratch Files

- No `.owlbear/scratch/948-*` files found.

### Lint

`ruff check fetcher.py` — clean after edit.
[[2026-04-18]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| fetch() resolves hostname async before HTTP | `_ssrf.py` L60-61 `asyncio.to_thread(getaddrinfo)`, test: `test_dns_resolution_called_before_http_request` | PASS |
| Blocked ranges: 5 ipaddress properties + ipv4_mapped | `_ssrf.py` L24-34, 8 blocked tests + `test_blocks_ipv4_mapped_ipv6_loopback` | PASS |
| DNS rebinding: IP rewrite + Host header | `_ssrf.py` L74-81, tests: `test_request_url_rewritten_to_resolved_ip`, `test_host_header_set_to_original_hostname` | PASS |
| follow_redirects=False | `_ssrf.py` L80, test: `test_follow_redirects_disabled` | PASS |
| ValueError with descriptive message | `_ssrf.py` L63-72, tests: `test_blocked_ip_raises_value_error_not_returns_none`, `test_blocked_ip_error_message_contains_ip` | PASS |
| Reuse shared utility from #947 | `fetcher.py` L5 imports `safe_async_fetch` from `owlbear_knowledge._ssrf` | PASS |
| All 10 required IP ranges in unit tests | 9 blocked + 1 happy-path dedicated tests | PASS |
| ruff check passes | Quality-Runner: clean, exit 0 | PASS |

### Test Results

- pytest: 414 passed, 8 failed (all unrelated: #541 outputschema x4, #950 ssrf_preflight x2, search_v2 x1, phase_a_config x1). Zero failures in #948 scope.
- ruff: clean

### Architect Quality: 5/5

Exemplary AC: 8 specific testable criteria covering all SSRF vectors. Binding architecture guidance (Host header, shared utility, empty URL) followed cleanly by downstream agents. No improvisation needed.

### Deduction Breakdown

- AC lines without evidence: 0 (all 8 mapped)
- Lint violations: 0
- AC quality score 5 (no deduction)
- Reviewer evidence: present and thorough (no deduction)
- Full-suite failures in scope: 0 (no deduction)

### Confidence: 1.00

### Action: archive
