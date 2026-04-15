# ideation-security Agent Design

> **Owning task:** #650 — P4-10: Create ideation-security.agent.md
> **Date:** 2026-04-06 **Status:** Complete

## 1. Context and Question

Task #650 creates the `ideation-security.agent.md` domain opinion subagent. It must follow the Voice Reasoning Cycle from the thinking companion spec (§7, §12): read context, form opinion from security lens, run embedded Critic loop (≤5 cycles), publish hardened position + debate log. The ideation-architect research (#647) established the reusable template for all domain opinions — this task instantiates it for the security domain.

**Questions investigated:**
1. Does the ideation-architect template apply directly, or does security need adaptations?
2. What persona traits distinguish the Security Mind from other voices?
3. Are the tool set and structural pattern identical to ideation-architect?
4. What AC refinements does the architect gate need?

## 2. Sources Studied

| # | Source | Relevance | What |
|---|--------|-----------|------|
| 1 | thinking-companion-framework.md §7, §12 | .95 | Ideation panel architecture, Security Mind role, activation logic, read/write table |
| 2 | .owlbear/research/ideation-architect-agent.md | .95 | Template pattern: tool set, structure, frontmatter, AC refinements |
| 3 | share/agents/ideation-critic.agent.md (#644) | .90 | Structural reference: 69-line voice subagent, sections, frontmatter |
| 4 | share/agents/ideator.agent.md (#645) | .85 | Invoking agent — confirms ideation-security in agents list, invocation contract |
| 5 | h-agent-structure SKILL | .80 | Structural standards: T4 tier, required sections, forbidden content |
| 6 | Task #647 body (ideation-architect research) | .80 | AC refinements pattern: disable-model-invocation, exact tool set, argument-hint |

## 3. Analysis

### 3.1 Template Reuse Assessment

| Aspect | ideation-architect | ideation-security | Identical? |
|--------|----------------|---------------|------------|
| Frontmatter fields | 8 fields (name, description, argument-hint, user-invocable, disable-model-invocation, model, tools, agents) | Same 8 fields | Yes |
| Tool set | 8 tools (edit/create*, read/*, search, vscode/memory, agent) | Same 8 tools | Yes |
| Agents list | [ideation-critic] | [ideation-critic] | Yes |
| Model | Claude Opus 4.6 (copilot) | Claude Opus 4.6 (copilot) | Yes |
| Tier | T4 (Tools) | T4 (Tools) | Yes |
| Sections | persona, critical_rules, Voice Reasoning Cycle, Input/Output Contract | Same sections | Yes |
| Persona domain | System design, structure, patterns | Access control, data safety, trust boundaries, compliance | No |
| Output files | opinions/architect.md, opinions/architect-debate.md | opinions/security.md, opinions/security-debate.md | No |

Delta from template: persona text + 2 file path strings. Everything else is identical.

### 3.2 Persona Differentiation

From spec §7, the Security Mind's domain and example opinion:

| Voice | Domain | Example Opinion |
|-------|--------|-----------------|
| Architect | System design, structure, patterns, integration | "Separate what changes from what doesn't. This coupling will hurt you." |
| Security Mind | Access control, data safety, trust boundaries | "Who sees this data when it fails? What's the blast radius?" |

The security persona should encode: OWASP awareness, trust boundary analysis, data flow scrutiny, blast radius thinking, defense-in-depth, least-privilege advocacy. It should NOT perform code-level security scanning (that's a build/review concern) — it provides security perspective during ideation-stage problem framing.

### 3.3 Activation Context (Mediator-controlled, not voice-internal)

| Problem Signal | Security Mind Activated? |
|----------------|------------------------|
| Sensitive data / multi-user / networked | Yes (primary trigger) |
| High investment tier (Shared/Production) | Yes (added to any combination) |
| Data processing / ETL | Only if sensitive data |
| Automation / scripting | Only if networked/external |

This logic lives in the ideator (Mediator), not in ideation-security. The voice is passive — invoked when the Mediator decides security perspective is relevant.

## 4. Recommendation (confidence: 0.88)

Build `share/agents/ideation-security.agent.md` as a ~65-75 line agent file using the ideation-architect template with security-domain adaptations:

- **T4 tier**, `user-invocable: false`, `disable-model-invocation: true`
- **Model:** Claude Opus 4.6 (copilot) — per spec §12
- **Tools:** 8 tools — `[edit/createDirectory, edit/createFile, edit/editFiles, read/readFile, read/viewImage, search, vscode/memory, agent]`
- **Agents:** `[ideation-critic]`
- **Persona:** OWASP-aware security perspective — access control, data safety, trust boundaries, blast radius, defense-in-depth, least privilege. Opinionated, not neutral.
- **Output files:** `opinions/security.md` (final position), `opinions/security-debate.md` (Critic dialogue log)

### AC Refinements for Architect Gate

1. **New AC:** `disable-model-invocation: true` set (standard for T4 subagent-only agents; precedent: ideation-critic #644, ideation-architect #647)
2. **New AC:** Tool set exactly 8: `[edit/createDirectory, edit/createFile, edit/editFiles, read/readFile, read/viewImage, search, vscode/memory, agent]`
3. **New AC:** `argument-hint` field present describing security analysis invocation context

**Challenge:** FALLBACK — challenger agent not in available agent roster. Self-challenge performed:
- (a) OWASP depth: prompt-based reasoning is appropriate for ideation stage, not code-level scanning — **accepted**
- (b) Same 8 tools as ideation-architect: sufficient; voice reads context + research-notes, forms opinions — **accepted**
- (c) Activation logic: Mediator's responsibility, not voice-internal — **accepted**
- (d) File path naming: `opinions/security.md` (not `ideation-security.md`) per spec §12 — **accepted**
- Confidence in original: 0.88

**Tier: T1** — agent file creation following established voice pattern. No new capability.

## 5. Follow-up Tasks

None required. Task #650 is itself the build task. Board has full coverage (#647-#652).
