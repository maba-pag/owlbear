---
id: 143
title: 'Research: Admin dashboard — manage agents, memory, tools, activity'
status: ideation
priority: someday
created: 2026-02-27T14:59:00.7312135+01:00
updated: 2026-03-21T06:40:14.581532+01:00
started: 2026-03-01T20:08:50.8256779+01:00
tags:
    - research
    - ui
    - phase-14
blocked: true
block_reason: Broad multi-domain dashboard idea lacks scoped AC and overlaps prior research; re-enter ideation with a single, research-backed question.
class: standard
---

A web-based or TUI dashboard for managing OwlBear. View and edit: agent definitions and their 'souls', memory/knowledge contents, tool and skill assignments, agent hierarchy, activity history, cron jobs, database contents.

References to evaluate: jontsai/openclaw-command-center, generic admin panels (streamlit, gradio, nicegui). Key question: is this worth building custom, or does PydanticAI's Logfire + a kanban board cover 90% of the need? Don't build a dashboard for the sake of having one.

[[2026-03-21]] Sat 06:40
## Architecture Review
**Verdict:** Block

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| A web-based or TUI dashboard for managing OwlBear. | No interface choice, no bounded user flow, and no verifiable AC. Prior research already rejects a web dashboard now and defers a TUI until a daemon event stream exists. | Move back to ideation. |
| View and edit agent definitions and their 'souls'. | Crosses agent-definition files and the registry scan path in src/owlbear/core/agent_registry.py; no safe mutation API or file contract is defined. | Separate ideation task if still needed. |
| View and edit memory/knowledge contents. | Crosses the memory and knowledge subsystems; existing access is file/CLI/DB-based, e.g. src/bearclaw/commands/knowledge_source.py. The task does not define allowed mutations or safety boundaries. | Separate ideation task if justified. |
| View and edit tool and skill assignments, agent hierarchy. | Crosses agent config, skill loading, and delegation structure with no runtime-vs-file boundary specified. | Separate ideation task if justified. |
| View activity history. | Existing activity and observability data already live in kanban/activity.jsonl and structured logs read by src/owlbear/core/retrospective_hook.py and documented in docs/research/agent-observability.md. The task does not identify a missing capability. | Use prior research; do not approve as-is. |
| View and edit cron jobs, database contents. | Crosses daemon scheduling and storage internals; no interface, safety model, or invariant set is specified. | Separate research before backlog. |
| Is this worth building custom, or does Logfire + kanban cover 90%? | This product question is already researched in docs/research/agent-observability.md, docs/research/workflow-dashboards-devtools.md, and docs/research/textual-tui-dashboard.md. | Return to ideation and anchor any future work in those findings. |

### Architecture Notes
- This is not a single-domain task. It spans agent definitions, skills, memory/knowledge, observability, scheduling, and storage internals, which violates the atomicity rule for backlog -> todo approval.
- Current subsystem boundaries are already distinct:
  - src/owlbear/core/agent_registry.py scans agent definition files and provides a read-oriented registry, not an editing API.
  - src/bearclaw/commands/daemon.py already exposes daemon status via Rich panel output.
  - src/bearclaw/commands/knowledge_source.py already manages one slice of knowledge data through CLI commands.
  - src/owlbear/core/retrospective_hook.py already consumes kanban/activity.jsonl for activity history.
- Prior research already narrows the dashboard question:
  - docs/research/workflow-dashboards-devtools.md recommends Rich-enhanced CLI now and rejects a web dashboard on YAGNI grounds.
  - docs/research/textual-tui-dashboard.md defers a TUI until a daemon event stream exists.
  - docs/research/agent-observability.md recommends structured local observability plus opt-in OTel instead of a bespoke admin surface.
- Because no implementation contract or scoped research outcome exists here, the task belongs back in ideation. A future task should ask one concrete question only, cite the relevant prior research, and define one subsystem boundary.

### Changes Made
- Claimed #143 for architecture review.
- Appended this architecture review with evidence from existing code and prior research.
- Moved #143 from backlog to ideation and blocked it pending scoped follow-up research.

### Dependencies
- Verified prior research: docs/research/agent-observability.md, docs/research/workflow-dashboards-devtools.md, docs/research/textual-tui-dashboard.md.
- Verified current boundaries: src/owlbear/core/agent_registry.py, src/bearclaw/commands/daemon.py, src/bearclaw/commands/knowledge_source.py, src/owlbear/core/retrospective_hook.py.
