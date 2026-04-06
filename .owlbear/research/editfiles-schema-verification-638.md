# editFiles PreToolUse Schema Verification — #638

> **Owning task:** #638 — Add editFiles to deny-code-writes.ps1 write-tool gate after schema verification
> **Date:** 2026-04-06 **Status:** Complete

## 1. Context and Question

During architecture review of #591, `edit/editFiles` was removed from doc-writer's
tools list because the PreToolUse hook cannot extract paths from an unverified
`tool_input` schema. VS Code docs show `{ "tool_name": "editFiles", "tool_input":
{ "files": ["src/main.ts"] } }` but no empirical confirmation exists in the codebase.

**Questions:**
1. What is the actual `editFiles` tool_input schema for PreToolUse hooks?
2. Is the documented schema reliable enough to build path extraction?
3. What is the correct implementation approach for deny-code-writes.ps1?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | VS Code Hooks docs — PreToolUse input | code.visualstudio.com/docs/copilot/customization/hooks §PreToolUse | 1.0 |
| 2 | VS Code Hooks docs — PostToolUse input | Same page §PostToolUse | 0.9 |
| 3 | VS Code Hooks FAQ — tool names | Same page §FAQ | 0.9 |
| 4 | VS Code Cheat Sheet — built-in tools | code.visualstudio.com/docs/copilot/reference §Chat tools | 0.8 |
| 5 | deny-code-writes-ac-validation-637.md | `.owlbear/research/deny-code-writes-ac-validation-637.md` | 1.0 |
| 6 | deny-src-writes.ps1 (path extraction pattern) | `.owlbear/hooks/deny-src-writes.ps1` | 1.0 |
| 7 | lint-changed.ps1 (tool_input handling) | `.owlbear/hooks/lint-changed.ps1` | 0.8 |
| 8 | Agent tools list survey (11 agents) | `share/agents/*.agent.md` | 0.7 |
| 9 | VS Code Hooks docs — updatedInput note | Same page §PreToolUse output | 0.8 |

## 3. Analysis

### 3.1 Documented Schema (Sources 1–3)

VS Code hooks docs (canonical, updated 2026-04-01) show in **both** PreToolUse
and PostToolUse input examples:

```json
{ "tool_name": "editFiles", "tool_input": { "files": ["src/main.ts"] } }
```

Key observations:
- `tool_name` is `editFiles` (camelCase) — unlike other write tools (`create_file`,
  `replace_string_in_file`) which use snake_case
- `tool_input.files` is an **array of strings** (file paths)
- Example path is workspace-relative with forward slashes

The FAQ (source 3) confirms: "VS Code uses tool names like `create_file` and
`replace_string_in_file`" — `editFiles` follows its own naming convention.

### 3.2 Schema Confidence Assessment

| Evidence | Confidence | Note |
|----------|-----------|------|
| Official docs show exact schema | .85 | Canonical source, current as of 2026-04-01 |
| Schema used in 2 doc sections (Pre+PostToolUse) | +.05 | Consistent across examples |
| API is "Preview" — may change | -.05 | Documented volatility risk |
| No empirical verification in codebase | -.05 | Lack of confirmation, not contradiction |
| updatedInput note says "check agent logs" | +.02 | Implies logged schema is real format |
| **Net confidence** | **.82** | |

### 3.3 Unknown Factors

| Factor | Risk | Mitigation |
|--------|------|-----------|
| `files[]` may contain absolute paths | Low | Normalize: strip drive prefix, use relative |
| `files[]` may contain objects not strings | Low | Defensive extraction: check string vs object |
| `files[]` may contain URIs (file://) | Low | Strip URI scheme prefix before path check |
| Schema may change in future VS Code | Medium | Preview API caveat — covered by test suite |

### 3.4 Implementation Approach — Trade-off Matrix

| Approach | Complexity | Robustness | KISS | Maintenance |
|----------|-----------|-----------|------|-------------|
| A: Strict docs-only (`files[]: string[]`) | Low | .75 — breaks if objects | .90 | Low |
| B: Defensive (handle string + object) | Medium | .90 — covers both | .75 | Medium |
| C: Empirical-first (verify then build) | High | .95 — built on evidence | .60 | Low |
| D: Logging hook + defensive build | Medium | .90 — verify during build | .80 | Low |

### 3.5 tool_name Naming Inconsistency

The write-tools gate array in deny-code-writes.ps1 must use the exact `tool_name`
from hook stdin. Current gated tools use snake_case (`create_file`,
`replace_string_in_file`). `editFiles` uses camelCase. The array must contain the
exact string `'editFiles'`.

### 3.6 Dependency Status

#591 is at `todo` — deny-code-writes.ps1 does not exist yet. #638 cannot be
implemented until #591 is complete. The doc-writer agent currently has
`edit/editFiles` in its tools list (not yet removed per #591 AC4).

## 4. Recommendation (confidence: .70)

**Recommended: Schema-verified build** — Empirical verification is a hard
prerequisite for implementation, per original AC1 intent and challenger feedback.

Sequence:
1. Wait for #591 to complete (deny-code-writes.ps1 must exist)
2. **Empirical verification (AC1):** Add temporary logging hook to capture actual
   `editFiles` PreToolUse stdin JSON — trigger via doc-writer, inspect payload
3. Confirm `tool_input.files` property name, element format (string vs object),
   and path style (relative vs absolute)
4. Build extraction code against **confirmed** schema — not docs-only speculation
5. Add `'editFiles'` to write-tools array, add path extraction, re-add
   `edit/editFiles` to doc-writer tools list

**Why empirical-first:** Defensive extraction covers element *format* (string vs
object) but NOT property *name* (`files` vs `edits` vs `paths`). If the property
name is wrong, extraction silently returns empty and the guard is bypassed — a
security-silent failure mode. The docs are a Preview API single-source; the task
exists specifically because the schema was unverified.

**Logging hook template** (for AC1 verification):
```powershell
$input_text = [Console]::In.ReadToEnd()
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$input_text | Out-File ".owlbear/scratch/hook-stdin-$ts.json" -Encoding utf8
Write-Output '{}'
```

Challenge: reconsider — confidence in original: .65

## Challenge Results
- Challenger: reconsider (confidence: .65)
- Key challenges: C1 confidence inflation (double-counted docs sections), C2
  empirical verification was the task's purpose, C3 defensive extraction
  mitigates wrong risk (property name not element format), C4 Preview API
  structural reliability gap, C5 dependency sequencing opportunity
- Researcher response: accepted C1–C3 (lowered to .70, reinstated empirical
  verification as prerequisite, acknowledged silent-bypass risk); partially
  accepted C4; noted C5 as natural sequencing advantage

## 5. Follow-up Tasks

| # | Task | Status | Depends |
|---|------|--------|---------|
| 1 | Implement editFiles in deny-code-writes.ps1 (empirical-first) | ideation | #591 |
