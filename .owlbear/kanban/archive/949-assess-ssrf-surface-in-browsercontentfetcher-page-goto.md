---
id: 949
title: Assess SSRF surface in BrowserContentFetcher (page.goto)
status: archived
priority: important
created: 2026-04-18T01:09:19.403442+00:00
updated: 2026-04-18T02:00:47.612065+00:00
tags:
- security
- browser
- type:research
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Problem

`BrowserContentFetcher` in `serve/browser/src/owlbear_browser/fetcher.py` calls `page.goto(url)` with no IP validation. The `mcp-browser` server's `DomainAllowlist` checks domain names but not IP addresses — `http://127.0.0.1/` may bypass the allowlist when empty or when the literal IP is listed.

After #946, #947, and #948 fix SSRF in `_web_read`, `read_url`, and `HttpxContentFetcher.fetch`, this remains the only `ContentFetcher` implementation without IP-level SSRF protection.

## Research Questions

- [ ] Is `BrowserContentFetcher` reachable from user-controlled input today? (Check `RefreshOrchestrator` wiring in `mcp-knowledge`)
- [ ] Does Playwright's `page.goto()` support connecting to a resolved IP with Host header? If not, what mitigation patterns apply?
- [ ] Does the `DomainAllowlist` already cover this threat adequately for the current deployment model?
- [ ] Should SSRF validation be lifted to a protocol-level wrapper (`SafeContentFetcher`) to protect all implementations automatically?

## Context

Discovered during architecture review of #948. Sibling vulnerability to #946/#947/#948 but in a different package (`owlbear_browser`) with a different HTTP client (Playwright).

[[2026-04-18]]

## Research

- Research doc: .owlbear/research/949-ssrf-browser-fetcher.md
- Sources: 6 studied, 3 external (Playwright docs)
- Recommendation: Add pre-flight DNS + IP blocklist + scheme check to `navigate()` in mcp-browser server (confidence: .72)
- Follow-up tasks created: #950 (nice-to-have, research status)
- Decision requests: none

## Challenge Results

- Challenger: reconsider (confidence in original: .45)
- Key challenges: (1) fix belongs in `navigate()` not `BrowserContentFetcher.fetch()` — 3 `page.goto()` call sites; (2) redirect-based SSRF more realistic than DNS rebinding; (3) priority should be `nice-to-have` not `important` given unreachability
- Researcher response: accepted — revised recommendation to target `navigate()`, downgraded priority, noted redirect SSRF as accepted risk (requires compromised allowlisted domain)

## Key Findings

