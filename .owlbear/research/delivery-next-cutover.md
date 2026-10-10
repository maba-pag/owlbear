# Delivery Next: Cutover and Deletion Plan (D5)

> **Owning task:** none — M3 D5 of the [liveness-first rebuild](delivery-liveness-first-rebuild.md)
> **Date:** 2026-10-10
> **Question:** How do the old and new Delivery coexist until cutover, which content moves so the
> Copilot harness loads it, under which gates is the old engine deleted, what exactly is deleted,
> and how is a failed cutover rolled back?
> **Status:** design draft; `autonomous` until the user approves M3. Revision 2026-10-10 after
> design challenge: separate host app until M6, switch and rollback launchers, lane gate G6,
> deletion-list corrections, no partial syncs to `main` before cutover. Revised after TD-10: no
> switch of OwlBear's own development.

## 1. Context and Question

The rebuild chose a thin core on the Copilot runtime beside the old engine (route R2+3). The open
Changes keep running on the old engine until they finish (TD-2), and the old engine runs only on
the Local harness, which "will be removed in a future release" (rebuild §3.9 F2). Delivery-next
need not support OwlBear developing itself (TD-10): OwlBear keeps being developed directly in chat,
so cutover switches nothing for OwlBear's own development. Cutover is: the open Changes finish on
the old engine, then one deletion PR retires it (M6). This document is the D5 deliverable:
coexistence rules for M4 and M5, the E1 content move, the M6 gates and order, a rollback path, the
deletion list with measured sizes, the documentation changes and the risks. It adds no mechanism;
every step uses git, setup, the sync workflow or an existing file.

## 2. Sources Studied

| ID | Source | Used for | Limits |
| --- | --- | --- | --- |
| C01 | [Rebuild research](delivery-liveness-first-rebuild.md) §3.7–§3.9 | M0–M7, E1, TD-1–TD-22, option S3, provenance rule | Only TD-1–TD-22 are user decisions |
| C02 | [Charter draft](delivery-next-charter.md) §3.4, §3.7, §3.9, §3.11 | Route, Cockpit as status surface, size and style rules, non-goals | Draft, not approved |
| C03 | [Ownership map](delivery-next-ownership-map.md) §4 | 47 of 55 engine modules unnecessary; agents, skills, prompts and tools dropped | Classified by docstring and purpose |
| C04 | [Route comparison](delivery-next-route-comparison.md) §3.4 | Eight reuse items, copied not imported | Coupling read statically |
| C05 | [Distribution research](owlbear-distribution-agent-host.md) F1–F4, §3.5, §5 | `share/` invisible to the harness; plugin content option C3; `.mcp.json` `cwd` follows the session; agent hooks run only in Local | Static reading of VS Code 1.140 |
| C06 | [Platform probe](delivery-next-platform-probe.md) rows 6–8 | `.github/agents`, `.github/skills` and instructions load in CLI sessions; repo `.mcp.json` needs folder trust per worktree | One laptop, free identity |
| C07 | `git ls-files` and `wc -l` at `dev` on 2026-10-10 | Every count in §3.6 | Lines include blanks and docstrings |
| C08 | [pyproject.toml](../../pyproject.toml), [sync-manifest.json](../../.github/sync-manifest.json), [.vscode/mcp.json](../../.vscode/mcp.json), [.vscode/settings.json](../../.vscode/settings.json), [seed/.vscode](../../seed/.vscode/), [setup/init.py](../../setup/init.py) L81–L83, L994–L1042 | Loading paths and registration that change | Read, not run |
| C09 | [delivery_controller.py](../../serve/tools/src/owlbear_tools/delivery_controller.py) L3, L183–L188; [pin.json](../../.owlbear/controller/pin.json) | Releases are `git archive` plus `uv sync --locked --package <controller packages>`; pinned release `43fdf236` | Not executed |
| C10 | `grep owlbear_delivery` over surviving code | Cockpit [main.py](../../serve/cockpit/src/owlbear_cockpit/main.py) L46–L47 and [ideas.py](../../serve/cockpit/src/owlbear_cockpit/routes/ideas.py) import the old engine; `serve/tools` and `serve/cockpit` depend on it | Import level only |

