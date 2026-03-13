# Instruction File Token Audit

> **Owning task:** #686 — Instruction file audit: measure and reduce token bloat
> **Date:** 2026-03-08 **Status:** Complete

## 1. Context and Question

Instruction files grow monotonically — each incident adds rules, never removes them. More text means the LLM is more likely to miss critical rules (Liu et al. 2023; Li et al. 2024). What is the actual token load per agent, where is the bloat, and what can be cut?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| Liu et al. "Lost in the Middle" (2023) | arxiv.org/abs/2307.03172 | .90 — proves performance degrades with context length, especially for mid-positioned info |
| Li et al. "Long-context LLMs Struggle" (2024) | arxiv.org/abs/2404.02060 | .85 — shows classification accuracy drops as in-context examples grow |
| Anthropic prompt engineering docs | platform.claude.com/docs/en/docs/build-with-claude/prompt-engineering | .80 — recommends conciseness, placing key info at start/end, queries at end boost quality 30% |
| OpenAI prompt engineering docs | developers.openai.com/api/docs/guides/prompt-engineering | .75 — recommends clear sections, minimal context, prompt caching for repeated prefixes |

**Key findings from sources:** (1) Performance degrades with context length even in "long-context" models. (2) Information in the middle of long contexts is systematically ignored. (3) Both vendors recommend concise, structured prompts over verbose ones.

## 3. Measurements

### 3a. Individual File Sizes

| File | Chars | ~Tokens |
|------|------:|--------:|
| copilot-instructions.md | 73,396 | 18,349 |
| orchestrator.agent.md | 14,625 | 3,656 |
| reviewer.agent.md | 10,204 | 2,551 |
| architect.agent.md | 10,075 | 2,519 |
| kanban-planner.agent.md | 8,082 | 2,020 |
| writer.agent.md | 7,695 | 1,924 |
| researcher.agent.md | 7,404 | 1,851 |
| builder.agent.md | 6,922 | 1,730 |
| curator.agent.md | 6,454 | 1,614 |
| auditor.agent.md | 5,781 | 1,445 |
| agent-common.instructions.md | 7,997 | 1,999 |
| architecture.instructions.md | 4,147 | 1,037 |
| terminal.instructions.md | 3,113 | 778 |
| research-docs.instructions.md | 1,872 | 468 |
| python.instructions.md | 1,727 | 432 |
| frontend.instructions.md | 3,104 | 776 |
| kanban-md SKILL.md | 15,544 | 3,886 |
| code-review SKILL.md | 7,341 | 1,835 |
| project-definition SKILL.md | 5,802 | 1,450 |
| kanban-based-dev SKILL.md | 4,368 | 1,092 |
| tdd-workflow SKILL.md | 3,752 | 938 |
| task-verification SKILL.md | 2,497 | 624 |
| docs-gate SKILL.md | 2,488 | 622 |

### 3b. copilot-instructions.md Section Breakdown

| Section | ~Tokens | % of file |
|---------|--------:|----------:|
| **Tech stack TABLE** | **12,393** | **67.5%** |
| Kanban lifecycle (board/roles/research/tags) | 2,437 | 13.3% |
| Principles + Process habits | 908 | 4.9% |
| Inventories (agent/skill/instruction/prompt) | 1,486 | 8.1% |
| Dir structure + File placement | 495 | 2.7% |
| Confidence + Workflow steps | 245 | 1.3% |
| Attribution + Formatting rules | 375 | 2.0% |

**The tech stack table is 12,393 tokens — 67.5% of the file.** It has become an implementation changelog, with paragraph-length Notes cells documenting every config field, class name, and design pattern. This is architecture documentation masquerading as a quick-reference table.

### 3c. Per-Agent Context Chain (128K window)

Auto-loaded = copilot-instructions.md + agent.md + agent-common + terminal + file-pattern instructions.
Must-read = skills the agent's workflow explicitly requires reading.

| Agent | Auto-loaded | Must-read skills | Total | % of 128K |
|-------|------------:|:-----------------|------:|----------:|
| Reviewer | 25,146 | code-review (1,835) | **26,981** | **21.1%** |
| Orchestrator | 24,782 | — | **24,782** | **19.4%** |
| Architect | 25,114 | — | **25,114** | **19.6%** |
| Builder | 24,325 | tdd-workflow (938) | **25,263** | **19.7%** |
| Writer | 23,950 | docs-gate (622) | **24,572** | **19.2%** |
| Auditor | 24,040 | task-verification (624) | **24,664** | **19.3%** |
| Researcher | 23,445 | — | **23,445** | **18.3%** |
| Kanban-planner | 23,146 | — | **23,146** | **18.1%** |
| Curator | 22,740 | — | **22,740** | **17.8%** |

**Top 3:** Reviewer (26,981), Builder (25,263), Architect (25,114).

> **Note (2026-03-08):** agent-common.instructions.md grew from 5,104 to 7,997 chars (+2,893 chars / +723 tokens) due to the self-defense section added in #663. All per-agent totals updated accordingly.

