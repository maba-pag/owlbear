# Clean Up .github/ v1 Prompts and Residual Files

> **Owning task:** #29 — Clean up .github/ v1 prompts and residual files
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #29 asks to clean up `.github/` after agents (#8), skills (#9), and instructions (#10) were ported to root directories. The key questions: which files should be deleted, which kept, and what stale references remain?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | VS Code prompt file docs | https://code.visualstudio.com/docs/copilot/customization/prompt-files | `.github/prompts/` is the canonical workspace location for prompt files |
| S2 | Task #8 audit (archived) | kanban task #8 body | `.github/agents/` confirmed empty, agents at root |
| S3 | Task #117 (done) | kanban task #117 body | `.github/skills/` deleted, dual-path config removed |
| S4 | Task #10 audit (archived) | kanban task #10 body | `.github/instructions/` deleted |
| S5 | `.vscode/settings.json` | local file L33 | Still has stale `.github/agents: true` entry |
| S6 | `scripts/setup.py` L35,42 | local file | Still generates stale `.github/agents` and `.github/instructions` mappings |

## 3. Analysis

### Current `.github/` contents

| Path | Status | Action |
|------|--------|--------|
| `.github/copilot-instructions.md` | Active v2 instructions | **Keep** — standard GitHub/VS Code location [S1] |
| `.github/dependabot.yml` | Active GitHub config | **Keep** — platform file |
| `.github/prompts/` (6 files) | Active prompt files | **Keep** — canonical VS Code location [S1] |
| `.github/agents/` | Empty directory | **Delete** — agents ported to `agents/` [S2] |
| `.github/skills/` | Already deleted | N/A [S3] |
| `.github/instructions/` | Already deleted | N/A [S4] |

### Prompt file review

| File | v2 Relevant? | Issues Found |
|------|-------------|--------------|
| `orchestrate.prompt.md` | Yes — dispatches orchestrator agent | None |
| `agent-audit.prompt.md` | Yes — comprehensive audit tool | L16: stale `.github/agents/*.agent.md` ref (should be `agents/`) |
| `design-context.prompt.md` | Yes — design onboarding | L21,107: `.github/copilot-instructions.md` refs are correct (file is there) |
| `frontend-audit.prompt.md` | Yes — read-only audit | L14-15: `../skills/` resolves to deleted `.github/skills/` — **broken** |
| `frontend-normalize.prompt.md` | Yes — normalization tool | L15: `../skills/` resolves to deleted `.github/skills/` — **broken** |
| `frontend-polish.prompt.md` | Yes — polish tool | L16-21: `../skills/` resolves to deleted `.github/skills/` — **broken** |

### Broken relative paths (.90 confidence)

From `.github/prompts/`, the path `../skills/` resolves to `.github/skills/` (deleted by #117), not root `skills/`. The correct relative path would be `../../skills/`. Verified: `Test-Path ".github/skills/frontend-design/SKILL.md"` returns `False`; `Test-Path "skills/frontend-design/SKILL.md"` returns `True`. [S1, S3]

### Stale settings references

| Location | Stale Reference | Fix |
|----------|----------------|-----|
| `.vscode/settings.json` L33 | `.github/agents: true` | Remove entry [S5] |
| `scripts/setup.py` L35 | `.github/agents` mapping | Remove line [S6] |
| `scripts/setup.py` L42 | `.github/instructions` mapping | Remove line [S6] |

## 4. Recommendation (.90 confidence)

1. **Keep all 6 prompts** — they are useful v2 tools in the canonical VS Code location
2. **Fix broken paths** — update `../skills/` → `../../skills/` in 3 frontend prompts
3. **Fix stale agent ref** — update `.github/agents/` → `agents/` in agent-audit prompt
4. **Delete empty `.github/agents/`** directory
5. **Clean stale settings** — remove `.github/agents` from VS Code settings and setup.py; remove `.github/instructions` from setup.py

Risks: path changes in prompts need manual verification (no automated tests for prompt path resolution). KISS-aligned — minimal changes, no restructuring.

## 5. Follow-up Tasks

Three tasks at `ideation` — each scoped to a single logical change:

1. **Fix broken skill paths in frontend prompts** — update `../skills/` → `../../skills/` in 3 prompt files
2. **Delete empty .github/agents/ and clean stale settings** — remove directory, update settings.json + setup.py
3. **Update stale agent path in agent-audit prompt** — `.github/agents/` → `agents/` at L16