## 3. Design

### 3.1 Phases at a glance

| Phase | Old Delivery | New core | Content and loading |
| --- | --- | --- | --- |
| Now to G4 (M3–M5) | Runs the open Changes from the pinned controller on Local; fixes only for them (M0) | Built and proven on the sandbox consumer repository as its own host app with a small Changes page; not registered in OwlBear's workspace; Cockpit unchanged | E1 moves non-Delivery content; Delivery content stays in `share/` |
| M6 deletion | Unregistered; source deleted in one PR | Registered for consumers only (TD-10); its Changes page and host routes move into Cockpit | `share/` removed; product docs rewritten |
| Retention window | Pinned release and state kept on disk for rollback | Runs consumer Changes | — |
| After window | Live state, refs and releases removed with the user's confirmation | Sole Delivery | — |

### 3.2 Coexistence while M4 and M5 run

**Keep unchanged** (the open Changes depend on them):

| Item | Rule |
| --- | --- |
| `.owlbear/controller/` (pin, two releases, `bin/delivery-mcp`, `bin/cockpit`) | Changed only by `/upgrade-delivery` for a fix an open Change needs |
| `owlbear-delivery` entry in [.vscode/mcp.json](../../.vscode/mcp.json) | Stays the only registration of the old server |
| `chat.*FilesLocations` in [.vscode/settings.json](../../.vscode/settings.json) | Stay; Local keeps loading `share/` |
| Delivery agents, skills and prompts in `share/` (§3.6 rows 10–12) | No move, rename or edit except an M0 fix |
| `serve/delivery*`, `delivery_*` tools, Cockpit Delivery routes and views | M0 fixes only; each names the deletion row it later falls under |
| `.owlbear/delivery/`, Change worktrees, `owlbear/delivery-state`, `refs/owlbear/*` | Never read or written by new work |
| The ~15 fix and redesign lane worktrees | Not touched by this plan; classified at G6 |

**Adding the new package** without breaking the old loading path:

1. Create it as `serve/delivery-next/` (working name; D4 fixes it). The `serve/*` workspace glob adds
   it to `uv.lock`; controller releases install only their named packages with `--locked` (C09), so
   the new package and its `github-copilot-sdk` dependency never enter an old release.
2. One-way isolation: the new package imports nothing from `owlbear_delivery`; it copies the reuse
   list (§3.6 "Copied first"). No old package (`cockpit`, `tools`, `delivery*`) depends on or imports
   the new one before M6.
3. Distinct names everywhere: Python module, console scripts, MCP server name
   (`owlbear-delivery-next`), state root outside the checkout, branch prefix, and its own host launch
   command and port other than Cockpit's 8420. Before M6 the host is a separate app in
   `serve/delivery-next/` with its own small Changes page; Cockpit is not modified, because fixes
   for the open Changes are released from `dev` to the pinned controller.
4. M4 runs on the sandbox repository, whose own `.mcp.json` registers the new server from a dev
   checkout. OwlBear's workspace gets no new-core registration (TD-10), so no OwlBear chat sees
   two Delivery servers.
5. Add the package to ruff `src` in [pyproject.toml](../../pyproject.toml). The sync manifest on the
   prototype branch `next/m4-slice1` has a `delivery-next` scope behind the `sync_delivery_next`
   input of `sync-to-main.yml`, default off: the package reaches consumer `main` only when that
   input is set at dispatch. It stays off until M6, so consumer `main` keeps today's content. The
   sync workflow replaces the selected scopes from current `dev`, so between the first E1 move and
   cutover no partial `share` or `infra` sync to `main` runs unless the projection, loading
   configuration and lock membership move together. The new package never appears in a published
   lock early, and moved content never vanishes from consumer `share/`.
