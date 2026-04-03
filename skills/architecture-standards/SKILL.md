---
name: architecture-standards
description: "OwlBear architectural standards: module layering, interface design, error handling, dependency injection, toolset wrapping, workspace confinement. Use when reviewing, building, or planning changes to src/ code."
user-invocable: false
---

# Architecture Standards

This document lists only conventions that are **not obvious best practices**. If it's standard Python, PydanticAI, or general software engineering practice, it does not belong here unless OwlBear deviates from or adds specificity to the norm. When in doubt: if a senior Python developer would do it by default, don't list it.

## Module layering

The dependency direction is strictly top-down. Lower layers never import from higher layers.

```
bootstrap.py / daemon.py   (assembly — imports everything, owns wiring)
    ↓
agents/                    (agent definitions + registry)
    ↓
tools/                     (toolsets — may depend on core/ and memory/)
    ↓
core/                      (hooks, errors, retry, delegation — no deps on tools/ or agents/)
    ↓
memory/                    (knowledge, sessions, WIP — no deps on tools/, agents/, or core/)
    ↓
config.py                  (settings — leaf node, no deps on any owlbear module)
```

- `core/` **never** imports from `tools/`, `agents/`, or `memory/`.
- `memory/` **never** imports from `tools/`, `agents/`, or `core/`.
- `tools/` may import from `core/` and `memory/` but **never** from `agents/`.
- Cross-layer communication uses protocols (`tools/protocols.py`) or dependency injection, never direct imports of concrete classes.
- `bootstrap.py` is the only module allowed to import from all layers (it is the assembly root).

Violations → architect blocks the task until the dependency is inverted or a protocol is introduced.

## Interface design

- Cross-module boundaries use `typing.Protocol` or `abc.ABC` — not concrete class references.
- The existing `WorkspaceAware` protocol in `tools/protocols.py` is the pattern to follow.
- Toolsets expose functionality through `FunctionToolset` methods. Internal helpers are private (`_prefixed`).
- Hook handlers implement the `HookHandler` callable signature from `core/hooks.py`.
- **Hooks are observational, not blocking.** The `HookRegistry` swallows exceptions from hook callbacks by design. POST_TOOL_USE and other hooks cannot block execution or propagate errors. Blocking operations (content scanning, quality gates, safety checks) must be **direct function calls** in tool wrappers, following the `URLSafetyGuard.check_url()` pattern.

## Error handling

- `core/errors.py` defines the error taxonomy: `ErrorCategory` (StrEnum) + `classify_error()` + `ToolError` (frozen dataclass).
- New error types extend this taxonomy — don't create parallel hierarchies in other modules.
- Tool code catches specific exceptions, never bare `except Exception`. Bare `except` is allowed **only** in hook handlers (where failures must not propagate).
- `error_to_user_message()` sanitizes all user-facing error strings — never expose raw tracebacks, tokens, or internal paths to channels.

## Configuration

- All settings live in `config.py` as `pydantic-settings` fields. Never read `os.environ` directly in application code.
- New features that need configuration: add a field to the settings model with a sensible default. The field becomes the single source of truth.
- Feature flags use `bool` fields with `default=False` (opt-in).

## Dependency injection

- PydanticAI's `deps` parameter is the injection mechanism for agent tools. Toolsets receive their dependencies at construction time (via `bootstrap.py`), not by importing singletons.
- No module-level mutable state. If state must be shared, it flows through the bootstrap wiring.

## Toolset wrapping

New toolsets follow the layered wrapping pattern established in `bootstrap.py`:

```
ApprovalGateToolset(HookedToolset(RawToolset))
```

- Innermost: the raw toolset implementation
- Middle: `HookedToolset` — emits PRE/POST hooks, invokes guards, retries transient errors
- Outermost (optional): `ApprovalGateToolset` — gates destructive operations behind user approval

Never bypass this wrapping. If a toolset needs custom behavior, add it inside the raw toolset or as a hook — not by circumventing the wrapper chain.

## Workspace confinement

All file and command operations are confined to the workspace root:

- `FileToolset` validates paths with `is_relative_to(workspace_root)`
- `TerminalToolset.run_command()` rejects null bytes and path escapes
- New toolsets that touch the filesystem **must** enforce the same confinement

## Domain taxonomy

Each task targets exactly one domain. Multi-domain work → split into separate tasks.

| Domain       | Module path scope                                                    |
| ------------ | -------------------------------------------------------------------- |
| config       | `config.py`                                                          |
| memory       | `memory/`                                                            |
| core         | `core/`, `safety/`                                                   |
| tools        | `tools/`, `projects/`, `planning/`                                   |
| channels     | `channels/`                                                          |
| bootstrap    | `bootstrap/`, `daemon.py`, `heartbeat.py`                            |
| providers    | `providers/`, `auth/`                                                |
| cli          | `bearclaw/`                                                          |
| agent-config | `.github/agents,skills,instructions,prompts/`, `src/owlbear/agents/` |
| test-infra   | shared conftest, fixtures, factories (not individual test files)     |
| docs         | `docs/`, `README.md`, `SECURITY.md`                                  |

**Edge case:** Adding a `config.py` field as part of a core feature is NOT a domain violation — domain = primary concern.
