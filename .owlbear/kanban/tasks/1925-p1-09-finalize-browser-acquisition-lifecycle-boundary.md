---
id: 1925
title: 'P1-09: Finalize browser acquisition lifecycle boundary'
status: collect
priority: medium
created: 2026-07-13T15:47:42.616043+02:00
updated: 2026-07-14T08:09:56.216805+02:00
tags:
  - phase-1
  - scope:browser
  - feature
  - type:build
  - rigor:thorough
parent: 1924
depends_on: []
ac:
  - 'AC-1: Given delayed rendered content, document redirects with a subresource,
    a protected page requiring visible user interaction, and invalid terminal-page
    fixtures, the public browser acquisition API returns structured Markdown provenance
    for success, document-only redirect history, reusable-session success after manual
    completion, and distinguishable non-success outcomes without credential input
    or secret-bearing diagnostics.'
  - 'AC-2: Given a launched persistent browser session, a browser acquisition consumer
    obtains the shared acquisition capability through the public launcher boundary
    while raw Playwright context, cookie access, and storage-state access remain absent
    from that public boundary; inspection of the exported API and a real Playwright
    lifecycle check verify the result.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Planning source: `openspec/changes/complete-browser-content-acquisition/`

Objective: reconcile the final browser-core acquisition state with the approved persistent-session and public-contract boundaries, and commit the task-owned browser implementation that remained outside the archived leaf commits.

Contract authorities: OpenSpec `browser-content-acquisition` spec and design; `serve/browser/src/owlbear_browser/contract.py`, `fetcher.py`, and `playwright_launcher.py`; final Verify Notes for #1917, #1918, #1919, and #1920.

In scope: the current uncommitted browser contract, acquisition, launcher, and focused browser proof delta; bounded authentication-page retry; ambiguous terminal-page rejection; document-only redirect provenance; a launcher-owned acquisition composition surface that does not expose raw Playwright context/session-secret APIs.

Out of scope: MCP tool authorization and serialization, DDGS/configuration work, agent guidance, crawling, and knowledge ingestion.

Change envelope: expected production owners are `serve/browser/src/owlbear_browser/contract.py`, `fetcher.py`, and `playwright_launcher.py`; expected durable proof owner is the existing browser package suite. Preserve unrelated worktree changes.

Proof guidance: run the focused browser package checks and real Playwright fixtures; use a local page host below the public acquisition boundary. Record the task commit SHA after committing only owned files. Existing maintained acquisition tests should be extended only for a concrete uncovered regression.

Product Promise contribution: closes the reusable Python API and persistent-session portion of parent #1924; it does not claim agent-callable MCP completion by itself.

[[2026-07-14T05:03:21+02:00]]
## Builder Notes
- Change envelope: browser acquisition contract, fetcher, launcher, and existing focused browser proof only.
- Files changed: `serve/browser/src/owlbear_browser/contract.py`, `serve/browser/src/owlbear_browser/fetcher.py`, `serve/browser/src/owlbear_browser/playwright_launcher.py`, `serve/browser/tests/test_acquisition.py`.
- Module map: no deviations. Launcher now owns the public `acquire` capability; raw Playwright context/page accessors were removed from the public boundary. Fetcher retains pending authentication state internally and exposes cleanup for launcher shutdown.
- Proof selected: focused real Playwright browser package suite plus focused Ruff and diff checks; no new durable test file added. Existing authentication lifecycle proof was updated because the prior direct-context path contradicted AC-2.
- Commands run: `uv run pytest serve/browser/tests` -> 20 passed; `uv run ruff check serve/browser/src/owlbear_browser/contract.py serve/browser/src/owlbear_browser/fetcher.py serve/browser/src/owlbear_browser/playwright_launcher.py serve/browser/tests/test_acquisition.py` -> all checks passed; `git diff --check -- serve/browser` -> clean.
- Builder challenger: pass, no blockers.
- Follow-up risk: verifier should confirm the public launcher export surface and persistent-session lifecycle against the OpenSpec contract.

[[2026-07-14T08:09:56+02:00]]
## Verify Notes
- Verdict: PASS after a local verifier patch.
- Evidence reviewed: AC-1 and AC-2; builder notes; OpenSpec `browser-content-acquisition` specification and design; `contract.py`, `fetcher.py`, `playwright_launcher.py`; existing browser proofs; and final Verify Notes for #1917, #1918, #1919, and #1920.
- Named authorities checked: the typed contract rejects caller credentials, MFA, scripts, headers, storage state, and actions; diagnostics redact sensitive fields and now redact sensitive URL query parameters. The launcher exposes acquisition and capability operations only, while its Playwright context and fetcher remain private. The fetcher retains an authentication-required page privately, reuses it on retry, and launcher shutdown closes it before the persistent context.
- Change Module Map: implementation commit `f2d3835c9bf37fde9df3898c6f82ba1533ec5136` changed precisely the mapped contract, fetcher, launcher, and existing acquisition proof. The verifier patch stays in the contract and existing contract-proof owner. No deviations found.
- Normal-path boundary exercised: real Chromium and a local deterministic HTTP host exercised delayed content, document redirect provenance, selector-scoped Markdown, inert discovered links, terminal-page rejection, and a public `PlaywrightLauncher` authentication-required then protected-page retry. The fixture replaces only served page content below the public acquisition boundary.
- Replacements used below that boundary: local HTTP fixture only; no replacement of the public acquisition, launcher, persistent-session, or Playwright lifecycle under test.
- Checks run:
  - `uv run pytest serve/browser/tests` passed: 20 passed in 13.08s.
  - `uv run ruff check serve/browser/src/owlbear_browser/contract.py serve/browser/src/owlbear_browser/fetcher.py serve/browser/src/owlbear_browser/playwright_launcher.py serve/browser/tests/test_acquisition.py serve/browser/tests/test_contract.py` passed.
  - `git diff --check -- serve/browser` passed.
- Finding and patch: verifier-challenger identified that a diagnostic URL with secret-bearing query parameters could leak values. Updated `contract.py` to structurally redact `api_key`, `access_token`, `client_secret`, cookie, password, secret, and token query values, and extended `test_contract.py` to prove `api_key` and `access_token` redaction while preserving a public query value.
- Verifier-challenger: final decision pass. It found the repair sufficient, evidence proportionate, and scope within the approved envelope.
- Final route: PASS to collect.

