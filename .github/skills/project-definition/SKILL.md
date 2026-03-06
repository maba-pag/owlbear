---
name: project-definition
description: LLM-guided project scoping and definition workflow. Turns a vague idea into a structured ProjectDefinition through clarification, research, and iterative refinement with the user.
user-invocable: false
---

# Project Definition Workflow

Structured workflow for turning a user's idea into an actionable project
definition. The planner agent loads this skill to guide the idea-to-spec
pipeline — producing a `ProjectDefinition` that downstream agents can
decompose into kanban tasks.

## Workflow Template

Follow these six steps in order. Do not skip steps. Use `ask_user` liberally
to keep the user in the loop and avoid building on assumptions.

1. **Receive idea** — Accept the user's initial description. Restate it in
   your own words to confirm understanding. Identify the core problem or
   opportunity the project addresses.

2. **Clarify via ask_user** — Ask targeted clarifying questions to remove
   ambiguity. Focus on scope boundaries, target users, constraints, and
   non-goals. Present options when multiple valid interpretations exist
   (see the example interaction below). Continue until no open questions
   remain or the user explicitly says "that's enough."

3. **Research via knowledge + web_search** — Search the knowledge base
   (`query_knowledge`) for relevant prior art, patterns, and existing
   components. Use `web_search` to find libraries, frameworks, or similar
   projects. Summarize findings and surface any risks or blockers
   discovered during research.

4. **Propose definition** — Draft a `ProjectDefinition` covering all fields
   in the reference table below. Present it to the user as a structured
   summary. Highlight any fields left empty or marked as open questions.

5. **Iterate with user** — Ask the user to review the proposed definition.
   Incorporate feedback, resolve open questions, and refine until the user
   approves. Use `ask_user` for each feedback round.

6. **Finalize** — Lock the approved definition. Write it as a markdown
   document to the workspace (via `filesystem` tools). The definition is
   now ready for task decomposition by the planner's kanban workflow.

## ProjectDefinition Field Reference

Use this table as the schema when populating the project definition. All
"Required" fields must be filled before finalization. "Optional" fields
should be populated when information is available.

| Field                | Type                   | Required / Optional | Description                                                    |
| -------------------- | ---------------------- | ------------------- | -------------------------------------------------------------- |
| name                 | `str`                  | Required            | Short project identifier (kebab-case recommended)              |
| description          | `str`                  | Required            | One-paragraph summary of what the project does and why         |
| goals                | `list[str]`            | Required            | 3–5 concrete outcomes the project achieves                     |
| requirements         | `list[Requirement]`    | Required            | Functional and non-functional requirements (see sub-table)     |
| acceptance_criteria  | `list[str]`            | Required            | Testable AC lines — each must be verifiable as pass/fail       |
| tech_stack           | `list[str]`            | Optional            | Languages, frameworks, libraries, and infrastructure           |
| risks                | `list[str]`            | Optional            | Known risks with brief mitigation notes                        |
| open_questions       | `list[str]`            | Optional            | Unresolved items that need user input or further research      |

### Requirement Sub-fields

| Field       | Type                                     | Required / Optional | Description                                      |
| ----------- | ---------------------------------------- | ------------------- | ------------------------------------------------ |
| description | `str`                                    | Required            | What the requirement is                          |
| kind        | `Literal["functional", "non-functional"]`| Required            | Whether it describes behaviour or a quality attr |
| priority    | `str`                                    | Optional            | Defaults to "important" if omitted               |

## Example ask_user Interaction

When multiple valid approaches exist, present them as numbered options with
confidence scores so the user can make an informed choice:

```
ask_user(
    question=(
        "The project could store data in two ways. Which do you prefer?\n\n"
        "Option 1 (.75) — SQLite local database\n"
        "  Pros: zero setup, fast for small datasets, portable\n"
        "  Cons: no concurrent writes, limited to single machine\n\n"
        "Option 2 (.60) — PostgreSQL via Docker\n"
        "  Pros: concurrent access, scales to large datasets\n"
        "  Cons: requires Docker, more complex setup\n\n"
        "Option 3 (.40) — Flat JSON files\n"
        "  Pros: simplest possible, human-readable\n"
        "  Cons: no querying, slow at scale, no integrity checks\n\n"
        "Recommendation: Option 1 — matches KISS principle and the "
        "project's single-user scope.\n\n"
        "Pick a number, or describe a different approach."
    )
)
```

Key patterns in this example:

- Each option has a **confidence score** (`.75`, `.60`, `.40`).
- Each option lists **pros and cons** concisely.
- A **recommendation** is called out separately — it may differ from the
  highest-confidence option.
- The closing line **invites alternatives** the user might prefer.
