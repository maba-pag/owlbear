# Decisions — macOS Compatibility

<!-- Written after user choices -->

## D1: Investment Tier

**Tier:** Shared

**Rationale:** This touches core infrastructure (hooks, agents, setup) used by every consumer project. Needs cross-platform hook system with bash equivalents, platform-aware agent config, updated setup/init.py, and test parity — but not a full abstraction layer or CI matrix.

## D2: No PowerShell on macOS
Hooks must be native POSIX shell (bash). No PowerShell 7 dependency on macOS.

## D3: Browser features deferred
Playwright launcher and Chrome extension discovery stay Windows-only for now.

## D4: kanban-md binary is legacy
Python `owlbear_kanban` engine is the active path. Old .exe references need cleanup, not a macOS build.

## D5: Approach — Python hooks (Option A)
Rewrite all 7 PowerShell hooks as Python scripts. Agent commands become `uv run python .owlbear/hooks/{name}.py`. Single implementation per hook, no platform drift. Amends D2.

## D2 (amended): Hook language is Python
~~Hooks must be native POSIX shell (bash).~~ → Hooks use Python (platform-agnostic via `uv run python`). No PowerShell dependency on macOS. No bash dependency on Windows.

## D6: Immediate .ps1 retirement
Delete .ps1 files after Python equivalence tests pass. No deprecation period. Consumer projects re-run init.py to get new hooks. Only 2 consumer projects exist, both under full control — no backwards compatibility concern.

## D10: Clean break migration
No platform-conditional commands, no dual maintenance. Ship .py, retire .ps1, consumers re-run init.py. Fixes are easy since both consumers are controlled.

## D7: Bug-for-bug fidelity in port
Regex weaknesses in deny-src-writes and deny-scratch-only-writes are ported as-is. Hardening tracked as a separate follow-up task.

## D8: Fail-open behavior preserved
Current fail-open design (JSON parse error → allow) is kept during port. Follow-up task to add visible error output (stderr/logging) so guard-down state is observable.

## D9: Hooks stay per-project in .owlbear/hooks/
Agent `command:` fields use literal workspace-relative paths. No variable substitution available. Moving to share/ would break consumer path resolution. Seeding via init.py is the correct pattern.