6. Before any controller upgrade an open Change needs, the upgrade's live-compatibility gate must
   pass at that dev head; a failure blocks the upgrade, not the new package.

### 3.3 E1 content portability

**What survives** (non-Delivery workflows):

| Kind | Survives | Count, lines | Delivery-only (not ported) |
| --- | --- | --- | --- |
| Agents | `conceptual-design-reviewer`, `knowledge-enricher`, `knowledge-ingestor`, `memory-curator`, `test-curator` | 5 | 9 (§3.6 row 10) |
| Skills | `h-agent-structure`, `h-codebase-orientation`, `h-frontend-conventions`, `h-frontend-design`, `h-knowledge-ops`, `h-mcp-memory`, `h-memory-structure`, `h-module-design`, `h-pytest-and-linting`, `h-python-conventions`, `h-visual-output`, `h-vitest-and-linting`, `r-challenger-protocol`, `r-doc-standards`, `r-workspace-governance`, `w-idea-refinement`, `w-knowledge-enrichment`, `w-mem-curation`, `w-research`, `w-test-curation` | 20, 3,529 | 12 (row 11) |
| Prompts → skills | `ideate`, `kb-ingest`, `kb-enrich`, `test-curation`, `memory-audit`, `arch-audit`, `architecture-review`, `frontend-audit`, `legacy-audit` | 9, 820 | 9 (row 12) |
| Instructions | Six stubs in `share/instructions/` | 6, 136 | — |
| Dev-only | `.owlbear/skills` (3), `.owlbear/instructions` (3), `.owlbear/prompts` (4), `.github/prompts` (2) | 12 | — |

**Where it moves:**

| Content | Target | Loaded by |
| --- | --- | --- |
| Product agents and skills, converted prompts | New plugin root `plugin/` (working name) per the Agent Plugins spec, option C3 of C05 | Harness via `chat.pluginLocations` (dev) or user-level plugin install (consumers), never in the project; Local via the same setting |
| Product instruction stubs | Dev: `.github/instructions/`; consumers: installed user-level with the skills, never copied into the project (DR14) | Harness and Local |
| `owlbear-system` instructions | Merged into [.github/copilot-instructions.md](../../.github/copilot-instructions.md) and the seed copy; Delivery text rewritten at M6 | Harness (probe row 7) and Local |
| Dev-only skills, prompts, instructions | `.github/skills/`, `.github/instructions/` (already consumer-excluded) | Harness and Local |
| Delivery-next worker agents and craft | Inside the new package, passed to SDK sessions; rewritten from `designer`, `planner`, `builder`, the challengers, `build-reviewer`, `h-ac-quality` | SDK only; not E1 |
| Interactive brief-shaping skill | `plugin/`, authored new in M4 | Harness |

Surviving content moves out of `share/`, not copied, so Local never sees two definitions of one
name. Delivery content refers to nine surviving skills and agents by name only (no `share/` paths;
C07), so the open Changes keep resolving them from the plugin root.

**Prompt → skill conversion.** Each prompt becomes a skill with the same name, so `/ideate` and the
other slash commands keep working (probe row 7). A prompt that only invokes one workflow skill
becomes a short skill that names it; `agent:` frontmatter becomes an instruction to run that agent.

**MCP registration.** A new root `.mcp.json` takes servers one at a time; each server lives in
exactly one file. Order: `markitdown` and `owlbear-browser` first (no workspace binding); then
`owlbear-memory` and `owlbear-knowledge` once they resolve the primary worktree through
`git rev-parse --git-common-dir`, because repo `.mcp.json` servers start in the session worktree
(C05 §3.2). `owlbear-delivery` stays in `.vscode/mcp.json` until M6.

