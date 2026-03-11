---
description: "Generate a visual HTML recap of the project's current state, activity, and next steps"
---

# Project Recap

Generate a single-page HTML mental-model snapshot of this project.

## Phase 1 — Gather data

Run these commands in the terminal and collect the output:

1. `git log --oneline --since="2 weeks ago"` — recent commits
2. `kanban\kanban-md.exe list --compact --status todo,in-progress,review,done` — active tasks
3. `kanban\kanban-md.exe list --compact --blocked` — blocked tasks
4. `Get-ChildItem -Recurse -Depth 2 -Name` — directory tree (depth 2)
5. Read `.github/copilot-instructions.md` — project purpose and tech stack

## Phase 2 — Generate HTML

Read the [visual-output skill](../skills/visual-output/SKILL.md) for styling rules,
approved palettes, and the anti-slop checklist. Follow it strictly.

Produce a **self-contained HTML page** (inline CSS, no external stylesheets or scripts)
with these 8 sections:

1. **Project Identity** — name, purpose, tech stack (from copilot-instructions.md)
2. **Architecture Snapshot** — top-level directories, key modules, dependency overview
3. **Recent Activity** — git commits from the last 2 weeks, grouped by theme
4. **Decision Log** — recently completed/done kanban tasks as decisions made
5. **State of Things** — in-progress, review, and todo tasks (current WIP)
6. **Mental Model Essentials** — core abstractions, data flow, key interfaces
7. **Cognitive Debt Hotspots** — blocked tasks, stale backlog, known tech debt
8. **Next Steps** — highest-priority todo tasks, recommended focus areas

Use CSS Grid cards with depth tiers for sections. Pick one approved palette from the
skill. Each section should be scannable — use bullet lists, badges, or compact tables
rather than prose.

## Phase 3 — Save and open

1. Save the HTML to `.owlbear/diagrams/project-recap.html`
2. Open it in the default browser:
   ```powershell
   Start-Process (Resolve-Path ".owlbear/diagrams/project-recap.html")
   ```
