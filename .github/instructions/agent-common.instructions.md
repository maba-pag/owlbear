---
applyTo: ".github/agents/**"
description: "Cross-agent rules that apply to all OwlBear agents"
---

# Cross-Agent Rules

All agents inherit project conventions from `copilot-instructions.md` (principles, coding discipline, process habits). This file covers only rules specific to the multi-agent dispatch model.

## Task discipline

- **ONE task per invocation.** Never work on multiple kanban tasks in a single session. If dispatched with multiple task IDs, work only on the first and report the rest as not started.
- **This rule applies to ALL agents** — builder, reviewer, writer, architect, auditor, researcher. No agent is exempt. The orchestrator enforces this by dispatching separate subagent calls (one per task) and running them in parallel waves.

## Evidence over claims

- **Never trust self-reports.** Verify deliverables yourself — run tests, read files, check the board. "The builder said it's done" is not evidence.
- **Cite specifics.** Reference file paths, line numbers, test names, and command output. "It looks fine" is never acceptable.
