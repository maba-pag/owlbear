---
id: 1925
title: 'P1-09: Finalize browser acquisition lifecycle boundary'
status: verify
priority: medium
created: 2026-07-13T15:47:42.616043+02:00
updated: 2026-07-14T05:03:21.162928+02:00
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
