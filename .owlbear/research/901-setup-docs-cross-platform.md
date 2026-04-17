# Update setup and sharing docs for macOS

> **Owning task:** #901 — Update setup and sharing docs for macOS
> **Also covers:** #908 — Update setup docs for cross-platform hooks
> **Date:** 2026-04-17 **Status:** Complete

## 1. Context and Question

Tasks #901 and #908 (children of #890 macOS-compat) update `setup-guide.md` and `sharing-guide.md` to be cross-platform. All code changes are done: hooks are `.py`, `init.py` is generic. The docs still contain stale `.ps1` references, `powershell` code fences, and Windows-only examples.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `setup/setup-guide.md` (200 lines) | Codebase | 1.0 |
| 2 | `setup/sharing-guide.md` (119 lines) | Codebase | 1.0 |
| 3 | `seed/.owlbear/hooks/` (7 .py files) | Codebase | 0.9 |
| 4 | `.owlbear/research/900-init-py-hook-references.md` | Codebase | 0.9 |
| 5 | `setup/init.py` (generic rglob seeder) | Codebase | 0.8 |

## 3. Analysis

### 3.1 Issue Inventory

| File | Line | Issue | AC |
|------|------|-------|-----|
| setup-guide.md | 17-19 | Windows-only limitation presented as universal blocker | #901-AC2 |
| setup-guide.md | 25 | `` ```powershell `` code fence | #908-AC2 |
| setup-guide.md | 29 | Comment says "same drive" — Windows-only concern | #901-AC2 |
| setup-guide.md | 34 | `python ..\owlbear\setup\init.py` — backslash path | #901-AC1 |
| setup-guide.md | 51 | `.owlbear/hooks/deny-writes.ps1` — stale name | #908-AC1 |
| setup-guide.md | 52 | `.owlbear/hooks/lint-changed.ps1` — stale name | #908-AC1 |
| sharing-guide.md | 17 | "same drive" phrased as universal requirement | #901-AC2 |
| sharing-guide.md | 20-22 | Windows limitation note (already scoped — good) | OK |
| sharing-guide.md | 30 | `` ```powershell `` code fence | #908-AC2 |
| sharing-guide.md | 31 | Comment says "same drive" — Windows-only | #901-AC2 |
| sharing-guide.md | 32-38 | `C:\Dev\...` Windows-only paths | #901-AC3 |
| sharing-guide.md | 39 | `python ..\owlbear\setup\init.py` — backslash | #901-AC3 |
| sharing-guide.md | 116 | Troubleshooting references `setup.py` (should be `init.py`) | Bonus |
| sharing-guide.md | 117 | Troubleshooting references `setup.py` (should be `init.py`) | Bonus |
| sharing-guide.md | 119 | Troubleshooting references `setup.py` (should be `init.py`) | Bonus |
| setup-guide.md | 182 | Troubleshooting references `setup.py` (should be `init.py`) | Bonus |

### 3.2 Missing Content

| What's missing | AC |
|----------------|-----|
| macOS prerequisites (none needed — Python/uv/Git all work) | #901-AC1 |
| macOS section in sharing-guide for hooks + MCP startup | #901-AC3 |
| All 7 hooks listed in setup-guide "What Setup Creates" table | #908-AC1 |

### 3.3 Required Changes — setup-guide.md

| Change | Details |
|--------|---------|
| Scope Windows limitation | Move same-drive note into a Windows-only callout; add macOS note (no restrictions) |
| Replace code fence | `powershell` → `shell` |
| Cross-platform Quick Start | Show forward-slash path: `python ../owlbear/setup/init.py`; add Windows note for backslash |
| Update hook table | Replace 2 `.ps1` rows with 7 `.py` hooks from seed/ |
| Fix troubleshooting | `setup.py` → `init.py` |

### 3.4 Required Changes — sharing-guide.md

| Change | Details |
|--------|---------|
| Scope "same drive" text | Clarify as Windows-only in body text |
| Replace code fence | `powershell` → `shell` |
| Cross-platform examples | Show macOS/Linux first (`~/Dev/...`, forward slashes), Windows in note |
| Add macOS hooks section | Note: hooks are `.py` (cross-platform), executed by VS Code's agent runtime — no shell dependency |
| Add macOS MCP note | MCP servers use `uv run` — works identically on macOS |
| Fix troubleshooting | `setup.py` → `init.py` throughout; scope ValueError to Windows |

## 4. Recommendation (confidence: 0.92)

**Straightforward documentation update.** Both files need the same pattern: replace Windows-only examples with cross-platform defaults, add platform-specific notes in callouts. No design choices or competing options — this is a factual correction.

Challenge: skipped — no competing options; factual audit of stale documentation.

### Implementation approach

- Quick Start examples: show `python ../owlbear/setup/init.py` (forward slashes) as the primary command. Add a `> **Windows:** use backslashes` note.
- Hook table: list all 7 `.py` hooks with descriptions.
- sharing-guide macOS section: brief (hooks are .py and cross-platform; MCP servers use uv which is cross-platform).
- Merge #901 and #908 into one editing pass — same files, complementary ACs.

## 5. Follow-up Tasks

Combined editing task recommended — see task creation below.
