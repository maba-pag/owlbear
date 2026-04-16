# macOS Compatibility — Brief

## Problem

OwlBear is Windows-only. The hook system (7 PowerShell scripts, 19 agent `command:` fields), seeded consumer config, setup docs, and test suite assume Windows/PowerShell. Two workflows must be functional on macOS:

1. **Dev workflow** — develop on `dev` branch: run tests, lint, use MCP servers, operate the kanban pipeline, run agents.
2. **Consumer workflow** — use the `main` branch in other projects via `setup/init.py`, with agents, hooks, and MCP servers working end-to-end.

## Approach

**The hook system is the only critical blocker.** Without working hooks, agents fail on every tool use because `powershell` doesn't exist on macOS. Everything else — seed config, docs, legacy .exe refs, test skips — is cleanup work with no design decisions needed. The architectural question is how to port the hooks.

**Rewrite all hooks as Python scripts.** Single cross-platform implementation per hook. Agent commands: `uv run python .owlbear/hooks/{name}.py`. Clean break — retire .ps1 immediately. Two controlled consumers, no backwards compatibility needed.

This shifts the runtime dependency from "PowerShell must exist" to "`uv` and Python must resolve" — the same dependency boundary already used by all MCP servers. Accepted trade-off.

## Outcomes

**O1 — Cross-platform hook system:** 7 Python hook scripts replace .ps1 equivalents with identical I/O contracts (same stdin JSON → same stdout JSON, same exit codes, same fail-open behavior). All 19+ agent `.agent.md` `command:` fields updated to `uv run python`. Parameterized equivalence tests verify behavioral parity per-hook, including malformed input handling.

**O2 — Consumer setup works end-to-end on macOS:** `python ../owlbear/setup/init.py` seeds `.py` hooks (not `.ps1`), produces settings without Windows-only terminal profiles (no pwsh.exe paths), and generates working MCP config. Opening the consumer project in VS Code on macOS → agents visible, hooks execute, MCP servers respond. Setup and sharing docs cover macOS.

**O3 — Dev workflow passes on macOS:** `uv run ruff check .` and `uv run pytest` exit 0 on macOS. Legacy `.exe` references in orchestrator/tests cleaned up or properly skipped. Browser code paths fail gracefully on non-Windows (already caught by exception handling — verify, don't change).

## Scope

### In scope
- Rewrite 7 PowerShell hooks as Python (same I/O contract)
- Update all 19+ agent `.agent.md` `command:` fields
- Write equivalence tests for each hook (replaces Windows-only PowerShell test suite)
- Update `seed/.owlbear/hooks/` — replace .ps1 with .py, sync to 7 hooks (fix existing drift: seed has 6, dev has 7)
- Update `seed/.vscode/settings.json` — remove Windows-only terminal profiles
- Update `setup/init.py` — seed .py hooks
- Update `setup/setup-guide.md` and `setup/sharing-guide.md` — macOS instructions
- Clean up legacy `kanban-md.exe` references in tests and orchestrator
- Delete all .ps1 files after equivalence tests pass

### Out of scope
- Browser discovery (Playwright launcher, Chrome extension paths) — stays Windows-only, deferred
- CI matrix (macOS + Windows runners) — future work
- Docker compatibility — future work
- Regex hardening in deny-src-writes and deny-scratch-only-writes — follow-up task
- Fail-closed hook behavior — follow-up task (add error logging)

## Key Decisions

| ID | Decision |
|----|----------|
| D1 | Investment tier: Shared |
| D2 | Hook language: Python (amended from bash) |
| D3 | Browser features: deferred |
| D4 | kanban-md.exe: legacy, cleanup only |
| D5 | Approach: Option A (Python hooks) |
| D6 | Immediate .ps1 retirement |
| D7 | Bug-for-bug fidelity in port |
| D8 | Fail-open behavior preserved |
| D9 | Hooks stay per-project in .owlbear/hooks/ |
| D10 | Clean break migration, no backwards compatibility |

## Implementation Sequence

1. **Port hooks to Python** — rewrite all 7 scripts with identical stdin/stdout JSON contract. Use `sys.stdin`, `json` stdlib. Maintain fail-open error handling.
2. **Write equivalence tests** — parameterized tests per hook: feed same JSON inputs, assert same outputs. Include malformed input cases (truncated JSON, empty stdin, BOM, binary). These tests run on both platforms.
3. **Update agent files** — change all 19+ `.agent.md` `command:` fields from `powershell -NoProfile -NonInteractive -File .owlbear/hooks/{name}.ps1` to `uv run python .owlbear/hooks/{name}.py`.
4. **Update seed/** — replace `.ps1` hooks with `.py` in `seed/.owlbear/hooks/`. Add missing `deny-scratch-only-writes.py` (fix seed drift). Remove Windows terminal profiles from `seed/.vscode/settings.json`.
5. **Update setup/init.py** — seed `.py` hooks. Update any `.ps1` filename references.
6. **Update documentation** — `setup-guide.md`: add macOS prerequisites and commands. `sharing-guide.md`: add macOS section. Remove PowerShell-only examples or add cross-platform alternatives.
7. **Clean up legacy references** — `kanban-md.exe` in orchestrator CLI and test files: remove or guard with proper skip conditions.
8. **Verify browser graceful degradation** — confirm `playwright_launcher.py` and MCP browser server handle non-Windows gracefully (they catch exceptions already; verify, don't change).
9. **Delete .ps1 files** — remove all PowerShell hooks from `.owlbear/hooks/` and `seed/.owlbear/hooks/`.
10. **Full macOS validation** — `uv run ruff check .` + `uv run pytest` must exit 0 on macOS.

## Follow-up Tasks (out of scope for this brief)

- Regex hardening: deny-src-writes and deny-scratch-only-writes use `(^|/)` prefix patterns that match target dirs anywhere in path, not just root-relative.
- Fail-open observability: add stderr/logging when hooks fail to parse input, so guard-down state is visible to the developer.
- Browser macOS support: Playwright launcher and Chrome extension discovery for macOS paths.
- CI matrix: add macOS runner to GitHub Actions.
