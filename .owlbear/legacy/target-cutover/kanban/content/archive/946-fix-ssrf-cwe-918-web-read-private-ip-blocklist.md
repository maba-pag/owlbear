---
id: 946
title: 'Fix SSRF CWE-918 in _web_read: add private/loopback IP blocklist'
status: archived
priority: medium
created: 2026-04-18T00:00:00+00:00
updated: 2026-04-18T01:02:15.768975+00:00
tags:
- security
- mcp-knowledge
- type:fix
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---

## Problem

`_web_read` in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` (L156–169) accepts user-controlled URLs with only an http/https scheme check. No private/loopback IP blocklist is applied before the HTTP request is made, enabling Server-Side Request Forgery (SSRF CWE-918).

An attacker can provide `http://127.0.0.1/admin`, `http://169.254.169.254/latest/meta-data/` (AWS IMDS), `http://10.0.0.1/` etc. and the server will happily fetch them.

**Flagged by curator for 28 consecutive curation cycles without a task being created.**

## Acceptance Criteria

- [ ] `_web_read` resolves the URL hostname to IP(s) before making any HTTP request
- [ ] Blocked ranges: loopback (127.0.0.0/8, ::1), link-local (169.254.0.0/16, fe80::/10), private (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16), and unspecified/broadcast
- [ ] DNS rebinding is mitigated: IP check is performed after DNS resolution, not just on the raw hostname
- [ ] Any blocked URL returns `None` (not an exception) — callers already handle `None`
- [ ] Unit tests cover: localhost, 127.x, 10.x, 172.16.x, 192.168.x, 169.254.x, ::1, fe80::, and a safe public IP (allowed)
- [ ] `ruff check` passes

## Context

```python
# serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py L156–169
async def _web_read(url: str) -> str | None:
    from urllib.parse import urlparse
    if urlparse(url).scheme.lower() not in {"http", "https"}:
        return None
    # BUG: no IP blocklist here — SSRF possible
    async with httpx.AsyncClient(follow_redirects=False, timeout=30) as client:
        resp = await client.get(url)
```

## Suggested Approach

Use `socket.getaddrinfo` (or `ipaddress.ip_address`) to resolve and validate the IP before passing to httpx. Alternatively, use httpx's transport hooks or a custom resolver to intercept and block at the transport layer.

[[2026-04-18]]

## Refined Acceptance Criteria

- [ ] `_web_read` resolves the URL hostname to IP(s) **asynchronously** (e.g. `loop.getaddrinfo` or `asyncio.to_thread(socket.getaddrinfo, ...)`) before making any HTTP request
- [ ] Blocked ranges: loopback (127.0.0.0/8, ::1), link-local (169.254.0.0/16, fe80::/10), private (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16), unspecified, broadcast, **and IPv4-mapped IPv6 equivalents** (e.g. `::ffff:127.0.0.1`) — use `ipaddress` stdlib properties (`.is_private`, `.is_loopback`, `.is_link_local`, `.is_reserved`, `.is_unspecified`) plus check `.ipv4_mapped` when present, rather than enumerating CIDR ranges manually
- [ ] DNS rebinding is mitigated: after resolving the hostname, the HTTP request is made **to the resolved IP directly** (rewriting URL to IP + setting `Host` header, or using a custom httpx transport that validates at connect time) — httpx must NOT perform its own independent DNS resolution
- [ ] `follow_redirects=False` is preserved as defense-in-depth (prevents open-redirect bypass)
- [ ] Any blocked URL returns `None` (not an exception) — callers already handle `None`
- [ ] Unit tests cover: localhost, 127.x, 10.x, 172.16.x, 192.168.x, 169.254.x, ::1, fe80::, **::ffff:127.0.0.1** (IPv4-mapped), and a safe public IP (allowed)
- [ ] `ruff check` passes

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One function, one fix |
| Interface clarity | PASS (after refinement) | AC now specifies exact blocking mechanism, return contract, and async resolution |
| Dependency correctness | PASS | No task dependencies needed |
| Module layering | PASS | Change is within mcp-knowledge server.py; helper stays local (YAGNI — no shared utility yet) |
| TDD compliance | PASS | Test-writer will process in todo |
| KISS/YAGNI | PASS | Minimal scope for this call site; sibling fetchers get follow-up tasks |
| Premise challenge | PASS | Vulnerability is real, verified in code at L156–169 |
| Pattern consistency | PASS | Preserves existing `None`-on-failure contract |
| Security surface | PASS (after refinement) | DNS rebinding TOCTOU addressed, IPv4-mapped IPv6 addressed, redirect defense preserved |
| Single domain | PASS | mcp-knowledge only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| DNS resolution | Host unresolvable | `socket.gaierror` | Yes — caught by existing `except Exception: return None` | Bookmark fetch fails gracefully |
| IP validation | Blocked private IP | None (returns `None`) | Yes — AC specifies | SSRF prevented |
| IPv4-mapped IPv6 | Mapped address bypasses check | None | Yes — AC mandates `.ipv4_mapped` check | SSRF prevented |
| DNS rebinding | Second resolution returns different IP | None | Yes — AC mandates connecting to resolved IP directly | SSRF prevented |

