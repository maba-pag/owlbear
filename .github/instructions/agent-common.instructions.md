---
applyTo: ".github/agents/**"
description: "Cross-agent rules that apply to all OwlBear agents"
---

# Cross-Agent Rules

## Task discipline

- **ONE task per invocation.** Never work on multiple kanban tasks in a single session. If dispatched with multiple task IDs, work only on the first and report the rest as not started.
- **Goal-driven execution.** Every action traces back to a concrete kanban task. If you cannot name the task you are working on, stop and check the board first.

## Evidence over claims

- **Never trust self-reports.** Verify deliverables yourself — run tests, read files, check the board. "The builder said it's done" is not evidence.
- **Cite specifics.** Reference file paths, line numbers, test names, and command output. "It looks fine" is never acceptable.

## Tool hygiene

- **`manage_todo_list` extensively.** Track progress, create checkpoints, update after each completed step. Mark ONE item in-progress at a time; mark completed immediately when done.
- **`askQuestions` at decision points.** Never assume — include confidence scores (`.0`–`1.0`) on option labels. Prefix with `(bp:)` for best practice, `(rec:)` for recommendation.
- **kanban-md compact flag.** Always use `--compact` on `list`, `board`, `metrics`, `log` commands.

## Quality baseline

- **Surgical changes.** Smallest diff that achieves the goal. One logical change per task.
- **Think before coding.** Articulate what will change, expected behavior, and what could go wrong — before touching any file.
- **Research before implementation.** Nothing we build is new. Before implementing anything, find how others have solved it.
