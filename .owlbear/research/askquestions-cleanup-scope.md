# askQuestions Reference Cleanup — Scope and Approach

> **Owning task:** #125 — Clean up askQuestions references: decouple confidence patterns from tool usage
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

OwlBear's docs reference `askQuestions` as a tool, but the project decision (2026-03-29) is that `vscode/askQuestions` will not be granted to any agent. The decision-requests skill is the async deferral mechanism. Task #101 handles removing the tool from YAML frontmatter. This task (#125) handles decoupling the valuable behavioral patterns (confidence scores, structured options, `(bp:)`/`(rec:)` annotations) from the tool name in instructional text.

Question: What files need changes, what's the replacement language, and how should confidence scoring be standardized across the project?

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | OwlBear docs/research/vs-code-new-tools-evaluation.md | .95 | Project decision: askQuestions not adopted; decision-requests is the mechanism |
| S2 | OwlBear docs/research/gstack-agent-patterns.md | .85 | Prior art: gstack's structured question protocol ("one issue, recommend+WHY+options") |
| S3 | OwlBear decision-requests skill (SKILL.md) | .90 | Existing `(bp:)`/`(rec:)` convention and confidence score usage — already tool-agnostic |
| S4 | OwlBear agent-common.instructions.md | .90 | Confidence threshold table already exists (reviewer ≥.90, auditor ≥.95) |
| S5 | VS Code Copilot customization docs [S5] | .70 | Confirms askQuestions is a built-in tool, not a behavioral pattern |

## 3. Analysis

### 3.1 File Inventory (grep-verified)

| File | Matches | Type | Overlap with #101? |
|------|:-------:|------|:-------------------:|
| `agents/planner.agent.md` | 3 | Prohibition text | No — behavioral text, not YAML tools |
| `agents/kanban-planner.agent.md` | 1 | YAML tools list | **Yes — #101 covers this** |
| `agents/orchestrator.agent.md` | 1 | YAML tools list | **Yes — #101 covers this** |
| `agents/curator.agent.md` | 1 | YAML tools list | **Yes — #101 covers this** |
| `.github/prompts/agent-audit.prompt.md` | 3 | Behavioral guidance | No |
| `skills/project-definition/SKILL.md` (×2 mirrors) | 5 each | Behavioral guidance + code example | No |
| `skills/research-workflow/SKILL.md` (×2 mirrors) | 1 each | Behavioral guidance | No |
| `instructions/agent-common.instructions.md` | 1 | Cross-reference | No |
| `.github/copilot-instructions.md` | 0 | Missing rules | No — needs new content per AC |
| `docs/research/*.md` (5 files) | ~15 | Historical research docs | N/A — not instructional |

### 3.2 Change Categories

| Category | Files | Approach |
|----------|-------|----------|
| YAML tool removal | 3 agent files | Out of scope — handled by #101 |
| Prohibition rewording | `planner.agent.md` | Replace tool name with behavior: "request user input" / "prompt the user" |
| Behavioral guidance rewrite | `agent-audit.prompt.md`, 2×`project-definition/SKILL.md`, 2×`research-workflow/SKILL.md` | Replace "use askQuestions" with "present structured options"; keep confidence/`(bp:)`/`(rec:)` patterns |
| Cross-reference cleanup | `agent-common.instructions.md` | Replace "instead of askQuestions" with direct prose |
| New rules in copilot-instructions | `.github/copilot-instructions.md` | Add confidence scoring rule + structured options guideline |
| Historical docs | 5 research docs | **No changes** — these are records of past analysis, not instructions [S1] |

### 3.3 Replacement Language Matrix

| Current phrasing | Replacement | Rationale |
|-----------------|-------------|-----------|
| "Use `askQuestions`" | "Present structured options to the user" | Tool-agnostic; preserves intent [S2] |
| "askQuestions liberally" | "State confidence and present structured options at every decision point" | Keeps the "don't assume" intent; ties to confidence convention [S4] |
| "via askQuestions" | "when presenting proposals" | Removes tool dependency |
| "instead of `askQuestions`" | Remove the comparison entirely | Decision-requests stands on its own [S3] |
| Prohibition: "Never use `askQuestions`" | "Never prompt the user for decisions" | Behavior-focused prohibition |

### 3.4 Confidence Scoring Gap

Agent-common already has a confidence threshold table [S4], but it only applies to reviewer/auditor verdicts. The AC asks for a general rule in copilot-instructions.md that all agents should state confidence when deriving decisions from source material. This aligns with gstack's pattern [S2] and the existing `(bp:)`/`(rec:)` convention in the decision-requests skill [S3].

## 4. Recommendation (.85 confidence)

Split into two implementation tasks:

1. **Rewrite instructional references** — mechanical find-and-replace using the language matrix above. ~12 edits across 7 unique files (counting mirrors). Low risk.
2. **Add confidence scoring rules to copilot-instructions.md** — new section in Process Habits. Moderate risk (wording matters; affects all agents).

Both tasks are docs-only changes (no `.py` files). Research docs should NOT be modified — they are historical records.

Risk: The `project-definition` skill has an `askQuestions()` code example that needs rewriting as a generic "present options" example. This is the most complex single edit.

## 5. Follow-up Tasks

Task commands executed below to create at `ideation` status.
