# Reviewer Loop Pattern Detection

> **Owning task:** #436 — Add loop-pattern detection to reviewer checklist
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

The reviewer agent verifies builder work quality via the `code-review` skill (Steps 6.0–6.6 CRITICAL, 7.1–7.4 INFORMATIONAL). Currently no step inspects builder Channel B notes for loop patterns — repeated identical tool calls, brute-force retries, or tier-3 violations. Task #432's research (`docs/research/loop-detection-instruction-patterns.md`) established a 3-tier escalation model for agent instructions, but the reviewer needs its own detection checklist to verify builders actually followed it.

## 2. Sources Studied

| Source | URL / Path | Relevance |
|--------|-----------|-----------|
| deer-flow LoopDetectionMiddleware | `github.com/bytedance/deer-flow` → `backend/.../loop_detection_middleware.py` | .95 — hash tool calls, warn@3, stop@5, sliding window |
| AutoGen termination conditions | `microsoft.github.io/autogen/stable/.../termination.html` | .85 — composable conditions (MaxMessage, FunctionCall, Text) |
| OwlBear loop-detection research (#432) | `docs/research/loop-detection-instruction-patterns.md` | 1.0 — 3-tier model (detect/adapt/stop) for instructions |
| OwlBear code-review skill | `skills/code-review/SKILL.md` | 1.0 — existing 6 CRITICAL + 4 INFO checks |
| OwlBear builder agent notes format | `agents/builder.agent.md` §Channel B | 1.0 — `## Builder Notes` structure (files, tests, lint, fixes) |
| Real builder notes (kanban_temp.json) | `kanban_temp.json` tasks #143, #158, #167 | 1.0 — shows retry suffixes: "Builder Notes (retry)", "(retry 2)" |

## 3. Analysis

### What loop patterns look like in builder notes

Builders append `## Builder Notes` sections to the task body. Retries produce suffixed sections: `Builder Notes (retry)`, `Builder Notes (retry 2)`. Both deer-flow and AutoGen treat repeated identical actions as the primary loop signal.

In OwlBear's instruction-based system, the reviewer is the post-hoc detector — checking whether the builder complied with the 3-tier escalation rules after the fact.

### Detection signals

| Signal | What to look for | Severity |
|--------|-----------------|----------|
| Multiple retry sections | Count `Builder Notes` headers (original + retries) | INFO if ≤ 2, CRITICAL if ≥ 3 |
| Identical commands across retries | Same pytest/ruff/grep invocations with same flags/args | CRITICAL — tier-1 violation (no approach variation) |
| Missing diagnosis between retries | No reasoning about why previous attempt failed | CRITICAL — brute-force retry pattern |
| Tier 3 without handoff | 3+ failed attempts at same goal, no `BLOCK`/handoff | CRITICAL — violates agent-common §Loop detection |
| Approach variation present | Different flags, different search terms, changed strategy | PASS — correct escalation behavior |

### Where to place in code-review skill

| Option | Location | Rationale |
|--------|----------|-----------|
| **(rec:) New Step 6.7** | After 6.6 (necessity), before Step 7 | Natural extension of CRITICAL checks; reads task body not code |
| (bp:) New Step 7.5 | Informational section | Lower friction, but misses tier-3 violations which should FAIL |
| (bp:) Separate red flag | Reviewer agent red flags | Only triggers self-check, not evidence table |

Recommendation (.85): **Step 6.7** — a CRITICAL check with a split severity model: tier-3 violations auto-FAIL, while moderate retries (≤ 2 with approach variation) are noted but don't block.

### Proposed Step 6.7 — Builder process quality (loop detection)

Read the full task body via `kanban\kanban-md.exe show {id}`. Check builder notes for loop patterns:

1. **Count retry sections.** Count `## Builder Notes` headers (including suffixed retries). Record the count.
2. **Check approach variation.** For each retry, verify the builder describes a different diagnosis, changed approach, or new strategy. Identical approaches across retries = loop pattern.
3. **Check for tier-3 violation.** If 3+ retries at the same logical goal exist without a handoff/block statement, the builder violated the loop detection escalation rules.
4. **Produce a process-quality assessment.**

Assessment values: **CLEAN** (≤ 1 retry or all retries show approach variation), **FRICTION** (2 retries with approach variation — note but don't fail), **LOOP** (identical approaches or tier-3 without handoff — FAIL).

**Any LOOP assessment = automatic FAIL.** FRICTION is informational only.

## 4. Recommendation (.85 confidence)

Add Step 6.7 to the code-review skill as a CRITICAL check with the split severity model above. Also add a corresponding red flag to the reviewer agent: "You haven't checked builder notes for loop patterns (Step 6.7)."

**Risk:** Builders who legitimately retry with good approach variation may get flagged as FRICTION unnecessarily. Mitigation: FRICTION is informational only — it does not block PASS.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Add Step 6.7 loop-detection check to code-review skill" --priority needed --status ideation --tags "scope:agents,phase-2" --body "## Context\nAdd a new CRITICAL check (Step 6.7) to the code-review skill that inspects builder Channel B notes for loop patterns.\n\nSee docs/research/reviewer-loop-pattern-detection.md for full analysis.\n\n## Acceptance Criteria\n- [ ] New Step 6.7 'Builder process quality (loop detection)' added to code-review skill after Step 6.6\n- [ ] Step counts Builder Notes retry sections and checks for approach variation\n- [ ] LOOP assessment (identical approaches or tier-3 without handoff) triggers automatic FAIL\n- [ ] FRICTION assessment (retries with variation) is informational, does not block PASS\n- [ ] CLEAN assessment (no retries or single retry) noted but no action needed"
```

```
kanban\kanban-md.exe create "Add loop-detection red flag to reviewer agent" --priority important --status ideation --tags "scope:agents,phase-2" --body "## Context\nAdd a red flag entry to reviewer.agent.md that cross-references the new Step 6.7 loop-detection check.\n\nSee docs/research/reviewer-loop-pattern-detection.md for analysis.\n\n## Acceptance Criteria\n- [ ] New red flag in reviewer.agent.md: 'You have not checked builder notes for loop patterns (Step 6.7)'\n- [ ] Red flag placed in the existing Red flags list alongside other review checks"
```
