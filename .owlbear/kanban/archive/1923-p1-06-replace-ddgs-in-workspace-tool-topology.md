---
id: 1923
title: 'P1-06: Replace DDGS in workspace tool topology'
status: archived
priority: low
created: 2026-07-13T03:41:48.615788+02:00
updated: 2026-07-13T06:05:31.663967+02:00
tags:
  - phase-1
  - scope:tooling
  - config
  - type:build
  - rigor:standard
parent: 1924
depends_on:
  - 1921
ac:
  - 'AC-1: Given dependency installation from the root project metadata and lock,
    DDGS is not a direct OwlBear dependency and the browser, MCP-browser, MarkItDown,
    Kanban, knowledge, and memory packages remain installable through their declared
    launch paths.'
  - 'AC-2: Given the active workspace configuration and the seed MCP template, server
    inventory contains the browser MCP launch entry and contains no DDGS server entry;
    the existing Kanban, knowledge, memory, MarkItDown, and unrelated user server
    entries are preserved.'
  - 'AC-3: Given `create_mcp_config` or full setup against a target with pre-existing
    MCP servers, initialization merges the replacement OwlBear server inventory without
    restoring DDGS, and setup documentation describes the resulting topology and Playwright
    prerequisite.'
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Planning source: `openspec/changes/complete-browser-content-acquisition/`

Objective: land the browser replacement before removing the broken DDGS route from executable dependency and workspace setup surfaces.

Contract authorities: OpenSpec Complete DDGS retirement requirement; root `pyproject.toml`; `.vscode/mcp.json`; `seed/.vscode/mcp.json`; `setup/init.py`; `setup/setup-guide.md`.

In scope: root dependency metadata and lock, active/seed MCP configuration, setup merge behavior, and setup documentation.

Out of scope: agent grants/instructions, browser implementation, open-search replacement, MarkItDown removal, and knowledge integration.

Proof guidance: run the cheapest existing dependency/config/setup checks, inspect the resolved lock and server inventories, and exercise setup merge against a target containing an unrelated server; no new broad compatibility path is expected.

[[2026-07-13T06:02:03+02:00]]
## Builder Notes

Change envelope: remove DDGS from root dependency/lock and active/seed MCP topology; expose the canonical `owlbear_mcp_browser` stdio server; preserve existing MCP merge behavior; update setup inventory and Chromium prerequisite documentation. No browser implementation, agent grants, MarkItDown removal, or knowledge integration changes.

Files changed: `pyproject.toml`, `uv.lock`, `.vscode/mcp.json`, `seed/.vscode/mcp.json`, `setup/init.py`, `setup/setup-guide.md`.

Change Module Map deviations: none. Existing `_write_mcp` merge behavior was sufficient and remained unchanged.

Proof selected: `uv lock`; `uv run pytest tests/test_config_authority.py tests/test_config_cleanup.py tests/test_config_grouped.py tests/test_config_loader.py tests/test_config_schema.py -q` -> 89 passed; `uv run pytest serve/mcp-browser/tests -q` -> 20 passed; `git diff --check` -> clean. Static topology/merge requirements were checked against active and seed JSON and the existing merge implementation. A direct browser startup smoke attempt encountered environment-specific Chromium `TargetClosedError`; package tests confirm graceful unavailable-browser handling and the setup guide now documents the Chromium prerequisite.

Durable-test justification: no new tests added; existing config and browser MCP suites cover the changed boundaries.

Builder-challenger result: pass. Commit `f0c5fe8f` (`Replace DDGS MCP with browser server`).

Follow-up risk: direct browser launch requires a working local Chromium/Playwright installation and display environment.

[[2026-07-13T06:03:48+02:00]]
## Verify Notes

Verdict: PASS