### Challenge Results

- Challenger: **block** (confidence 0.35 on original)
- Architect response: **accepted and refined** — all four challenger concerns addressed:
  - C1 (DNS rebinding): AC now mandates connecting to resolved IP directly
  - C2 (IPv4-mapped IPv6): AC now mandates `ipaddress` stdlib + `.ipv4_mapped` check, test matrix includes `::ffff:127.0.0.1`
  - C3 (sibling fetchers): Follow-up tasks to be created for `intake.read_url()` and `HttpxContentFetcher.fetch()`
  - C4 (blocking getaddrinfo): AC now mandates async resolution

### Follow-up Tasks Needed

1. Fix SSRF in `intake.read_url()` (`serve/knowledge/src/owlbear_knowledge/intake.py` L58–85) — same vulnerability pattern
2. Fix SSRF in `HttpxContentFetcher.fetch()` (`serve/knowledge/src/owlbear_knowledge/fetcher.py` L29–33) — same vulnerability pattern
3. After all three are fixed, consider extracting shared SSRF validation utility (only if pattern stabilises)

### Verdict: APPROVE (after refinement)

### Action Taken: Refined AC to address DNS rebinding TOCTOU, IPv4-mapped IPv6 bypass, async resolution requirement, and redirect defense preservation. Advanced to todo. Follow-up tasks created for sibling fetchers

[[2026-04-18]]

## Test-Writer Notes

- Test file: serve/mcp-knowledge/tests/test_ssrf_fix_946.py
- Classes: `TestFromAC_WebReadSSRF`
- Tests per category: boundary 7 (127.0.0.1, 127.x, 10.x, 172.16.x, 192.168.x, 169.254.x, ipv4-mapped ::ffff:127.0.0.1), edge 3 (::1, fe80::1, dns-rebinding-hostname), error 2 (blocked-returns-none-not-exception, dns-failure-returns-none), dns-rebinding 1 (httpx-receives-resolved-ip)
- Total: 13 tests, all FAIL
- ruff: clean

### AC Coverage

| AC line | Test(s) |
|---------|---------|
| Resolve hostname before HTTP request | `test_dns_resolution_failure_returns_none_httpx_not_called` |
| Block loopback 127.0.0.0/8 | `test_blocks_loopback_127_0_0_1`, `test_blocks_loopback_127_x_non_zero` |
| Block private 10.x, 172.16.x, 192.168.x | `test_blocks_private_10_x`, `test_blocks_private_172_16_x`, `test_blocks_private_192_168_x` |
| Block link-local 169.254.x | `test_blocks_link_local_169_254_169_254` |
| Block IPv6 ::1, fe80:: | `test_blocks_ipv6_loopback_1`, `test_blocks_ipv6_link_local_fe80` |
| Block IPv4-mapped ::ffff:127.0.0.1 | `test_blocks_ipv4_mapped_ipv6_loopback` |
| DNS rebinding mitigated (check after DNS) | `test_dns_rebinding_hostname_resolving_to_private_ip_is_blocked` |
| DNS rebinding mitigated (httpx uses resolved IP) | `test_dns_rebinding_httpx_receives_resolved_ip_not_original_hostname` |
| Blocked returns None (not exception) | `test_blocked_url_returns_none_not_exception` |
| DNS failure returns None | `test_dns_resolution_failure_returns_none_httpx_not_called` |

