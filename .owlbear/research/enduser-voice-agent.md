# End-User Voice Agent Design

> **Owning task:** #649 — P4-09: Create enduser-voice.agent.md
> **Date:** 2026-04-06 **Status:** Complete

## 1. Context and Question

Task #649 creates the end-user domain voice subagent (`enduser-voice.agent.md`). Per the spec (§7), this voice focuses on human experience, usability, clarity, and discoverability. It follows the Voice Reasoning Cycle from §12: read context, form opinion from end-user lens, run embedded Critic loop (≤5 cycles), publish hardened position + debate log.

**Questions investigated:**
1. What tool set does this domain voice need?
2. What structural pattern to follow?
3. What persona domain should the end-user voice embody?
4. What AC refinements does the architect gate need?

## 2. Sources Studied

| # | Source | Relevance | What |
|---|--------|-----------|------|
| 1 | thinking-companion-framework.md §7, §12 | .95 | Voice panel architecture, Voice Reasoning Cycle, end-user domain description, read/write table |
| 2 | share/agents/critic-voice.agent.md (#644) | .95 | First voice subagent, structural template, read-only tool set, dual-scope |
| 3 | .owlbear/research/architect-voice-agent.md (#647) | .95 | Domain voice research template — tool set analysis, structural pattern, AC refinements |
| 4 | share/agents/ideator.agent.md (#645) | .90 | Invoking agent — confirms enduser-voice in agents list, parallel invocation pattern |
| 5 | h-agent-structure SKILL | .85 | Tier classification, frontmatter standards, required sections |

## 3. Analysis

### 3.1 Tool Set

Identical to architect-voice recommendation (§3.1 of architect-voice research). Domain voices share the same tool set — differentiation is in persona, not capabilities.

**8 tools:** `[edit/createDirectory, edit/createFile, edit/editFiles, read/readFile, read/viewImage, search, vscode/memory, agent]`

| Tool | Purpose for enduser-voice |
|------|--------------------------|
| edit/createDirectory | Create `voices/` dir if absent |
| edit/createFile | Write `voices/enduser.md` + `voices/enduser-debate.md` |
| edit/editFiles | Append to debate log during Critic loop |
| read/readFile | Read `context.md`, `decisions.md`, optionally `research-notes.md` |
| read/viewImage | Input materials may include UI mockups/screenshots |
| search | Verify codebase patterns referenced in context |
| vscode/memory | Standard memory access |
| agent | Invoke `critic-voice` subagent for embedded Critic loop |

### 3.2 Structural Pattern

Follow Option A from architect-voice research: mirror critic-voice structure with domain-specific adaptations.

| Section | Content (enduser-voice) |
|---------|------------------------|
| Persona | UX practitioner: usability, clarity, discoverability, approachability. Opinionated on human experience. |
| Critical rules | 5 rules: voice reasoning cycle, Critic loop protocol, file output discipline, Working Dir boundaries, domain scope |
| Voice Reasoning Cycle | Embedded Critic loop (≤5 cycles), same as architect-voice |
| Input Contract | Table: `context.md`, `decisions.md`, optionally `research-notes.md` |
| Output Contract | `voices/enduser.md` (final position), `voices/enduser-debate.md` (Critic dialogue log) |

Estimated size: ~65-75 lines (matching architect-voice).

### 3.3 Domain Scope

Per spec §7:
- **Domain:** Human experience, usability, clarity, discoverability
- **Activated for:** Any tool that humans interact with
- **Example opinion:** "If the user can't tell what happened at a glance, the whole system failed."

Persona should embody a UX practitioner mindset — someone who thinks in terms of user flows, error states from the human's perspective, feedback clarity, and cognitive load. Not neutral; opinionated from experience with real users.

### 3.4 Frontmatter Decisions

| Field | Value | Rationale |
|-------|-------|-----------|
| name | enduser-voice | AC line, matches ideator agents list |
| description | Domain voice: human experience, usability, clarity, discoverability | Spec §7 |
| user-invocable | false | AC line |
| disable-model-invocation | true | Standard for subagent-only T4 agents |
| model | Claude Opus 4.6 (copilot) | AC + spec §12 multi-model assignment |
| tools | 8-tool set (§3.1) | Derived from spec §12 read/write table, matches architect-voice |
| agents | [critic-voice] | AC + spec §12 Voice Reasoning Cycle |
| argument-hint | "End-User: {problem and outcome context for usability and user-experience analysis}" | h-agent-structure standard |

### 3.5 Comparison: Domain Voice Agents

| Aspect | Critic-voice | Architect-voice (research) | Enduser-voice (rec) |
|--------|-------------|---------------------------|---------------------|
| Tier | T4 | T4 | T4 |
| Model | GPT-5.4 | Claude Opus 4.6 | Claude Opus 4.6 |
| Tools | 5 (read-only) | 8 (read+write+agent) | 8 (read+write+agent) |
| Agents | [] | [critic-voice] | [critic-voice] |
| Writes files | No | Yes (voices/) | Yes (voices/) |
| Critic loop | N/A (is the Critic) | Embedded ≤5 cycles | Embedded ≤5 cycles |
| Domain | Adversarial challenge | System design, patterns | Usability, clarity, UX |

## 4. Recommendation (confidence: 0.90)

Build `share/agents/enduser-voice.agent.md` as a ~65-75 line agent file following the domain voice pattern established by architect-voice research:

- **T4 tier**, `user-invocable: false`, `disable-model-invocation: true`
- **Model:** Claude Opus 4.6 (copilot) — per spec §12
- **Tools:** 8 tools — file read/write for Working Dir, search for codebase, agent for Critic loop
- **Agents:** `[critic-voice]`
- **Persona:** Opinionated UX practitioner — usability, clarity, discoverability, approachability. Thinks in user flows, cognitive load, error states from the human's perspective, feedback quality.
- **Body:** Voice Reasoning Cycle with embedded Critic loop (≤5 cycles), Input/Output Contract
- **Output files:** `voices/enduser.md`, `voices/enduser-debate.md`

Challenge: FALLBACK — challenger agent not in available agent roster. Confidence in original: 0.90.

Self-challenges considered:
- (a) _Tool set identical to architect-voice_ — intentional: domain differentiation is in persona, not tools. All domain voices share the same capability set per spec §12.
- (b) _No unique structural innovation_ — correct: this is a template replication task. Innovation belongs in the spec, not in each voice file.
- (c) _Dependency on #647 architect-voice not built yet_ — not blocking: we follow the researched pattern, not the built artifact. #649 depends on #644 and #645, both satisfied.

### AC Refinements for Architect Gate

1. **New AC:** `disable-model-invocation: true` set (standard for subagent-only T4, precedent: #644)
2. **New AC:** Tool set exactly 8: `[edit/createDirectory, edit/createFile, edit/editFiles, read/readFile, read/viewImage, search, vscode/memory, agent]`
3. **New AC:** `argument-hint` field present describing end-user analysis invocation context
4. **New AC:** Voice Reasoning Cycle section with embedded Critic loop (≤5 cycles)

## 5. Follow-up Tasks

No follow-up tasks needed. Task #649 is itself the build task; the existing board (#646-#652) covers the full voice panel implementation.
