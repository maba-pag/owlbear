---
id: 1926
title: 'P1-10: Prove assembled browser acquisition at a committed revision'
status: build
priority: high
created: 2026-07-13T15:47:53.790613+02:00
updated: 2026-07-14T13:09:00.557576+02:00
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
claimed_at: 2026-07-14T13:09:00.557576+02:00
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
