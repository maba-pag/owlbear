---
id: 579
title: 'Recurring: Comprehensive project audit (every 3 days)'
status: backlog
priority: needed
created: 2026-03-04T08:03:44.3041014+01:00
updated: 2026-03-04T08:03:44.3041014+01:00
tags:
    - recurring
    - sop
class: standard
---

## Purpose

Conduct a comprehensive, multi-expert audit of the entire OwlBear project. This is the primary quality assurance mechanism — it catches everything that slips through individual task reviews. Each run produces a fresh assessment, tracks regressions from previous audits, and creates actionable tasks for all findings.

## Schedule

- **Type:** recurring
- **Frequency:** every 3 days
- **Last run:** 2026-03-04
- **Next due:** 2026-03-07

## Execution Protocol

1. The orchestrator creates a subtask: `Comprehensive project audit — YYYY-MM-DD` with `--parent 579 --status ideation --tags "sop-run,audit"`
2. The subtask moves through the full pipeline (ideation → … → done)
3. After the subtask reaches `done`, update `Last run` date in this task's body

## SOP: Comprehensive Project Audit

### CONTEXT

OwlBear is an always-on, laptop-resident AI development system. It receives user intent (via CLI, Slack, or voice), extracts intent, plans work, executes it autonomously, and delivers results. The codebase lives in `src/owlbear/` (~112 files, ~15K LOC) and `src/bearclaw/` (CLI). Tech stack: Python 3.12+, PydanticAI, httpx, SQLite knowledge graph, Qdrant vectors, BGE-M3 embeddings, Slack integration, Playwright browser automation.

The project follows strict principles: Quality over speed. KISS/YAGNI/DRY. Research before implementation. TDD with ≥90% coverage. Every finding must be evidence-backed and actionable.

### Phase 0: Baseline

Before any expert runs, establish the current state:

1. **Tests**: Run `uv run pytest tests/ -m "not api" -q --tb=short` — record pass count, fail count, error count
2. **Lint**: Run `uv run ruff check src/ tests/` — record violation count and categories
3. **Coverage**: Run `uv run coverage run -m pytest tests/ -m "not api" -q` then `uv run coverage report` — record overall % and per-module %
4. **Existing audit tasks**: Run `kanban-md list --compact --tag audit` — record count and status distribution to avoid creating duplicates
5. **Previous audit reports**: Read the most recent `docs/*-audit.md` files to understand the baseline — which findings were already identified, which should be fixed by now

Record all baseline metrics in the subtask body. These are the starting point for the audit.

### Phase 1: Expert Audits

Dispatch one researcher subagent per domain. Each expert:

- **Reads ALL relevant source files** — complete modules, not samples. Use `grep_search` and `read_file` systematically
- Produces a **structured report** with findings rated CRITICAL / HIGH / MEDIUM / LOW / INFO
- Each finding includes: **ID** (domain prefix + number), **severity**, **affected files with line numbers**, **evidence** (actual code snippets), **recommendation**, and **acceptance criteria for the fix**
- Must check whether **previous audit findings** for their domain have been addressed — classify as: fixed, partially fixed, unfixed, regressed, or new
- Writes report to `docs/{domain}-audit.md` (overwrites previous)

#### Required Domains (12 minimum — expand if warranted)

1. **Architecture & Design Patterns** (prefix: `ARC`)
   Focus: layering violations, coupling metrics, cohesion, composition root design, interface contracts, SOLID principles, module boundaries, dependency direction

2. **Security & OWASP Compliance** (prefix: `SEC`)
   Focus: injection vectors (shell, SQL, template, regex), access control, secret management, input validation, authentication flows, session handling, error information leakage, SSRF

3. **Code Quality & Standards** (prefix: `CQ`)
   Focus: cyclomatic complexity (C901), cognitive complexity, duplication, naming conventions, type annotation coverage, dead code, suppression audit (`noqa`/`type: ignore` — each must be justified), import hygiene

4. **DRY / YAGNI / KISS Compliance** (prefix: `DRY`)
   Focus: duplicated logic across modules, unnecessary abstractions, over-engineering, dead features, premature generalization, unused parameters, code that exists "just in case"

5. **Error Handling & Resilience** (prefix: `RES`)
   Focus: retry patterns and their interaction (no retry multiplication), timeout coverage on all I/O, circuit breakers where appropriate, graceful degradation, resource cleanup (`__aenter__`/`__aexit__`), exception hierarchy, error propagation chains, cascading failure paths

6. **Test Coverage & Quality** (prefix: `TST`)
   Focus: coverage gaps per module, mock appropriateness (no over-mocking), test isolation, assertion quality (not just "no exception"), edge cases, async testing patterns, flaky test indicators, test-to-code ratio

7. **Configuration & Dependencies** (prefix: `CFG`)
   Focus: version pinning health, import guards for optional dependencies, config validation completeness, secret handling in config, build system correctness, extras group organization, lock file consistency

8. **Integration & Interface Contracts** (prefix: `INT`)
   Focus: module coupling measurement, protocol compliance, payload schema validation, dependency direction violations, public API surface audit, hook/event contracts, backwards compatibility concerns

9. **Documentation Accuracy** (prefix: `DOC`)
   Focus: stale documentation vs actual code behavior, docstring coverage on public APIs, instruction file accuracy, README currency, architecture doc alignment with implementation, code comment quality

10. **Performance & Resource Management** (prefix: `PRF`)
    Focus: N+1 patterns in database/vector queries, connection and resource pooling, memory leaks (especially in long-running daemon), blocking calls in async context, concurrency limits, startup time, model loading overhead