**Guards.** Agent `hooks:` run only in Local (C05 §3.5). `conceptual-design-reviewer` gets a
read-only `tools:` allow-list. `test-curator` keeps its Local hook until a repository hook that
filters by agent is proven; until then its guard is advisory under the harness.

**E1 probes** (each a few minutes, in the sandbox): (a) a `chat.pluginLocations` plugin exposes one
agent and one skill in a harness session and in Local; (b) a `.mcp.json` server is visible in both
and not duplicated; (c) an `applyTo` instruction in `.github/instructions/` applies in the harness.
If (a) fails, product agents and skills go to `.github/agents/` and `.github/skills/` instead
(proven, probe row 6–7): the manifest lists product skill directories individually, and for
consumers setup installs them user-level (`~/.copilot/skills/`), never into the project (DR14).

**E1 done:** ideate, memory curation, knowledge ingestion and the audits run in a harness session;
`/continue-change` still runs in Local for the open Changes.

### 3.4 Cutover gates and order (M6)

Cutover is: the open Changes finish on the old engine (TD-2), then one deletion PR. OwlBear's own
development is not switched (TD-10).

| Gate | Condition | Checked by |
| --- | --- | --- |
| G1 | M3 approved by the user (D1–D5) | User |
| G2 | M4 exit criterion met on the sandbox, including the interruption case | Demonstration record |
| G3 | Two Changes merged in consumer projects (M5); every finding fixed locally or returned to M3 and closed | PR links |
| G4 | B1 `macos-managed-browser-authentication`, `memory-revision-binding` and `static-website-knowledge-ingestion-v2` each completed and cleaned up on the old engine, or parked by the user's explicit decision | User, Cockpit history |
| G5 | No old-engine worker or claim running; no retained Change worktree without a decision | Cockpit (old view) |
| G6 | Before a lane worktree is retired, its committed, dirty and untracked work and detached heads are preserved; otherwise the exact worktree is kept. A branch alone does not preserve dirty or untracked files | User |
| G7 | Charter size and style rules hold for the new core (M7 tests) and E1 is done | Rule tests |

A parked Change keeps its branch and PR in git and GitHub. It restarts as a new Change on the new
core whose brief names that branch; old state is not migrated.

**Deletion PR on OwlBear's repository** (one PR on `dev`, user-approved):

1. Tag the current `dev` head `delivery-v1-final` and push the tag; it is the archive and rollback
   point.
2. Remove `owlbear-delivery` from `.vscode/mcp.json` and the `chat.*FilesLocations` settings;
   register no new core for OwlBear (TD-10).
3. Move the Changes page and host routes into Cockpit; remove Cockpit's unconditional old-engine
   imports and routers (`main.py` L40–L47 with the `target_work` router; the `atomic_write` import
   in `routes/ideas.py`, repointed to the copied module) and the checkpoint supervisor.
4. Delete §3.6 rows 1–14 and apply the edits listed under the table.
5. Rewrite the product documents (§3.7).
6. Prove: `uv run test`, `npm test` and `uv run test-e2e` pass; the new core's rule tests pass; one
   sandbox consumer Change starts from a fresh setup, reaches its first `done` exit and shows one
   status line.
7. Merge. Stop the old launchers (`.owlbear/controller/bin/cockpit`, `bin/delivery-mcp`); OwlBear
   development continues directly in chat.

**Switch for consumers** (no consumer uses the old Delivery):

1. In the same PR: `setup/init.py` stops writing `.owlbear/delivery/config.json` and the state branch
   setting and writes the new registration, plugin location and project profile (D4); re-running
   setup removes an existing `owlbear-delivery` entry. Seed `mcp.json` and `settings.json` follow.
2. Sync manifest: drop the `delivery` scope paths, sync the `delivery-next` scope by default, add
   `plugin/`, remove the `share` scope; update the `sync_delivery` and `sync_delivery_next` inputs of
   [sync-to-main.yml](../../.github/workflows/sync-to-main.yml).