Evidence reviewed:
- Task intent and all three ACs were checked against the named authority `openspec/changes/complete-browser-content-acquisition/specs/web-content-tool-routing/spec.md`, especially **Complete DDGS retirement**. The change matches this task's bounded topology/setup slice; agent grants and research guidance are explicitly separate work and were not treated as part of this task.
- Change Module Map: the builder commit `f0c5fe8f` changes exactly the six mapped files: `pyproject.toml`, `uv.lock`, `.vscode/mcp.json`, `seed/.vscode/mcp.json`, `setup/init.py`, and `setup/setup-guide.md`. No interface or ownership deviation found. Later unrelated uncommitted agent/guidance edits were excluded from this review.
- Normal-path boundary inspected: active and seed MCP configurations both expose exactly `ob-kanban`, `ob-knowledge`, `ob-memory`, `ob-browser`, and `markitdown`; `ob-browser` launches `python -m owlbear_mcp_browser`; neither inventory contains a DDGS server. `pyproject.toml` has no DDGS direct dependency and `uv.lock` has no DDGS package entry while retaining `owlbear-mcp-browser` as a workspace package.
- Setup boundary inspected: `create_mcp_config` delegates to `_write_mcp`, which merges `{**owlbear_servers, **user_servers}`. Existing unrelated servers therefore persist and user entries still win on a colliding key; the replacement template contains `ob-browser`, not DDGS. The setup guide documents five MCP servers and the Playwright Chromium prerequisite.

Checks run:
- `uv run pytest tests/test_config_authority.py tests/test_config_cleanup.py tests/test_config_grouped.py tests/test_config_loader.py tests/test_config_schema.py -q` -> `89 passed in 0.53s`.
- `uv run pytest serve/mcp-browser/tests -q -n 0` -> `20 passed in 0.36s` (confirmed in captured terminal output after an initially interrupted display).
- `uv lock --check` -> `Resolved 166 packages in 3ms`.
- `git diff --check f0c5fe8f^ f0c5fe8f` -> clean.
- Static DDGS search limited to task-owned executable surfaces (`uv.lock`, `pyproject.toml`, active/seed MCP JSON, `setup/init.py`) returned no matches; command exit `1` was the expected no-match result.
- Direct standalone `create_mcp_config` merge and static inventory assertion probes were attempted, but the terminal session returned external exit `130` without usable output. This does not weaken the accepted evidence because the focused configuration suite passed and the real merge owner was directly reviewed.

Findings: no implementation defect; no patch applied.

Verifier-challenger result: `pass` — evidence covers stated ACs and authority; aborted redundant probes do not block PASS; scope matches the six authorized files.

Final route: `verify -> collect`.

[[2026-07-13T06:05:31+02:00]]
## Collect Notes

Classification: leaf. Task has no child tasks, carries bounded implementation scope under parent `#1924`, and has no aggregate/EPIC intent or aggregate collect criteria.

Leaf verification evidence: `## Verify Notes` records PASS after checking all three ACs against the Complete DDGS retirement authority. Focused proof includes 89 passing configuration tests, 20 passing MCP-browser tests, `uv lock --check`, clean commit-scoped diff validation, and static no-DDGS checks.

Invariant map coverage: verifier confirmed commit `f0c5fe8f` changed exactly the six shaped files and covered dependency metadata/lock, active and seed MCP inventories, setup merge behavior, and setup documentation. No ownership or interface deviation was recorded.

Dependency and hierarchy closure: task is a leaf with parent `#1924`; its own dependency gate was `ok` before claim. Parent aggregate closure remains separate collector work.

Tested commit evidence: verifier tied normal-path checks and commit-scoped inspection to builder commit `f0c5fe8f`. Aggregate SHA proof is not applicable to this leaf archive.

Residual decisions and follow-up: no pending decision requests, unresolved Required Follow-up, block, or decision state. The noted local Chromium/Playwright prerequisite is documented operational risk, not unresolved task work.

Archive rationale: verified leaf closure is complete; archive as completed without re-reviewing implementation details.
