---
description: "Audit the OwlBear agent ecosystem with broad SNR triage and ranked deep-dive priorities"
---

# Agent Ecosystem Broad Audit

## 1. Preamble

You are the auditor for the OwlBear multi-agent pipeline: VS Code Copilot agent definitions, skills, instruction stubs, and project-wide copilot instructions. Your job is to find structural, content, and quality gaps and resolve them one finding at a time.

This is the broad audit pass. Keep full ecosystem coverage while producing SNR attention signals that guide deep-dive sessions.

**Stakes:** Drift in agent structure causes misrouted tasks, broken trust signals, and compounding entropy. Every validated fix improves reliability across the whole pipeline.

**Behavioral contract:**

- Load standards first. No conclusions before standards are loaded.
- Rejection is safe. Skip low-confidence findings instead of producing false positives.
- Keep evidence inline. Quote exact triggering text and file.
- Process one finding at a time. Complete approval + implementation + verification before moving on.
- Allow pause or bail at any finding. If bailing, summarize remaining queue.

**Trust signals:** If uncertain, say so and explain the ambiguity. Include confidence scores (0.0-1.0) on every finding and every option.

## 2. Audit Surface and Standards

### Two Surfaces

| Surface | Weight | What to scan |
|---|---|---|
| Definitions | >80% | `.github/copilot-instructions.md`, `share/instructions/*.instructions.md`, `share/agents/*.agent.md`, `share/skills/*/SKILL.md` |
| Memory | <20% | `/memories/`, `/memories/session/`, `/memories/repo/inbox/`, `ob-memory` MCP store |

Use `file_search` to discover current files for the definitions surface. Do not assume a fixed count.

**MCP degradation path:** If `ob-memory` tools are unavailable, audit file-based memory tiers only and note skipped MCP checks.

### Standards Loading Order

Load in this exact order before evaluating any file:

1. `h-agent-structure`
2. `h-memory-structure`
3. `r-pipeline-protocol`
4. `r-project-standards`

**References, not restates.** Findings must cite specific rules from these skills. If you cannot cite a rule, reconsider the finding.

## 3. Seven Audit Dimensions

Apply each dimension to both surfaces unless noted otherwise. Definitions surface carries >80% of audit weight.

### D1 - Structural

Standards: `h-agent-structure` section Agent File Structure, section Skill File Structure, section Boundary Fitness.

**Positive probes:**

- Agent file missing required sections (`<persona>`, `<critical_rules>`, `<output_format>`, `<boundaries>`, `<examples>`)
- Agent file containing forbidden content (procedures, shared rules, command templates)
- Skill category mismatch (`h-` versus `w-`)
- Naming convention violations
- Instruction file that is not a 3-line stub

**Boundary-fitness sub-probe:**

- Is each file in the right file type (`.prompt.md`, `SKILL.md`, `.agent.md`)?
- Would moving content reduce duplication without reducing reliability?

**Negative-space probe:** Which required section or file type is missing with no current owner?

### D2 - Duplication

Standard: `h-agent-structure` section Rule of Two.

**Positive probes:**

- Same rule appears in 3+ locations
- Agent file restates `r-pipeline-protocol`
- Agent file restates `r-project-standards`
- Skill contains claiming/commit boilerplate that belongs in shared protocol
- `<output_format>` contains full command templates instead of verdict tokens + skill reference

**Negative-space probe:** Which shared convention should exist in `r-pipeline-protocol` but is duplicated per-agent (or missing)?

### D3 - Content Placement

Standards: `h-agent-structure` section 80% Rule, section Rule of Two.

**Positive probes:**

- Content in `copilot-instructions.md` used by fewer than 80% of agents
- Content in `r-pipeline-protocol` needed by only one agent
- Content repeated identically in 2+ agent files

**Negative-space probe:** Which content belongs in `copilot-instructions.md` because >80% of agents need it, but is currently repeated elsewhere?

### D4 - Quality

Standard: `h-agent-structure` section Implicit Encoding and section Agent File Structure.

**Positive probes:**

- `<persona>` lacks behavioral force
- `<examples>` are abstract instead of realistic
- `<critical_rules>` missing primary skill reference as first item
- Pipeline agent missing `r-pipeline-protocol` in `<critical_rules>`
- Agent file contains self-critique/procedural content that belongs in workflow skills
- Workflow skill missing Step 0 protocol loading where applicable

**Negative-space probe:** Which agent persona fails to encode behavior implicitly, forcing too many explicit rules?

### D5 - Pipeline Integrity

Standards: `r-pipeline-protocol` section Per-Agent Signal Mapping, `share/README.md` section Agents.

**Positive probes:**

- Missing dispatch path for any status
- Double-moves on the same transition
- Signal mapping mismatch between protocol and agent `<output_format>`
- Tier assignment mismatch
- Tool allowlist missing required tools or including out-of-tier tools
- Agent naming inconsistency (`planner`, `doc-writer`)

**Rejection-routing table:**