3. Dispatch `sync-to-main` with all scopes after the merge; run setup on a fresh clone of `main`
   into the sandbox and walk J0.

### 3.5 Rollback

| Failure | Action |
| --- | --- |
| A gate fails before the PR merges | Do not merge; old path untouched |
| The deletion breaks OwlBear or the new core fails for consumers after the merge, inside the retention window | `git revert` the deletion PR; this restores the `owlbear-delivery` registration and Local locations. Restart the retained old launchers (`.owlbear/controller/bin/cockpit`, `bin/delivery-mcp`). The pinned release is self-contained (`git archive` plus its own `.venv`), and state, worktrees and refs were kept, so the old engine resumes. Re-dispatch `sync-to-main` from the reverted `dev` |
| A Change already started on the new core | Keeps its state but stays paused until a compatible host runs again; its state is not converted back |

The retention window ends when two more Changes have merged on the new core in consumer projects.
Then, with the
user's confirmation for each destructive step: remove `.owlbear/controller/`,
`.owlbear/delivery/` (42 tracked files, 3,189 lines; 3.0 GB of worktrees),
`.owlbear/delivery-migrations/`, the remote branch `owlbear/delivery-state`, the 23
`refs/owlbear/*` refs, and the Delivery lines of `.owlbear/.gitignore`.

### 3.6 Deletion list

Measured at `dev` on 2026-10-10 (C07). "Copied first" means copied into the new package before the
deletion PR, per the route comparison §3.4.

| # | Group | Paths | Files | Lines | Copied first |
| --- | --- | --- | --- | --- | --- |
| 1 | Engine | `serve/delivery/` (55 modules 60,824; tests 143 files 86,366; packaging 270) | 200 | 147,460 | `remote_git`, `git_executable`, `storage_io`, `publication_provider`, `merge_offer`, `merge_approval`, `worker_stall`, `acceptance_criteria` (2,215 lines) |
| 2 | MCP server | `serve/delivery-mcp/` (64 tools) | 10 | 9,588 | None; new tools follow T1–T8 |
| 3 | GitHub adapter | `serve/delivery-github/` | 11 | 5,560 | `github.py`, `effect_launcher.py`, `memory.py` (2,344), adapted |
| 4 | Controller tools | Under `serve/tools/`: `src/owlbear_tools/delivery_*.py` (6), `scripts/delivery-diagnose`, `tests/test_delivery_*` (6), `tests/fixtures/delivery_lc` | 14 | 10,013 | None |
| 5 | Cockpit backend | `routes/target_work.py`, `target_models.py`, `target_context.py`, `tests/test_target_context_startup.py` | 4 | 1,875 | None |
| 6 | Cockpit views | `api/workItems.ts`, `CompletedHistoryWorkspace`, `DeliveryPrimitives`, `DesignWorkDetail`, `DesignWorkSection`, `MergeApprovalDialog`, `PortfolioOperatingSummary`, `WorkItemDetail`, `WorkPortfolioTable`, `designWorkPresentation`, `workItemPresentation`, `useWorkItems`, `WorkPortfolioPage`; `useCleanupFlow` stays (it implements `useMemoryPurgeFlow` for `MemoryTab.tsx`) | 13 | 8,394 | Patterns only (table, merge dialog), per D4 |
| 7 | Cockpit unit tests | `__tests__/WorkItemDetail.*` (8), `WorkPortfolio*` (6), `workPortfolioHarness.tsx` | 15 | 8,224 | None |
| 8 | Cockpit e2e | `e2e/work-portfolio.spec.ts`, `support/seed-work-portfolio-delivery.py`, `start-work-portfolio-stack.mjs`, `fake-gh.mjs` | 4 | 2,562 | `fake-gh.mjs` if D4's proof needs it |
| 9 | Workspace tests | `tests/test_delivery_journey.py`, `test_delivery_worktree_authority.py`, `test_cockpit_work_items.py`, `tests/fixtures/delivery-authority/` (26) | 29 | 7,445 | None |
| 10 | Agents | `orchestrator`, `planner`, `builder`, `finalizer`, `repairer`, `designer`, `designer-challenger`, `planner-challenger`, `build-reviewer` | 9 | 955 | Craft rewritten, not copied |
| 11 | Skills | `w-orchestration`, `w-packet-building`, `w-frontier-planning`, `w-design-session`, `w-change-finalization`, `w-delivery-attention-resolution`, `w-delivery-repair`, `w-target-conflict-resolution`, `w-address-pr-feedback`, `h-ac-quality`, `h-decision-requests`, `h-process-observations` | 12 | 2,914 | Craft of `h-ac-quality` and the Builder and Planner checklists rewritten |
| 12 | Prompts | `continue-change`, `design`, `inspect-change`, `finalize-change`, `address-pr-feedback`, `repair-delivery`, `resolve-delivery-attention`, `resolve-target-conflict`, `upgrade-delivery` | 9 | 233 | None |
| 13 | Seed | `seed/.owlbear/delivery/runtime/host.json` | 1 | 5 | None |
| 14 | Research | 53 superseded Delivery documents (`delivery-*` except `delivery-next-*`, the rebuild research and the tool-surface audit; `change-continuation-delivery-redesign`, `target-delivery-information-flow-*`, `agent-driven-delivery-redefinition`, `cockpit-delivery-admission-visibility-remediation`, `user-delivery-cockpit-flow`) and `cockpit-work-items-redesign-evidence/` (5) | 58 | 28,673 | Archived by the `delivery-v1-final` tag; links from kept documents point to it |
| | **Total** | | **389** | **233,901** | 4,559 lines copied |

