# PostToolUse additionalContext for Builder Lint Feedback

> **Owning task:** #547 — Add model-facing lint feedback via additionalContext to builder PostToolUse hook
> **Date:** 2026-04-02 **Status:** Complete

## 1. Context and Question

Task #210 implements a PostToolUse lint guard for the builder agent returning
`systemMessage` with ruff output (user-facing only). Empirical verification (#532)
confirmed `hookSpecificOutput.additionalContext` reaches the subagent model context,
wrapped in `<PostToolUse-context>` XML tags. This task researches how to add
`additionalContext` to lint-changed.ps1 so the builder model receives lint feedback
and can self-correct after file edits.

**Questions:** (1) Correct JSON output combining systemMessage + additionalContext?
(2) Should model output differ from user output? (3) Context window management?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| VS Code Hooks docs (4/2/2026) | code.visualstudio.com/docs/copilot/customization/hooks | .95 — PostToolUse output schema |
| OwlBear #532 empirical verification | docs/research/posttooluse-subagent-output-routing.md | 1.0 — Confirmed additionalContext model-facing |
| OwlBear #210 feasibility | docs/research/posttooluse-lint-guard-feasibility.md | 1.0 — Lint guard design |
| claude-plugins-official #317 | github.com/anthropics/claude-plugins-official/issues/317 | .90 — systemMessage alone doesn't reach model |
| microsoft/vscode #296189 | github.com/microsoft/vscode/issues/296189 | .85 — Correct PostToolUse output format |

## 3. Analysis

### 3.1 Output Format — Both Fields Coexist

VS Code docs and external bug reports confirm the combined pattern:

```json
{
  "systemMessage": "<ruff output>",
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "<ruff output>"
  }
}
```

- `systemMessage`: shown in chat panel (user monitoring) — Sources: VS Code docs, #210 design
- `additionalContext`: injected into model conversation as `<PostToolUse-context>` XML — Sources: #532 empirical, VS Code docs
- Combined response: both fire independently — Sources: claude-plugins-official #317 fix pattern

### 3.2 Content Strategy

| Strategy | Pros | Cons | KISS |
|----------|------|------|------|
| Same ruff output for both | Single source of truth, minimal code | No audience tailoring | High |
| Structured JSON for model | Optimized model parsing | Over-engineered, dual format logic | Low |
| additionalContext only | Simplest diff | Loses user visibility (violates AC) | N/A |

Ruff's default text output is structured (`file:line:col: code message`) and
models parse it well. Custom formatting is over-engineering for a first iteration.

### 3.3 Context Window Impact (Napkin Estimate)

| Metric | Estimate | Source |
|--------|----------|--------|
| Avg ruff output per file | ~200–500 chars | Typical single-file lint |
| Edits per builder session | 10–30 | Observed builder behavior |
| Total injected context | 2–15 KB | Conservative upper bound |
| Builder context budget | ~100–200 KB | Typical LLM context window |
| Context fraction used | 1–8% | Within acceptable range |

Each `additionalContext` injection is per-tool-call, not cumulative. The model's
conversation history grows, but lint context for clean edits is not injected (empty
JSON on clean path). Worst case (30 edits, all failing lint) adds ~15 KB — manageable.

### 3.4 Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| N=1 empirical basis (create_file only) | Moderate | Verify for apply_patch in #546; docs are unambiguous |
| Builder reacts to lint mid-implementation | Low | Non-blocking design; builder can defer fixes |
| Context inflation on many errors | Low | Add truncation in future if observed |
| #210 script shape unknown | Moderate | Task blocked on #210; spec change is minimal |

### 3.5 AC2 Verification Protocol

AC2 ("Builder model receives lint feedback in its conversation context") requires
manual observation via Chat Debug View during a live builder session. This cannot
be automated — the builder or reviewer must verify during implementation by
inspecting the Chat Debug View Tool Call Debug Log for `<PostToolUse-context>` tags
containing ruff output after the builder edits a file with lint errors.

## 4. Recommendation (.75 confidence)

**T1 (Autonomous): Add `additionalContext` with same ruff output as `systemMessage`.**

Implementation: when ruff finds errors, lint-changed.ps1 returns both fields.
Clean path unchanged (empty JSON). Never exit code 2.

Confidence lowered from .85 to .75 due to N=1 empirical basis and unverified
model behavioral response to injected lint context. The mechanism is well-documented
(VS Code docs + 2 independent bug reports) but production behavior across all
tool_names is unverified.

T1 rationale: no architecture change, no agent/skill modification, no security
change, no pipeline change. The builder already has lint awareness (critical_rules).
This adds automatic delivery of the same information through an existing hook.

Challenge: reconsider (.55 confidence in original). Accepted C1 partially (lowered
to .75), C2 (dependency note added), C5 (verification protocol added). Rebutted C3
(KISS is correct — ruff text is structured), C4 (behavior change is refinement, not
new capability; non-blocking by design).

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Add hookSpecificOutput.additionalContext to lint-changed.ps1" --priority important --status ideation --tags "scope:agents,hooks,type:build" --depends-on 210 --body "## Context\nSee docs/research/posttooluse-additionalcontext-lint-feedback.md (task #547).\nEmpirical verification (#532) confirmed additionalContext reaches the builder model in subagent context. This task adds additionalContext output to lint-changed.ps1 alongside the existing systemMessage.\n\n## Acceptance Criteria\n- [ ] When ruff finds errors, lint-changed.ps1 returns both systemMessage and hookSpecificOutput.additionalContext containing the ruff output\n- [ ] hookSpecificOutput includes hookEventName: PostToolUse\n- [ ] Clean path (no errors) still returns empty JSON\n- [ ] Never exits with code 2 (non-blocking)\n- [ ] Builder model receives lint feedback in conversation context (verify via Chat Debug View)\n- [ ] Existing systemMessage behavior preserved\n\n## Implementation Notes\nOutput JSON structure:\n{ systemMessage: ruff_output, hookSpecificOutput: { hookEventName: PostToolUse, additionalContext: ruff_output } }\nSame ruff output for both fields (KISS). No truncation initially (YAGNI).\n\n## Dependencies\nDepends on #210 (lint-changed.ps1 must exist first)."
```