### Failure evidence

```
FAILED test_blocks_loopback_127_0_0_1
FAILED test_blocks_loopback_127_x_non_zero
FAILED test_blocks_private_10_x
FAILED test_blocks_private_172_16_x
FAILED test_blocks_private_192_168_x
FAILED test_blocks_link_local_169_254_169_254
FAILED test_blocks_ipv6_loopback_1
FAILED test_blocks_ipv6_link_local_fe80
FAILED test_blocks_ipv4_mapped_ipv6_loopback
FAILED test_blocked_url_returns_none_not_exception
FAILED test_dns_resolution_failure_returns_none_httpx_not_called
FAILED test_dns_rebinding_hostname_resolving_to_private_ip_is_blocked
FAILED test_dns_rebinding_httpx_receives_resolved_ip_not_original_hostname
13 failed, 0 passed — RED confirmed
```

### Implementation hint for builder

- DNS mock uses `patch("socket.getaddrinfo", ...)` — implementation should use `asyncio.to_thread(socket.getaddrinfo, host, port, 0, socket.AF_UNSPEC)` so the patch intercepts it
- Use `ipaddress.ip_address(ip)` with `.is_loopback`, `.is_private`, `.is_link_local`, `.is_reserved`, `.is_unspecified` + `.ipv4_mapped` check for IPv4-mapped IPv6 addresses
- Rewrite URL to resolved IP (e.g. replace hostname with IP string, set `Host` header) to prevent httpx from doing its own DNS lookup
[[2026-04-18]]
Re-verified RED state: 13 tests in `serve/mcp-knowledge/tests/test_ssrf_fix_946.py`, all FAIL. ruff clean. No changes needed — work already complete from prior session.
[[2026-04-18]]

## Builder Notes

### Files changed

- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` — replaced old `_web_read` (no IP check) with SSRF-safe version; added `_is_blocked_ip` helper

### Implementation

- Added `_is_blocked_ip(ip_str)`: uses `ipaddress.ip_address()` + checks `.is_loopback`, `.is_private`, `.is_link_local`, `.is_reserved`, `.is_unspecified`; unwraps IPv4-mapped IPv6 via `isinstance(addr, IPv6Address) and addr.ipv4_mapped` before checking
- `_web_read` now: (1) resolves hostname via `asyncio.to_thread(socket.getaddrinfo, ...)`, (2) blocks any result matching `_is_blocked_ip`, (3) rewrites URL to resolved IP + sets `Host` header to prevent DNS-rebinding TOCTOU, (4) preserves `follow_redirects=False`

### Test results

- 13/13 `TestFromAC_WebReadSSRF` tests PASS (all RED → GREEN verified)
- No `TestBuilderDiscovered` tests needed (all AC scenarios fully covered)
- Builder-discovered fix: `IPv4Address` has no `ipv4_mapped` attribute (IPv6-only); fixed with `isinstance(addr, IPv6Address)` guard

### Lint

- ruff clean (`PLR0911` resolved by removing dead `if not addrs` guard — `getaddrinfo` always returns ≥1 entry on success)

### Coverage

- `owlbear_mcp_knowledge/server.py`: 69% (new `_is_blocked_ip` + SSRF-protected `_web_read` well covered by 13 dedicated tests)

### Commit

- `ab22f704` — fix: add SSRF blocklist to _web_read (CWE-918) (#946, builder)
[[2026-04-18]]

## Review Evidence

### Test Results

- pytest: 13 passed, 0 failed

### Lint

clean: true

### Coverage

`owlbear_mcp_knowledge.server`: 39% module-level (low — untouched server tools drag the number; dedicated SSRF tests cover new `_is_blocked_ip` + `_web_read` at higher density per builder report of 69%)

---

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: async DNS resolution before HTTP | `test_dns_resolution_failure_returns_none_httpx_not_called`, `test_dns_rebinding_hostname_resolving_to_private_ip_is_blocked` | Yes — mocked `socket.getaddrinfo` won't intercept if impl skips `asyncio.to_thread` | COVERED |
| AC2: blocked ranges incl. broadcast | `test_blocks_loopback_*`, `test_blocks_private_*`, `test_blocks_link_local_*`, `test_blocks_ipv6_*`, `test_blocks_ipv4_mapped_*` | Yes for all explicitly tested IPs — **no test for `255.255.255.255` or `240.0.0.0/4`** | **MISSING (broadcast)** |
| AC3: DNS rebinding — request to resolved IP | `test_dns_rebinding_httpx_receives_resolved_ip_not_original_hostname` | Yes — asserts `mock_get.called` + `"example.com" not in call_url` | COVERED |
| AC4: `follow_redirects=False` preserved | None | No — no test inspects `httpx.AsyncClient(...)` constructor kwargs; removing `follow_redirects=False` would go undetected | LAX |
| AC5: blocked returns None not exception | `test_blocked_url_returns_none_not_exception` | Yes | COVERED |
| AC6: localhost, 127.x, 10.x, 172.16.x, 192.168.x, 169.254.x, ::1, fe80::, ::ffff:127.0.0.1, safe public IP | 127.x–192.168.x covered; `::1`, `fe80::`, `::ffff:127.0.0.1`, safe public IP covered — **`http://localhost/` hostname entirely absent** | AC6 explicitly names `localhost` | **MISSING (localhost hostname)** |
| AC7: ruff check passes | ruff exit 0 per quality-runner | — | COVERED |

**2 MISSING → automatic FAIL.**

#### Security Review

- No hardcoded secrets, injection, path traversal, or unsafe deserialization in changed code.
- Loop-then-rewrite pattern in `_web_read` (server.py ~L204–220) is correct — all addresses validated before `addrs[0]` is used for rewrite.
- `is_reserved` covers `255.255.255.255` and `240.0.0.0/4` in Python 3.12 (implementation is sound); however absence of a test leaves this unverifiable by the test suite.
- Note: `is_reserved` is deprecated in Python 3.13 — forward-looking risk, not a current failure.

#### Test Integrity

All 13 `TestFromAC_WebReadSSRF` tests preserved unchanged by the builder.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 13 tests | None | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Every blocked-IP test asserts `result is None` + `mock_cls.assert_not_called()` |
| Negative/error-path coverage | **WEAK** | `except Exception: return None` at server.py ~L234–238 (httpx error path) entirely untested; `resp.raise_for_status()` raise path untested |
| Mutation reasoning | ADEQUATE | Removing `_is_blocked_ip` call would fail blocked-IP tests; removing `follow_redirects=False` would not be caught |
| Test independence | STRONG | No shared mutable state |
| Descriptive names | STRONG | All names precise and scenario-specific |

**WEAK on dimension 2 → automatic FAIL.**

#### Data Safety

No issues. `asyncio.to_thread` correctly isolates blocking DNS call. Both exception handlers return `None` safely.

#### Implementation-Aware Gaps

Significant untested paths:

1. `http://localhost/` hostname — goes through DNS resolution path; AC6 explicitly names it (→ test-writer)
2. `255.255.255.255` broadcast — AC2 explicitly names it (→ test-writer)
3. `except Exception: return None` for httpx error — no test injects httpx exception (→ test-writer)
4. Non-http/https scheme → `return None` (server.py ~L190) — minor; scheme check is pre-existing guard
5. Empty hostname → `return None` (server.py ~L193) — minor

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | **CLEAN** |

