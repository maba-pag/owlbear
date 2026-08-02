---
id: 1921
title: 'P1-05: Expose browser acquisition through MCP'
status: archived
priority: high
created: 2026-07-13T03:41:32.691784+02:00
updated: 2026-07-13T05:56:38.411671+02:00
tags:
  - phase-1
  - scope:mcp-browser
  - feature
  - type:build
  - rigor:thorough
parent: 1924
depends_on:
  - 1920
ac:
  - 'AC-1: Given a running browser MCP server and a delayed-render local page, invoking
    its acquisition operation through a real MCP client crosses the shared browser
    API and returns the success status, requested URL, canonical URL, redirect chain,
    title, non-empty Markdown, discovered links, content hash, UTC fetch time, and
    diagnostics without adapter-owned extraction or authentication rules.'
  - 'AC-2: Given a structured core non-success outcome, the MCP operation serializes
    that outcome without replacing it with generic transport failure; given browser
    startup failure, acquisition reports browser unavailability and never returns
    the input URL or cached text as apparent success.'
  - 'AC-3: Given an explicitly requested private-address HTTP(S) page, the acquisition
    operation delegates under the user-authorized URL contract, while `navigate`,
    `click`, `type`, `select`, `read_text`, and `snapshot` remain separate operations
    and acquisition accepts no arbitrary action or JavaScript fields.'
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Planning source: `openspec/changes/complete-browser-content-acquisition/`

Objective: make the shared acquisition behavior agent-callable through one thin FastMCP surface without broadening or silently changing interactive browser actions.

Contract authorities: OpenSpec Shared single-page acquisition capability and Acquisition remains non-interactive automation requirements; `serve/mcp-browser/src/owlbear_mcp_browser/server.py`; `.owlbear/instructions/mcp-server.instructions.md`; package dependency boundary `owlbear_mcp_browser` to `owlbear_browser` in `tests/test_package_boundary.py`.

In scope: `serve/mcp-browser` tool contract, lifespan composition, structured serialization, startup-unavailable behavior, public exports, package description, and package README.

Out of scope: browser acquisition algorithms, MCP-to-MCP calls, DDGS/configuration migration, agent grants, changes to interactive tool authorization policy, and knowledge ingestion.

Downstream-impact scan: preserve the established interactive tool names and annotations; inspect current server tests and add durable MCP contract coverage only for operation visibility, serialization, and startup false-success risk.

Proof guidance: invoke the registered operation through a real MCP client against real Playwright and a local fixture; injected dependencies may replace the fixture server but not FastMCP registration, lifespan assembly, or the core acquisition call.

[[2026-07-13T05:53:59+02:00]]
## Builder Notes

Change envelope: expose one thin `acquire` FastMCP operation over the existing shared browser acquisition contract; preserve interactive operations and avoid browser-core changes.

Files changed: `serve/mcp-browser/src/owlbear_mcp_browser/server.py`, `serve/mcp-browser/README.md`. Change Module Map deviation: none. Added public `acquire` export, safe `AcquisitionRequest` construction, existing `DomainAllowlist` enforcement, structured success/failure serialization, and explicit startup-unavailable error. Acquisition intentionally does not call `navigate`'s SSRF preflight so explicitly user-authorized private HTTP(S) URLs remain delegated per AC-3.

Proof selected: `uv run ruff check serve/mcp-browser/src/owlbear_mcp_browser/server.py`; `uv run pytest serve/mcp-browser/tests tests/test_package_boundary.py -q` -> 54 passed; `git diff --check -- serve/mcp-browser/src/owlbear_mcp_browser/server.py serve/mcp-browser/README.md`. Durable-test delta: zero; existing focused tests plus direct source/challenger review cover the changed adapter boundary, and no new durable regression test was required by the shaped scope.

Builder-challenger result: pass. Commit: `47c5ba15` (`feat(mcp-browser): expose acquisition tool`). Follow-up risk: the shaped real MCP-client/local delayed-render proof belongs to verify and was not reproduced in this builder environment.

[[2026-07-13T05:55:55+02:00]]
## Verify Notes

Verdict: PASS

Evidence reviewed:
- Task AC-1 through AC-3; OpenSpec `Shared single-page acquisition capability` and `Acquisition remains non-interactive automation` requirements; `serve/mcp-browser/src/owlbear_mcp_browser/server.py`; MCP-server conventions; package import boundary.
- Change Module Map: builder changed only the mapped MCP-browser server owner and its README. `git show --stat --oneline 47c5ba15` confirms two files; `git diff --check 47c5ba15^ 47c5ba15` was clean. No interface, browser-core, or interactive-policy deviation.
- Normal-path boundary exercised: real stdio `ClientSession` started `python -m owlbear_mcp_browser`, discovered `acquire` plus existing `navigate`, `click`, `type`, `select`, `read_text`, and `snapshot`, then invoked `acquire` against a real Playwright session and local delayed-render loopback fixture. It returned `success`, requested and canonical URL, title, non-empty Markdown containing delayed content, discovered links, content hash, UTC timestamp, and complete diagnostics. This covered FastMCP registration, lifespan assembly, and the shared fetcher; only the local fixture server was substituted.
- Failure boundaries exercised through the same real client: an authentication fixture returned structured `authentication_required` with diagnostics; a server started with no available Playwright browsers returned the `Browser unavailable` tool error and no apparent success payload.
- AC-3 checked: the successful normal-path call used an explicitly requested private-address HTTP URL under the allowlist and reached the core acquisition path. Source inspection confirms acquisition accepts only its documented acquisition fields and does not apply `navigate` SSRF preflight; interactive tools remain separately registered.

Checks run:
- `uv run ruff check serve/mcp-browser/src/owlbear_mcp_browser/server.py` -- passed.
- `uv run pytest serve/mcp-browser/tests tests/test_package_boundary.py -q` -- 54 passed.
- Real MCP client delayed-render success probe -- passed.
- Real MCP client structured non-success and startup-unavailable probes -- passed.

Patches applied: none.

Verifier-challenger result: pass. It found the AC evidence sufficient, no scope drift, and no unresolved defect.

Final route: verify hands off to collect.

[[2026-07-13T05:56:38+02:00]]
## Collect Notes

Classification: leaf. Task has no child tasks and is a scoped implementation deliverable under parent #1924, not an aggregate contract.

Leaf verification evidence: `## Verify Notes` records PASS with verifier-challenger pass and no patches or Required Follow-up. AC-1 through AC-3 are covered by a real stdio MCP `ClientSession` against real Playwright and a local delayed-render fixture, structured non-success and startup-unavailable probes, 54 focused tests, and Ruff.

Invariant map coverage: verifier confirmed changes stayed within the mapped MCP-browser server owner and README, preserved all established interactive operations, and found no browser-core, interface, or authorization-policy deviation.

Child coverage: none; `list_tasks(parent=1921)` returned no tasks. Dependency gate: dependency #1920 was satisfied (`dep_status: ok`) before claim. Completion evidence is commit `47c5ba15`; Verify Notes tie the real MCP-client normal-path and failure-path proof to review of that commit and confirm its two-file scope and clean diff.

Residual decisions: no pending requests, unresolved decision state, block, or Required Follow-up.

Archive rationale: verified leaf implementation is complete and all closure conditions are satisfied.
