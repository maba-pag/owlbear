# Planner: askQuestions Tool + Explicit Mode Prefix Convention

> **Owning task:** #1005 — Planner: add askQuestions tool + explicit mode prefix convention
> **Date:** 2026-04-19 **Status:** Complete

## 1. Context and Question

Child task of #998. Scope: update `share/agents/planner.agent.md` to add askQuestions support and replace NL-based mode detection with explicit prefix convention.

**Question:** What exact changes are needed in planner.agent.md, and does the parent research (#998) still apply?

## 2. Sources Studied

| # | Source | Relevance | Notes |
|---|--------|-----------|-------|
| 1 | `.owlbear/research/998-planner-askquestions-approval.md` | 1.0 | Parent research — full design |
| 2 | `share/agents/planner.agent.md` (current) | 1.0 | Target file — verified unchanged since research |
| 3 | `share/agents/ideator.agent.md` (codebase) | 0.85 | Only agent with askQuestions — pattern reference |
| 4 | `share/agents/scribe.agent.md` (codebase) | 0.80 | Mode parameter in argument-hint — closest pattern |
| 5 | #998 architecture review (task body) | 0.95 | AC refinements, fallback spec, argument-hint gap |

## 3. Analysis

### Validation Pass

Parent research is current. Codebase state verified:
- planner.agent.md: only change since research is model bump (Opus 4.6 → 4.7). No structural changes.
- ideator remains the only agent with askQuestions (1 of 23).
- No other agent has adopted explicit mode prefix convention yet (scribe uses mode parameter, which is similar but structurally different).

### Implementation Spec

Five changes to `share/agents/planner.agent.md`:

| # | Section | Current | Target |
|---|---------|---------|--------|
| 1 | `tools:` list | No askQuestions | Add `vscode/askQuestions` |
| 2 | `argument-hint:` | `"Plan: {feature_or-plan_description}"` | Dual-prefix hint showing both modes |
| 3 | `<critical_rules>` execution mode | NL-based: "parent task ID" / "no parent task" | Explicit prefix: "Plan and create:" / "Plan:" |
| 4 | `<critical_rules>` fallback | None | Dual-mode fallback per architecture review |
| 5 | `<examples>` | No mode prefix examples | Add good/bad examples for both prefixes |

### Change Details

**1. Tools list** — Insert `vscode/askQuestions` after `vscode/memory`:
```
tools: [vscode/memory, vscode/askQuestions, read/problems, ...]
```

**2. Argument-hint** — Per architecture review C2:
```yaml
argument-hint: "Plan: {description} (approval mode) | Plan and create: #{id} — {description} (dispatch mode)"
```

**3. Execution mode section** — Replace:
```markdown
# CURRENT (NL-based, fragile)
- Orchestrator-dispatched (parent task ID): execute task creation commands
- User-invoked (no parent task): output commands for user review

# TARGET (explicit prefix)
- "Plan and create: #{id} — ..." → dispatch mode: claim task, auto-create subtasks, report Channel B
- "Plan: ..." (default) → user mode: present plan → askQuestions("Approve?") → create on approve
```

**4. Fallback** — Per architecture review, dual-mode:
```markdown
- Pipeline markers detected + no "Plan and create:" prefix → abort with error explaining missing prefix
- Freeform user input without pipeline markers → default to approval mode (askQuestions)
```

**5. Examples** — Two new examples:
- Good: user invokes `Plan: add health check endpoint` → planner presents plan → askQuestions → creates on approve
- Good: orchestrator dispatches `Plan and create: #42 — decompose health check feature` → planner auto-creates
- Bad: pipeline dispatch without prefix → planner fires askQuestions mid-pipeline (the #973 failure)

### Persona and output_format alignment

The persona already says: "When invoked directly by the user, you present the plan for review before executing. When dispatched by the orchestrator, you execute the plan immediately." This aligns with the prefix convention. The persona text can remain as-is — it describes intent; critical_rules implements mechanism.

The Channel B / output_format section already differentiates: "When user-invoked without a parent task, Channel B does not apply." This needs minor update to reference "Plan:" prefix instead of "no parent task."

## 4. Recommendation

**Proceed with parent research design** — confidence: 0.85

No new findings. The parent research and architecture review (0.88 post-challenge) provide a complete, validated design. All five changes are well-specified.

Challenge: SKIPPED — validation pass of parent-researched design. Parent went through challenger twice (research: reconsider→revised, arch review: reconsider→refined). No new recommendation to challenge.

Risk: askQuestions in user-invocable agent (non-ideator) is untested. Mitigated by: simpler interaction pattern than ideator (single ask-once vs multi-turn), and approval mode is the safe default.

## 5. Follow-up Tasks

No new follow-up tasks. This task IS the implementation — it advances to backlog for builder execution. Sibling tasks #1006, #1007, #1008 already exist as follow-ups from parent #998.
