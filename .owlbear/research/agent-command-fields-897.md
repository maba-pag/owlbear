# Update agent.md command: fields to uv run python

> **Owning task:** #897 — Update agent.md command: fields to uv run python
> **Date:** 2026-04-17 **Status:** Complete

## 1. Context and Question

Part of macOS compatibility initiative (#890). All 7 Python hook equivalents exist (delivered by #894, #895, #896 — all archived). The remaining step is updating the 16 agent `.agent.md` files to reference `.py` hooks instead of `.ps1`.

AC also requires zero `powershell` / `.ps1` references anywhere in `share/agents/` — this surfaces prose content in quality-runner and fix-attempt that needs updating beyond the YAML `command:` fields.

## 2. Sources Studied

| Source | Relevance | What was taken |
|--------|-----------|----------------|
| Brief `.owlbear/briefs/draft-macos-compat/brief.md` | 1.0 | Target format: `uv run python .owlbear/hooks/{name}.py` |
| `.owlbear/hooks/*.py` (7 files) | 1.0 | Confirmed all Python hooks exist |
| `share/agents/*.agent.md` (22 files, grep audit) | 1.0 | Full mapping of 19 command: lines + prose references |
| Parent #890 + deps #894/#895/#896 (archived) | 0.9 | All prerequisites completed |

## 3. Analysis

### 3.1 Command field replacement (19 lines, 16 files)

Mechanical find-replace. Pattern:

| From | To |
|------|----|
| `powershell -NoProfile -NonInteractive -File .owlbear/hooks/{name}.ps1` | `uv run python .owlbear/hooks/{name}.py` |

### 3.2 Agent-to-hook verified mapping

| Agent | Hook type | Hook script |
|-------|-----------|-------------|
| architect | PreToolUse | deny-code-writes |
| auditor | PreToolUse | deny-writes |
| builder | SessionStart | session-context |
| builder | PostToolUse | lint-changed |
| challenger | PreToolUse | deny-writes |
| code-reader | PreToolUse | deny-writes |
| doc-writer | SessionStart | session-context |
| doc-writer | PreToolUse | deny-code-writes |
| fix-attempt | PostToolUse | lint-changed |
| ideation-architect | PreToolUse | allow-stances-only |
| ideation-critic | PreToolUse | deny-writes |
| ideation-data | PreToolUse | allow-stances-only |
| ideation-enduser | PreToolUse | allow-stances-only |
| ideation-security | PreToolUse | allow-stances-only |
| quality-runner | PreToolUse | deny-writes |
| researcher | PreToolUse | deny-code-writes |
| reviewer | PreToolUse | deny-writes |
| test-writer | SessionStart | session-context |
| test-writer | PreToolUse | deny-src-writes |

6 agents have no hooks: curator, ideation-pragmatist, ideator, orchestrator, planner, scribe.

### 3.3 Prose PowerShell references (beyond command: fields)

| File | Lines | Content | Action |
|------|-------|---------|--------|
| quality-runner | 36, 47 | "Never pipe through PowerShell cmdlets" | Remove or rewrite as platform-neutral |
| quality-runner | 55, 63, 87, 98 | ` ```powershell` code block labels | Change to ` ```sh` |
| quality-runner | 63–65 | WMI hang mitigation (`Get-Process` / `Stop-Process`) | Replace with cross-platform: `pkill -9 -f pytest` |
| fix-attempt | 78, 84 | ` ```powershell` code block labels | Change to ` ```sh` |

**quality-runner pitfall #1** ("Never pipe through PowerShell cmdlets") references Windows-specific cmdlets (`Out-File`, `Tee-Object`, etc.). The underlying principle (don't pipe `uv run` output — terminal captures it automatically) is still valid. Reword to be platform-neutral.

**quality-runner pitfall #5** (WMI hang mitigation) is Windows-only. Replace with `pkill -9 -f pytest` (already used in the codebase — see terminal history).

## 4. Recommendation

Proceed with implementation. Confidence: **0.95**.

No design decisions required — the brief (D2, D5, D10) already specifies the exact target format. All prerequisites delivered.

Challenge: SKIP — trivial config change, no recommendation trade-offs to challenge.

## 5. Follow-up Tasks

None needed — #897 itself is the implementation task. Advance to backlog.