Code and tests (rows 1–9, 13) are 301 files and 201,126 lines; agent content (rows 10–12) is 30
files and 4,102 lines; research is 58 files and 28,673 lines. The 64 MCP tools and the six
controller console scripts (`delivery-controller`, `delivery-lc`, `delivery-migrate`,
`delivery-repair`, `delivery-diagnose`, `target-branch`) disappear with rows 2 and 4.

**Edits in the same PR:** root `pyproject.toml` (`pythonpath` and three ruff `src` entries);
`serve/cockpit/pyproject.toml` and `serve/tools/pyproject.toml` (old dependencies and scripts);
`serve/tools/src/owlbear_tools/project.py`, which imports `_delivery_config_status` from
`delivery_config` (remove or replace the old Delivery diagnostic; `doctor`, `setup-project` and
`hooks-install` keep working), and its entries in the command catalogue `commands.py`; `uv.lock`;
`setup/init.py` (Delivery config and registration); seed `mcp.json` and `settings.json` L63–L64;
`.vscode/mcp.json`, `.vscode/settings.json`; sync manifest and `sync-to-main.yml`;
`.owlbear/scripts/validate_agents.py`; and the tests that name the old engine
(`test_cockpit_boundary`, `test_package_boundary`, `test_agent_ecosystem_validation`,
`test_sync_manifest`, `test_setup_init_settings`, `test_setup_init_uninstall`, `test_init_exports`,
`test_dependency_verification_workflow`, `test_linter_formatter_policy`).

**Review at cutover, delete if unused:** `.owlbear/hooks/lint-changed.py` and `session-context.py`
(used only by `builder`), `deny-writes.py` and `deny-src-writes.py` once E1 guards replace them,
their `seed/.owlbear/hooks/` copies and their tests; `share/README.md`, `share/WIRING.md` and
`share/diagrams/` move to `plugin/` or are rewritten.

### 3.7 Documentation updates

