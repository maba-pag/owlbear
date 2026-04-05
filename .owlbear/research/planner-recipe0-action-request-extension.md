# Planner Recipe 0 — Action Request Extension

> **Owning task:** #226 — Update planner Recipe 0 for action request resolution
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Task #224 (archived) added the `request_type: action` format to the decision-requests skill. Recipe 0 in `skills/dispatch-planning/SKILL.md` currently handles only decision requests (`approved: true`). How should Recipe 0 be extended to also handle action request resolution, auto-timeout, and pending-count surfacing?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| OwlBear decision-requests skill | skills/decision-requests/SKILL.md | 1.0 — Defines action request format, resolution workflow, `completed` field |
| OwlBear dispatch-planning skill | skills/dispatch-planning/SKILL.md | 1.0 — Current Recipe 0, planner output format, JSON fields |
| Parent research #221 | docs/research/extend-decision-request-for-action-requests.md | 1.0 — Design rationale, option analysis, risk assessment |
| GitHub Actions environment protection | https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment | .75 — Wait-timer auto-approve after timeout; structured file-based gate with auto-resolution |
| AutoGen Human-in-the-Loop | https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/human-in-the-loop.html | .70 — HandoffTermination typed pause-point pattern; confirms need for structured resume signals |

## 3. Analysis

### Current Recipe 0 behavior

Recipe 0 runs before the Board Scan. It: (1) lists `docs/decisions/pending/*.md`, (2) reads frontmatter, (3) if `approved: true` → unblock + move to `resolved/`, (4) if `approved: false` and >5 days old → auto-resolve with agent recommendation.

### Extension design

The decision-requests skill (post-#224) already documents that the planner should treat `completed: true` the same as `approved: true`. The extension is mechanical:

| File state | Request type | Action |
|------------|-------------|--------|
| `approved: true` | decision | Unblock task + move file to resolved/ *(existing)* |
| `completed: true` | action | Unblock task + move file to resolved/ *(new — same action)* |
| `approved: false`, >5 days | decision | Auto-resolve: set `approved: auto`, unblock, move *(existing)* |
| `completed: false`, >5 days | action | Auto-resolve: set `completed: auto`, unblock, move *(new)* |
| `approved: false`, ≤5 days | decision | Count as pending decision |
| `completed: false`, ≤5 days | action | Count as pending action request |

**Type detection:** Check for `completed:` field (action) vs `approved:` field (decision). Files without `request_type` default to decision (backwards-compatible per #224 design).

### Auto-resolution semantics for action requests

**Design tension:** Decision auto-resolution is low-risk because the agent pre-fills a recommendation. Action auto-resolution is higher-risk — the user action was never performed.

GitHub Actions' wait-timer provides precedent: deployments auto-approve after the timer expires, even though the reviewer never explicitly approved. The reasoning: permanent blockage is worse than proceeding with risk. The same logic applies here.

**Mitigation:** `completed: auto` (parallel to `approved: auto`) signals to downstream agents that the action was not manually confirmed. Agents encountering a task unblocked by auto-resolution can choose to re-verify or proceed with caution. This is sufficient for OwlBear's laptop-resident model where the user is the sole operator.

### Session-start surfacing

**Approach:** Add a `pending` field to the planner's JSON output alongside `dispatch` and `gate_warnings`:

```json
{"dispatch":[...],"gate_warnings":[],"pending":{"decisions":2,"actions":1}}
```

The orchestrator can surface "3 pending user requests (2 decisions, 1 action)" at the start of each cycle. This is KISS-aligned: one new field, machine-readable, no changes to existing `dispatch` or `gate_warnings` semantics.

**Alternative considered:** Stderr diagnostic line before JSON. Rejected — it complicates parsing and the planner's contract is "single-line JSON only."

### Implementation scope

Changes are confined to one file: `skills/dispatch-planning/SKILL.md`. Specifically:

1. **Recipe 0 prose** (lines ~109–117): Extend the resolution logic description to cover both `approved: true` and `completed: true`, add auto-resolution for action requests with `completed: auto`
2. **Step 1 prose** (line ~154): Update "Check pending decision requests" paragraph to reference action requests
3. **Step 3 JSON format** (lines ~262–290): Add `pending` field to the output format spec, update the format examples
4. **Self-critique checklist** (near end): Add checklist item for action request handling

No new files needed. No code changes (this is a skill/docs task).

## 4. Recommendation (.90 confidence)

Extend Recipe 0 with the symmetric treatment shown in the table above. Use `completed: auto` for action request auto-resolution (parallel to `approved: auto`). Add `pending` field to JSON output for session-start surfacing.

**Risks:**
- Auto-resolved action requests (completed: auto) may mask genuinely needed user actions. Low probability in practice — 5-day timeout is generous, and the user is the sole operator.
- `pending` field addition breaks strict JSON schema consumers. Mitigated: only the OwlBear orchestrator consumes this output, and it tolerates extra fields.

## 5. Research Checklist

1. **Theoretical validity** — Sound. Symmetric treatment of decisions and actions in a unified scan is the simplest design. The decision-requests skill already mandates this equivalence.
2. **Environment audit** — No existing mechanism handles action request resolution in Recipe 0. The gap is exactly what this task addresses.
3. **Prior art** — GitHub Actions wait-timer auto-approve, AutoGen HandoffTermination typed resume. Both confirm the pattern of structured pause-points with timeout-based auto-resolution.
4. **Technical feasibility** — Trivial. Changes are prose edits to a skill file with no code dependencies.
5. **Architecture fit** — Extends existing Recipe 0 without new abstractions. JSON output field addition is backwards-compatible.
6. **Implementation approach** — Edit 4 sections of dispatch-planning/SKILL.md as described above. No new files.
7. **Testing strategy** — N/A (type:docs — no code to test). Validation via architect review of skill file changes.
