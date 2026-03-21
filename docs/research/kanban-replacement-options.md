# Kanban Replacement Options — Research

> **Owning task:** #144 — Research: Kanban replacement — richer task management
> **Date:** 2026-03-21 **Status:** Complete

## 1. Context and Question

OwlBear uses [kanban-md](https://github.com/antopolskiy/kanban-md) (v0.33.0) as its
file-based task board. Every pipeline agent, the daemon hooks, and the CLI toolset talk
to it through a single Go binary (`kanban-md.exe`). The question is whether that choice
still makes sense, or whether a richer task-management tool would improve agent
operability, dependency tracking, or board visibility enough to justify migration.

**Integration seams at risk in any replacement:**

| Seam | File | How it uses kanban-md |
|------|------|-----------------------|
| KanbanToolset | `src/owlbear/tools/kanban.py` | `asyncio.create_subprocess_exec` → CLI subcommands (list, show, create, move, edit, pick) |
| BoardContextProvider | `src/owlbear/core/board_context.py` | `kanban-md list --compact --status …` — injects live board into agent turns |
| ContextInjectionHook | `src/owlbear/core/context_hook.py` | `kanban-md context` — SESSION_START hook enrichment |
| RetrospectiveHook | `src/owlbear/core/retrospective_hook.py` | `subprocess.run` via kanban-md to read completed tasks |
| ProjectWorkspace | `src/owlbear/projects/workspace.py` | `kanban-md init` on new project scaffolding |

Any replacement must expose either the same CLI surface (zero migration) or a
well-defined CLI that each seam can adapt to without business-logic changes.

## 2. Sources Studied

| Source | Relevance | What |
|--------|:---------:|------|
| docs/research/mission-control.md | .90 | Full Mission Control evaluation — architecture, patterns, task board design |
| docs/research/textual-tui-dashboard.md | .85 | TUI dashboard feasibility — richer UI layered on top of existing file-based board |
| kanban-md v0.33.0 source and docs | .95 | Current baseline — statuses, priorities, WIP limits, claims, YAML frontmatter, `--compact` |
| kanban/config.yml | .95 | OwlBear's live board configuration — 7 statuses, 5 priorities, WIP classes |
| GitHub Issues + Projects REST/GraphQL API docs | .80 | Evaluation of GitHub-native task management |
| Taskwarrior v3.x docs and source | .70 | Leading offline CLI task manager — file format, scripting, dependency model |
| github.com/nicoulaj/idea-markdown parser notes | .40 | Background on markdown-native task state (indirect) |

## 3. Candidates

Four candidates are evaluated:

| # | Candidate | Type |
|---|-----------|------|
| 0 | **kanban-md (current baseline)** | File-based markdown, Go CLI |
| 1 | **Mission Control** | TypeScript/Next.js web app with JSON files |
| 2 | **GitHub Issues + Projects** | Cloud API, `gh` CLI wrapper |
| 3 | **Taskwarrior** | Offline C++ CLI, binary+JSON task store |
| 4 | **Augment kanban-md** | Keep backbone, add targeted enhancements |

## 4. Comparison Matrix

Scoring: **5** = excellent, **4** = good, **3** = adequate, **2** = poor, **1** = unusable.
Higher is always better for every criterion.

| Criterion | kanban-md | Mission Control | GitHub Issues | Taskwarrior | Augment kanban-md |
|-----------|:---------:|:---------------:|:-------------:|:-----------:|:-----------------:|
| Offline operation | **5** | 3 | 1 | **5** | **5** |
| File-based agent operability | **5** | 2 | 1 | 3 | **5** |
| CLI ergonomics | 4 | 2 | 3 | 4 | **5** |
| Dependency/priority/assignment | 4 | 3 | **5** | 3 | 4 |
| Richer UI surface | 2 | 4 | **5** | 3 | 3 |
| Migration cost (OwlBear seams) | **5** | 1 | 2 | 2 | 4 |
| Security / privacy | **5** | 4 | 2 | **5** | **5** |
| **Total** | **30** | **19** | **19** | **25** | **31** |

### 4.1 kanban-md (current baseline)

**Strengths:**
- Zero-network: all ops are local filesystem reads/writes via a single Go binary.
- Tasks are plain Markdown + YAML frontmatter — agents can read and parse them
  directly without a tool call if needed.
- `--compact` list output is already injected into every agent turn via
  `BoardContextProvider` and `ContextInjectionHook`.
- Custom statuses, WIP limits, claim/lock protocol, and activity JSONL log are
  already purpose-built for OwlBear's multi-agent pipeline.
- All five integration seams are stable and well-tested.

**Weaknesses:**
- No web or TUI — browsing the board requires `kanban-md board` in a terminal.
- No native time-box or milestone grouping beyond tags.
- Binary (not in PATH, gitignored) — developers must run `kanban/setup.ps1` on
  any new machine.

**Migration cost:** zero — this is the baseline.

### 4.2 Mission Control

> Source: docs/research/mission-control.md

Mission Control's task-board feature is a Next.js web UI backed by JSON flat files.
It was designed for a single human operator monitoring spawned Claude agents via a web
dashboard. Key evaluation findings from the existing research:

- **Stack mismatch:** TypeScript/Next.js. Integrating it as OwlBear's authoritative
  task store would require rewriting all five seams in terms of the MC file schema or
  exposing a compatible CLI shim.
- **Agent operability:** MC agents communicate via a JSON inbox / decisions queue, not
  a CLI. The `KanbanToolset` subprocess pattern cannot wrap this without substantial
  middleware.
- **No custom pipeline statuses:** MC uses its own state machine (todo/in-progress/
  completed/failed). OwlBear's seven-status pipeline (ideation → backlog → todo →
  in-progress → review → docs → done/archived) doesn't map cleanly.
