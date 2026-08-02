---
id: 947
title: 'Fix SSRF CWE-918 in intake.read_url: add private/loopback IP blocklist'
status: archived
priority: medium
created: 2026-04-18T00:12:36.287538+00:00
updated: 2026-04-18T01:48:09.571290+00:00
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

`read_url` in `serve/knowledge/src/owlbear_knowledge/intake.py` (L58–85) accepts user-controlled URLs with no IP validation — only scheme check. Same SSRF vulnerability as #946 (`_web_read`).

Uses `httpx.AsyncClient().get(url)` with default settings (follows redirects, no IP blocklist).

## Acceptance Criteria

- [ ] `read_url` resolves the URL hostname to IP(s) asynchronously before making any HTTP request
- [ ] Blocked ranges match #946: use `ipaddress` stdlib properties (`.is_private`, `.is_loopback`, `.is_link_local`, `.is_reserved`, `.is_unspecified`) plus `.ipv4_mapped` check
- [ ] DNS rebinding is mitigated: HTTP request is made to the resolved IP directly (same pattern as #946)
- [ ] Redirects are disabled (`follow_redirects=False`) as defense-in-depth
- [ ] Any blocked URL raises `ValueError` with descriptive message (this function raises on errors, unlike `_web_read` which returns None)
- [ ] Reuse the validation helper from #946 if one was extracted, or extract a shared utility if the pattern is identical
- [ ] Unit tests cover: localhost, 127.x, 10.x, 172.16.x, 192.168.x, 169.254.x, ::1, fe80::, ::ffff:127.0.0.1, and a safe public IP
- [ ] `ruff check` passes

## Context

Sibling of #946. Discovered during architecture review of #946 — same vulnerability pattern in a different call site. Called by `RefreshOrchestrator` at `serve/knowledge/src/owlbear_knowledge/refresh.py` L166 with URLs from `source.config["urls"]`.

[[2026-04-18]]

## Architecture Review

### AC Refinements Applied

**Added AC line (scheme validation):** Original AC lacked explicit scheme check — `file://`, `ftp://`, `gopher://` bypass DNS resolution entirely. Added: "Reject URLs with schemes other than `http` / `https` before DNS resolution (raise `ValueError`)."

**Refined AC line 3 (Host header):** Added Host header requirement for IP-rewritten requests — mandatory for TLS SNI and virtual-host routing. Without it, HTTPS requests fail on certificate mismatch.

**Refined AC line 6 (utility extraction):** Replaced ambiguous "if the pattern is identical" with explicit guidance: extract a complete `safe_async_fetch(url) -> str` utility to `serve/knowledge/src/owlbear_knowledge/_ssrf.py` encapsulating the full resolve-check-rewrite-fetch pattern. This prevents #947, #948, and server.py from independently reimplementing the same multi-step pipeline. Include `_is_blocked_ip()` and the DNS pre-resolution + URL rewrite logic. The `mcp-knowledge/server.py` migration to use this utility is OUT OF SCOPE — that's a follow-up.

**Refined AC line 7 (test coverage):** Added `0.0.0.0` and `::` (unspecified addresses) to match `.is_unspecified` requirement in AC line 2.

**Added note on `follow_redirects=False`:** This will break legitimate redirect-bearing URLs (HTTP→HTTPS, URL shorteners). This is an intentional security trade-off — SSRF via redirect is a known attack vector. The refresh orchestrator's `_handle_url_list` should use final/canonical URLs.

### Revised Acceptance Criteria

- [ ] `read_url` rejects URLs with schemes other than `http` / `https` before DNS resolution (raise `ValueError`)
- [ ] `read_url` resolves the URL hostname to IP(s) asynchronously before making any HTTP request
- [ ] Blocked ranges match #946: use `ipaddress` stdlib properties (`.is_private`, `.is_loopback`, `.is_link_local`, `.is_reserved`, `.is_unspecified`) plus `.ipv4_mapped` check
- [ ] DNS rebinding is mitigated: HTTP request is made to the resolved IP directly with `Host` header set to the original hostname (required for TLS SNI and virtual-host routing)
- [ ] Redirects are disabled (`follow_redirects=False`) as defense-in-depth — intentional trade-off: callers must use canonical URLs
- [ ] Any blocked URL raises `ValueError` with descriptive message (this function raises on errors, unlike `_web_read` which returns None)
- [ ] Extract a complete SSRF-safe fetch utility to `serve/knowledge/src/owlbear_knowledge/_ssrf.py` containing `_is_blocked_ip()` and the full resolve → check → rewrite → fetch pipeline. `read_url` delegates to this utility. Migrating `mcp-knowledge/server.py` to use it is out of scope.
- [ ] Unit tests cover: localhost, 127.x, 10.x, 172.16.x, 192.168.x, 169.254.x, 0.0.0.0, ::1, ::, fe80::, ::ffff:127.0.0.1, and a safe public IP
- [ ] `ruff check` passes

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Fix SSRF in `read_url` + extract shared utility (necessary supporting change) |
| Interface clarity | PASS (after refinement) | All AC lines now testable; scheme, Host header, error type explicit |
| Dependency correctness | PASS | #946 archived (done). Utility goes in knowledge pkg (correct dep direction) |
| Module layering | PASS | `_ssrf.py` in `serve/knowledge/` — mcp-knowledge depends on knowledge, not inverse |
| TDD compliance | PASS | AC includes test requirements; pipeline will RED then GREEN |
| KISS/YAGNI | PASS | Minimal scope with utility extraction justified by 3 identical call sites |
| Premise challenge | PASS | Genuine CWE-918 vulnerability confirmed in code |
| Pattern consistency | PASS | Follows proven pattern from #946 (`_web_read`) |
| Security surface | PASS | This IS the security fix; AC covers scheme, DNS, IP, redirect, rebinding |
| Single domain | PASS | Knowledge domain only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| Scheme check | Non-http(s) URL | ValueError | Yes (AC) | Rejected with message |
| DNS resolution | Hostname unresolvable | OSError → ValueError | Needs wrapping | Rejected with message |
| IP check | All resolved IPs blocked | ValueError | Yes (AC) | Rejected with message |
| HTTP request | Non-2xx response | httpx.HTTPStatusError | Existing behavior | Propagated to caller |
| HTTP request | Network/timeout error | httpx exception | Existing behavior | Propagated to caller |

### Challenge Results

- Challenger: reconsider (0.55)
- Architect response: accepted C1 (scheme), C4 (Host header), C5 (test list), alternative (full utility extraction). Rejected C3 (out of scope — #948). AC refined accordingly.

### Verdict: APPROVE (after REFINE)

### Action Taken: Refined 4 AC lines, added 1 new AC line, added builder guidance note. Advanced to todo

[[2026-04-18]]

## Test-Writer Notes

**Test file:** `serve/knowledge/tests/test_ssrf_fix_947.py`

**Classes:**

- `TestFromAC_ReadUrlSSRF` — 22 tests for `read_url` SSRF contract
- `TestFromAC_SsrfUtility` — 9 tests for `owlbear_knowledge._ssrf` utility module

**Tests by category:**

| Category | Count | Examples |
|----------|-------|---------|
| Scheme rejection (AC1) | 3 | file://, ftp://, gopher:// → ValueError |
| Blocked IPv4 literals (AC3/6/8) | 7 | 127.0.0.1, 10.x, 172.16.x, 192.168.x, 169.254.x, 0.0.0.0 |
| Blocked IPv6 literals (AC3/6/8) | 4 | ::1, ::, fe80::1, ::ffff:127.0.0.1 |
| Hostname DNS pre-resolution (AC8) | 1 | localhost → 127.0.0.1 |
| Descriptive error message (AC6) | 1 | ValueError message matches blocklist keywords |
| DNS failure raises ValueError | 1 | OSError from getaddrinfo → ValueError |
| DNS rebinding — private IP blocked (AC4) | 1 | hostname resolves to 10.0.0.50 |
| DNS rebinding — TOCTOU (AC4) | 1 | httpx receives resolved IP URL, not hostname |
| Host header (AC4) | 1 | headers={Host: example.com} in httpx call |
| follow_redirects=False (AC5) | 1 | AsyncClient(follow_redirects=False) |
| Happy path + DNS called (AC2) | 1 | mock_dns.assert_called_once() |
| _ssrf module exportable (AC7) | 9 | importlib.import_module fails on missing module |

**Total: 31 tests, all FAIL**

Confirmed: `uv run pytest serve/knowledge/tests/test_ssrf_fix_947.py -v --tb=line -n 0` → 31 failed, 0 passed.

**AC coverage:**

| AC line | Tests |
|---------|-------|
| Reject non-http/https schemes → ValueError | test_rejects_{file,ftp,gopher}_scheme |
| Async DNS resolution before HTTP | test_blocks_localhost, test_dns_rebinding_private, test_allows_safe_public_ip_dns_resolved |
| Block loopback/private/link-local/reserved/unspecified + ipv4_mapped | 11 IP-blocking tests |
| DNS rebinding: IP URL rewrite + Host header | test_dns_rebinding_httpx*, test_host_header |
| follow_redirects=False | test_follow_redirects_is_disabled |
| Blocked URL raises ValueError with message | test_blocked_ip_valueerror_has_descriptive_message |
| Extract _ssrf.py with_is_blocked_ip + safe_async_fetch | 9 TestFromAC_SsrfUtility tests |
| IP coverage: localhost, 127.x, 10.x, 172.16.x, 192.168.x, 169.254.x, 0.0.0.0, ::1, ::, fe80::, ::ffff:127.0.0.1, safe public | covered across IP-blocking tests |

ruff check: all checks passed.
[[2026-04-18]]

## Builder Notes

**Files changed (2):**

- `serve/knowledge/src/owlbear_knowledge/_ssrf.py` — NEW: `_is_blocked_ip()` + `safe_async_fetch()` utility
- `serve/knowledge/src/owlbear_knowledge/intake.py` — `read_url` delegates to `safe_async_fetch`; removed obsolete httpx try/except import

**Test results:** 31 passed, 0 failed — all `TestFromAC_ReadUrlSSRF` (22) and `TestFromAC_SsrfUtility` (9) tests green

**Coverage:** `_ssrf.py` 91%, `intake.py` 81% (uncovered lines are in `read_file`/`read_text` — unrelated to this task)

**Lint:** `ruff check serve/ tests/` — all checks passed

**Evidence summary:**

- Scheme check: `file://`, `ftp://`, `gopher://` → ValueError before DNS ✓
- IPv4 literals: 127.0.0.1, 127.0.0.100, 10.x, 172.16.x, 192.168.x, 169.254.169.254, 0.0.0.0 → ValueError ✓
- IPv6 literals: ::1, ::, fe80::1, ::ffff:127.0.0.1 → ValueError ✓
- DNS pre-resolution: localhost → 127.0.0.1 → ValueError ✓
- DNS rebinding: hostname resolving to 10.0.0.50 → ValueError ✓
- TOCTOU: httpx receives resolved IP URL, not original hostname ✓
- Host header: `{"Host": "example.com"}` on rewritten request ✓
- `follow_redirects=False` kwarg on `AsyncClient` ✓
- DNS failure (OSError) → ValueError ✓
- Descriptive ValueError message matches pattern ✓
- `_ssrf` module importable, `_is_blocked_ip` and `safe_async_fetch` callable ✓

**Commit:** `7a8bd2a7` fix(security): extract _ssrf.py and harden read_url against CWE-918 (#947)
[[2026-04-18]]

## Review Evidence

### Test Results

- pytest: 31 passed, 0 failed

### Lint: clean

### Coverage

- `owlbear_knowledge._ssrf`: 91%
- `owlbear_knowledge.intake`: 81% (uncovered lines in `read_file`/`read_text` — unrelated to this task)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: Reject non-http/https | test_rejects_{file,ftp,gopher}_scheme | Yes — pytest.raises(ValueError) + mock_dns.assert_not_called() | COVERED |
| AC2: Async DNS resolution | test_allows_safe_public_ip_dns_resolved_before_fetch | Yes — mock_dns.assert_called_once() | COVERED |
| AC3: Blocked ranges + ipv4_mapped | 11 IP-blocking tests | Yes — pytest.raises(ValueError) per IP | COVERED |
| AC4: DNS rebinding + Host header | test_dns_rebinding_httpx_*, test_host_header_* | Yes — URL contains no hostname + headers["Host"] check | COVERED |
| AC5: follow_redirects=False | test_follow_redirects_is_disabled | Yes — call_kwargs.get("follow_redirects") is False | COVERED |
| AC6: ValueError descriptive message | test_blocked_ip_valueerror_has_descriptive_message | Yes — pytest.raises(ValueError, match=...) | COVERED |
| AC7: _ssrf.py extraction | TestFromAC_SsrfUtility (9 tests) | Yes — importlib + callable checks | COVERED |
| AC8: All 12 IP addresses | All IP-blocking tests | Yes — individual raises per IP | COVERED |

#### Security Review

No issues. All resolved IPs checked (loop over all addrs, not just first). IPv4-mapped bypass covered (addr.ipv4_mapped unwrap). No DNS re-query between check and fetch. No hardcoded secrets, injection, or secret leakage in error messages.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 31 TestFromAC_* methods | None — identical to test-writer output | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | host_value == "example.com", follow_redirects is False, result.content == "public page content" |
| Negative/error-path coverage | STRONG | 14/22 tests are blocking/error cases |
| Manual mutation reasoning | STRONG | Remove any guard → corresponding test fails |
| Test independence | STRONG | Fresh mocks per test |
| Descriptive names | STRONG | All names describe exact security property |

#### Data Safety

No issues.

#### Implementation-Aware Gaps

IPv6 safe-IP URL rewrite branch (`f"[{first_ip}]"`) untested — all IPv6 test cases block before reaching it. Trivial logic, accounts for 9% coverage gap. Not flagged.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

- IPv6 happy-path URL rewrite (`f"[{first_ip}]"`) untested. Trivial `isinstance` check + string format. Low risk.
- `timeout=30` hardcoded in AsyncClient. Reasonable; YAGNI applies.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: Reject non-http/https | _ssrf.py: scheme not in {"http","https"} → ValueError | test_rejects_{file,ftp,gopher}_scheme | PASS |
| AC2: Async DNS | _ssrf.py: asyncio.to_thread(socket.getaddrinfo, ...) | test_allows_safe_public_ip_dns_resolved_before_fetch | PASS |
| AC3: Blocked ranges + ipv4_mapped | _ssrf.py: all 5 properties + addr.ipv4_mapped unwrap | 11 IP-blocking tests | PASS |
| AC4: DNS rebinding + Host header | _ssrf.py: ip_url rewrite + headers={"Host": hostname} | test_dns_rebinding_httpx_*, test_host_header_* | PASS |
| AC5: follow_redirects=False | _ssrf.py: AsyncClient(follow_redirects=False, timeout=30) | test_follow_redirects_is_disabled | PASS |
| AC6: ValueError message | _ssrf.py: f"URL {url!r} is blocked: resolved IP {sockaddr[0]!r} is private, loopback…" | test_blocked_ip_valueerror_has_descriptive_message | PASS |
| AC7: _ssrf.py extraction | serve/knowledge/src/owlbear_knowledge/_ssrf.py exists; read_url delegates to safe_async_fetch | TestFromAC_SsrfUtility (9 tests) | PASS |
| AC8: All 12 IP addresses | localhost, 127.x, 10.x, 172.16.x, 192.168.x, 169.254.x, 0.0.0.0, ::1, ::, fe80::, ::ffff:127.0.0.1, safe public | All IP-blocking tests | PASS |

### Confidence: .96

### Verdict: PASS

[[2026-04-18]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `copilot-instructions.md` has no tech stack or API table. `read_url` behavior change (raises `ValueError` on blocked URLs) is internal security hardening — no agent-facing convention changed. |
| 2 | Module docstrings | Yes | Verified | `_ssrf.py`: module docstring accurate, `_is_blocked_ip()` ✓, `safe_async_fetch()` ✓ (Raises section correct). `intake.py`: module docstring ✓, `read_url` docstring updated with correct Raises entries ✓, `read_file`/`read_text`/`IntakeResult` unchanged and accurate. |
| 3 | External attribution | No | N/A | Pattern extracted from internal #946 (stdlib `ipaddress`, `socket`, `asyncio.to_thread` — no external repos or articles). |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | No | N/A | No research doc produced; task originated as sibling fix from #946 architecture review. No `.owlbear/research/*947*` file expected or present. |

### Files Updated

- None — docstrings verified accurate as committed, no edits required.

### Scratch Files Cleaned

- None — no `.owlbear/scratch/947-*` files found.
[[2026-04-18]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Reject non-http/https schemes | _ssrf.py L52-54: scheme check, ValueError | PASS |
| AC2: Async DNS resolution before HTTP | _ssrf.py L64-66: asyncio.to_thread(socket.getaddrinfo) | PASS |
| AC3: Blocked ranges + ipv4_mapped | _ssrf.py L18-36: all 5 properties + ipv4_mapped unwrap | PASS |
| AC4: DNS rebinding + Host header | _ssrf.py L78-85: ip_url rewrite + headers={"Host": hostname} | PASS |
| AC5: follow_redirects=False | _ssrf.py L85: AsyncClient(follow_redirects=False, timeout=30) | PASS |
| AC6: ValueError descriptive message | _ssrf.py L73-76: f-string with IP and context | PASS |
| AC7: _ssrf.py extraction | _ssrf.py exists with_is_blocked_ip + safe_async_fetch; intake.py delegates | PASS |
| AC8: All 12 IP addresses covered | 31 tests across TestFromAC_ReadUrlSSRF + TestFromAC_SsrfUtility | PASS |
| AC9: ruff check passes | ruff exit 0, clean | PASS |

### Test Results

- pytest: 398 passed, 24 failed (all failures from other tasks: #946, #948, #950, #541 — none in task scope)
- ruff: clean (exit 0)

### Architect Quality: 5/5

Exemplary. Scheme validation gap identified and added. Host header for TLS SNI. Comprehensive failure mode map. Clear scope boundary (mcp-knowledge migration out of scope). Challenger review conducted and addressed. All AC lines specific and testable.

### Deduction Breakdown

- AC lines without evidence: 0 (all 9 PASS) — no deduction
- Lint violations: none — no deduction
- AC quality score: 5/5 — no deduction
- Missing reviewer evidence: present, detailed, PASS — no deduction
- Full-suite failures in task scope: 0 — no deduction

### Confidence: 1.00

### Action: archive
