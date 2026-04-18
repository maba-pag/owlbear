# ideation-architect Agent Design

> **Owning task:** #647 — P4-07: Create ideation-architect.agent.md
> **Date:** 2026-04-06 **Status:** Complete

## 1. Context and Question

Task #647 creates the first domain opinion subagent (`ideation-architect.agent.md`). It must follow the Voice Reasoning Cycle from the thinking companion spec (§7, §12): read context, form opinion from architectural lens, run embedded Critic loop (≤5 cycles), publish hardened position + debate log. Key constraint: this is the template for ideation-data, ideation-enduser, and ideation-security — structure must be clean and generalizable.

**Questions investigated:**
1. What tool set does a domain opinion need?
2. What structural pattern fits (file sections, frontmatter)?
3. How does naming coexist with the pipeline `architect.agent.md`?
4. What AC refinements does the architect gate need?

## 2. Sources Studied

| # | Source | Relevance | What |
|---|--------|-----------|------|
| 1 | thinking-companion-framework.md §7, §12 | .95 | Ideation panel architecture, Voice Reasoning Cycle, multi-model assignment, read/write table |
| 2 | share/agents/ideation-critic.agent.md (#644) | .95 | First voice subagent built, structural pattern, dual-scope, read-only tools |
| 3 | share/agents/ideator.agent.md (#645) | .90 | Invoking agent — defines how domain opinions are called, agents list, tool set |
| 4 | h-agent-structure SKILL | .85 | Structural standards: tiers, frontmatter, required sections, forbidden content |
| 5 | share/agents/challenger.agent.md | .80 | Structural template for adversarial subagent — persona, critical_rules, I/O contract |
| 6 | share/agents/architect.agent.md | .70 | Pipeline architect — confirms naming coexistence (different name, tier, role) |

## 3. Analysis

### 3.1 Tool Set Comparison

| Tool | ideation-critic | Ideator | ideation-architect (rec) | Rationale |
|------|-------------|---------|----------------------|-----------|
| edit/createDirectory | — | Yes | Yes | Create opinions/ dir |
| edit/createFile | — | Yes | Yes | Write position + debate files |
| edit/editFiles | — | Yes | Yes | Update debate log during Critic loop |
| read/readFile | Yes | Yes | Yes | Read context.md, decisions.md, research-notes.md |
| read/viewImage | Yes | Yes | Yes | Input materials may include diagrams |
| search | Yes | Yes | Yes | Verify codebase claims from research-notes |
| vscode/memory | Yes | Yes | Yes | Standard memory access |
| agent | — | Yes | Yes | Invoke ideation-critic subagent |
| read/problems | Yes | — | No | Opinion-forming, not code diagnostics |
| owlbear-kanban/* | — | Yes | No | Not a pipeline agent |
| owlbear-project/* | — | Yes | No | Reads only Working Dir |
| owlbear-knowledge/* | — | Yes | No | Not doing research |
| owlbear-memory/* | — | Yes | No | KISS — not needed for voice deliberation |

**Recommended set (8 tools):** `[edit/createDirectory, edit/createFile, edit/editFiles, read/readFile, read/viewImage, search, vscode/memory, agent]`

Rationale: Read tools mirror ideation-critic (minus `read/problems` — not needed). Write tools added for file output. `agent` added for Critic loop. No MCP tools — domain opinions operate only within the Working Dir + codebase read.

### 3.2 Structural Pattern (Options)

| Option | Description | Est. Lines | Score |
|--------|-------------|-----------|-------|
| A. Mirror ideation-critic closely | Same sections: persona, critical_rules, Input/Output Contract | ~65-75 | .85 |
| B. Hybrid: critic + challenger sections | Add examples section and boundaries from challenger pattern | ~80-90 | .75 |
| C. Minimal: frontmatter + persona + rules only | Drop formal I/O contract, embed cycle in rules | ~45-55 | .65 |

**Recommendation: Option A (.85)** — Mirror ideation-critic with domain-specific adaptations. The Input Contract, Output Contract, and Voice Reasoning Cycle sections provide clear structure that future domain opinions can replicate by changing only the persona and domain.

Sections: persona (strong architectural opinions), critical_rules (5 rules), Voice Reasoning Cycle (Critic loop protocol), Input Contract (table), Output Contract (file outputs).

### 3.3 Naming Coexistence

| Agent | File | Name | Tier | Role |
|-------|------|------|------|------|
| Pipeline Architect | architect.agent.md | architect | T2 Pipeline | AC review, backlog gate |
| ideation-architect | ideation-architect.agent.md | ideation-architect | T4 Tools | Ideation domain opinion |

No conflict: different files, different names, different tiers, different dispatch chains. Pipeline architect is invoked by orchestrator; ideation-architect is invoked by ideator. They never interact.

### 3.4 Frontmatter Decisions

| Field | Value | Source |
|-------|-------|--------|
| name | ideation-architect | AC, distinct from pipeline `architect` |
| user-invocable | false | AC spec |
| disable-model-invocation | true | Standard for subagent-only T4 agents (ideation-critic pattern) |
| model | Claude Opus 4.7 (copilot) | AC + spec §12 |
| tools | 8-tool set (§3.1 above) | Derived from spec §12 read/write table |
| agents | [ideation-critic] | AC + spec §12 Voice Reasoning Cycle |
| argument-hint | "Architect: {problem and outcome context for architectural analysis}" | h-agent-structure standard |

## 4. Recommendation (confidence: 0.88)

Build `share/agents/ideation-architect.agent.md` as a ~65-75 line agent file following Option A (mirror ideation-critic pattern with domain-specific adaptations):

- **T4 tier**, `user-invocable: false`, `disable-model-invocation: true`
- **Model:** Claude Opus 4.7 (copilot) — per spec §12 multi-model assignment
- **Tools:** 8 tools — file read/write for Working Dir, search for codebase, agent for Critic loop
- **Agents:** `[ideation-critic]` — sole subagent
- **Persona:** Strong architectural opinions — system design, structure, patterns, component integration. Not neutral; opinionated from experience.
- **Body:** Voice Reasoning Cycle with embedded Critic loop (≤5 cycles), Input Contract (context.md, decisions.md, research-notes.md), Output Contract (opinions/architect.md, opinions/architect-debate.md)
- **Template role:** Structure must be cleanly replicable for ideation-data, ideation-enduser, ideation-security (change persona + domain + file paths)

### AC Refinements for Architect Gate

1. **New AC:** `disable-model-invocation: true` set (standard for subagent-only agents; precedent: ideation-critic #644)
2. **New AC:** Tool set exactly 8: `[edit/createDirectory, edit/createFile, edit/editFiles, read/readFile, read/viewImage, search, vscode/memory, agent]`
3. **New AC:** `argument-hint` field present describing architectural analysis invocation context
4. **AC clarification:** `agents: [ideation-critic]` — sole subagent, not empty list

Challenge: FALLBACK — challenger agent not in available agent roster. Self-challenge: tool set breadth (8 vs critic's 5) justified by file-write requirement; no `read/problems` justified by opinion-forming vs diagnostics role; template generalizability validated against spec §7 voice table (all 4 domain opinions share same tool needs).

## 5. Follow-up Tasks

None required — task #647 is itself the build task. Board has full coverage: #648-650 (other domain opinions), #651-652 (workflow/handbook skills).