---

### Pass 2 — INFORMATIONAL

- `ipaddress` imported twice with `# noqa: PLC0415` (inside `_is_blocked_ip` and inside `_web_read`); hoisting to module top removes both suppressions.
- `test_dns_rebinding_httpx_receives_resolved_ip_not_original_hostname` asserts `"example.com" not in call_url` but does NOT assert `"93.184.216.34" in call_url` — an impl that rewrites URL to empty string still passes; add positive assertion.
- `follow_redirects=False` is preserved in code but no test verifies it; adding `assert mock_cls.call_args.kwargs["follow_redirects"] is False` would prevent future regression (AC4 is LAX).

---

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Async DNS resolution before HTTP | `asyncio.to_thread(socket.getaddrinfo, ...)` at server.py ~L196–199 | `test_dns_resolution_failure_returns_none_httpx_not_called` | PASS |
| Blocked ranges: loopback, link-local, private, unspecified, broadcast, IPv4-mapped | `_is_blocked_ip` uses 5 ipaddress flags + `.ipv4_mapped` at server.py ~L157–178; no broadcast test | boundary+edge tests | FAIL (no broadcast test) |
| DNS rebinding: HTTP to resolved IP | URL rewritten at server.py ~L213–220; `Host` header preserved | `test_dns_rebinding_httpx_receives_resolved_ip_not_original_hostname` | PASS |
| `follow_redirects=False` preserved | server.py ~L233 | None | PASS (LAX) |
| Blocked returns None not exception | `except Exception: return None` at server.py ~L234–238 | `test_blocked_url_returns_none_not_exception` | PASS |
| Unit tests cover localhost + all listed IPs | `localhost` hostname absent from test file | — | FAIL |
| ruff check passes | quality-runner exit 0 | — | PASS |

---

### Confidence: .67

### Verdict: FAIL → todo

**Action for test-writer:** Add to `test_ssrf_fix_946.py`:

1. `test_blocks_localhost_hostname` — `http://localhost/` with `socket.getaddrinfo` patched to return `_addr4("127.0.0.1")`, assert `result is None`, `mock_cls.assert_not_called()`
2. `test_blocks_broadcast_255_255_255_255` — `http://255.255.255.255/` (literal IP), assert `result is None`, `mock_cls.assert_not_called()`
3. `test_httpx_exception_returns_none` — mock `socket.getaddrinfo` returning safe public IP, mock `httpx.AsyncClient.__aenter__.get` raising `httpx.ConnectError`, assert `result is None` (no exception raised)
[[2026-04-18]]

## Test-Writer Notes

- Test file: serve/mcp-knowledge/tests/test_ssrf_fix_946.py
- Classes: `TestFromAC_WebReadSSRF`
- Retry: 3 tests added to address reviewer FAIL findings

### New Tests Added

| Reviewer Finding | New Test |
|-----------------|----------|
| AC6 missing `localhost` hostname | `test_blocks_localhost_hostname` — `http://localhost/` with `socket.getaddrinfo` patched to `127.0.0.1`, asserts `None` + `mock_cls.assert_not_called()` |
| AC2 missing broadcast `255.255.255.255` | `test_blocks_broadcast_255_255_255_255` — literal broadcast IP, patched via `getaddrinfo`, asserts `None` + `mock_cls.assert_not_called()` |
| WEAK: httpx exception path untested | `test_httpx_exception_returns_none` — safe IP, httpx raises `ConnectError`, asserts `None` + no exception propagated |

### Test Results

- 16/16 passed (13 original + 3 new) — builder implementation already covers all new scenarios
- ruff: clean
- Commit: aee16dcb

### AC Coverage (complete)

All 7 AC lines now have coverage including `localhost` hostname (AC6), broadcast (AC2), and httpx error path.
[[2026-04-18]]

## Builder Notes

### Files changed