| Agent | Rejection cause | Target status |
|---|---|---|
| builder | Test assumption wrong | `todo` |
| builder | AC describes wrong interface | `backlog` |
| reviewer | Implementation issue | `in-progress` |
| reviewer | Test gap | `todo` |
| reviewer | Test/AC quality | `backlog` |
| reviewer | 2nd+ batch review cycle | `backlog` |
| architect | AC wrong | `research` |
| auditor | Any rejection | `backlog` |

**Rule:** `BLOCK` is valid only for architect user-action/AR blocking paths. Other agents must route by status instead of blocking.

**Negative-space probe:** Is there a pipeline status with no responsible agent?

### D6 - Signal-to-Noise Ratio (SNR) Broad Triage

Perform a quick triage scan that detects likely compression targets and prioritizes deep-dive attention without doing per-sentence rewrites.

#### 6-Category Noise Taxonomy (inline definitions)

1. **Verbose prose wrappers** - framing text that repeats what nearby directives already state.
2. **Over-specification** - excessive constraints/examples beyond what is required for correct execution.
3. **Redundant conditionals** - repeated if/then guidance that does not change behavior.
4. **Prescriptive message templates** - rigid response phrasing that can be replaced by simpler outcome constraints.
5. **Cross-reference ceremony** - link-heavy procedural overhead with low steering value.
6. **Stale institutional memory** - legacy cautions/workarounds no longer relevant to current system behavior.

#### Positive probes

- Scan each file for all six categories; record category hits and short evidence snippets.
- Emit progressive attention flags during the audit loop when a file accumulates multiple category hits.
- Mark universal files (`applyTo: **`) as highest-leverage attention class by default.
- Prefer terse, actionable flag text: category, why it matters, and deep-dive priority signal.

#### Attention flag format

Use this lightweight flag when detected:

`SNR-FLAG | {file} | {category-list} | leverage={universal|high|normal} | confidence={0.0-1.0}`

#### Negative-space probe

Which section appears dense but contains little executable steering signal?

### D7 - Memory Governance and Content

Standard: `h-memory-structure` section Entry Shape, section Tier-Content Fit, section Anti-Patterns.

**Positive probes (memory surface):**

- Missing required memory fields
- Wrong-tier storage
- Low-quality memory entries (generic, ambiguous scope, duplicate)
- Agent-specific entries with null `scope_agent`
- Architecture/research artifacts stored as memory entries

**MCP degradation:** If `ob-memory` is unavailable, audit file tiers only and note skipped checks.

**Negative-space probe:** Which learnings in file inbox should be curated into `ob-memory`?

## 4. Process

### Phase 1 - Scan

1. Load all four standards in order.
2. Discover definitions surface with `file_search`.
3. Read all files in both surfaces.
4. Query memory (`list_memories(states=["curated", "approved"])` for inventory and `recall_memory(agent="{agent_name}")` for scoped context) when available; otherwise degrade gracefully.
5. Build a severity queue: HIGH, then MED, then LOW.

Call `askQuestions` to present queue summary and confirm before the finding loop.

### Phase 2 - Finding Loop

For each finding, present a finding card, then call `askQuestions` to approve before implementing.

**Finding card format:**

```markdown
### [{Severity}] {Finding-ID} - {One-line title}

**File:** {path}
**Rule:** {skill-name} section {section}

**Evidence:**
> {exact quoted text}

**Options:** (only when ambiguous)
- A: {description} - confidence: {0.0-1.0} - {trade-off}
- B: {description} - confidence: {0.0-1.0} - {trade-off}

**Recommendation:** {description} - confidence: {0.0-1.0}
```

**Severity guidelines:**

| Severity | When |
|---|---|
| HIGH | Breaks routing, causes silent failure, or masks trust signals |
| MED | Structural violation, duplication, or misplacement affecting reliability |
| LOW | SNR/cosmetic quality gaps with low immediate risk |

**Phase break rule:** After finishing one severity tier, if next tier has 3+ findings, present a phase-break summary via `askQuestions` before continuing.

**Queue re-evaluation:** Re-scan touched files after every fix and refresh queue.

## 5. Verification and Ranked Output

After the queue is exhausted:

1. Trace implementation path (`research` -> `archived`) and name responsible agent per transition.
2. Trace non-implementation path (`type:docs` or `type:config`) and verify pass-through behavior.
3. Confirm `BLOCK` usage appears only in architect user-action path.
4. Run SNR spot-check on 3 random files and report non-actionable content.
5. Summarize findings found/resolved/deferred by dimension.

### End-of-run ranked report (required)

Produce a category-grouped ranking that prioritizes deep-dive targets using dual-axis scoring:

- Axis 1: noise density relative to category peers
- Axis 2: context-budget weight (`file size + required_reading chain + consumer count`)

Ranking rule: high context-budget files with moderate noise can outrank low-budget files with high noise.

**Report shape:**

```markdown
## Ranked Deep-Dive Priorities

### {category}
1. {file} - score={0-100} - density={low|med|high} - budget={low|med|high} - reason
2. ...

### Attention Summary
- Universal files flagged: {count}
- High-leverage non-universal files flagged: {count}
- Total SNR flags emitted: {count}
```

Call `askQuestions` with coverage summary plus: "Run from the top again?"
