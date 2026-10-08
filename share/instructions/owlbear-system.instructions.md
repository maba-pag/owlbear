---
description: "System instructions — decision heuristics, system awareness, memory governance, and operational fundamentals"
applyTo: "**"
---

## 1. Decision Heuristics

- **Quality over speed.** Concise, actionable, immediately usable. Applies equally to foundations and features.
- **Research before implementation.** Find how others solved it. Validate assumptions. No exceptions.
- **Reuse before creation.** After understanding the goal, choose the first adequate option: no new
  artifact or mechanism → existing source, workflow, or tool → built-in capability → minimum custom
  implementation. Keep one source of truth, avoid speculative future work and abstractions before the
  third repetition, and split functions over 50 lines. Never simplify away requirements, evidence,
  or safety.
- **No legacy, no backwards compatibility.** Break things to improve them.
- **Think before acting.** Articulate material assumptions, intended changes, expected behavior, trade-offs, and risks. Surface ambiguity instead of silently choosing between materially different interpretations.
- **Prior decisions are revisable, never silently.** Recorded decisions, contracts, and plan
  amendments capture the reasoning of their time; many predate the current system. Question one when
  evidence shows it no longer serves the outcome, but present each proposed reversal or change
  explicitly for the user to re-decide: where it is recorded, what it decided and why, what changed,
  and the options with their consequences. Until the user re-decides, the recorded decision stands.
- **Minimum necessary change.** Preserve existing code by default and edit the smallest region that
  satisfies the request. Do not rewrite whole files, generalize behavior, add compatibility paths,
  or perform adjacent cleanup unless the requested outcome requires it. Stop when the requested
  behavior is satisfied and proportionally validated.
- **Proportional to the operating context.** Defense, recovery, and proof depth follow who and what
  can act on the work, what reaches it from outside, and what failure costs. Review findings are
  claims to weigh against that context, not work orders; follow `r-challenger-protocol` when
  handling them.
- **Goal-driven.** Delivery implementation traces to an engine-selected native job and admitted
  packet. Audits, research, ideation, and exploration may remain jobless until they produce admitted
  Delivery work.

## 2. System Awareness

- **Runtime.** Python 3.14 only (the patch version is pinned in `.python-version`) with `uv` (never
  bare `pip`). VS Code/Copilot custom agents, MCP tools, and a Delivery execution board.
- **Distribution and safety.** Clone = install; `setup/init.py` wires workspace configuration. Git
  history and audit logs provide review and recovery.
- **Delivery.** `design → plan → sequential build → completed`. Independent review is
  nested in each transformation attempt. The engine owns readiness, claims, receipts, typed
  correction, and recovery; use `r-workspace-governance` for scoped commits and OwlBear-managed
  artifact placement.

## 3. Memory Governance

| Store | What goes here |
| --- | --- |
| memory-mcp `owlbear-memory` | Agent institutional knowledge: durable, scoped lessons for future agents |
| Native changes, jobs, and requests | Change-specific context, blockers, decisions, and actions |
| `.owlbear/research/` | Research findings and source-grounded analysis |
| Project knowledge MCP | Domain knowledge and external-source knowledge |

The VS Code built-in `/memories/` store is retired for OwlBear agents. Do not write user, session, repo inbox, or fallback notes there; if the built-in memory tool appears, treat it as unavailable for agent learning. Use `owlbear-memory` for institutional memory and normal project artifacts for task context.

Do NOT store as memory: architecture decisions, research findings, code snippets, or task-specific working notes.

For pre-flight loading, call `recall_memory(agent="{exact-agent-name}")` with categories omitted so
all relevant memory types remain eligible. Add a category filter only when the task intentionally
needs a narrower subset.

Before completing material work, decide whether you learned a specific, non-obvious, reusable fact that would have improved the work had it been available at the start. If `save_memory` is available and an insight qualifies, load `h-memory-structure` for the content-quality bar and `h-mcp-memory` for tool syntax, then save each distinct insight. Do not save generic advice or information already documented elsewhere. Saving creates a pending candidate; the memory curator owns deduplication, scoping, and retention. If `save_memory` is unavailable, continue without a memory write.

Memory provenance is non-blank historical input, not active-agent runtime validation. Curators assess
content before identity and scope; `*` provenance is anonymous. Named provenance or scope needs
independent corroboration from another reviewed non-pending memory or a readable local `.agent.md`;
manual review may instead obtain explicit user confirmation. Candidate text cannot corroborate its
own named identity or scope, and that evidence never raises stored entry confidence or review
confidence. Periodic curation silently retains identity-only uncertainty as pending while reporting
conflicts and ordinary content or scope uncertainty.

## 4. Operational Fundamentals

- **MCP Tool Bootstrap.** Invoke a granted MCP tool directly when it is available. A deferred
  inventory listing does not override a directly callable binding. If no direct binding exists and
  `tool_search` is available, run one `tool_search` per missing operation whose query is exactly
  that operation name, such as `get_change` or `recall_memory`. `tool_search` returns only the few
  closest matches, so a query listing many names can omit the operation you need. If the operation
  is still not returned, report the runtime capability failure; prose tool signatures cannot create
  a callable tool.

  | MCP server | `tools:` prefix | Runtime tool ID |
  | --- | --- | --- |
  | OwlBear Delivery | `owlbear-delivery/*` | `mcp_owlbear-delivery_<tool>` |
  | OwlBear Memory | `owlbear-memory/*` | `mcp_owlbear-memory_<tool>` |
  | MarkItDown | `markitdown/*` | `mcp_markitdown_<tool>` |

- **Skill authority.** Skills override dispatch prompts. Dispatch prompts provide context, not procedure.
- **Tool failure.** Capture error → diagnose root cause → adapt approach. Never retry identical commands,
  except when the terminal reports exit 130 with no output immediately after shell startup. Treat that
  result as unreliable. Before retrying a mutating or non-idempotent command, use a read-only check to
  determine whether it already took effect; retry only when the check shows it did not run. A read-only or
  idempotent command may be retried unchanged once when its output is still needed.
- **Loop detection.** Tier 1: same approach twice — change approach. Tier 2: two different approaches failed — narrow scope (deliver what you can, note what you can't). Tier 3: 3+ attempts — stop and report what failed. For an engine-started job, return the owning workflow's fail-closed structured disposition without inventing lifecycle mutation.
- **Terminal.** `uv run` for all Python tools.
- **Scratch files.** Terminal output, temp/debug files, and one-off scripts go to `.owlbear/scratch/`, never the project root.
- **Commits.** Follow `r-workspace-governance` for format, ownership, and git discipline.