- None — implementation from prior builder session already covers all 3 new tests added by test-writer (retry after reviewer FAIL)

### Test results

- 16/16 `TestFromAC_WebReadSSRF` tests PASS (13 original + 3 new: `test_blocks_localhost_hostname`, `test_blocks_broadcast_255_255_255_255`, `test_httpx_exception_returns_none`)
- All RED → GREEN confirmed in prior session; new tests GREEN on first run (existing implementation already correct)
- No `TestBuilderDiscovered` tests needed

### Lint

- ruff clean — `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` + `serve/mcp-knowledge/tests/test_ssrf_fix_946.py`

### Evidence summary

- `_is_blocked_ip` checks `.is_loopback`, `.is_private`, `.is_link_local`, `.is_reserved`, `.is_unspecified` + `.ipv4_mapped` unwrap → covers localhost (127.0.0.1 via DNS), broadcast (255.255.255.255 via `is_reserved`), and httpx exception path (caught by `except Exception: return None`)
- Reviewer gap items fully addressed by test-writer additions; no implementation change required
[[2026-04-18]]

## Review Evidence

### Test Results

- pytest: 16 passed, 0 failed (quality-runner, independent run)

### Lint

clean: true (ruff exit 0)

### Coverage

`owlbear_mcp_knowledge.server`: 40% module-level — expected; untouched MCP tool handlers drag the number. SSRF-relevant code well-covered by 16 dedicated tests.

---

### Pass 1 — CRITICAL (Cycle 2)

#### 5.0 Test-Writer AC Coverage

| AC Line | Mapped Test(s) | Would Fail If AC Violated? | Verdict |
|---------|---------------|---------------------------|---------|
| AC1: async DNS resolution before HTTP | `test_dns_resolution_failure_returns_none_httpx_not_called`, all hostname tests via `socket.getaddrinfo` patch | Yes — patch only intercepts if `asyncio.to_thread(socket.getaddrinfo,...)` is used | COVERED |
| AC2: blocked ranges incl. broadcast | `test_blocks_loopback_*`, `test_blocks_private_*`, `test_blocks_link_local_*`, `test_blocks_ipv6_*`, `test_blocks_ipv4_mapped_*`, `test_blocks_broadcast_255_255_255_255` (new) | Yes for all | COVERED |
| AC3: DNS rebinding — request to resolved IP | `test_dns_rebinding_httpx_receives_resolved_ip_not_original_hostname` | Partially — negative assertion only; see Pass 2 | COVERED (LAX) |
| AC4: `follow_redirects=False` preserved | None — no test asserts this kwarg | AC4 is an impl requirement ("preserved as defense-in-depth"), not a test requirement; verified in code at server.py ~L222 | COVERED (impl-verified) |
| AC5: blocked returns None not exception | `test_blocked_url_returns_none_not_exception` | Yes | COVERED |
| AC6: all named IPs incl. localhost | All 10 cases present: localhost (new), 127.x, 10.x, 172.16.x, 192.168.x, 169.254.x, ::1, fe80::, ::ffff:127.0.0.1, safe public IP | Yes | COVERED |
| AC7: ruff passes | quality-runner exit 0 | — | COVERED |

No MISSING. → PASS

#### 5.1 Security Review

- No hardcoded secrets, injection, path traversal, or unsafe deserialization.
- `_is_blocked_ip` unwraps IPv4-mapped via `isinstance(addr, IPv6Address) and addr.ipv4_mapped` before property checks — correct.
- `is_reserved` covers broadcast (`255.255.255.255`) and class-E range on Python 3.12+.
- `follow_redirects=False` confirmed at server.py ~L222.
- Minor: `addrs[0]` access post-loop at server.py ~L213 has no empty-list guard. `socket.getaddrinfo` on success always returns ≥1 entry per POSIX, but if it returned empty, `IndexError` would propagate rather than `None`. No realistic attack vector; no realistic trigger path. Noted in Pass 2. → PASS

#### 5.2 Test Integrity

