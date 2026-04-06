# PreToolUse Path Guard for Doc-Writer Agent (Phase 5)

> **Owning task:** #591 — Add PreToolUse path guard hook to doc-writer agent (Phase 5)
> **Date:** 2026-04-06 **Status:** Complete

## 1. Context and Question

Task #591 (Phase 5) calls for adding a PreToolUse path guard hook to the doc-writer agent,
reusing `deny-src-writes.ps1` from #589. The AC states: "Reuses existing deny-src-writes.ps1
from #589 (no new script needed)."

**Question:** Can the existing script be reused, and if not, what is the correct guard design?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | deny-src-writes.ps1 implementation | `.owlbear/hooks/deny-src-writes.ps1` | 1.0 — actual script logic |
| 2 | test-writer agent (Phase 3 pattern) | `share/agents/test-writer.agent.md` | 1.0 — hook registration pattern |
| 3 | Agent-scoped hooks research | `.owlbear/research/agent-scoped-hooks.md` §3.1, §3.3 | 1.0 — original Phase 5 recommendation |
| 4 | Doc-writer agent file + boundaries | `share/agents/doc-writer.agent.md` | 1.0 — legitimate write targets |
| 5 | Task #589 body (full pipeline) | Archived — challenger revised approach from deny-list to allow-list | 1.0 — design evolution |

## 3. Analysis

### 3.1 Script Compatibility — INFEASIBLE

The `deny-src-writes.ps1` script (source 1) uses an **allow-list** approach:
```powershell
$isInTests = $normalized.StartsWith('tests/')
```
Any path NOT starting with `tests/` is denied. This was correct for test-writer (#589)
but is incompatible with doc-writer.

### 3.2 Doc-Writer Legitimate Write Targets (source 4: boundaries section)

| Target | Example Path | Starts with `tests/`? |
|--------|-------------|----------------------|
| Root READMEs | `README.md`, `README-consumer.md` | No — DENIED |
| Copilot instructions | `.github/copilot-instructions.md` | No — DENIED |
| Research docs | `.owlbear/research/*.md` | No — DENIED |
| Source attribution | `.owlbear/sources/overview.md` | No — DENIED |
| Skill/instruction docs | `share/skills/*/SKILL.md`, `share/instructions/*.md` | No — DENIED |
| Python docstrings | `serve/**/*.py`, `v1/**/*.py` | No — DENIED |

**100% of doc-writer's legitimate write targets would be blocked** by the current script.

### 3.3 Root Cause

The original research (source 3, §3.1) recommended a **deny-list** ("deny writes to `packages/`")
for both test-writer and doc-writer. During #589's challenger review, the approach was
correctly revised to an **allow-list** for test-writer (only `tests/` permitted). The #591
AC was written before this revision and still assumes deny-list reusability.

### 3.4 Design Options

| Option | Description | Security | Complexity | KISS | Reuses existing? |
|--------|-------------|----------|------------|------|-----------------|
| A: Allow-list script | New script: allow `*.md`, `.owlbear/*`, `.github/*`, `share/*` | .85 — explicit allow | High — many prefixes, regex | .50 | No |
| B: Deny-list script | New script: deny `serve/*`, `v1/*`, `tests/*`, `setup/*` | .65 — new dirs unguarded | Medium — ~4 deny prefixes | .70 | No |
| C: Parameterize script | Modify deny-src-writes.ps1 to read allow-list from env/arg | .80 — configurable | High — arg parsing, testing | .40 | Partial |
| D: Deny `*.py` only | New script: deny writes to `*.py` files (docstring edits done via instruction) | .60 — doesn't guard dirs | Low — extension check | .75 | No |
| E: No hook, instruction-only | No hook — doc-writer already has strong boundary instructions | .40 — no enforcement layer | None | .90 | N/A |

### 3.5 Feasibility of `.py` Docstring Edits

A path-based hook cannot distinguish docstring edits from logic changes. Options A-C
would either allow ALL `.py` writes (permissive) or deny ALL `.py` writes (blocking a
stated boundary). This is an inherent limitation of PreToolUse hooks (source 3, §3.5).

The doc-writer boundaries say "Never change function signatures, return types, or control
flow in `.py` files" — this is content-level enforcement, not path-level. A hook cannot
enforce it. Instruction-based enforcement is the only practical option for `.py` boundaries.

## 4. Recommendation (confidence: .73)

**Recommended: Option B (revised) — Deny-list script** (`deny-code-writes.ps1`)

Deny writes to: `serve/`, `v1/`, `tests/`, `setup/`, `.owlbear/hooks/`,
`.owlbear/scripts/`, `conftest.py`. Allow everything else. ~35 LOC. Separate script —
different logic (deny-list vs allow-list), different role, different messages.

**Write-tools array must include:** `create_file`, `replace_string_in_file`,
`multi_replace_string_in_file`, `create_directory`, `apply_patch` (known bypass from
deny-src-writes.ps1 that omits apply_patch — must not be repeated).

**Rationale:**
- Doc-writer has many legitimate write targets across multiple directory trees — allow-list
  is too complex (Option A) and fragile as new doc paths are added
- Deny-list covers the actual risk surface: source code dirs + executable hooks/scripts
- `.py` docstring enforcement stays instruction-based (§3.5: hooks can't enforce content)
- KISS over perfect security — marginal security gain of allow-list doesn't justify complexity

**AC revision required:** AC2 ("Reuses existing deny-src-writes.ps1") must be revised
to "Create deny-code-writes.ps1 with deny-list approach." AC1 path: `.owlbear/hooks/`
(not `scripts/hooks/` — renamed in #609 migration).

**Challenge: reconsider** — confidence in original: .78. Revised to .73 after accepting:
- C1 (blocking): `.owlbear/hooks/` self-modification vector — added to deny-list
- C2 (blocking): `apply_patch` bypass — added to write-tools requirement
- C3 (advisory): `conftest.py` — added to deny-list
- C4 (advisory): confidence lowered from .78 to .73
- C5 (advisory): maintenance comment header in script — noted in AC

## 5. Follow-up Tasks

| # | Title | Status | One-line AC |
|---|-------|--------|-------------|
| #637 | Revise #591 AC: deny-list script for doc-writer path guard | ideation | Deny-list script + revised AC for doc-writer hook |
