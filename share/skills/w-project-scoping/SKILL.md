---
name: w-project-scoping
description: "Workflow (DEPRECATED): Project scoping — use ideator agent instead"
user-invocable: true
argument-hint: "[project name or idea]"
---

> **Deprecated.** Superseded by the Ideator agent (Phase 4). Retained for reference until ideator ships.

# Project Scoping

Turn a user's vague idea into a structured, actionable project definition through iterative clarification, research, and refinement. Produces a `ProjectDefinition` ready for task decomposition.

## Step 0 — Setup

Read `r-pipeline-protocol` skill if not already loaded.

This is a user-invoked workflow — there may not be a kanban task. If a task exists, claim it via `start_work`. If invoked ad-hoc, proceed without claiming.

## Step 1 — Receive Idea

Accept the user's initial description. Restate it to confirm understanding. Identify the core problem or opportunity.

## Step 2 — Clarify

Ask targeted clarifying questions to remove ambiguity using `vscode_askQuestions`:

- Scope boundaries, target users, constraints, non-goals.
- Present options when multiple valid interpretations exist.
- Continue until no open questions remain or the user says "that's enough."

## Step 3 — Research

- Use `fetch-webpage` to find libraries, frameworks, or similar projects.
- Search existing codebase for relevant prior art and patterns.
- Summarize findings and surface risks or blockers.

## Step 4 — Propose Definition

Draft a `ProjectDefinition` covering all fields in the schema below. Present to the user. Highlight empty fields or open questions.

### ProjectDefinition Schema

| Field | Type | Required? | Description |
|-------|------|-----------|-------------|
| name | str | Required | Short project identifier (kebab-case) |
| description | str | Required | One-paragraph summary |
| goals | list[str] | Required | 3–5 concrete outcomes |
| requirements | list[Requirement] | Required | Functional and non-functional requirements |
| acceptance_criteria | list[str] | Required | Testable AC lines (pass/fail verifiable) |
| tech-stack | list[str] | Optional | Languages, frameworks, libraries |
| risks | list[str] | Optional | Known risks with mitigations |
| open_questions | list[str] | Optional | Unresolved items needing input |

**Requirement fields:** `description` (str, required), `kind` ("functional" or "non-functional", required), `priority` (str, optional, defaults to "important").

## Step 5 — Iterate

Ask the user to review the proposed definition. Incorporate feedback, resolve open questions, refine until the user approves. Use `vscode_askQuestions` for each feedback round.

## Step 6 — Finalize

Lock the approved definition. Write it as a markdown document via `create_file`. The definition is now ready for decomposition by the planner.

If a kanban task exists, advance via `end_work`.

## Option Presentation Pattern

When multiple valid approaches exist, present as numbered options:

```
Option 1 (.75) — SQLite local database
  Pros: zero setup, fast, portable
  Cons: no concurrent writes

Option 2 (.60) — PostgreSQL via Docker
  Pros: concurrent access, scales
  Cons: requires Docker, more complex

Option 3 (.40) — Flat JSON files
  Pros: simplest possible
  Cons: no querying, slow at scale

Recommendation: Option 1 — matches KISS and single-user scope.
Pick a number, or describe a different approach.
```

Key patterns: confidence score per option, pros/cons, explicit recommendation, invite alternatives.

## Verification Checklist

- [ ] User's idea restated and confirmed
- [ ] All ambiguities clarified (or user said "enough")
- [ ] Research performed (web search + codebase scan)
- [ ] All required ProjectDefinition fields populated
- [ ] AC lines are testable (pass/fail verifiable)
- [ ] Risks and open questions surfaced
- [ ] User approved the final definition
- [ ] Definition written to workspace

## Known Pitfalls

- **Building on assumptions:** Always clarify before proposing. A wrong assumption compounds through every downstream task.
- **Over-scoping:** Keep the definition focused. YAGNI applies — don't add features the user didn't ask for.
- **Non-testable AC:** "System is fast" is not testable. "Response time under 200ms for N=1000" is testable.
- **Skipping research:** Even when you think you know the answer, look it up. Prior art saves implementation time.