All 13 original `TestFromAC_WebReadSSRF` tests preserved unchanged. 3 new tests added (localhost, broadcast, httpx exception). No test weakened or removed. → PASS

#### 5.3 Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | 15/16 tests assert `result is None` + `mock_cls.assert_not_called()` (STRONG); `test_dns_rebinding_httpx_receives_resolved_ip_not_original_hostname` asserts negative-only (`"example.com" not in call_url`) — see Pass 2 |
| Negative/error-path coverage | STRONG | `test_httpx_exception_returns_none` (new) covers httpx error path; `test_blocked_url_returns_none_not_exception` verified |
| Mutation reasoning | ADEQUATE | Removing `_is_blocked_ip` call fails 10+ tests; DNS rebinding rewrite target weak (informational) |
| Test independence | STRONG | No shared mutable state |
| Descriptive names | STRONG | All 16 names precise and scenario-specific |

Overall: ADEQUATE-STRONG. No WEAK dimension. The pre-existing DNS rebinding assertion gap was noted by prior reviewer as Pass 2 (informational) — retains that classification. → PASS

#### 5.4 Data Safety

`_is_blocked_ip` is a pure predicate; `_web_read` is a pure network fetch. No persistence, no shared state, no race conditions. → PASS

#### 5.5 Implementation-Aware Test Gaps

Minor untested paths: port-in-URL netloc branch (server.py ~L215), non-http scheme early return (server.py ~L192), `is_unspecified` (0.0.0.0/::), `_is_blocked_ip` ValueError on malformed IP. All are trivial defensive code or pass-through branches — not "significant" per skill criteria. No FAIL.

#### 5.7 Builder Process Quality

2 builder sessions: session 1 = full implementation, session 2 = no changes (existing impl already covered new tests). Approach variation confirmed. No loop. → CLEAN

**All Pass 1 checks: PASS**

---

### Pass 2 — INFORMATIONAL

1. `test_dns_rebinding_httpx_receives_resolved_ip_not_original_hostname` asserts `"example.com" not in call_url` but lacks `assert "93.184.216.34" in call_url` — an impl that rewrites URL to any non-hostname string would pass. Adding the positive assertion would fully verify the IP rewrite contract (flagged in prior review as well).
2. `follow_redirects=False` has no test assertion — `assert mock_cls.call_args.kwargs["follow_redirects"] is False` would prevent silent regression.
3. `addrs[0]` post-loop access has no empty-list guard — adding `if not addrs: return None` before the access would eliminate the theoretical `IndexError` propagation path.
4. `import ipaddress` appears twice (inside `_is_blocked_ip` and inside `_web_read`) with `# noqa: PLC0415` — hoisting to module level removes both suppressions.

---

### Prior Cycle FAIL Items: All Resolved

| Prior FAIL | Resolution |
|------------|-----------|
| AC6: localhost hostname missing | `test_blocks_localhost_hostname` added ✓ |
| AC2: broadcast 255.255.255.255 missing | `test_blocks_broadcast_255_255_255_255` added ✓ |
| WEAK: httpx exception path untested | `test_httpx_exception_returns_none` added ✓ |

---

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Async DNS resolution before HTTP | `asyncio.to_thread(socket.getaddrinfo, ...)` server.py ~L196–199 | `test_dns_resolution_failure_returns_none_httpx_not_called` + all hostname tests | PASS |
| Blocked ranges incl. broadcast | `_is_blocked_ip` uses 5 flags + `.ipv4_mapped`; broadcast via `is_reserved` | 10 blocked-IP tests | PASS |
| DNS rebinding via resolved-IP rewrite | URL rewritten at server.py ~L213–220; `Host` header set | `test_dns_rebinding_httpx_receives_resolved_ip_not_original_hostname` | PASS |
| `follow_redirects=False` preserved | server.py ~L222 | impl-verified | PASS |
| Blocked returns None not exception | `except Exception: return None` server.py ~L234–238 | `test_blocked_url_returns_none_not_exception` | PASS |
| Unit tests cover all named IPs | 16 tests, all 10 AC6-required cases present | full matrix | PASS |
| ruff passes | quality-runner exit 0 | — | PASS |

