---
id: 950
title: Add SSRF pre-flight check to navigate() in mcp-browser server
status: archived
priority: medium
created: 2026-04-18T01:22:38.865118+00:00
updated: 2026-04-18T02:28:28.505858+00:00
tags:
- security
- browser
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Problem

The `navigate()` tool in `serve/mcp-browser/src/owlbear_mcp_browser/server.py` has three `page.goto()` call sites (lines ~111, ~117, ~126) with no IP-level SSRF protection. The `DomainAllowlist` checks domain names but not resolved IPs.

Currently unreachable from user-controlled input (agent-only, behind closed-by-default allowlist), but defense-in-depth is warranted per the #946/#947/#948 hardening pattern.

## Acceptance Criteria

- [ ] Before any `page.goto()` call in `navigate()`, resolve hostname via `socket.getaddrinfo()` and check all resolved IPs against an `_is_blocked_ip()` function (loopback/private/link-local/reserved/unspecified, with IPv4-mapped IPv6 unwrapping)
- [ ] Reject URLs with non-http/https schemes (`file://`, `data:`, `javascript:` etc.)
- [ ] The check runs in `navigate()` itself (not in `BrowserContentFetcher.fetch()`), covering all three `page.goto()` paths
- [ ] TOCTOU risk from DNS rebinding is documented as accepted (Playwright cannot connect to pre-resolved IP)
- [ ] Tests cover: blocked IP rejection, scheme rejection, allowed domain pass-through

## Context

Research: `.owlbear/research/949-ssrf-browser-fetcher.md`
Parent research: #949
Sibling tasks: #946 (done), #947, #948

## Files Affected

- `serve/mcp-browser/src/owlbear_mcp_browser/server.py` — add pre-flight check before `page.goto()` calls
- `serve/mcp-browser/tests/` — new test file for SSRF protection
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/950-ssrf-browser-navigate.md
- Sources: 6 studied, 4 high-relevance
- Recommendation: Option C — pre-flight DNS + IP check + scheme check in navigate(), ~25 LOC, duplicate _is_blocked_ip locally (confidence: .75)
- Follow-up tasks created: none (this IS the implementation task)
- Decision requests: none

Key findings:

