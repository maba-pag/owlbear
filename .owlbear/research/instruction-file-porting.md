# Instruction File Porting — v1 to v2

> **Owning task:** #10 — Port instruction files
> **Date:** 2026-03-28 **Status:** Complete

## 1. Context and Question

Task #10 requires copying `.github/instructions/*.instructions.md` files to
`instructions/` at repo root, removing v1-specific references (PydanticAI,
BearClaw, daemon, approval gates), and ensuring VS Code auto-applies them.

Key question: What v1-specific content exists, and what VS Code configuration
changes are needed?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| VS Code Custom Instructions docs | https://code.visualstudio.com/docs/copilot/customization/custom-instructions | .90 — confirms `chat.instructionsFilesLocations` setting and discovery |
| VS Code Customization overview | https://code.visualstudio.com/docs/copilot/customization/overview | .75 — parent repo discovery, monorepo patterns |
| Project `.vscode/settings.json` | (local file) | 1.0 — confirms `instructions/` already in `chat.instructionsFilesLocations` |
| `.github/copilot-instructions.md` | (local file) | 1.0 — confirms v2 directory table lists `instructions/` as target |

## 3. Analysis

### V1 references audit

Searched all 4 instruction files for: PydanticAI, BearClaw, daemon, approval
gates, `src/owlbear/`, v1 path patterns.

| File | Line | V1 content | Action |
|------|------|-----------|--------|
| `python.instructions.md` | 23 | `src/owlbear/` (namespace package) | Update to `packages/*/src/` monorepo layout |
| `python.instructions.md` | 24 | `tests/test_config.py` for `src/owlbear/config.py` | Update example to v2 paths |
| `python.instructions.md` | 43 | `Typer` for CLI, `BearClaw` entry point | Remove (BearClaw dropped in v2) |
| `python.instructions.md` | 44 | `PydanticAI` agents reference | Remove (PydanticAI dropped in v2) |
| `python.instructions.md` | 45 | `GitHub Copilot OAuth — see src/owlbear/config.py` | Remove (v1-specific config) |
| `agent-common.instructions.md` | — | None found | Copy as-is |
| `research-docs.instructions.md` | — | None found | Copy as-is |
| `frontend.instructions.md` | — | None found | Copy as-is |

### VS Code configuration status

| Setting | Current value | Action needed |
|---------|--------------|---------------|
| `chat.instructionsFilesLocations` | `{".github/instructions": true, "instructions": true}` | None — already configured |
| `.github/copilot-instructions.md` | Exists, v2-aligned | None |

### File placement

- **Target:** `instructions/` at repo root (per copilot-instructions.md directory table)
- **Cleanup:** Deletion of `.github/instructions/` is owned by task #13
- **README:** Update `instructions/README.md` from "transition placeholder" to authoritative

## 4. Recommendation (.90 confidence)

Straightforward file-copy + targeted edits. Only `python.instructions.md` needs
substantive changes (5 lines). The other 3 files copy unchanged. No decision
request needed — the approach is unambiguous.

**Risk:** applyTo patterns are workspace-relative globs (e.g., `**/*.py`), which
are location-independent — moving files to `instructions/` does not affect pattern
matching.

### Testing approach

Builder should verify via VS Code: **Chat: Configure Instructions** (Ctrl+Shift+P)
or right-click Chat view → Diagnostics. Confirm all 4 files appear as loaded from
`instructions/` path.

## 5. Follow-up Tasks

No additional tasks needed. Task #10 itself has complete AC covering all required
changes. The downstream cleanup (deleting `.github/instructions/`) is already
tracked by task #13.
