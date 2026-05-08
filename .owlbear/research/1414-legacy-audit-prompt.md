# Legacy Audit Prompt — Research

> **Owning task:** #1414 — E1: legacy-audit.prompt.md — cleanup scan prompt for stale references
> **Date:** 2026-05-08 **Status:** Complete

## 1. Context and Question

The workspace accumulates stale references over time: TODO comments for completed tasks, dead imports, test files for archived tasks, legacy-named functions. Task #1414 (from brief #1403) calls for a user-triggered one-shot prompt that scans for these and produces a ranked report.

**Key questions:** (1) Is any existing prompt or tool already covering this? (2) What scan categories are feasible with available tools? (3) What output format best serves the user?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `share/prompts/frontend-audit.prompt.md` | Codebase | 0.9 — established audit prompt pattern (read-only, severity-ranked, guardrails) |
| S2 | `share/prompts/agent-broad-audit.prompt.md` | Codebase | 0.9 — structural audit with SNR triage and approval loops |
| S3 | `share/skills/w-test-curation/SKILL.md` | Codebase | 0.7 — overlaps on stale task-test detection; action-oriented, agent-dispatched |
| S4 | Vulture (jendrikseipp/vulture) | External | 0.6 — Python dead code finder; detects unused functions, imports, unreachable code |
| S5 | Ruff F401 rule | External | 0.5 — unused import detection already available via `ruff check --select F401` |
| S6 | Knip (webpro-nl/knip) | External | 0.4 — JS/TS dead code finder; structural inspiration but different ecosystem |

## 3. Analysis

### 3.1 Overlap Assessment

| Existing tool | Overlap with AC | Differentiation |
|---------------|----------------|-----------------|
| `w-test-curation` | Stale task-test detection | Action-oriented (mines + deletes); agent-dispatched; coverage-focused. Legacy-audit is report-only, user-triggered. |
| `ruff check --select F401` | Unused imports | Only imports; no TODO/task/naming/mock scan. Already in CI. |
| `agent-broad-audit` | Agent ecosystem staleness | Scopes to agent/skill/instruction files only, not source code. |

**Conclusion:** No existing prompt covers the full scan surface. Overlap with test-curation on stale tests is complementary (report vs. action).

### 3.2 Scan Category Feasibility

| Category | AC ref | Detection method | Feasibility |
|----------|--------|-----------------|-------------|
| TODO(#nnnn) with done/archived task | P2 | `grep_search` for `TODO(#\d+)`, extract IDs, check kanban status | High — straightforward grep + kanban lookup |
| Dead imports / zero-caller functions | P2 | `ruff check --select F401` for imports; `grep_search` for function defs + call sites | Medium — imports easy via ruff; zero-caller needs heuristic grep |
| Mocks referencing obsolete patterns | P2 | `grep_search` for `Mock`, `patch(`, `MagicMock` in tests; verify mocked targets exist | Medium — requires cross-referencing mock targets against production code |
| Stale task-test files | P2 | `file_search` for `test_*_*.py`, extract task IDs, check kanban for archived status | High — well-established pattern from w-test-curation |
| Legacy/compat/bridge/shim naming | P2 | `grep_search` for those keywords in function/class/module names | High — simple keyword search with manual triage |

### 3.3 Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Prompt structure | Inline audit (no `agent:` dispatch) | Matches frontend-audit pattern; user controls pace |
| Read-only enforcement | Behavioral contract + guardrails section | Standard audit prompt pattern (S1, S2) |
| Ruff for dead imports | Recommend `ruff check --select F401` output | Reuse existing tooling instead of manual grep |
| Output grouping | 5 categories from AC, severity-tiered | Matches AC requirement "grouped by type" |
| Severity tiers | critical / warning / info | Critical = definitely stale (task archived); warning = likely stale; info = review manually |
| Kanban tool access | Add `tools:` frontmatter for kanban lookups | Needed for TODO and stale-test task status checks |
| User input | `${input:scope}` for optional path filter | Allows focused scans on specific directories |

### 3.4 Confirmed Codebase Instances

Validated that scan categories would find real results:

- `_knowledge_stats_bridge()` in mcp-knowledge (bridge naming)
- `_drop_legacy_approval_state()` in mcp-memory (legacy naming)
- "Compatibility alias" docstrings in mcp-memory tools (compat naming)
- `_LEGACY_CONFIG_KEYS` in kanban migrate.py (legacy naming)
- 100+ task-scoped test files in `tests/` (potential stale tests)

## 4. Recommendation

**Proceed with prompt creation** following the inline audit pattern from `frontend-audit.prompt.md`.

Confidence: **0.90** — well-defined AC, established prompt patterns, all scan categories feasible with existing tools, no architecture changes needed.

Challenge: Skipped — trivial T1 prompt file creation with no architectural decisions or trade-offs requiring adversarial review.

### Implementation Notes for Builder

1. Follow `frontend-audit.prompt.md` structure: preamble → scan steps → output format → guardrails
2. For TODO(#nnnn) and stale-test categories: use kanban tools to check task status
3. For dead imports: delegate to `ruff check --select F401` rather than manual scanning
4. For zero-caller functions: use heuristic grep (define → search for callers → flag if none found)
5. For mocks: search test files for `patch("module.Class")` and verify `module.Class` still exists
6. Output: grouped table per category, severity-tiered, with file paths and line numbers

## 5. Follow-up Tasks

T1 classification — autonomous prompt file creation. Single follow-up task at `backlog` for the builder to create the prompt file.

No DR needed — no new capability, no architecture change, no security implications.
