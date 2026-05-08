# Pre-end_work Scoped Commit Check

> **Owning task:** #1412 — D1: Pre-end_work scoped commit check — domain-scoped uncommitted file verification
> **Date:** 2026-05-08 **Status:** Complete

## 1. Context and Question

Agents forget to commit their deliverables ~20% of the time (researcher and test-writer worst offenders — source: brief #1403 panel analysis). The current protocol says "commit before `end_work`" but provides no verification step. The reviewer's dirty-tree contamination check (`w-code-review` Step 1.1) catches this downstream, but that's reactive — the task already advanced, wasting a dispatch cycle.

**Question:** What protocol text should be added to `r-pipeline-protocol` so that each agent verifies its own domain files are committed before calling `end_work`?

**Constraint:** The check must be domain-scoped. Raw `git status --porcelain` shows ALL dirty files in the shared worktree, including other agents' in-progress work. A naive check would false-positive on every shared-worktree invocation.

## 2. Sources Studied

| Source | URL / Path | Relevance |
|--------|-----------|-----------|
| `r-pipeline-protocol` § 4 Closing — Who Commits What | `share/skills/r-pipeline-protocol/SKILL.md` | 1.0 — current commit rules, no verification step |
| `w-code-review` Step 1.1 — Dirty-Tree Contamination Check | `share/skills/w-code-review/SKILL.md` | .95 — prior art for domain-scoped `git status --porcelain -- <paths>` |
| Brief #1403 — D1 specification | `.owlbear/briefs/draft-pipeline-review-rethink/brief.md` | 1.0 — design intent and 20% miss-rate stat |
| Git documentation — `git status --porcelain` | git-scm.com/docs/git-status | .85 — pathspec filtering semantics |

## 3. Analysis

### Mechanism

`git status --porcelain -- <paths>` filters output to only files matching the given pathspecs. This is exactly what the reviewer's dirty-tree check already uses. The same mechanism works for self-checks.

### Domain Path Mapping

Extends the existing "Who Commits What" table with explicit pathspecs:

| Agent | Domain Paths | Notes |
|-------|-------------|-------|
| Researcher | `.owlbear/research/` `.owlbear/sources/` | Both dirs are deliverables |
| Test-writer | `tests/` | Task-scoped test files |
| Builder | `serve/` | Source code in workspace packages |
| Doc-writer | `README.md` `README-consumer.md` `SECURITY.md` `serve/*/README.md` `share/README.md` `setup/*.md` `share/diagrams/` | All doc targets per copilot-instructions |
| Auditor | N/A | Auditor commits kanban state, handled differently |

### Exclusions

- `.owlbear/kanban/tasks/` — always dirty (pipeline ephemera), excluded by convention.
- Other agents' domain paths — excluded by design (domain-scoped check).

### Action on Dirty Domain

If `git status --porcelain -- <domain-paths>` returns non-empty output:
1. Stage and commit the missed files using the standard atomic command.
2. Then proceed to `end_work`.

No need to fail or block — the check is a self-heal step, not a gate. The agent catches its own mistake and fixes it before advancing.

### Placement in Protocol

Insert as a new rule in the existing "Who Commits What" → Rules list, after "Commit gates advance" and before "Atomic single command." Title: **Pre-advance verification.**

### Why Not PostToolUse Hooks

The brief explicitly rules out PostToolUse hooks. Reasons from the panel:
- Hooks fire on every tool call, causing overcommits in parallel agent environments.
- Protocol-level checks are simpler, more visible, and easier to audit.
- No VS Code API dependency — works with any agent runtime.

## 4. Recommendation

**Add a "Pre-advance verification" rule** to `r-pipeline-protocol` § 4 Closing → Who Commits What → Rules. The rule includes:
1. Domain-path table (agent → pathspecs)
2. Verification command: `git status --porcelain -- <domain-paths>`
3. Self-heal action: commit if dirty, then proceed

Confidence: **.90** — straightforward protocol addition, mechanism already proven in `w-code-review`.

Challenge: SKIP — trivial protocol change, no competing alternatives.

## 5. Follow-up Tasks

- One follow-up at `backlog`: implement the protocol text change in `r-pipeline-protocol/SKILL.md`.
