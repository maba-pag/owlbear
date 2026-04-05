# Challenger → Arch-Review Integration

> **Owning task:** #468 — Integrate Challenger into arch-review workflow (Step 3.5)
> **Date:** 2026-03-31 **Status:** Complete

## 1. Context and Question

Task #467 created `challenger.agent.md` — a read-only adversarial subagent with structured I/O. Task #468 wires it into the architect's `arch-review` workflow as Step 3.5, mandatory before APPROVE verdicts. The parent research (`docs/research/challenger-subagent-design.md`, #465) designed the integration in sections S3e–f. This research validates technical feasibility and implementation specifics.

**Core question:** What are the exact changes needed to `architect.agent.md` and `arch-review/SKILL.md`, and are there any blockers or design gaps in the parent research?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | VS Code Subagents Guide | https://code.visualstudio.com/docs/copilot/agents/subagents | .95 — `agents:` array overrides `disable-model-invocation`, one-shot return |
| S2 | OwlBear #465 Challenger design | docs/research/challenger-subagent-design.md S3e-f | .95 — integration protocol, trigger points |
| S3 | OwlBear #228 nesting research | docs/research/subagent-nesting-architecture.md | .90 — L2 confirmed, assign mode, parallel exec |
| S4 | OwlBear challenger.agent.md | agents/challenger.agent.md | .95 — I/O contract, tools, persona — already implemented |
| S5 | OwlBear architect.agent.md | agents/architect.agent.md | .95 — current frontmatter, tools list includes `agent` |
| S6 | OwlBear arch-review SKILL.md | skills/arch-review/SKILL.md | .95 — current Step 3→4 boundary, body template |

## 3. Analysis

### 3a. Frontmatter change — `agents: [] → [challenger]`

The architect already has `agent` in its tool list (S5). VS Code docs confirm `agents:` array overrides `disable-model-invocation: true` on listed agents (S1). The challenger has `disable-model-invocation: true` (S4), so it's only invocable when explicitly listed. Change is single-field, no side effects.

### 3b. Step 3.5 placement and trigger logic

| Current flow | Proposed flow |
|---|---|
| Step 3: Evaluate architecture → Step 4: Decide | Step 3: Evaluate → **Step 3.5: Challenge** → Step 4: Decide |

Trigger conditions per S2:

| Proposed verdict | Challenge? | Rationale |
|---|---|---|
| APPROVE | **Mandatory** | Highest stakes — wrong approvals cascade to 4+ downstream agents |
| REFINE | Optional (architect's judgment) | Medium stakes — refined AC may introduce issues |
| SPLIT / BLOCK | Skip | Low stakes — these don't advance work downstream |

### 3c. Prompt construction

The architect must construct a prompt matching the challenger's input contract (S4):

| Field | Source in arch-review context |
|---|---|
| `task_id` | From dispatched task |
| `proposed_verdict` | Architect's Step 3 conclusion (APPROVE/REFINE) |
| `reasoning` | Architect's evaluation summary (Step 3 notes) |
| `ac_lines` | The refined AC being approved |
| `codebase_evidence` | Files examined, patterns found (Step 2 findings) |
| `research_doc` | Task body reference to `docs/research/*.md` if present |

The architect uses `runSubagent` with `agentName: "challenger"` and passes these fields in the prompt text. The challenger returns structured text (6 sections per S4 output contract).

### 3d. Integration protocol (from S2 S3f)

| Challenger output | Architect action |
|---|---|
| `proceed` + confidence ≥ .80 | Continue with APPROVE. Note challenge results in body. |
| `reconsider` OR confidence < .80 | Re-evaluate. May revise AC, change verdict, or justify override. |
| `block` | Strong signal to move task back to ideation. Must provide rebuttal if overriding. |

**Final authority remains with the architect** — the Challenger advises, never decides.

### 3e. Error handling / fallback

If `runSubagent` fails (timeout, tool error, malformed response):

1. Architect proceeds without challenge
2. Notes in body: `Challenge: FALLBACK — {error reason}`
3. No verdict change required — the architect's own analysis stands

This is a sequential (non-blocking) fallback. The challenge is an additional check, not a gate prerequisite.

### 3f. Body template addition

The Architecture Review body section (Step 5) needs a `### Challenge Results` subsection:

```
### Challenge Results
- Challenger: {proceed/reconsider/block}
- Confidence in original: {.XX}
- Key challenges: {summary}
- Architect response: {accepted/rebutted/revised}
```

For FALLBACK scenarios: `### Challenge Results\nChallenge: FALLBACK — {reason}`.

### 3g. Gap analysis vs parent research

| Parent design (S2) | Implementation gap? | Notes |
|---|---|---|
| Step 3.5 trigger points | No | Clear: mandatory APPROVE, optional REFINE |
| Integration protocol | No | 3 paths well-defined |
| Final authority | No | Explicit in design |
| Sequential fallback | Minor | Parent says "if Challenger subagent errors" — need to specify what errors look like (timeout vs malformed vs tool-not-found) |
| Body template | Minor | Parent says "includes Challenge Results subsection" — need exact format |
| Prompt format | Minor | Parent I/O contract is defined but the exact prompt text construction for runSubagent needs to be spelled out in Step 3.5 |

All gaps are minor implementation details, not design concerns. The builder can resolve them from the AC + this research.

## 4. Recommendation (.90 confidence)

Proceed with implementation as designed. The parent research is sound, the dependency (#467) is archived, and no design gaps block implementation. All changes are to declarative config/skill files (no Python code).

**Specific changes:**

1. `architect.agent.md`: change `agents: []` to `agents: [challenger]`
2. `arch-review/SKILL.md`: add Step 3.5 between Steps 3 and 4 with trigger logic, prompt construction guidance, integration protocol, and fallback handling
3. `arch-review/SKILL.md`: update Step 5 body template to include Challenge Results subsection

**Risk:** One additional Opus call per APPROVE verdict (~30% of architect tasks reach APPROVE per S2). Bounded by one-shot design.

**T3 note:** This task modifies agent instructions and skills (T3 triggers). However, the parent research (#465) established the design, and the first implementation step (#467) was already fully completed through the pipeline (architect → auditor → archived). This is continuation of accepted work, not a new T3 finding. The architect gate (backlog → todo) provides the remaining safety check.

## 5. Follow-up Tasks

No new follow-up tasks needed. Task #468 IS the follow-up task. Sibling #469 (researcher expansion) depends on #468 and remains at ideation.
