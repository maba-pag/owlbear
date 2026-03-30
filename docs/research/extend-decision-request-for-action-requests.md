# Extend Decision-Request Process for User Action Requests

> **Owning task:** #221 — Research: Extend decision-request process to handle user action requests
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Agents sometimes need the user to **do** something (manual testing, GUI verification, credential setup) rather than **decide** something (choose A vs B). Currently the only structured async-deferral mechanism is the decision-request process (`docs/decisions/pending/`), which only handles binary/multi-option decisions. When agents need user actions, they use unstructured `--block "Waiting on user: ..."` text, which provides no discovery mechanism, no checklist format, and no resolution workflow.

Task #167 (manual VS Code validation) illustrates the gap: 5 AC items requiring GUI interaction sat blocked with no structured notification. Other blocked tasks (#29, #174) show similar patterns.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| AutoGen Human-in-the-Loop docs | https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/human-in-the-loop.html | .85 — HandoffTermination pattern for async user requests |
| CrewAI Task docs | https://docs.crewai.com/concepts/tasks | .70 — `human_input` attribute, callback mechanism |
| GitHub Actions environment protection | https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment | .75 — Required-reviewer approval gate, structured file-based state |
| OwlBear decision-requests skill | skills/decision-requests/SKILL.md | 1.0 — Current format, planner Recipe 0, resolution workflow |
| OwlBear dispatch-planning skill | skills/dispatch-planning/SKILL.md | 1.0 — Planner Recipe 0, decision detection loop |
| OwlBear agent-common instructions | instructions/agent-common.instructions.md | 1.0 — Handoff pattern, blocking convention |

## 3. Analysis

### What AutoGen and CrewAI teach us

AutoGen's `HandoffTermination` pattern separates the **handoff signal** (structured, typed) from the **resume input** (provided by the user). CrewAI's `human_input` flag is binary — it blocks until human review. Both confirm the pattern: agent declares a typed pause point, system surfaces it, user resolves it. Neither offers a file-based async checklist model, which is what OwlBear needs for laptop-resident, session-gap workflows.

GitHub Actions' environment protection rules are the closest analog: a structured gate file with required reviewers, auto-timeout, and a well-known directory that the CI runner checks each cycle. This maps directly to OwlBear's planner Recipe 0.

### Option comparison

| Criterion | A: Extend decision-request (.85) | B: Separate `docs/actions/` (.55) | C: Move to root `decisions/` + extend (.50) |
|-----------|----------------------------------|-------------------------------------|----------------------------------------------|
| KISS | High — reuses existing format, location, planner recipe | Low — new dir, new recipe, new skill | Low — breaking rename + extension |
| YAGNI | High — one format, one location | Low — premature separation | Med — root move is speculative value |
| Planner changes | Minimal — Recipe 0 already scans the dir | New recipe needed | Recipe 0 path change + extension |
| User discovery | Same location users already know | Two places to check | Slightly better visibility, but breaking |
| Conceptual clarity | Action requests are a superset of decisions | Clean separation | Same as A but at root |
| Implementation effort | ~3 tasks, ~2 files changed | ~6 tasks, ~5 files changed | ~8 tasks, 20+ file reference updates |

### Current gap inventory

| Pattern | Current mechanism | Structured? | Discoverable? |
|---------|-------------------|-------------|---------------|
| User decision (choose A/B) | `docs/decisions/pending/` file | Yes | Yes (planner Recipe 0) |
| User action (do X, report) | `--block "Waiting on user: ..."` | No | No (must search blocked tasks) |
| Credentials/access needed | `--block "Waiting on user: ..."` | No | No |

## 4. Recommendation (.85 confidence)

**Option A: Extend the decision-request format** to support action requests alongside decisions.

### Design sketch

**Frontmatter extension** — add `request_type` field:

```yaml
request_type: action     # new field: "decision" (default) or "action"
completed: false          # replaces "approved" semantics for actions
decision: ""              # unused for action type
```

**Body format for action requests:**

```markdown
# Action Request: {title}

## Context
Why this action is needed, what task is blocked.

## Steps
- [ ] Step 1 description
- [ ] Step 2 description
- [ ] Step 3 with expected outcome

## Completion
When all steps are checked, set `completed: true` in the frontmatter.
```

**Resolution:** User checks off steps, sets `completed: true`. Planner Recipe 0 treats `completed: true` same as `approved: true` — unblocks the task.

**Why not separate directories:** The user already checks `docs/decisions/pending/` for work. Adding a second directory splits attention and doubles the planner's scan paths. Action requests and decision requests are both "things the user needs to address" — one inbox is simpler.

### Risk

Mid-complexity action requests (like #167 with 5 GUI steps) may accumulate. Mitigation: planner can surface a count at session start ("3 pending action requests").

## 5. Follow-up Tasks

### Task 1: Update decision-requests skill for action request type

Add `request_type: action` format, body template, and resolution rules to `skills/decision-requests/SKILL.md`. Update `docs/decisions/README.md` with action request instructions. Rename skill to "decision-and-action-requests" or keep name and expand scope.

### Task 2: Update agent-common handoff to reference action requests

Update `instructions/agent-common.instructions.md` handoff section and defer-to-user boundary to reference action requests for "user must do X" scenarios. Add per-role triggers for action request creation.

### Task 3: Update planner Recipe 0 to handle action request resolution

Extend planner's Recipe 0 in `skills/dispatch-planning/SKILL.md` to check for both `approved: true` (decisions) and `completed: true` (action requests). Add session-start surfacing of pending action request count.

### Task 4: Create action request for task #167

Create a proper action request file for the currently-blocked #167 task using the new format, so the user discovers the 5 manual GUI steps they need to perform.