All agents are under the 30% target (38,400 tokens). But **copilot-instructions.md alone is 75-83% of every agent's context**, and 67.5% of that file is the tech stack table — implementation details no agent needs at system prompt time.

## 4. Analysis

### What's bloated and why

| Bloat source | Tokens | Who needs it | Problem |
|-------------|-------:|:-------------|:--------|
| Tech stack Notes column | 12,393 | Nobody at prompt time | Implementation detail changelog. Agents discover API shapes by reading source code, not by memorizing config field names from a table. |
| Kanban lifecycle section | 2,437 | Orchestrator, planner | Duplicates kanban-md skill + kanban-based-development skill + individual agent files which already define their own movement authority. |
| Inventory tables | 1,486 | Nobody | VS Code discovers agents from .agent.md files and skills from SKILL.md files. These tables are stale the moment an agent/skill is added. |
| Research checklist | ~600 | Researcher only | Duplicated in researcher.agent.md workflow and in the mode override pasted by VS Code. |
| Docs gate rule | ~250 | Writer only | Duplicated verbatim in docs-gate SKILL.md. |

### Reduction strategy

| Action | Target | Estimated savings | Risk |
|--------|--------|------------------:|:-----|
| **(a) Compress** tech stack Notes to one-liners | copilot-instructions.md | ~11,000 tokens | Low — detail lives in source code + architecture.instructions.md |
| **(b) Remove** inventory tables | copilot-instructions.md | ~1,486 tokens | Low — VS Code auto-discovers these |
| **(c) Remove** kanban lifecycle duplication | copilot-instructions.md | ~1,500 tokens | Medium — keep 5-line summary, delete rest (exists in skills) |
| **(c) Remove** research checklist from copilot-instructions | copilot-instructions.md | ~600 tokens | Low — authoritative copy is in researcher.agent.md |
| **(c) Remove** docs gate rule from copilot-instructions | copilot-instructions.md | ~250 tokens | Low — authoritative copy is in docs-gate SKILL.md |
| **(b) Remove** Workflow steps section | copilot-instructions.md | ~245 tokens | Low — agents have their own workflows |

**Total estimated savings: ~15,000 tokens (82% of copilot-instructions.md).**

Post-reduction, copilot-instructions.md would be ~3,300 tokens. Every agent's total context would drop to ~8,000-12,000 tokens (~7-9% of 128K window).

## 5. Recommendation (.90 confidence)

The tech stack table compression is the single highest-impact change: **11,000 tokens saved × 9 agents = 99,000 wasted tokens eliminated per orchestration session**. The Notes column should contain only what an agent needs to make a decision — technology name + one-line constraint — not class names and config field defaults.

Risk: a builder working on the daemon module won't see the full architecture of `poll_loop` + `channel_loop` in the system prompt. **This is correct behavior.** They should discover it by reading source code (which they do anyway). The system prompt exists for conventions and constraints, not for code documentation.

## 6. Follow-up Tasks

> **Created 2026-03-08:** All 3 tasks below were executed and are on the board at `backlog` status: #696, #698, #699.

```text
kanban\kanban-md.exe create "Compress copilot-instructions.md tech stack table Notes to one-liners" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --body "- Reduce each Notes cell to: one line stating the key convention or constraint the agent must follow\n- Move implementation details nowhere — they live in source code and docstrings\n- Target: tech stack section under 1,500 tokens (currently 12,393)\n- Keep Component + Technology columns unchanged\n- AC: tech stack section is under 1,500 tokens; no agent behavior changed"

kanban\kanban-md.exe create "Remove inventory tables and duplicated lifecycle sections from copilot-instructions.md" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --body "- Remove Agent inventory table (VS Code discovers agents from .agent.md files)\n- Remove Skill inventory table (VS Code discovers skills from SKILL.md descriptions)\n- Remove Instruction file inventory table (redundant — applyTo patterns handle loading)\n- Remove Prompt file inventory table\n- Remove Research checklist (authoritative in researcher.agent.md)\n- Remove Docs gate rule (authoritative in docs-gate SKILL.md)\n- Remove Workflow steps section (each agent has its own workflow)\n- Compress Kanban lifecycle to 5-line summary pointing to kanban-md and kanban-based-development skills\n- AC: copilot-instructions.md total under 5,000 tokens; no lost rules (each removed rule has authoritative source elsewhere)"

kanban\kanban-md.exe create "Validate agent behavior post-instruction-trim" --priority needed --tags "scope:copilot,agent,phase-agent-arch,test" --depends-on <prev-two-ids> --body "- Run one orchestration cycle (e.g., orchestrate.prompt.md) after the trims\n- Verify: builder still follows TDD, reviewer still runs all checks, writer still does docs-gate\n- Verify: no agent errors about missing context or unknown conventions\n- AC: one full pipeline pass (builder->reviewer->writer) completes without regressions"
```