---

### Deductions

- DNS rebinding positive assertion missing: −0.03
- `follow_redirects=False` no test assertion: −0.02
- `addrs[0]` no empty-list guard (theoretical propagation risk): −0.02
- Port-in-URL branch untested: −0.01

### Confidence: .92

### Verdict: PASS → docs

[[2026-04-18]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `_web_read` and `_is_blocked_ip` are private helpers (`_` prefix); no public API or MCP tool signatures changed. `.github/copilot-instructions.md` documents only repo branches — mcp-knowledge internals not covered there. |
| 2 | Module docstrings | Yes | Verified | `_is_blocked_ip` (L156): "Return True if *ip_str* is a private/loopback/link-local/reserved address." — accurate. `_web_read` (L180): full docstring covering SSRF protection, async resolution, blocklist, and URL-rewrite strategy — accurate and complete. Module-level docstring present (L1). |
| 3 | External attribution | No | N/A | Implementation uses Python stdlib only: `ipaddress`, `socket`, `asyncio.to_thread`, `httpx`. No external repos or articles referenced in task body or AC. `.owlbear/sources/overview.md` entry not required. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | No | N/A | No `.owlbear/research/*946*` file created. Task originated from curator flag, not a research workflow. No link expected. |

### Files Updated

- None

### Scratch Files Cleaned

- None found (`find .owlbear/scratch/946-*` — no matches)
[[2026-04-18]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Async DNS resolution before HTTP | `asyncio.to_thread(socket.getaddrinfo, ...)` at server.py L196-199; mocked in all hostname tests | PASS |
| Blocked ranges: loopback, link-local, private, unspecified, broadcast, IPv4-mapped | `_is_blocked_ip` uses 5 ipaddress flags + `.ipv4_mapped` unwrap at server.py L156-178; 10 blocked-IP tests + broadcast test | PASS |
| DNS rebinding: HTTP to resolved IP | URL rewritten at server.py L213-220; `Host` header set; `test_dns_rebinding_httpx_receives_resolved_ip_not_original_hostname` verifies | PASS |
| `follow_redirects=False` preserved | server.py L222 confirmed | PASS |
| Blocked returns None not exception | `except Exception: return None` at server.py L234-238; `test_blocked_url_returns_none_not_exception` + `test_httpx_exception_returns_none` | PASS |
| Unit tests cover all named IPs | 16 tests: localhost, 127.x, 10.x, 172.16.x, 192.168.x, 169.254.x, ::1, fe80::, ::ffff:127.0.0.1, broadcast 255.255.255.255, safe public IP | PASS |
| ruff check passes | quality-runner ruff exit 0 | PASS |

### Test Results

- pytest: 348 passed, 6 failed (all 6 pre-existing: 4x task #541 output schema, 1x search API top_k, 1x SKILL.md path; none in task scope)
- 16/16 task-specific tests PASS
- ruff: clean

### Architect Quality: 5/5

Excellent. Refined AC after challenger input addressed DNS rebinding TOCTOU, IPv4-mapped IPv6 bypass, async resolution, and redirect defense. Failure mode map included. Follow-up tasks for sibling fetchers identified. Specific mechanisms prescribed (ipaddress stdlib properties, URL rewrite, Host header). Clean implementation path with no builder improvisation needed.

### Deduction Breakdown

- AC lines without evidence: 0 (all 7 verified) = 0
- Lint violations: none = 0
- AC quality score: 5/5 (above threshold) = 0
- Reviewer evidence section: present, detailed, PASS on cycle 2 = 0
- Full-suite test failures in task scope: 0 = 0

Informational (no deduction): DNS rebinding test uses negative-only assertion; `follow_redirects=False` impl-verified only. Both noted by reviewer as Pass 2 items.

### Confidence: .98

### Action: archive
