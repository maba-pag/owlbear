# Add search/usages Guidance to Reviewer and Builder Skill Workflows

> **Owning task:** #103 — Add search/usages guidance to reviewer and builder skill workflows
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #95 (docs/research/vs-code-new-tools-evaluation.md) identified that `search/usages` (`vscode_listCodeUsages`) is available to 9/11 agents via the `search` tool set but no skill workflow references it by name. This task validates the approach for adding explicit guidance to the code-review and tdd-workflow skills so agents know to use semantic code navigation for impact analysis.

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | VS Code Copilot Cheat Sheet [S1] | .95 | `#search/usages` — "Combination of Find All References, Find Implementation, and Go to Definition"; part of `#search` tool set |
| S2 | VS Code Agent Tools docs [S2] | .90 | Tool set JSON example includes `search/usages` alongside `search/changes` and `search/codebase`; confirms `search` set membership |
| S3 | OwlBear code-review SKILL.md [S3] | 1.0 | Current reviewer workflow: Step 6.5 (Implementation-aware test gap analysis) reads changed code but uses `read_file` only — no semantic tracing of callers |
| S4 | OwlBear tdd-workflow SKILL.md [S4] | 1.0 | Current builder workflow: Step 2 ("Plan the change") asks "What could go wrong?" but provides no tool guidance for discovering callers |
| S5 | OwlBear vs-code-new-tools-evaluation.md [S5] | .90 | Prior research: `search/usages` value for reviewer (trace callers) and builder (dependency graph), .75 confidence, language support includes Python |
| S6 | OwlBear reviewer.agent.md / builder.agent.md [S6] | 1.0 | Both agents list `search` in tool set — no `.agent.md` changes needed |

## 3. Analysis

### 3.1 Tool Capabilities

`vscode_listCodeUsages` accepts:
- `symbol` — exact name of the function/class/variable to trace
- `filePath` or `uri` — file where the symbol appears
- `lineContent` — line of code containing the symbol (for disambiguation)

Returns references, definitions, and implementations across the workspace. Supported for: Python, JSON, Markdown, `.agent.md`, `.instructions.md`, prompt files, skill files [S1]. This covers OwlBear's full stack.

### 3.2 Reviewer Integration (code-review SKILL.md)

| Approach | Placement | Rationale |
|----------|-----------|-----------|
| Add to Step 2 (after listing changed files) | Extend existing scope-gathering step | Natural next action: list changes, then trace callers of changed functions |
| Add to Step 6.5 (implementation-aware gap analysis) | Part of deep code reading | Callers inform test gap analysis — "if this function's signature changed, would callers break?" |
| Both locations | Steps 2 and 6.5 | Duplicates guidance, adds cognitive load |

**Recommendation (.80 confidence):** Extend Step 2. After the reviewer lists changed files with `get_changed_files`, add a sub-step to trace callers of any changed function signatures using `vscode_listCodeUsages`. This informs scoping for all later steps — test reading, code reading, and gap analysis. One mention with the tool name is sufficient for agent awareness.

### 3.3 Builder Integration (tdd-workflow SKILL.md)

| Approach | Placement | Rationale |
|----------|-----------|-----------|
| Add to Step 2 ("Plan the change") | Extend planning guidance | Understanding callers before changing interfaces prevents regressions |
| Add to Step 1 ("Read and claim the task") | Part of initial context gathering | Too early — builder hasn't identified what needs changing yet |
| Add to Step 7 ("Verify") | Post-implementation check | Too late — breaking changes already made |

**Recommendation (.80 confidence):** Extend Step 2. The plan step already asks "What could go wrong?" — callers of functions about to change are the primary regression risk. Adding a concrete tool reference here gives the builder a specific action instead of guesswork.

### 3.4 Tool Name Reference

The runtime name visible to agents is `vscode_listCodeUsages` (what appears in tool calls). The `#search/usages` name is the user-facing `#`-mention shorthand [S1]. Skills should reference `vscode_listCodeUsages` since agents invoke tools by runtime name, matching the precedent set by `get_changed_files` in the code-review skill [S3].

### 3.5 Scope and Limitations

- The tool requires knowing the symbol name and a file+line where it appears. Agents must first identify changed symbols (from `get_changed_files` or `read_file`), then trace each.
- Language support is limited to the listed types [S1]. Python coverage is confirmed — this is the only production language in OwlBear.
- The tool does not find dynamic calls (e.g., `getattr(obj, name)()`). Guidance should note this as a gap.

## 4. Recommendation (.80 confidence)

Proceed with the task as specified. Minimal, targeted additions to two skill files:

1. **code-review SKILL.md:** In Step 2 (Check source control changes), add a sub-step: after listing changed files, for any changed function signatures, use `vscode_listCodeUsages` to trace callers and assess downstream impact before proceeding to tests.

2. **tdd-workflow SKILL.md:** In Step 2 (Plan the change), add bullet: before modifying function signatures or interfaces, use `vscode_listCodeUsages` to find all callers and verify the change won't break downstream consumers.

Risk: Low — both agents already have the `search` tool set. No `.agent.md` changes needed. Changes are additive text in skill workflow docs.

KISS check: No new abstractions, no new tools, no config changes. Workflow documentation only.

## 5. Follow-up Tasks

No additional tasks needed. Task #103 is the implementation task. The AC is concrete and directly actionable by a writer/builder agent.