1. Scheme check is a required control (not optional) — `javascript://allowlisted-host/` bypasses DomainAllowlist
2. TOCTOU from DNS rebinding is accepted — Playwright cannot connect to pre-resolved IP
3. Click-triggered navigation (via click() tool) is a known uncovered vector — accepted at nice-to-have priority
4. `_is_blocked_ip` should be duplicated locally — cross-package dep for 20 LOC violates KISS
5. Challenge verdict: reconsider (.55) — accepted C1/C3/C4, rejected Option B upgrade and DomainAllowlist placement
[[2026-04-18]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: SSRF pre-flight in `navigate()` |
| Interface clarity | PASS (after refinement) | Error type and DNS failure behavior added via binding guidance below |
| Dependency correctness | PASS | No task dependencies. #946 done, #947/#948 in-progress but independent — local duplication avoids cross-package dep |
| Module layering | PASS | Check stays in `mcp-browser/server.py`. No dep on `owlbear-knowledge` for 20 LOC utility |
| TDD compliance | PASS | Will flow through test-writer. No tests/ dir exists yet — test-writer creates it |
| KISS/YAGNI | PASS | Option C (~25 LOC), proportionate to nice-to-have priority |
| Premise challenge | PASS | Genuine CWE-918 defense-in-depth. `javascript://allowlisted-host/` bypasses DomainAllowlist (research finding §3.3) |
| Pattern consistency | PASS | Follows #946/#947/#948 pattern: `_is_blocked_ip` + DNS resolve + IP check. Differs from siblings only in omitting URL rewrite (Playwright constraint) |
| Security surface | PASS | This IS the security fix. AC covers scheme check, IP blocklist, and test coverage |
| Single domain | PASS | Browser domain only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| Scheme check | Non-http/https scheme (e.g. `javascript://`, `file://`) | `ToolError` | Yes (AC2 + binding guidance) | URL rejected |
| DNS resolution | Hostname unresolvable | `OSError` from `getaddrinfo` | Yes (binding guidance §2) → `ToolError` | URL rejected |
| DNS resolution | All resolved IPs in blocked ranges | `ToolError` | Yes (AC1 + binding guidance) | URL rejected |
| Redirect after page.goto | Allowlisted server 302s to internal IP | None | No — accepted limitation (binding guidance §3) | SSRF possible via compromised allowlisted domain |
| Empty URL | `urlparse("").hostname` → `None` | Scheme check catches (no scheme) | Yes | URL rejected |

### Challenge Results

- Challenger: **reconsider** (confidence 0.60)
- Key concerns: (C1) redirect SSRF undocumented as limitation, (C2) AC omits error type, (C3) AC omits DNS failure behavior, (C4) copy-count cosmetic error
- Architect response: **accepted C1/C2/C3** — addressed via binding guidance below. C4 noted (cosmetic). Rejected B2 (Playwright event hooks investigation = research beyond nice-to-have scope) and A1 (scheme check in DomainAllowlist = separate concern).

### Binding Architecture Guidance (builder MUST follow)

**1. Error type (addresses challenger C2):**
All rejections (blocked IP, blocked scheme, DNS failure) MUST raise `ToolError` — matching the existing allowlist rejection pattern at `server.py` L106-108.

**2. DNS failure handling (addresses challenger C3):**
If `socket.getaddrinfo()` raises `OSError`, catch it and raise `ToolError` with a descriptive message including the hostname. Do not let `OSError` propagate raw.

**3. Redirect SSRF — accepted limitation (addresses challenger C1):**
AC4 says "TOCTOU risk from DNS rebinding is documented as accepted." The builder MUST document TWO distinct accepted limitations in the code comment:

- (a) TOCTOU from DNS rebinding (Playwright cannot connect to pre-resolved IP)
- (b) Redirect SSRF: `page.goto()` follows HTTP redirects by default. An allowlisted server returning a redirect to an internal IP bypasses the pre-flight check. Mitigated by closed-by-default allowlist and agent-only access. Covering this would require `context.route()` interception (Option B) — disproportionate for nice-to-have priority.

**4. Check ordering:**
Call `_check_ssrf(url)` BEFORE `allowlist.check(url)`. This catches `javascript://allowlisted-host/` before the domain check passes it.

**5. Reference implementation:**
Duplicate `_is_blocked_ip` from `serve/knowledge/src/owlbear_knowledge/_ssrf.py` L16-35. This is copy #2 (not #4 as research claimed — `_ssrf.py` replaced the `mcp-knowledge/server.py` copy). Use `asyncio.to_thread(socket.getaddrinfo, hostname, port)` for non-blocking DNS.

**6. Test file:**
`serve/mcp-browser/tests/test_ssrf_preflight_950.py` — tests/ directory does not exist yet, create it with `__init__.py`.

### Verdict: APPROVE

### Action Taken: Advanced to `todo` with binding architecture guidance addressing challenger concerns C1-C3

[[2026-04-18]]

## Test-Writer Notes

**Test file:** `serve/mcp-browser/tests/test_ssrf_preflight_950.py`
Also created: `serve/mcp-browser/tests/__init__.py`

**Classes:**

| Class | Category | Tests |
|-------|----------|-------|
| `TestFromAC_NavigateSchemeCheck` | scheme rejection | 4 |
| `TestFromAC_NavigateIPBlocklist` | IP blocklist (happy/boundary/edge) | 10 |
| `TestFromAC_NavigateDNSFailure` | error path | 2 |
| `TestFromAC_NavigatePassthrough` | allowed pass-through (DNS-call contract) | 2 |

**Total: 18 tests, all FAIL** — confirmed via pytest (18 failed, 0 passed).
Ruff: clean.

**AC coverage:**

| AC line | Test(s) |
|---------|---------|
| AC1: resolve hostname + IP blocklist (loopback/private/link-local/reserved/unspecified + IPv4-mapped IPv6) | `test_blocks_loopback_*`, `test_blocks_private_*`, `test_blocks_link_local_*`, `test_blocks_ipv4_mapped_ipv6_*`, `test_blocks_all_ips_*`, `test_blocks_literal_ip_*` |
| AC2: reject non-http/https schemes | `test_javascript_scheme_rejected`, `test_file_scheme_rejected`, `test_data_scheme_rejected`, `test_ftp_scheme_rejected` |
| Binding §2: DNS OSError → ToolError with hostname | `test_dns_failure_raises_tool_error`, `test_dns_failure_message_contains_hostname` |
| AC5: allowed domain pass-through (DNS resolved) | `test_allowed_domain_dns_is_resolved`, `test_allowed_domain_https_returns_url` |

**Failure mode for RED:**

- Scheme tests: `navigate()` currently returns the URL for allowlisted hostnames regardless of scheme — no `ToolError`. Fails: `DID NOT RAISE`.
- IP blocklist tests: no DNS call, no IP check, `navigate()` returns URL. Fails: `DID NOT RAISE`.
- DNS failure tests: `getaddrinfo` never called, no `ToolError`. Fails: `DID NOT RAISE`.
- Pass-through tests: `mock_dns.assert_called()` → AssertionError (getaddrinfo never called). Fails: `AssertionError`.

**Builder notes:**

- `_check_ssrf(url)` must be called BEFORE `allowlist.check(url)` (binding guidance §4)
- Patch target: `socket.getaddrinfo` — server.py must `import socket` and call `asyncio.to_thread(socket.getaddrinfo, hostname, port)`
- All rejections raise `ToolError` (not `ValueError`, not `PermissionError`)
- DNS failure message must contain the hostname
[[2026-04-18]]

## Builder Notes

### Files Changed

- `serve/mcp-browser/src/owlbear_mcp_browser/server.py` — added `import asyncio`, `import ipaddress`, `import socket`, `from urllib.parse import urlparse`; added `_is_blocked_ip()` (duplicate of `owlbear_knowledge._ssrf`); added `_check_ssrf(url)` async function; wired `await _check_ssrf(url)` before `allowlist.check(url)` in `navigate()`.

### Test Results

- 16/18 passed (scheme check × 4, IP blocklist × 8 + literal-IP, DNS failure × 2, passthrough DNS-call contracts × 0 of 2)
- 2 FAILED: `TestFromAC_NavigatePassthrough::test_allowed_domain_dns_is_resolved`, `TestFromAC_NavigatePassthrough::test_allowed_domain_https_returns_url`

### Lint: ruff — CLEAN

### Reject Reason: Test-writer interface assumption is infeasible

`TestFromAC_NavigatePassthrough` uses RFC 5737 documentation addresses as "public IP" pass-through values:

- `203.0.113.1` (TEST-NET-3, RFC 5737)
- `198.51.100.42` (TEST-NET-2, RFC 5737)

Python 3.11+ changed `ipaddress.ip_address.is_private` to return `True` for ALL non-globally-routable addresses, including RFC 5737 documentation ranges. Both IPs are blocked by `_is_blocked_ip()` because `is_private=True`.

**Error observed:**

```
ToolError: URL 'https://target.example.com/page' resolved to a blocked IP address ('203.0.113.1').
```

### Fix Required (test-writer)

Replace the documentation IPs in `TestFromAC_NavigatePassthrough` with a genuinely globally routable IP. The sibling task #948 (`test_ssrf_fix_948.py`) correctly uses `93.184.216.34` (example.com's real IP, `is_global=True`):

```python
# test_allowed_domain_dns_is_resolved
with patch("socket.getaddrinfo", return_value=_addr4("93.184.216.34")) as mock_dns:

# test_allowed_domain_https_returns_url
with patch("socket.getaddrinfo", return_value=_addr4("93.184.216.34")) as mock_dns:
```

My implementation in `server.py` is correct and ready — only the two passthrough test IPs need changing.
[[2026-04-18]]

## Test-Writer Notes

**Retry fix:** Replaced RFC 5737 documentation IPs (`203.0.113.1`, `198.51.100.42`) with `93.184.216.34` (example.com, `is_global=True`) in `TestFromAC_NavigatePassthrough`. Python 3.11+ changed `ip_address.is_private` to return `True` for ALL non-globally-routable addresses, including RFC 5737 ranges — causing `_is_blocked_ip()` to block what should be pass-through IPs.

**Test file:** `serve/mcp-browser/tests/test_ssrf_preflight_950.py`

**Result:** 18 passed, 0 failed. Builder's implementation is correct and all tests pass.

**Commit:** `47e856d3` — test: fix passthrough IPs in SSRF preflight tests (#950, test-writer)
[[2026-04-18]]

## Builder Notes

### Files Changed

- `serve/mcp-browser/src/owlbear_mcp_browser/server.py` — added `import asyncio`, `import ipaddress`, `import socket`, `from urllib.parse import urlparse`; added `_is_blocked_ip()` (duplicate of `owlbear_knowledge._ssrf`); added `_check_ssrf(url)` async function; wired `await _check_ssrf(url)` before `allowlist.check(url)` in `navigate()`.
- `serve/mcp-browser/tests/__init__.py` — created (new tests/ dir)

### Test Results

- **18/18 passed**, 0 failed
- Coverage for `server.py`: 46% — SSRF functions fully covered; uncovered lines are Playwright/browser infrastructure (app_lifespan, click, type_input etc.) that require a live browser instance. Only uncovered SSRF-adjacent path: `except ValueError: return True` in `_is_blocked_ip` (unparseable IP edge case — no test exercises it).

### Lint

- `ruff check serve/mcp-browser/ tests/` — **CLEAN** (exit 0)

### Commit

- `fd2268cf` — fix(security): SSRF pre-flight check in navigate() (#950, builder)

### Evidence Summary

- Test-writer confirmed 18 FAILED in RED (before implementation)
- Previous builder implemented `_is_blocked_ip` + `_check_ssrf` + wired into `navigate()` — got 16/18 (passthrough IPs were RFC 5737 documentation ranges blocked by Python 3.11+ `is_private`)
- REJECT issued → test-writer fixed IPs to `93.184.216.34` (commit `47e856d3`)
- This build run: verified 18/18 GREEN, ruff clean, committed implementation + `__init__.py`
[[2026-04-18]]

## Review Evidence

### Test Execution (Quality-Runner — independent run)

- **18 passed, 0 failed**
- Lint: **clean** (ruff exit 0)
- Coverage: `owlbear_mcp_browser.server` = 46% (uncovered lines are pre-existing Playwright/browser infrastructure requiring a live browser; SSRF functions are line-covered — informational)

---

### Step 5.0 — AC-to-Test Coverage

| AC Line | Mapped Test(s) | Would Fail If AC Violated? | Verdict |
|---------|---------------|---------------------------|---------|
| AC1: resolve hostname via getaddrinfo → check loopback | `test_blocks_loopback_127_0_0_1`, `test_blocks_loopback_127_x_non_zero` | Yes — ToolError not raised → pytest.raises fails | COVERED |
| AC1: private ranges | `test_blocks_private_10_x`, `test_blocks_private_172_16_x`, `test_blocks_private_192_168_x` | Yes | COVERED |
| AC1: link-local | `test_blocks_link_local_169_254_x` | Yes | COVERED |
| AC1: **reserved** | *none* | No test exists for reserved IPs (e.g., 240.x, 192.0.2.x). Removing `or check.is_reserved` from `_is_blocked_ip` would not cause any test to fail. | **MISSING** |
| AC1: **unspecified** | *none* | No test for unspecified IPs (0.0.0.0, ::). Removing `or check.is_unspecified` would not cause any test to fail. | **MISSING** |
| AC1: IPv4-mapped IPv6 unwrapping | `test_blocks_ipv4_mapped_ipv6_loopback`, `test_blocks_ipv4_mapped_ipv6_private` | Yes | COVERED |
| AC2: scheme rejection | `test_javascript_scheme_rejected`, `test_file_scheme_rejected`, `test_data_scheme_rejected`, `test_ftp_scheme_rejected` | Yes | COVERED |
| AC3: check in navigate() before page.goto() | All blocklist/scheme tests | Yes — navigate() entry point verified | COVERED |
| AC4: TOCTOU + redirect SSRF documented | server.py L67–74 docstring — both limitations explicitly documented | Code-reader verified exact text at L67–74 | COVERED |
| AC5: blocked IP rejection | covered above (loopback/private/link-local/IPv4-mapped) — but reserved/unspecified missing | Partial | PARTIAL |
| AC5: scheme rejection | see AC2 | Yes | COVERED |
| AC5: allowed domain pass-through | `test_allowed_domain_dns_is_resolved`, `test_allowed_domain_https_returns_url` | Yes | COVERED |
| Binding §1: all rejections raise ToolError | server.py L78 (scheme), L90 (DNS), L93 (blocked IP) | Yes | COVERED |
| Binding §2: DNS OSError → ToolError with hostname | `test_dns_failure_raises_tool_error`, `test_dns_failure_message_contains_hostname` (match=_ALLOWED_HOST) | Yes | COVERED |
| Binding §3: check before allowlist | server.py L167–168: `_check_ssrf` before `allowlist.check` | Yes | COVERED |

**2 MISSING → automatic FAIL per 5.0.**

---

### Step 5.1 — Security Review

No OWASP concerns introduced. Implementation ADDS SSRF controls. No hardcoded secrets, no injection, no path traversal, no insecure deserialization. stdlib `ipaddress` and `socket` only. CLEAN.

---

### Step 5.2 — Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `test_allowed_domain_dns_is_resolved` | IP `203.0.113.1` → `93.184.216.34` (Python 3.11+ `is_private` reclassification fix) | STRENGTHENED |
| `test_allowed_domain_https_returns_url` | IP `198.51.100.42` → `93.184.216.34` (same reason) | STRENGTHENED |
| All other 16 TestFromAC_* tests | No changes | PRESERVED |

No WEAKENED or REMOVED. No automatic FAIL from 5.2.

---

### Step 5.3 — Test Quality

- Assertion specificity: STRONG for rejection tests (typed ToolError, regex match for hostname). `test_allowed_domain_dns_is_resolved` has a weak secondary `assert result is not None` but the primary guard `mock_dns.assert_called()` is strong — ADEQUATE.
- Error-path coverage: STRONG (4 scheme tests, DNS failure, IP blocklist).
- Mutation resistance: STRONG for covered paths.
- Independence: STRONG (isolated ctx/mock per test).
- Naming: STRONG.
Overall: **ADEQUATE**. No WEAK rating.

---

### Step 5.4 — Data Safety

No shared mutable state. No race conditions in new code. CLEAN.

---

### Step 5.5 — Implementation-Aware Test Gap Analysis

Additional gaps beyond 5.0 (informational):

- `except ValueError: return True` in `_is_blocked_ip` (L36): no test for malformed IP string. Fail-safe (blocks on doubt), so no silent security hole — informational only.
- Pure IPv6 non-mapped (e.g., `::1`): `else: check = addr` branch hit by IPv4 tests but pure IPv6 loopback not explicitly tested. Code correct per ipaddress library; informational.
- Empty hostname (`http://` → `hostname = ""`): passed to getaddrinfo, likely OSError → ToolError. Not tested; informational.

---

### Step 5.7 — Builder Process Quality

2 Builder Notes sections: initial impl (16/18 — test-writer used Python 3.11+ invalid IPs), then final confirm (18/18 after test-writer fix). Approach variation: first was implementation, second was verification. FRICTION, not LOOP. Correct pipeline handling.

---

### Deductions

| Issue | Criterion | Severity | Deduction |
|-------|-----------|----------|-----------|
| No test for `is_reserved` in `_is_blocked_ip` — AC1 explicitly requires it | 5.0 MISSING | Critical | −0.15 |
| No test for `is_unspecified` in `_is_blocked_ip` — AC1 explicitly requires it | 5.0 MISSING | Critical | −0.10 |
| server.py coverage 46% (below 90% threshold; all uncovered lines are pre-existing Playwright infra) | Step 4 | Suppressed — untouched infra | 0 |

**Confidence: 0.75**

---

### Verdict: FAIL → todo

**Root cause: test-writer gap.** Implementation is correct — `_is_blocked_ip` at server.py L30–47 correctly includes `or check.is_reserved or check.is_unspecified` per AC1. But no test exercises these branches. AC1 explicitly enumerates "reserved" and "unspecified" as required categories. Removing either condition from the return statement would not cause any test to fail.

**Fix required (test-writer):**

1. Add `TestFromAC_NavigateIPBlocklist::test_blocks_reserved_ip` — mock getaddrinfo returning a reserved IP (e.g., `240.0.0.1` — `is_reserved=True`). Assert ToolError.
2. Add `TestFromAC_NavigateIPBlocklist::test_blocks_unspecified_ip` — mock getaddrinfo returning `0.0.0.0` (`is_unspecified=True`). Assert ToolError.

Both tests follow the existing pattern in `TestFromAC_NavigateIPBlocklist`.
[[2026-04-18]]

## Test-Writer Notes

**Retry fix:** Added 2 missing tests to `TestFromAC_NavigateIPBlocklist` per reviewer's FAIL verdict.

**Test file:** `serve/mcp-browser/tests/test_ssrf_preflight_950.py`

**New tests added:**

- `test_blocks_reserved_ip` — `240.0.0.1` (class E, `is_reserved=True`). Assert `ToolError`. AC1 requires blocking reserved addresses; removing `check.is_reserved` from `_is_blocked_ip` would no longer cause any test to fail.
- `test_blocks_unspecified_ip` — `0.0.0.0` (`is_unspecified=True`). Assert `ToolError`. AC1 requires blocking unspecified addresses; removing `check.is_unspecified` would no longer cause any test to fail.

**Total: 20 tests, all PASS** — implementation was already correct (`_is_blocked_ip` at server.py L50-51 already has `or check.is_reserved or check.is_unspecified`). New tests pass immediately per retry-cycle rules (implementation ahead of tests; gap was in test coverage, not code).

**Ruff:** clean.

**Commit:** `44330e77` — test: add reserved/unspecified IP tests for SSRF preflight (#950, test-writer)

**AC coverage (complete):**

| AC line | Test(s) |
|---------|---------|
| AC1: loopback | `test_blocks_loopback_127_0_0_1`, `test_blocks_loopback_127_x_non_zero` |
| AC1: private | `test_blocks_private_10_x`, `test_blocks_private_172_16_x`, `test_blocks_private_192_168_x` |
| AC1: link-local | `test_blocks_link_local_169_254_x` |
| AC1: **reserved** | `test_blocks_reserved_ip` ✅ NEW |
| AC1: **unspecified** | `test_blocks_unspecified_ip` ✅ NEW |
| AC1: IPv4-mapped IPv6 | `test_blocks_ipv4_mapped_ipv6_loopback`, `test_blocks_ipv4_mapped_ipv6_private` |
| AC2: scheme rejection | `test_javascript_scheme_rejected`, `test_file_scheme_rejected`, `test_data_scheme_rejected`, `test_ftp_scheme_rejected` |
| Binding §2: DNS OSError → ToolError | `test_dns_failure_raises_tool_error`, `test_dns_failure_message_contains_hostname` |
| AC5: pass-through | `test_allowed_domain_dns_is_resolved`, `test_allowed_domain_https_returns_url` |
[[2026-04-18]]

## Builder Notes

### Context

This is a re-entry after reviewer FAIL. Implementation was already committed at `fd2268cf` (correct). Test-writer added 2 missing tests at `44330e77` (`test_blocks_reserved_ip` + `test_blocks_unspecified_ip`). Builder role here: verify RED→GREEN is satisfied with the 20-test suite.

### Files Changed

No new files changed — all changes were committed in prior cycles:

- `serve/mcp-browser/src/owlbear_mcp_browser/server.py` — `_is_blocked_ip`, `_check_ssrf`, wired into `navigate()` (commit `fd2268cf`)
- `serve/mcp-browser/tests/test_ssrf_preflight_950.py` — 20 tests (commit `44330e77`)
- `serve/mcp-browser/tests/__init__.py` — created (commit `fd2268cf`)

### Test Results

- **20/20 passed**, 0 failed (exit 0)
- New tests confirmed GREEN: `test_blocks_reserved_ip` (240.0.0.1, `is_reserved=True`) and `test_blocks_unspecified_ip` (0.0.0.0, `is_unspecified=True`)

### Lint

`ruff check serve/mcp-browser/ tests/` — **CLEAN** (exit 0)

### Evidence Summary

- 20 passed in 0.40s
- Reviewer's FAIL concerns (AC1 reserved/unspecified not test-covered) resolved by test-writer's retry
- Implementation at server.py L50-51 already included `or check.is_reserved or check.is_unspecified` — correct throughout
[[2026-04-18]]

## Review Evidence

### Test Execution (Quality-Runner — independent run, cycle 2)

- **20 passed, 0 failed**
- Lint: **clean** (ruff exit 0)
- Coverage: `owlbear_mcp_browser.server` = 46% (pre-existing Playwright infra uncovered; SSRF functions line-covered — suppressed)

---

### Prior FAIL Remediation

| Prior FAIL Finding | Remedy | Verdict |
|--------------------|--------|---------|
| No test for `is_reserved` — AC1 MISSING | `test_blocks_reserved_ip` (240.0.0.1, `is_reserved=True`): assert ToolError; removing `check.is_reserved` from `_is_blocked_ip` causes test to fail | RESOLVED |
| No test for `is_unspecified` — AC1 MISSING | `test_blocks_unspecified_ip` (0.0.0.0, `is_unspecified=True`): assert ToolError; removing `check.is_unspecified` causes test to fail | RESOLVED |

---

### AC-to-Test Coverage (Step 5.0)

| AC Line | Mapped Test(s) | Would Fail If Violated? | Verdict |
|---------|---------------|------------------------|---------|
| AC1: loopback | `test_blocks_loopback_127_0_0_1`, `test_blocks_loopback_127_x_non_zero` | Yes | COVERED |
| AC1: private | `test_blocks_private_10_x/172_16_x/192_168_x` | Yes | COVERED |
| AC1: link-local | `test_blocks_link_local_169_254_x` | Yes | COVERED |
| AC1: reserved | `test_blocks_reserved_ip` (240.0.0.1) | Yes | COVERED |
| AC1: unspecified | `test_blocks_unspecified_ip` (0.0.0.0) | Yes | COVERED |
| AC1: IPv4-mapped IPv6 unwrapping | `test_blocks_ipv4_mapped_ipv6_loopback/private` | Yes | COVERED |
| AC2: scheme rejection | `test_javascript/file/data/ftp_scheme_rejected` | Yes | COVERED |
| AC3: check in navigate() before page.goto() | server.py L167: `await _check_ssrf(url)` before `allowlist.check(url)` | Yes | COVERED |
| AC4: TOCTOU + redirect SSRF documented | server.py L67–74 docstring — both limitations explicit | Verified | COVERED |
| AC5: all test categories | see above + `test_allowed_domain_dns_is_resolved/https_returns_url` | Yes | COVERED |
| Binding §1: rejections raise ToolError | server.py L78 (scheme), L90 (DNS), L93 (blocked IP) | Yes | COVERED |
| Binding §2: DNS OSError → ToolError w/hostname | `test_dns_failure_raises_tool_error`, `test_dns_failure_message_contains_hostname` (match=_ALLOWED_HOST) | Yes | COVERED |
| Binding §3: _check_ssrf before allowlist | server.py L167: confirmed ordering | Yes | COVERED |

No MISSING. No LAX.

---

### Step 5.1 — Security Review

CLEAN. Implementation adds SSRF controls. No hardcoded secrets, no injection, no path traversal, no insecure deserialization. stdlib `ipaddress`, `socket`, `asyncio` only.

### Step 5.2 — Test Integrity

No TestFromAC_* tests weakened or removed. Passthrough IP change (`203.0.113.1`/`198.51.100.42` → `93.184.216.34`) is STRENGTHENED (Python 3.11+ `is_private` reclassification fix). Two new tests added (STRENGTHENED).

### Step 5.3 — Test Quality: STRONG

- Assertion specificity: STRONG — typed `pytest.raises(ToolError)`, DNS message uses `match=_ALLOWED_HOST`
- Error-path coverage: STRONG — 4 scheme tests, 10 IP blocklist tests (including 2 new), 2 DNS failure tests
- Mutation resistance: STRONG — new tests include comments explaining which code removal would cause failure
- Independence: STRONG
- Naming: STRONG

### Step 5.4 — Data Safety: CLEAN

No shared mutable state, no race conditions in new code.

### Step 5.7 — Builder Process Quality: FRICTION

Multi-cycle pipeline driven by test gap (cycle 1 FAIL on missing reserved/unspecified tests, not implementation error). Each cycle has approach variation. No tier-3 violation.

---

### Deductions

None.

### Verdict: PASS

**Confidence: .98**
All prior FAIL concerns resolved. All 20 AC tests pass. Lint clean. Implementation correct at server.py L167-168 (`_check_ssrf` before `allowlist.check`). Accepted limitations documented per binding guidance §3.
[[2026-04-18]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Security hardening to agent-only tool behind closed-by-default allowlist. `.github/copilot-instructions.md` documents branch organization only — no per-tool security policy section. No consumer-facing API change requiring doc update. |
| 2 | Module docstrings | Yes | Verified | `_is_blocked_ip`: docstring present — CWE-918 + IPv4-mapped note. `_check_ssrf`: comprehensive docstring — Raises section, 2 accepted limitations (TOCTOU + redirect SSRF) per binding §3. `navigate`: existing one-liner accurate; error details documented in `_check_ssrf`. All public classes/functions covered. |
| 3 | External attribution | Yes | Verified | `.owlbear/sources/overview.md` already has "SSRF Pre-Flight Check for navigate() (Task #950)" section with Playwright page.goto() docs and OwlBear #946 `_is_blocked_ip` as sources. No update needed. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/950-ssrf-browser-navigate.md` exists and is linked in task body. |

### Files Updated

None — all documentation verified accurate as-is.

### Scratch Files

None found (`.owlbear/scratch/950-*` — no matches).
[[2026-04-18]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: resolve hostname via getaddrinfo, check IPs (loopback/private/link-local/reserved/unspecified, IPv4-mapped IPv6) | server.py L80-93: asyncio.to_thread(socket.getaddrinfo) +_is_blocked_ip() L31-54 with all categories. 12 tests: loopback x2, private x3, link-local, IPv4-mapped x2, multi-blocked, literal IP, reserved (240.0.0.1), unspecified (0.0.0.0) | PASS |
| AC2: reject non-http/https schemes | server.py L78-79: scheme check. 4 tests: javascript, file, data, ftp | PASS |
| AC3: check in navigate() before page.goto() | server.py L173: await _check_ssrf(url) BEFORE L174: allowlist.check(url). All 20 tests invoke navigate() directly | PASS |
| AC4: TOCTOU + redirect SSRF documented | server.py L67-74 docstring: both limitations explicitly documented per binding guidance S3 | PASS |
| AC5: tests cover blocked IP, scheme rejection, allowed pass-through | 20 tests total across 4 test classes. Passthrough: test_allowed_domain_dns_is_resolved, test_allowed_domain_https_returns_url (93.184.216.34, is_global=True) | PASS |

### Test Results

- pytest (full suite): 418 passed, 6 failed, 0 skipped
- 6 failures are pre-existing in mcp-knowledge (get_stats schema x4, limit forwarding x1) and skill doc path test (x1). None in mcp-browser scope. No cross-task regressions.
- Task-scoped: 20/20 passed
- ruff: clean (exit 0)

### Architect Quality: 5/5

AC was exemplary: enumerated all IP categories explicitly, specified check ordering (before allowlist), identified scheme bypass vector (javascript://allowlisted-host/), included binding guidance addressing challenger concerns (error type, DNS failure handling, redirect SSRF documentation, reference implementation location). The only friction was a test-writer IP selection issue (RFC 5737 vs Python 3.11+ is_private), not an architect gap.

### Deduction Breakdown

- AC lines without evidence: 0 (all 5 verified)
- Lint violations: 0
- AC quality score: 5/5 (no deduction)
- Missing reviewer evidence: 0 (detailed, 2-cycle review with full AC-to-test mapping)
- Full-suite failures in task scope: 0

### Confidence: .98

(.02 held back: cannot independently verify git commits without terminal access; relying on builder/test-writer reported hashes fd2268cf, 47e856d3, 44330e77)

### Action: archive