11. **Observability & Operability** (prefix: `OBS`)
    Focus: logging quality and consistency, structured event coverage, metrics availability, health check completeness, debuggability (can you diagnose a production issue from logs alone?), error journal effectiveness, audit trail completeness

12. **Developer Experience** (prefix: `DX`)
    Focus: onboarding friction (can a new contributor run the project in <5 min?), CLI usability and error messages, configuration complexity, test execution speed, development workflow friction, documentation findability

### Phase 2: Coverage Matrix Gate

After all expert reports are complete, generate a **module × domain coverage matrix**:

| Module | ARC | SEC | CQ | DRY | RES | TST | CFG | INT | DOC | PRF | OBS | DX | Total |
|--------|-----|-----|----|----|-----|-----|-----|-----|-----|-----|-----|----|----|
| bootstrap.py | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | X/12 |
| knowledge/ | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | X/12 |
| (etc.) | | | | | | | | | | | | | |

Mark each cell with the number of findings or `—` for no findings.

**Gate rule**: If any production module (excluding tests/) has findings from ≤2 domain experts, flag it as a **coverage gap**. The executive (Phase 3) must either:

- (a) Explain why the gap is acceptable (e.g., module is trivial, or only 2 domains are relevant)
- (b) Request targeted follow-up audits from specific domain experts for the under-covered module

This prevents blind spots like the `providers/copilot.py` gap in the previous audit.

### Phase 3: Executive Synthesis

A single executive auditor reviews all domain reports and produces the final synthesis:

1. **Cross-reference all domain reports** — identify findings that appear in multiple domains
2. **Deduplicate** — combine findings that target the same root cause across domains into single entries. Reference all original finding IDs (e.g., "ARC-01 + DRY-01 + INT-02: Knowledge infrastructure duplication")
3. **Rank all unique findings** by risk score = probability × impact (both on 1-5 scale, product gives 1-25 range)
4. **Produce a prioritized remediation plan** — top 20 most impactful actions, grouped by effort level (quick fix / moderate / significant)
5. **Regression analysis** — compare against previous audit:
   - **Fixed**: findings from last audit that are now resolved (verify with evidence)
   - **Unfixed**: findings that remain (note if there's a task on the board for them)
   - **Regressed**: previously fixed findings that have reappeared
   - **New**: findings not present in the previous audit
6. **Address coverage gaps** from Phase 2 gate
7. **Write executive report** to `docs/executive-audit-report.md` (overwrites previous)

### Phase 4: Task Creation

**The executive synthesis is the sole authority for task creation** — individual domain reports propose tasks, but only the executive creates them. This eliminates the duplication problem (previous audit: ~60 proposed tasks for ~20 unique fixes).

For every actionable finding (CRITICAL, HIGH, MEDIUM — not LOW/INFO unless they form a pattern):

1. **Check existing board** — `kanban-md list --tag audit` to find existing tasks for this finding
2. If an existing task covers this finding: skip creation, but verify the existing task's AC is still accurate
3. If no existing task: create a kanban task in `ideation` with:
   - Title describing the fix concisely
   - Body with: all finding ID(s) from all domains, severity, affected files with line numbers, evidence, recommendation, and explicit acceptance criteria
   - Tags: `audit`, plus domain prefix (e.g., `sec`, `res`) and relevant module tags
   - Priority mapped from severity: CRITICAL → critical, HIGH → needed, MEDIUM → important
4. **Cross-domain findings MUST be combined** into single tasks — one task per root cause, listing all finding IDs
5. Trivial findings (LOW) of the same type may be grouped into a single "housekeeping" task

### Phase 5: Final Report & Verification

1. Verify all reports were written to `docs/`:
   - 12 domain reports: `docs/{domain}-audit.md`
   - 1 executive report: `docs/executive-audit-report.md`
2. Record in the subtask body:
   - Baseline metrics (from Phase 0)
   - Total unique findings: N (by severity: CRITICAL/HIGH/MEDIUM/LOW/INFO)
   - Tasks created: N (list IDs and titles)
   - Tasks skipped (already on board): N
   - Regression summary: X fixed, Y unfixed, Z regressed, W new
   - Coverage matrix summary: any gaps flagged?
   - Top 5 most critical findings (one-line each)
3. Compare baseline metrics with previous audit's baseline — are tests/lint/coverage trending up or down?

## Quality Requirements

- **No finding without evidence**: every finding must cite specific file paths, line numbers, and include a code snippet demonstrating the issue
- **No recommendation without acceptance criteria**: every fix suggestion must include testable AC
- **No domain skipped**: if a domain expert finds nothing, they must explicitly state "no findings" with reasoning (which modules they checked and why nothing was found)
- **No duplicate tasks**: cross-reference with existing `audit`-tagged tasks before creating
- **Every CRITICAL and HIGH finding must be verified** by reading the actual source code — do not infer issues from patterns or naming alone
- **Reports must be written to disk** — not just returned as chat messages
- **Previous audit reports are the baseline** — this is a delta assessment, not a from-scratch review (but still check everything, since code changes between audits)

## Self-Critique Requirement

Each domain expert and the executive must include a self-critique section in their report:

- What areas of the codebase might I have missed?
- What assumptions did I make that could be wrong?
- What would I check with more time or resources?
- Confidence score for my overall assessment (.0–1.0)

This ensures intellectual honesty and identifies the audit's own blind spots.