- **Self-hostable but not CLI-native:** Requires running a Node.js server process.
  Background agents would need to hit a local HTTP endpoint — introducing a new
  failure mode (server not running).

The patterns worth adopting from MC (loop detection, cost tracking, compact context
injection) have already been extracted and tracked as separate backlog tasks. Those
are applicable regardless of which task board OwlBear uses.

**Verdict:** MC is not a viable drop-in replacement. Its UI patterns are valuable
but its task-board subsystem is tightly coupled to a TS/web stack that conflicts
with OwlBear's file-first, CLI-everywhere architecture.

### 4.3 GitHub Issues + Projects

GitHub Issues is the obvious "enterprise-grade" comparison: rich dependency/milestone
support, web UI, assignees, labels, and a REST+GraphQL API wrapped by the `gh` CLI.

**Appeal:**
- First-class dependency graph (tracked via issue references and milestones).
- Assignee, labels, milestones — all natively supported.
- Excellent web/mobile visibility with no additional tooling.

**Disqualifying factors:**

| Factor | Issue |
|--------|-------|
| Offline operation | Every read/write requires a network round-trip. Agents running `kanban list` go dark without internet. |
| Rate limiting | GitHub API: 5000 requests/hour for authenticated users. A high-frequency pipeline (dozens of `show`, `edit` calls per task) can exhaust quota. |
| Security / privacy | Issues on public repos are world-readable. Even private repos expose task titles and body text to GitHub's servers and LLM training data policies. |
| Latency | Each `gh issue edit` round-trip adds ~200–600ms. `BoardContextProvider` re-polls every 60s — this becomes a 600ms TTL refresh instead of a local file read. |
| Custom pipeline statuses | GitHub Projects offers custom fields but the branching status machine (requires specific status transitions, claim/release semantics) needs custom project fields + automation rules. Significant setup cost with no persistence guarantee across API changes. |
| Migration | All five seams would need rewriting against `gh` CLI or the REST API. The claim/lock protocol has no direct equivalent in GitHub's issue lock model. |

**Verdict:** Excellent for social software development teams. Unsuitable for an
always-on, offline-first, privacy-conscious laptop daemon. The network dependency
alone is a hard disqualification.

### 4.4 Taskwarrior

Taskwarrior (v3.x) is the leading offline-first CLI task manager. It is written in C++,
stores tasks in binary + JSON (`~/.task/`), and exposes a rich scripting surface.

**Strengths:**
- Fully offline, no server requirement.
- `task add`, `task done`, `task modify`, `task export:json` — solid CLI ergonomics.
- Native dependency tracking (`depends:ID`), priorities (H/M/L), tags, projects.
- Hooks API (on-add, on-modify) that could trigger OwlBear daemon events.
- taskwarrior-tui (TUI) is a mature community wrapper.

**Weaknesses:**
- **Not file-based markdown:** tasks live in a binary database, not agent-readable
  `.md` files. The `task export:json` command adds a subprocess + JSON parse step
  on every agent read that currently is a plain file op.
