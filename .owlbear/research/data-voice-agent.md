# ideation-data Agent Design

> **Owning task:** #648 — P4-08: Create ideation-data.agent.md
> **Date:** 2026-04-06  **Status:** Complete

## 1. Context and Question

Task #648 creates the second domain opinion subagent (`ideation-data.agent.md`) for the Ideator's ideation panel. It follows the ideation-architect template pattern established by #647's research. Domain focus: data quality, validation, schemas, ETL pipeline patterns, data integrity, analytics.

**Key question:** Can ideation-data reuse the ideation-architect structural pattern with only persona/domain/file-path changes, or does the data domain require structural deviations?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `thinking-companion-framework.md` §7, §12 | Internal spec | 1.0 |
| 2 | `.owlbear/research/ideation-architect-agent.md` | Internal research | 0.95 |
| 3 | `share/agents/ideation-critic.agent.md` | Codebase (built) | 0.90 |
| 4 | `share/agents/ideator.agent.md` | Codebase (built) | 0.90 |
| 5 | `share/skills/h-agent-structure/SKILL.md` | Internal standard | 0.80 |
| 6 | `tests/test_grant_vscode_askquestions_to_user_invocable.py` | Codebase (test) | 0.75 |
| 7 | `tests/test_disable_model_invocation.py` | Codebase (test) | 0.70 |

## 3. Analysis

### 3.1 Can ideation-data reuse ideation-architect pattern directly?

| Dimension | ideation-architect | ideation-data | Change needed? |
|-----------|----------------|------------|---------------|
| Frontmatter structure | T4, 8 tools, agents:[ideation-critic] | Identical | No |
| Model | Claude Opus 4.7 (copilot) | Identical | No |
| Voice Reasoning Cycle | Read → opinion → Critic loop → publish | Identical | No |
| Input files | context.md, decisions.md, research-notes.md | Identical | No |
| Output files | opinions/architect.md, opinions/architect-debate.md | opinions/data-person.md, opinions/data-person-debate.md | File paths only |
| Persona | Structural design lens | Data quality/integrity lens | Domain swap |
| Sections | persona, critical_rules, Voice Reasoning Cycle, I/O Contract | Identical structure | No |

**Finding:** Pure template replication. No structural deviation needed. Only 3 elements change: persona text, domain-specific examples, output file names.

### 3.2 Tool Set (inherits from ideation-architect research)

**8 tools:** `[edit/createDirectory, edit/createFile, edit/editFiles, read/readFile, read/viewImage, search, vscode/memory, agent]`

Rationale unchanged from ideation-architect analysis: file read/write for Working Dir, search for codebase verification, agent for Critic loop. No MCP tools (domain opinions operate within Working Dir only).

### 3.3 Frontmatter Decisions

| Field | Value | Source |
|-------|-------|--------|
| name | ideation-data | AC |
| description | Domain opinion — data quality, validation, schemas, ETL, analytics | Spec §7 |
| argument-hint | "Data: {problem and outcome context for data quality analysis}" | h-agent-structure standard |
| user-invocable | false | AC |
| disable-model-invocation | true | ideation-critic + ideation-architect pattern |
| model | Claude Opus 4.7 (copilot) | AC + spec §12 |
| tools | 8-tool set (§3.2) | ideation-architect research §3.1 |
| agents | [ideation-critic] | AC |

### 3.4 Data Domain Persona Characteristics

From spec §7 ("The Data Person"):
- "Schema is the contract. Validate between steps."
- "NaN propagation is your enemy."
- Activated for: data processing, ETL, analytics, reporting

Domain expertise areas to encode in persona:
- Data quality: completeness, consistency, accuracy, timeliness
- Schema design: contracts between systems, validation boundaries
- ETL patterns: extract-transform-load, pipeline reliability, idempotency
- Data integrity: referential integrity, constraint enforcement, error propagation
- Analytics: aggregation correctness, statistical validity, reporting accuracy

### 3.5 File Output Naming

Spec §12 Working Directory structure specifies:

```
opinions/
  data-person.md          ← Data Person final position
  data-person-debate.md   ← Data Person ↔ Critic debate log
```

AC matches spec: `opinions/data-person.md` and `opinions/data-person-debate.md`.

### 3.6 Cross-Cutting Test Constraints

| Test | Impact | Status |
|------|--------|--------|
| `test_grant_vscode_askquestions_to_user_invocable.py` | Glob on ALL `*.agent.md` — must NOT have vscode/askQuestions | Not in proposed tool set ✓ |
| `test_disable_model_invocation.py` | Lists 8 specific pipeline agents — ideation-data NOT in list | No conflict ✓ |

### 3.7 Estimated File Size

~65-75 lines (same as ideation-architect estimate). Sections: frontmatter (~12), persona (~12), critical_rules (~8), Voice Reasoning Cycle (~15), Input/Output Contract (~15), boundaries/examples (~8).

### 3.8 Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| ideation-architect not yet built when ideation-data is built | Low | Research pattern is sufficiently detailed; both can be built independently from the same template |
| Persona too generic (not domain-specific enough) | Low | Use spec §7 quotes + data engineering domain knowledge in persona text |
| Tool set drift from ideation-architect | Negligible | Both derive from same source (spec §12 read/write table) |

## 4. Recommendation

**Replicate ideation-architect template with data domain adaptations** (confidence: 0.90)

Higher confidence than ideation-architect (.88) because:
- Template pattern is now established and validated by two prior voice agent researches (#644, #647)
- No structural decisions to make — purely a domain adaptation
- Spec is unambiguous on this agent's role and I/O

Implementation: ~65-75 line agent file. Persona encodes strong data quality/integrity opinions. Voice Reasoning Cycle with embedded Critic loop (≤5 cycles). Output to `opinions/data-person.md` and `opinions/data-person-debate.md`.

Challenge: FALLBACK — challenger agent not applicable for ideation-scope research. Self-challenge:
- (a) Does data domain need different tools? No — same Working Dir pattern, same codebase read needs.
- (b) Should persona be narrower (e.g., only ETL)? No — spec §7 defines broad data domain.
- (c) Is #647 dependency satisfied? #647 is in backlog (research done). Pattern is documented — ideation-data can be built without waiting for ideation-architect file to exist.

### AC Refinements (binding on #648)

| # | Issue | Refinement |
|---|-------|-----------|
| 1 | Missing `disable-model-invocation` | Add: `disable-model-invocation: true` |
| 2 | Missing exact tool set | Add: 8 tools `[edit/createDirectory, edit/createFile, edit/editFiles, read/readFile, read/viewImage, search, vscode/memory, agent]` |
| 3 | Missing `argument-hint` | Add: `argument-hint: "Data: {problem and outcome context for data quality analysis}"` |
| 4 | "Agents list includes ideation-critic" underspecified | Clarify: `agents: [ideation-critic]` — sole subagent, not just "includes" |

## 5. Follow-up Tasks

None required — task #648 is itself the build task. Board has full coverage (#649-652 for remaining voices and skills). Tier: T1 (agent file creation following established pattern).
