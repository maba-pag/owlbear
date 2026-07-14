---
id: 1926
title: 'P1-10: Prove assembled browser acquisition at a committed revision'
status: verify
priority: high
created: 2026-07-13T15:47:53.790613+02:00
updated: 2026-07-14T15:21:52.585154+02:00
tags:
  - phase-1
  - scope:mcp-browser
  - feature
  - type:build
  - rigor:thorough
parent: 1924
depends_on:
  - 1925
ac:
  - 'AC-1: Given an explicitly requested private-address HTTP(S) page, the registered
    MCP acquisition operation crosses FastMCP lifespan and the public browser acquisition
    API to return the structured success or expected non-success result; the existing
    `navigate`, `click`, `type`, `select`, `read_text`, and `snapshot` operations
    retain their current allowlist and SSRF policy.'
  - 'AC-2: Given delayed-render and persistent-session protected local pages, a real
    stdio MCP client invoking the registered acquisition operation at the task commit
    SHA receives non-empty Markdown and required provenance after session reuse, while
    authentication and invalid terminal states remain structured non-successes; Builder
    or Verify Notes record the tested SHA and successful command or artifact.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Planning source: `openspec/changes/complete-browser-content-acquisition/`

Objective: correct the thin MCP composition and authorization path, then tie the aggregate normal-path evidence to a commit that contains the finalized browser-core and MCP implementation.

Contract authorities: OpenSpec Shared single-page acquisition capability, User-authorized web navigation, and Acquisition remains non-interactive automation requirements; `serve/mcp-browser/src/owlbear_mcp_browser/server.py`; completed browser-core task #1925; collector rejection on parent #1924.

In scope: MCP lifespan composition through the public browser acquisition boundary; acquisition-specific authorization of explicitly supplied HTTP(S) private/intranet URLs and redirects; preservation of the existing allowlist/SSRF policy for interactive operations; structured success/non-success serialization; commit-bound assembled proof.

Out of scope: browser extraction/classification algorithms owned by #1925, DDGS/configuration migration already completed, interactive-tool policy changes, crawling, and knowledge ingestion.

Change envelope: expected production owner is `serve/mcp-browser/src/owlbear_mcp_browser/server.py`, with package-local MCP proof only when existing checks do not protect the authorization/composition regression. Preserve unrelated worktree changes.

Proof guidance: after committing task-owned files, record the tested commit SHA and invoke the registered acquisition operation through a real stdio MCP client, FastMCP lifespan, public browser acquisition API, and real Playwright against delayed-render and persistent-session local fixtures. The local page host may replace the remote site; FastMCP registration, lifespan, browser acquisition, and Playwright may not be mocked or injected. Run focused MCP-browser and browser checks plus the relevant package-boundary check.

Product Promise contribution: owns the agent-callable assembled boundary and the SHA-linked aggregate proof required before parent #1924 can collect.

[[2026-07-14T12:52:05+02:00]]
## Builder Notes

Change envelope: `serve/mcp-browser/src/owlbear_mcp_browser/server.py`, acquisition authorization only; preserve interactive allowlist/SSRF paths and unrelated worktree changes.

Files changed: `serve/mcp-browser/src/owlbear_mcp_browser/server.py` (one-line owner fix); task record updated by this transition. No durable tests added because existing coverage exercises the changed handler and the task requires assembled proof rather than a redundant unit test.

Change Module Map deviations: none. `acquire()` now calls `await _check_ssrf(url)` instead of the interactive `app_ctx.allowlist.check(url)`; `navigate()` retains both SSRF and allowlist checks.

Proof selected: `uv run pytest serve/mcp-browser/tests/` -> 20 passed; `uv run pytest tests/test_package_boundary.py` -> 34 passed; `uv run ruff check serve/mcp-browser/src/owlbear_mcp_browser/server.py` -> passed. `uv run pytest serve/browser/tests/` first reported one delayed-content status mismatch, then rerun passed 20/20; this is unrelated to the changed module. Real stdio MCP client against `python -m owlbear_mcp_browser` listed the registered `acquire` tool and crossed FastMCP lifespan, but returned structured `Browser unavailable` because the Playwright launcher failed internally; installing Chromium did not resolve it. Tested revision before the uncommitted source edit: `b017b31ce974d485fe68e6796fff83b08965066b`; no valid tested commit SHA exists for the new source because the required assembled proof did not complete.

Builder-challenger result: fail. It found the implementation in scope and focused checks passing, but correctly required the AC-2 real stdio/FastMCP/public acquisition/Playwright proof and recorded SHA before DONE.

Follow-up risk: resolve the local Playwright launcher startup failure, then rerun the real stdio acquisition against delayed-render and persistent-session fixtures at a committed revision before moving task to verify.

## AR: Resolve Playwright launcher startup for assembled browser proof
- **Outcome:** Resolved: MCP lifespan used removed PlaywrightLauncher.context access after #1925. Restored the public page() capability and migrated acquisition to launcher.acquire(); live lifespan now retains the browser and focused checks pass.

[[2026-07-14T15:21:52+02:00]]
## Builder Completion

Root cause: browser-core task #1925 removed direct `PlaywrightLauncher.context` exposure in favor of the public `acquire()` boundary, but MCP lifespan still dereferenced `.context`. Chromium therefore launched, MCP raised `AttributeError`, the broad startup fallback converted it to `Browser unavailable`, and cleanup immediately closed the visible window.

Fix: restored the launcher's narrow public `page()` capability for existing interactive tools; MCP lifespan now composes `launcher.page()` and registered acquisition delegates to `launcher.acquire()`. Acquisition no longer applies the interactive allowlist or SSRF preflight, matching the OpenSpec authorization for explicitly supplied private/loopback HTTP(S) URLs; `navigate` and all interactive operations retain their existing policy. Added a focused MCP regression proving loopback acquisition delegation.

Tested commit: `ddab6cdefc8a23c92170654a4cf21cb6a09b9309`.

Assembled proof: a real stdio MCP client launched `uv run python -m owlbear_mcp_browser`, listed the registered `acquire` tool, crossed FastMCP lifespan and public `PlaywrightLauncher.acquire()`, and used real headed Playwright against local fixtures. Results: delayed-render `success` with non-empty Markdown/provenance; session establishment `success`; protected cookie-backed session reuse `success`; login `authentication_required`; empty terminal `content_not_ready` with structured diagnostics.

Focused checks at the tested revision: `uv run pytest serve/mcp-browser/tests/ -q --tb=short` -> 21 passed; `uv run pytest serve/browser/tests/ -q --tb=short` -> 20 passed; `uv run pytest tests/test_package_boundary.py -q --tb=short` -> 34 passed; focused Ruff -> passed.

Builder challenger: PASS. It independently confirmed both ACs, the acquisition-versus-interactive authorization distinction, the assembled boundary, and 75 passing tests.