1. BrowserContentFetcher is NOT reachable from user-controlled input today (RefreshOrchestrator has no content_fetcher)
2. DomainAllowlist is closed-by-default (empty env var = all navigation blocked)
3. Playwright's page.goto() does NOT support IP+Host header pattern — TOCTOU risk from DNS rebinding is accepted
4. Three page.goto() paths in navigate() — fix must be in navigate(), not in the fetcher class
5. Redirect-based SSRF (302 to internal IP) is more realistic than DNS rebinding but requires compromised allowlisted domain
[[2026-04-18]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: assess SSRF surface in BrowserContentFetcher/navigate |
| Interface clarity | PASS | 4 research questions well-defined, all answered with evidence |
| Dependency correctness | PASS | No dependencies; none needed for standalone research |
| Module layering | N/A | Research task — no code changes |
| TDD compliance | PASS | Tagged `type:research`, pipeline pass-through |
| KISS/YAGNI | PASS | Scoped to assessment only; implementation deferred to #950 |
| Premise challenge | PASS | SSRF assessment warranted; sibling tasks #946/#947/#948 establish hardening precedent |
| Pattern consistency | PASS | Follows research doc pattern (sources, findings, recommendation, follow-up) |
| Security surface | PASS | This IS the security assessment; findings correctly identify gaps and severity |
| Single domain | PASS | Browser/security domain |

### Codebase Verification

- `fetcher.py` L22: `page.goto(url)` with no validation — confirmed
- `allowlist.py` L30: hostname-only check, no IP validation — confirmed
- `server.py` L110/L117/L126: three `page.goto()` paths in `navigate()` — confirmed
- Research finding that `BrowserContentFetcher` is unreachable from user input — confirmed (RefreshOrchestrator has no content_fetcher wiring)
- Follow-up #950 created at `research`/`nice-to-have` with concrete AC — confirmed

### Challenge Results

- Challenge: FALLBACK — challenger subagent unavailable in session
- Research-phase challenge already applied: reconsider (confidence .45), researcher accepted all key challenges (fix in `navigate()`, priority downgrade, redirect SSRF as accepted risk)

### Verdict: APPROVE

### Action Taken: Advanced #949 to todo. Research complete with thorough findings, codebase-verified gaps, and properly scoped follow-up task #950

[[2026-04-18]]

## Test-Writer Notes

- Non-implementation task (tagged `type:research`) — no tests applicable.
- Passing through to builder.
[[2026-04-18]]

## Builder Notes

**Type:** `type:research` — pass-through, no implementation.

**Files changed:** none

**Test results:** N/A — test-writer explicitly noted "no tests applicable"

**Lint status:** N/A

**Evidence summary:**

- Research doc confirmed at `.owlbear/research/949-ssrf-browser-fetcher.md`
- All 4 research questions answered with codebase-verified findings
- Architecture review approved, follow-up #950 created
- No code changes warranted for this task; implementation deferred to #950
[[2026-04-18]]

## Review Evidence

**Type:** `type:research` — no tests, lint, or coverage applicable.

### Test / Lint / Coverage

N/A — test-writer explicitly noted "no tests applicable." Builder confirmed "Files changed: none." No quality-runner dispatch needed.

### Ghost-Change Check

Verified `server.py` contains `_check_ssrf` additions — confirmed this is work-in-progress from the #950 builder (task #950 claimed/in-progress), NOT from the #949 builder. #949 produced zero file changes as declared. ✓

### Codebase Fact Verification

| Claim | Location | Verified |
|-------|----------|---------|
| `page.goto(url)` with no validation in fetcher | `fetcher.py` L22 | ✓ |
| DomainAllowlist does hostname-only check | `allowlist.py` L29-30 | ✓ |
| Three `page.goto()` paths in `navigate()` | `server.py` (2 direct + 1 via fetcher) | ✓ |
| RefreshOrchestrator has no `content_fetcher` wiring | `mcp-knowledge/server.py` L287-291 | ✓ |
| Follow-up #950 created at `nice-to-have` | Task confirmed | ✓ |
| DomainAllowlist is closed-by-default | `allowlist.py` raises if hostname not in frozenset | ✓ |

Line numbers in research doc (L111/L117/L126) vs current file (L187/L196) — delta explained by #950 builder adding `_check_ssrf` + `_is_blocked_ip` functions above `navigate()`. Research was accurate at time of writing.

### AC Compliance

| Research Question | Evidence | Status |
|-------------------|----------|--------|
| Q1: Is BrowserContentFetcher reachable from user input? | RefreshOrchestrator wiring confirmed — no `content_fetcher` param | COVERED |
| Q2: Does Playwright support IP+Host header pattern? | Research §3.4: no, TOCTOU risk accepted | COVERED |
| Q3: Does DomainAllowlist cover the threat adequately? | Closed-by-default confirmed; gaps documented (IP-literal bypass, redirect SSRF) | COVERED |
| Q4: Should SSRF be lifted to SafeContentFetcher wrapper? | Answered: fix in `navigate()`, not a wrapper | COVERED |

### Research Document Quality

- Doc present at `.owlbear/research/949-ssrf-browser-fetcher.md` ✓
- 6 sources studied, all high relevance ✓
- Sources table vs task body count: task body says "3 external (Playwright docs)" while sources table shows 2 Playwright docs — cosmetic discrepancy, does not affect findings
- Mitigation options table (A/B/C/D) with KISS scores: thorough ✓
- Challenge accepted and integrated: fix location corrected to `navigate()`, priority downgraded ✓
- Follow-up #950 created with concrete AC including scheme check, IP blocklist, DNS error handling, and test coverage requirements ✓

### Deductions

- −0.02: Minor source count discrepancy ("3 external" vs 2 Playwright docs in table)

### Verdict

Confidence: **.96** → **PASS**
[[2026-04-18]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `type:research` — zero code changes declared and verified by reviewer |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | Yes | Already done | `.owlbear/sources/overview.md` contains "SSRF Surface in BrowserContentFetcher (Task #949)" section with all 3 Playwright external sources — added by researcher |
| 4 | CLI changes | No | N/A | No CLI additions or modifications |
| 5 | Research doc | Yes | Verified | `.owlbear/research/949-ssrf-browser-fetcher.md` present; linked in task body; follow-up #950 created at `nice-to-have` |

### Files Updated

- None

### Scratch Files Cleaned

- None (no `.owlbear/scratch/949-*` files found)
[[2026-04-18]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Q1: BrowserContentFetcher reachable from user input? | Research doc S3.1 + reviewer verified mcp-knowledge/server.py L287-291: no content_fetcher wiring | PASS |
| Q2: Playwright supports IP+Host header? | Research doc S3.4: no, TOCTOU risk documented as accepted | PASS |
| Q3: DomainAllowlist covers threat adequately? | Research doc S3.2 + reviewer verified allowlist.py L29: closed-by-default, gaps documented | PASS |
| Q4: Lift SSRF to SafeContentFetcher wrapper? | Research doc S3: answered (fix in navigate(), not wrapper); follow-up #950 created | PASS |

### Research Deliverables

- Research doc: .owlbear/research/949-ssrf-browser-fetcher.md (exists, ~280 lines, 6 sources)
- Follow-up: #950 created at research/nice-to-have with concrete AC
- Challenge integrated: fix location corrected to navigate(), priority downgraded

### Test Results

- pytest: 416 passed, 6 failed (all in serve/mcp-knowledge — schema/config tests, outside task scope)
- ruff: clean

### Architect Quality: 4/5

4 specific research questions, all answerable. Challenge results properly integrated. Minor: Q4 wording could be more precise but was clear enough.

### Deduction Breakdown

- 4 AC lines all with specific evidence: no deduction
- Lint clean: no deduction
- AC quality 4/5: no deduction
- Reviewer evidence present and detailed (PASS .96): no deduction
- 6 test failures all outside task scope (mcp-knowledge): no deduction

### Confidence: 1.00

### Action: archive