| Document | Change |
| --- | --- |
| [README.md](../../README.md) | Replace the Delivery description with the new journey in five lines and link the operating guide |
| [README-consumer.md](../../README-consumer.md) | Install: plugin location, `.mcp.json`, profile confirmation, host start permission; remove the old Delivery section |
| [setup/setup-guide.md](../../setup/setup-guide.md) | Copilot harness as the default session target; setup steps of J0; no controller |
| [setup/operating-owlbear.md](../../setup/operating-owlbear.md) | Replace the Delivery chapters (74 mentions) with start, status, answers, person-only checks, automatic merge and pull-back; remove repair, attention, upgrade and target-conflict procedures |
| [setup/sharing-guide.md](../../setup/sharing-guide.md) | Plugin instead of `chat.*FilesLocations`; drop stance-hook text if the hook goes |
| [.github/copilot-instructions.md](../../.github/copilot-instructions.md) | Remove "Direct Delivery Redesign"; update branch contents, directory table (`plugin/`, `.github/agents`, `.github/skills`) and test mapping; take over `owlbear-system` content |
| [cloud-agent.instructions.md](../../.github/instructions/cloud-agent.instructions.md) | Remove "Delivery Redesign Tasks" |
| [sync-manifest.json](../../.github/sync-manifest.json) | Scopes as in §3.4 consumer step 2 |
| `serve/README.md`, `.owlbear/README.md` | Package and directory tables |

### 3.8 Risks

| Risk | Mitigation |
| --- | --- |
| Local removal is announced before G4 | E1 first, so only the old Delivery depends on Local; turn off VS Code auto-update on the user's machine for the old path; ask the user to finish or park the open Changes early |
| An open Change never finishes | G4 accepts an explicit park; branch and PR stay; restart as a new Change on the new core; no state migration |
| A consumer already set up with the old Delivery | None exists (user); re-running setup removes the old entry; the release note names the old `.owlbear/delivery/` files the user may delete |
| A controller upgrade for an open Change picks up the new package | `--locked --package` installs only controller packages; one-way isolation (§3.2 step 2); live-compatibility gate before upgrade |
| A partial `share` or `infra` sync to `main` between the first E1 move and cutover publishes the new package in a lock or drops moved content from consumer `share/` | No such sync unless projection, loading configuration and lock membership move together (§3.2 step 5) |
| Harness sessions see the old `owlbear-delivery` server through the forwarded `.vscode/mcp.json` | Delivery skills stay Local-only; operate old Changes only from Local chats |
| Repo `.mcp.json` memory or knowledge server writes into a session worktree | Register them only after primary-worktree resolution (§3.3) |
| Plugin or instruction loading behaves differently than documented | E1 probes (a)–(c); `.github/` fallback |
| A lane holds unpreserved work on deleted paths | G6 |
| Deletion breaks surviving code | Edit list in §3.6; full suites in switch step 6 |
| Kept research links break | Rewrite them to the `delivery-v1-final` tag |

## 4. Recommendation, Confidence, and Limits

**Recommendation (`autonomous`):** keep the old path frozen and untouched except for M0 fixes, add
the new package with one-way isolation and no OwlBear registration (TD-10), do E1 now for
non-Delivery content only, let the open Changes finish on the old engine (TD-2), then switch
consumers and delete the old engine in one reviewed deletion PR after G1–G7, with the
`delivery-v1-final` tag and the retained pinned release as the rollback path. Decisions for
the user: the content home (plugin root, or `.github/` copies if probe (a) fails), and the
retention-window condition (two more Changes merged in consumer projects).

**Confidence:** high for the coexistence rules and the deletion inventory (measured, import-checked).
Medium for E1 locations: plugin and instruction loading in the harness is documented and statically
read, not live-probed. Medium for rollback after the merge: it relies on the self-contained release,
which has not been exercised with its source removed.

**Limits:** counts are `git ls-files` plus `wc -l` and include tests, blanks and docstrings. Lane
worktrees, live Delivery state and running processes were not inspected. D4 decides the new status
view, the package name and the project profile; this plan only fixes when and where they switch.
