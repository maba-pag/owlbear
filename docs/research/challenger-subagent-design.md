# Challenger Subagent — Adversarial In-Process Review Design

> **Owning task:** #465 — Challenger subagent — adversarial in-process review for architect decisions
> **Date:** 2026-03-31 **Status:** Complete

## 1. Context and Question

Pipeline agents make high-stakes decisions in isolation. The architect's APPROVE verdict cascades to builder, reviewer, auditor — bad AC is the most expensive failure mode. The reviewer catches code quality issues post-hoc but cannot challenge the reasoning behind architectural decisions. The closed #681 evaluator was post-hoc at orchestrator level; the Challenger operates **in-process** before the decision is committed.

**Core question:** How should an adversarial challenge subagent be designed for in-process pre-decision review, starting with the architect agent?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | VS Code Subagents Guide | https://code.visualstudio.com/docs/copilot/agents/subagents | .95 — nesting, assign mode, coordinator/worker, multi-perspective review |
| S2 | VS Code Custom Agents docs | https://code.visualstudio.com/docs/copilot/customization/custom-agents | .90 — disable-model-invocation override via agents array, tool modes |
| S3 | Du et al. — Improving Factuality through Multiagent Debate (2023) | https://arxiv.org/abs/2305.14325 | .85 — debate improves factuality and reasoning across tasks |
| S4 | Liang et al. — MAD: Multi-Agent Debate (EMNLP 2024) | https://arxiv.org/abs/2305.19118 | .85 — DoT problem in self-reflection; external challenge needed |
| S5 | Chan et al. — ChatEval multi-agent debate (2023) | https://arxiv.org/abs/2308.07201 | .80 — multi-annotator collaboration outperforms single-agent eval |
| S6 | OwlBear #228 subagent nesting research | docs/research/subagent-nesting-architecture.md | .95 — L2 confirmed, assign mode, parallel execution |
| S7 | OwlBear code-reader.agent.md | agents/code-reader.agent.md | .90 — precedent: read-only adversarial subagent with structured I/O |
| S8 | OwlBear #681 evaluator final disposition | docs/research/evaluator-agent-final-disposition.md | .85 — post-hoc evaluator rejected; in-process challenge is distinct |

## 3. Analysis

### 3a. Why not self-reflection?