- **Custom pipeline statuses are non-trivial:** Taskwarrior has four states
  (pending/completed/deleted/waiting). OwlBear's seven-status pipeline would require
  encoding status in a UDA (user-defined attribute), which agents must know about.
- **Claim/lock protocol:** kanban-md's `--claim`/`--release` with TTL expiry has no
  equivalent in Taskwarrior — building one would add significant custom middleware.
- **Binary + platform dependency:** The C++ binary needs `brew install task` (macOS)
  or `apt install taskwarrior` (Linux). Windows support is via WSL or unofficial
  builds — a regression for the current Windows-resident workflow.
- **Migration:** Every seam's subprocess arg list changes and the YAML-frontmatter
  file format disappears entirely.

**Verdict:** Taskwarrior is excellent for personal task management but is a poor fit
for OwlBear's agent-pipeline use case. Its binary store, non-markdown format, and
Windows support gaps make it a lateral move at best.

### 4.5 Augment kanban-md

The alternative to replacement is targeted augmentation: keep kanban-md as the task
backbone and add the missing capabilities via thin wrappers or companion tooling.

Specifically, two gaps are real today:

1. **Richer board visibility** — `kanban-md board` renders in the terminal but requires
   a developer to open a shell. The textual-tui-dashboard research (§4.5) found that a
   Textual TUI can be layered on top of the existing file-based board (~480 LOC once the
   daemon event stream exists from other work). Re-evaluate when `autonomous_mode` is
   default-on.

2. **Assignment reporting / metrics** — `kanban-md metrics` covers WIP and cycle time.
   A `bearclaw board` CLI command (Rich table, ~120 LOC) could surface assignee workload
   and in-progress aging without any schema changes to the task files.

Everything else in the scoring matrix — offline operation, file-based operability, CLI
ergonomics, security/privacy — is already at maximum with kanban-md.

**Migration cost:** minimal — no seam changes; new capabilities are additive.

## 5. Richer Board Visibility: Augment Rather Than Replace

The architecture review for task #144 noted that `docs/research/textual-tui-dashboard.md`
shows richer board visibility can be delivered by layering a TUI/UI over the existing
file-based board rather than replacing the underlying store.

This finding is confirmed by this analysis:

- The file-based `.md` format is what enables direct agent reads, reproducible diffs,
  and editorial transparency. **Replacing it means losing those properties.**
- A Textual TUI (when justified) would poll `kanban/tasks/*.md` directly — the same
  files kanban-md writes. No schema migration needed.
- A Rich CLI table view (`bearclaw board`) could be built today for ~120 LOC without
  any infrastructure investment.

**Conclusion:** Richer board visibility is better delivered by augmenting kanban-md
than by replacing it.

## 6. Recommendation

**Keep kanban-md with targeted augmentation.**

Confidence: **.90**

Rationale:
- kanban-md scores highest in the comparison matrix (30/35 raw, 31/35 as augmented).
- All five integration seams are stable, tested, and already optimized for the
  file-CLI pattern.
- No candidate offers a materially better value proposition across the full criteria
  set. Mission Control and GitHub Issues trade away offline operation and privacy for
  UI richness that OwlBear does not yet need at scale. Taskwarrior is a lateral move
  with worse Windows support.
- The real gaps (board visibility, assignee metrics) are additive features that do
  _not_ require a new dependency or seam rewrite.
- KISS and YAGNI apply: OwlBear is a single-operator laptop daemon. The board's
  consumers are one human and a handful of automated agents — not a distributed team
  that needs enterprise project management.

The recommendation is therefore: **no replacement, one follow-up engineering task**.

## 7. Follow-up Tasks

One engineering task is warranted — the assignment/metrics gap can be closed today:

```powershell
kanban\kanban-md.exe create "bearclaw board: Rich table view of kanban tasks by status and assignee" --status ideation --priority nice-to-have --tags "cli,tooling,phase-14" --body "Add 'bearclaw board' CLI command that renders a Rich table grouped by status with columns: ID, title, assignee, age (days in status), tags. Target ~120 LOC in src/bearclaw/. No new deps (Rich is already transitive). See docs/research/kanban-replacement-options.md §5 and §6."
```

The Textual TUI is already tracked as deferred in docs/research/textual-tui-dashboard.md.
No new task required there.

If the `autonomous_mode` default-on milestone changes the single-user assumption,
re-evaluate this decision — at that point, a TUI becomes ~480 LOC on top of an
existing daemon event stream.
