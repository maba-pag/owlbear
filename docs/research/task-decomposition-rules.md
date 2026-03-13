# Task Decomposition Rules: Single-Domain Enforcement

> **Owning task:** #685 — Task decomposition rules: enforce single-domain tasks at planning level
> **Date:** 2026-03-08 **Status:** Complete

## 1. Context and Question

The builder agent is domain-agnostic — it reads existing code for patterns. If tasks span multiple domains (e.g., "add CLI flag and update database schema"), the builder context gets diluted and quality drops. The question: **how should we enforce single-domain decomposition, and where do the rules go?**

Sub-questions:

1. Is single-domain the right granularity? (vs. single-file, single-function, single-module)
2. How do other multi-agent systems handle task boundaries?
3. Where do rules go: planner, architect, or shared instructions?
4. How do follow-up tasks (from non-planner agents) stay quality-controlled?

## 2. Sources Studied

| # | Source | URL | Relevance | What was taken |
|---|--------|-----|-----------|----------------|
| 1 | ChatDev (Qian et al., ACL 2024) | arxiv.org/abs/2307.07924 | .80 | Chat chain decomposes dev into phase-scoped subtasks; each subtask has one instructor + one assistant with a single concern |
| 2 | MetaGPT (Hong et al., ICLR 2024) | arxiv.org/abs/2308.00352 | .75 | SOP-driven decomposition; assembly-line paradigm assigns roles to subtasks; intermediate artifacts are verified before passing downstream |
| 3 | OpenHands agent delegation | github.com/All-Hands-AI/OpenHands | .70 | Subtask = one agent conversation; delegator decomposes into bounded scope per delegation; task/subtask hierarchy with iteration counters |
| 4 | Fowler — Bounded Context (DDD) | martinfowler.com/bliki/BoundedContext.html | .85 | Domain boundaries drawn by model/language differences; "total unification not feasible or cost-effective"; bounded contexts with explicit integration points |
| 5 | OwlBear existing rules | kanban-planner.agent.md, architect.agent.md, agent-common.instructions.md | 1.0 | Current atomicity rules: "single responsibility," "if 'and' joins unrelated concerns, split" — but no domain enumeration |

## 3. Analysis

### 3.1 Granularity: Single-domain vs. alternatives

| Granularity | Pros | Cons | KISS/YAGNI fit |
|-------------|------|------|----------------|
| **Single-file** | Very precise | Too restrictive — many tasks legitimately touch 2-3 files in same domain | Poor |
| **Single-function** | Extreme atomicity | Creates task explosion; overhead exceeds value | Poor |
| **Single-module** | Good for backend | Modules can span domains (e.g., a CLI module with backend logic) | Medium |
| **Single-domain** | Matches how code is organized; builder reads one area of codebase | Needs clear domain list; edge cases at boundaries | Good |

**Recommendation (.85):** Single-domain is the right granularity. It matches ChatDev's phase-scoping (design/code/test are domain phases) and DDD's bounded contexts. The domain list should be explicit and fixed to prevent interpretation drift.

### 3.2 Domain list

Proposed domains (one per task):

| Domain | Scope | Example files |
|--------|-------|---------------|
| `backend` | Core logic, models, services, protocols | `src/owlbear/**/*.py` (non-CLI, non-UI) |
| `frontend` | UI components, styles, templates | `src/**/ui/**`, `*.tsx`, `*.css` |
| `database` | Schema, migrations, storage layer | `src/owlbear/memory/**` (storage-specific) |
| `cli` | CLI commands, argument parsing | `src/bearclaw/**/*.py` |
| `config` | Settings, env vars, TOML config | `pyproject.toml`, config modules |
| `test-infra` | Test fixtures, conftest, test utilities | `tests/conftest.py`, test helpers |
| `docs` | Documentation, instructions, agent files | `docs/**`, `.github/**` |

**Edge case:** A task that adds a config field AND the backend code that reads it could be argued as two domains. The right answer: the config field is part of the backend task's AC (it's the interface), not a separate task. Domain = the primary concern being changed.

### 3.3 Where do rules go?