Liang et al. (S4) identify "Degeneration-of-Thought" (DoT): once an LLM commits to a position, self-reflection cannot generate novel counter-arguments. The architect formulates its verdict during Step 3 (evaluate) — by that point, confirmation bias is locked in. External adversarial challenge breaks this pattern (S3, S4). The closed evaluator (#681, S8) was post-hoc — it assessed results after commitment. The Challenger intervenes pre-commitment.

### 3b. Interaction model comparison

| Model | Rounds | Fit for VS Code | Complexity | Quality |
|-------|--------|-----------------|------------|---------|
| Multi-round debate (S3, S4) | 3-5 | No — subagents return once | High | Highest |
| One-shot challenge | 1 | Yes — natural subagent fit | Low | High (.85) |
| Judge-moderated (S5) | 2-3 | No — requires orchestration | High | High |

**Recommendation: One-shot challenge** (.90 confidence). VS Code subagents are synchronous and return once (S1). Multi-round debate requires a wrapper loop outside the subagent model. One-shot is the KISS approach. Du et al. (S3) show even single-round debate improves factuality significantly over self-reflection.

### 3c. Agent design

| Dimension | Decision | Confidence | Rationale |
|-----------|----------|------------|-----------|
| Tool mode | Assign | .90 | Read-only — code-reader precedent (S7); prevents scope creep |
| Model | `Claude Opus 4.6 (copilot)` | .80 | Challenger must match consuming agent's capability for adversarial quality |
| user-invocable | false | .95 | Subagent only, not user-facing (S2) |
| disable-model-invocation | true | .90 | Only accessible via parent's agents array override (S2) |

**Tools (assign mode, 5 tools):**

| Tool | Purpose |
|------|---------|
| `read/readFile` | Read source code, research docs, task files to verify claims |
| `read/viewImage` | View architecture diagrams if referenced |
| `read/problems` | Check for existing lint/compile errors |
| `search` | Find codebase patterns the architect may have missed |
| `vscode/memory` | Access repo conventions and past lessons |

### 3d. I/O contract

**Input (from consuming agent's prompt):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| task_id | string | yes | Kanban task being decided on |
| proposed_verdict | string | yes | APPROVE / REFINE / SPLIT / BLOCK |
| reasoning | string | yes | Why this verdict — the architect's analysis summary |
| ac_lines | string[] | yes | The (possibly refined) AC being approved |
| codebase_evidence | string | yes | Files examined, patterns found, interfaces identified |
| research_doc | string | no | Path to research doc if task references one |

**Output (structured text returned to consuming agent):**

| Section | Content |
|---------|---------|
| Challenges | Array of {category, description, severity: critical/moderate/minor} |
| Blind Spots | Considerations the reasoning didn't address |
| Alternative Angles | Different architectural approaches worth considering |
| Risk Assessment | Risks the proposed decision introduces; overall: low/medium/high |
| Confidence in Original | Float (.0–1.0) — how sound the original reasoning is |
| Recommendation | `proceed` / `reconsider` / `block` |

### 3e. Trigger points in arch-review

| Trigger Point | Mandatory? | Rationale |
|---------------|------------|-----------|
| Before APPROVE (Step 3→4) | Yes | Highest stakes — wrong approvals cascade to 4+ downstream agents |
| Before REFINE (AC rewrite) | No (opt-in) | Medium stakes — refined AC may introduce issues |
| Before SPLIT/BLOCK | No | Low stakes — these don't send work to downstream agents |

**Integration:** Insert Step 3.5 in arch-review skill: architect formulates proposed verdict + reasoning, dispatches Challenger via `runSubagent`, reads response, may revise before committing in Step 4.

### 3f. Architect integration protocol

After receiving the Challenger's report:

1. **If `proceed` + confidence ≥ .80:** Continue with APPROVE. Note challenge results in Architecture Review body.
2. **If `reconsider` or confidence < .80:** Re-evaluate. May revise AC, change verdict, or justify why original is correct with rebuttal.
3. **If `block`:** Strong signal to move task back to ideation. Architect must provide explicit rebuttal if overriding.

The architect always has final authority — the Challenger advises, never decides.

### 3g. Model selection analysis

| Option | Cost | Adversarial Quality | Risk |
|--------|------|---------------------|------|
| Same as consumer (Opus 4.6) | High (~2x architect cost) | Highest | None |
| Lighter (Sonnet 4.6) | Low | Moderate | May miss subtle architectural issues |
| Model array (try lighter) | Medium | Varies | Inconsistent challenge quality |

**Recommendation: Opus 4.6** (.80 confidence). The Challenger must be at least as capable as the consuming agent to find blind spots. A weaker model gives false confidence — worse than no challenge. Cost is bounded (one-shot, not multi-round). For expansion to lower-stakes agents (test-writer, writer), a lighter model is appropriate.

### 3h. Expansion path assessment

| Agent | Gate | Stakes | Challenge Value | Priority |
|-------|------|--------|-----------------|----------|
| Architect | APPROVE | Highest — cascades to 4+ agents | High — prevents bad AC | **Phase 1** |
| Researcher | DONE (recommendation) | High — wrong research misdirects all downstream | Medium — evidence-based, less judgment | Phase 2 |
| Test-writer | Tests finalized | Medium — weak tests reduce reviewer effectiveness | Medium — "did you test the right things?" | Phase 2 |
| Writer | Docs finalized | Low — docs are least costly to fix | Low — not worth the cost | Skip |

### 3i. Differentiation from existing agents

| Concern | Reviewer | Code-reader | Challenger |
|---------|----------|-------------|------------|
| When | Post-implementation | Post-implementation | Pre-decision |
| What | Code quality, tests, security | Code analysis for reviewer | Reasoning quality, blind spots |
| Target | Builder's code | Builder's code + tests | Agent's proposed decision |
| Adversarial focus | "Is the code correct?" | "What did the code miss?" | "Is the reasoning sound?" |

## 4. Recommendation (.85 confidence)

Implement the Challenger as a one-shot, read-only, assign-mode subagent using Opus 4.6. Mandatory before APPROVE verdicts in the arch-review workflow (Step 3.5). Start with architect-only; expand to researcher and test-writer after the pattern proves itself.

**Risks:** (1) Cost — one additional Opus call per architect APPROVE (~30% of architect tasks reach APPROVE). (2) False challenges — Challenger may raise objections that are already addressed, wasting architect time. Mitigation: structured input includes codebase_evidence to ground challenges. (3) Circular reasoning — same model challenging itself is weaker than different models. Mitigation: adversarial persona + code-grounded verification breaks the self-agreement pattern.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Create challenger.agent.md (adversarial pre-decision review subagent)" --priority needed --status ideation --tags "scope:agents,phase-2" --body "Implement the Challenger agent per docs/research/challenger-subagent-design.md S3c-d.\n\nAC:\n- [ ] challenger.agent.md exists with assign-mode tools (readFile, viewImage, problems, search, memory)\n- [ ] Model: Claude Opus 4.6 (copilot), user-invocable: false, disable-model-invocation: true\n- [ ] Adversarial persona: structured devil's advocate, not validation\n- [ ] I/O contract matches research doc S3d (input: 6 fields, output: 6 sections)\n- [ ] Confidence scoring in output (.0-1.0)\n- [ ] Recommendation: proceed/reconsider/block\n- [ ] agents: [] (leaf subagent, no further nesting)"
kanban\kanban-md.exe create "Integrate Challenger into arch-review workflow (Step 3.5)" --priority needed --status ideation --tags "scope:agents,phase-2" --body "Wire Challenger invocation into the architect's arch-review skill per docs/research/challenger-subagent-design.md S3e-f.\n\nAC:\n- [ ] architect.agent.md frontmatter agents: changed from [] to [challenger]\n- [ ] arch-review SKILL.md has new Step 3.5: Challenge proposed verdict\n- [ ] Step 3.5 is mandatory for APPROVE verdicts, optional for REFINE\n- [ ] Integration protocol: proceed (confidence>=.80) / reconsider (<.80) / block in body\n- [ ] Architecture Review body section includes 'Challenge Results' subsection\n- [ ] Architect retains final authority — Challenger advises, never decides\n- [ ] Sequential fallback: if Challenger subagent errors, architect proceeds without challenge and notes fallback in body\nDepends on: challenger.agent.md task"
kanban\kanban-md.exe create "Expand Challenger to researcher agent (Phase 2)" --priority important --status ideation --tags "scope:agents,phase-2" --body "Extend Challenger invocation to the researcher agent per docs/research/challenger-subagent-design.md S3h.\n\nAC:\n- [ ] researcher.agent.md frontmatter agents: includes challenger\n- [ ] research-workflow SKILL.md has challenge step before finalizing recommendation\n- [ ] Mandatory before DONE signal for tasks with recommendations\n- [ ] Challenge input includes: proposed recommendation, evidence summary, confidence score\n- [ ] Researcher integrates challenge before writing final research doc section 4\n\nDepends on: challenger.agent.md task and arch-review integration task"
```