| Rule | Location | Rationale |
|------|----------|-----------|
| Domain list + atomicity gate | `kanban-planner.agent.md` | Planner is the entry gate for task creation — domain check belongs here |
| Single-domain validation | `architect.agent.md` step 3 | Architect is the quality gate for backlog→todo — catches tasks created outside planner |
| Follow-up task quality rules | `agent-common.instructions.md` | All agents may create follow-up tasks; shared rules prevent quality gaps |
| Follow-up tasks → backlog | `agent-common.instructions.md` | Routing rule — ensures architect gate applies to all tasks |

This matches the two-layer pattern from MetaGPT (SOP at creation) and ChatDev (verification at phase boundaries). The planner creates well-formed tasks; the architect catches anything that slipped through or was created by non-planner agents.

### 3.4 Follow-up task routing

Currently, non-planner agents can suggest tasks at any status. The risk: a reviewer creates a "fix X and Y" task at `todo`, bypassing the architect gate.

| Approach | How | Pros | Cons |
|----------|-----|------|------|
| **All follow-ups to `backlog`** | Rule in agent-common | Architect reviews everything; consistent quality | Adds latency for trivial fixes |
| **Follow-ups to `ideation`** | Stricter gate | Forces research phase too | Overkill for "fix this bug" tasks |
| **Follow-ups to `todo` for trivial** | Case-by-case | Fast for small fixes | Judgment call = inconsistency |

**Recommendation (.90):** All follow-up tasks from non-planner agents go to `backlog`. The architect gate is cheap (one review pass) and prevents compounding quality debt. Trivial tasks pass through quickly — the architect doesn't need to do deep research on "fix typo in X."

## 4. Recommendation (.85 confidence)

**Implement three changes:**

1. **kanban-planner.agent.md** — Add explicit domain list and single-domain gate to step 3 and critical_rules. The planner must tag each task with exactly one domain and refuse to create multi-domain tasks.

2. **architect.agent.md** — Add "single-domain" as item 9 in the Evaluate Architecture checklist (step 3). Architect splits multi-domain tasks that reach backlog.

3. **agent-common.instructions.md** — Add "Follow-up task quality" section with three rules: (a) AC required, (b) single-responsibility + affected files listed, (c) target `backlog` status so architect gate applies. This applies to all agents creating follow-up tasks (reviewer rejections, researcher findings, auditor findings).

**What NOT to do:** No specialized builder agents. The builder stays domain-agnostic. Domain knowledge comes from reading existing code patterns, not from builder specialization. This matches OwlBear's KISS principle and avoids the agent proliferation seen in MetaGPT's role explosion.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Update kanban-planner with single-domain decomposition gate" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --body "Add to kanban-planner.agent.md:\n- critical_rules: add 'Single-domain per task' rule with domain list (backend, frontend, database, cli, config, test-infra, docs)\n- step 3: add domain check — each task must target exactly one domain; if task spans domains, split it\n- step 6: task title convention includes domain tag\n- bad_example: multi-domain task\n- good_example: properly split domain tasks\n\nAC:\n- [ ] critical_rules has single-domain rule with enumerated domain list\n- [ ] step 3 checks domain as part of decomposition\n- [ ] examples show domain-aware decomposition" --status backlog

kanban\kanban-md.exe create "Add single-domain validation to architect gate" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --body "Add to architect.agent.md step 3 (Evaluate Architecture):\n- Item 9: Single-domain — does this task target exactly one domain? If it spans backend + CLI or backend + database, split it.\n- Reference the canonical domain list from kanban-planner\n\nAC:\n- [ ] architect step 3 has single-domain check as item 9\n- [ ] red flags section includes 'approving a multi-domain task without splitting'" --status backlog

kanban\kanban-md.exe create "Add follow-up task quality rules to agent-common.instructions.md" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --body "Add new section 'Follow-up task quality' to agent-common.instructions.md:\n- Rule 1: Every follow-up task requires AC (acceptance criteria)\n- Rule 2: Single-responsibility — one concern per task, affected files listed\n- Rule 3: Target backlog status — follow-up tasks from non-planner agents always go to backlog so architect gate applies\n- Note: only the kanban-planner may create tasks at ideation; all other agents create at backlog\n\nAC:\n- [ ] agent-common has 'Follow-up task quality' section with 3 rules\n- [ ] Section explicitly states follow-ups go to backlog\n- [ ] No new rule exceeds 2 sentences (token budget conscious per #686)" --status backlog
```
