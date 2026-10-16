# Delivery Next: Transfer Ledger and a Burndown Version of D5

> **Owning task:** none — night item 9 of 2026-10-16 (TD-183)
> **Date:** 2026-10-16
> **Question:** Which old Delivery artifacts are carried over, reused, still to carry or not needed; what is the
> state of the old engine's open Changes; and can D5's single deletion PR become a burndown that deletes each old
> piece once its replacement is in `dev`?
> **Status:** research for the owner's morning decision; Sol challenge recorded in §5. Nothing is deleted.

## 1. Context and Question

D5 ([cutover plan](delivery-next-cutover.md)) retires the old engine in one deletion PR (M6) after its open Changes
finish. TD-183 asked tonight for a transfer ledger (every old artifact: carried over to X / reused / still to carry /
not needed, with owner questions), the status of "the three open old-engine Changes", and a burndown version of D5:
the owner's idea "we can start deleting things from dev the moment we have transferred it into the new version".

## 2. Sources Studied

| ID | Source | Used for | Limits |
| --- | --- | --- | --- |
| S1 | [Cutover plan D5](delivery-next-cutover.md) §3.2, §3.6 | Deletion list (14 rows, 389 files, 233,901 lines), coexistence rules, M6 gates | Measured 2026-10-10 |
| S2 | Old engine's `list_changes` and `list_completed_changes` (MCP, 2026-10-16 04:44) | Open and completed Changes | Live state at that time |
| S3 | `owlbear-dev-next` at `a454c9539` (`serve/delivery-next/src/owlbear_delivery_next`) | What the new engine holds | One commit |
| S4 | `owlbear-dev` `dev`: `serve/cockpit/src/owlbear_cockpit/main.py` L40–L65, `target_models.py` L10–L44 | Live coupling of Cockpit to the old engine | Static read |
| S5 | A read-only Explore pass over both repositories | Candidate ledger rows | Its new-engine paths were partly wrong; every row below was re-checked against S3/S4 |
| S6 | [Decision record](delivery-liveness-first-rebuild.md) TD-2, TD-10, TD-163..183 | Which decisions bind the ledger | — |

## 3. Analysis

### 3.1 The old engine's Changes (S2)

TD-183 assumed three open old-engine Changes. The old engine reports **none unfinished**: 0 open, 12 completed (the
latest `macos-managed-browser-authentication`, 2026-10-11), and one unadmitted draft design,
`interactive-browser-tools` (stage design, never admitted; a backlog question, Q1). Completed is not cleaned up: one
retained worktree, `pr-feedback-replay-safe-resume`, is completed but blocked from cleanup (`git-registration-missing`,
`cleanup_blocked_reason: worktree-attention`). D5's other gates (G4 cleanup, G5 no worker or claim, G6 worktrees
preserved) were not checked tonight; "no open Change" is necessary for M6, not sufficient.

### 3.2 Transfer ledger (rows of D5 §3.6)

| # | Old artifact (D5 row) | Status | Evidence |
| --- | --- | --- | --- |
| 1a | Engine modules `serve/delivery/` (55 modules) | Not needed, except the copies below | The new loop replaces it (rebuild route R2+3) |
| 1b | Copy-first modules (8) | 3 copied, 3 adapted, 2 replaced | Copied: `remote_git`, `git_executable` (`next:git/`), `storage_io`. Adapted (file header names the source at `ab9cfc6cb`): `merge_offer` → `next:github/merge_offer.py`, `publication_provider` → `next:github/provider.py`, `worker_stall` → `next:process_probe.py`. Replaced by redesign: `merge_approval` (merge consent in `next:steps/merge.py`), `acceptance_criteria` (criteria in the brief and `next:worker_skills/owlbear-acceptance`); whether each old required behaviour survives is not proven by this ledger |
| 1c | Engine tests (143 files) | Not needed | The new package has its own suite (1,399 tests at S3) |
| 2 | MCP server `serve/delivery-mcp/` | Not needed | Owner chat tools in `next:mcp_server.py`, step tools in `next:step_mcp.py` |
| 3 | GitHub adapter `serve/delivery-github/` | Carried over | `next:github/` (gh client, checks, conversation, provider, merge offer) |
| 4 | Controller tools `serve/tools/delivery_*.py` (6) | Not needed | They install, pin, migrate and gate (`delivery_lc`) old-engine releases for open Changes; there are none (§3.1). `delivery_config` is imported by `owlbear_tools/project.py` (D5 "edits in the same PR") |
| 5 | Cockpit backend `target_work.py`, `target_models.py`, `target_context.py` | Carried over, **still wired** | Replaced by `next:api.py` + `next:web/changes.html`; Cockpit `main.py` L40–L63 still mounts `target_work_router` and `target_models.py` imports `owlbear_delivery` |
| 6 | Cockpit views (13) | Carried over (patterns) | `next:web/changes.html` (list, detail, approval, merge consent) |
| 7 | Cockpit unit tests (15) | Not needed | They test row 6 |
| 8 | Cockpit e2e (4) | Not needed | Same; the new pages have browser tests (`next:tests/test_approval_view.py`) |
| 9 | Workspace tests (29) | Not needed | They test rows 1–2 |
| 10 | Agents (9) | Carried over (rewritten) | `next:agents/*.md` (builder, planner, reviewer, challenger, designer, preparer, updater) + the shaper |
| 11 | Skills (12) | Carried over (rewritten), 2 owner questions | Loop skills replaced by the engine; `h-ac-quality` craft → `next:worker_skills/owlbear-acceptance`; `h-decision-requests` and `h-process-observations` are also used outside Delivery (Q2) |
| 12 | Prompts (9) | Not needed | One entry: the shaper chat (`next:skills/delivery/SKILL.md`) |
| 13 | Seed `seed/.owlbear/delivery/runtime/host.json` | Not needed | The new host has its own settings layers |
| 14 | Research (58 documents) | Not needed | D5: archived by the `delivery-v1-final` tag |

Counts: no old *code* is still to carry for the new engine to work; the remaining work is **integration and
retirement**, tracked per batch below: Cockpit row 5 still runs the old routes (`main.py` L40–L63) and imports the old
engine (`target_models.py` L10–L44); D5's "edits in the same PR" (root and package `pyproject.toml` files, `uv.lock`,
`owlbear_tools/project.py` diagnostics and the `commands.py` catalogue, `setup/init.py`, `.vscode/mcp.json` and
`settings.json`, seed `mcp.json`/`settings.json`, sync manifest and `sync-to-main.yml`, `validate_agents.py`, nine
named tests) and its "review at cutover" items (hooks and their seed copies, `share/README.md`, `WIRING.md`,
`diagrams/`) each belong to one batch. Two owner questions (§4).

### 3.3 The way into `dev` and `main`

- **Into `dev`:** PR #449 (`next/m4-slice1` → `dev`) is a draft titled "prototype; not for merge before charter
  approval". Its prerequisites are the charter approval (M3), then the M4 slice gates of the rebuild plan; until
  then nothing of the new engine is in `dev`, so no old row can be retired on the owner's rule "once its replacement
  is in dev". Per TD-10 OwlBear does not register the new engine for its own development.
- **Into `main`:** `main` is generated by `sync-to-main` from the sync manifest, which still publishes the old
  Delivery. D5 forbids partial publications before cutover: `main` changes once, when the manifest, workflow, setup,
  registrations and lock agree on the new engine. Burndown batches happen in `dev` only; `main` is synced after the
  last batch.

### 3.4 Burndown instead of one deletion PR

| Option | How | For | Against |
| --- | --- | --- | --- |
| A. D5 as planned | One PR deletes rows 1–14 at M6 | One review, one rollback point | A 233,901-line PR; nothing shrinks until then |
| B. One PR per row | 14 PRs | Smallest reviews | A row's tests would go before or after the code they protect; many green-keeping edits |
| C. Dependency-closed batches (recommended) | Each batch deletes production paths **with** their tests and the edits that unwire them, and its focused checks pass | `dev` shrinks soon (the owner's idea); each batch reverts alone | Needs the new engine in `dev` first (§3.3); several reviews |

Batches for C, in order (each with its tests, edits and checks):

1. Research row 14 and prompts row 12: no code depends on them; links from kept documents move to the
   `delivery-v1-final` tag. Check: link validation.
2. Cockpit Changes surface: rows 5–9 together (routes, models, views, unit and e2e tests, workspace tests), plus
   Cockpit's `owlbear_delivery` imports, `test_cockpit_boundary`. Precondition: the new Changes page reachable from
   `dev`. Check: Cockpit test suite and build.
3. Agents and skills rows 10–11 (except Q2's shared skills), with `validate_agents.py`,
   `test_agent_ecosystem_validation` and the `.vscode/settings.json` `chat.*FilesLocations` lines.
4. MCP server row 2 and controller row 4, with `.vscode/mcp.json`, seed `mcp.json`, `owlbear_tools` diagnostics and
   catalogue, `serve/tools/pyproject.toml`, the setup/init tests.
5. Engine rows 1 and 3 and seed row 13, with the root `pyproject.toml`, `uv.lock`, `setup/init.py`, the remaining
   named tests; then the hooks under review.
6. Sync manifest and `sync-to-main.yml`, then one sync to `main`.

**Rollback.** Tag `delivery-v1-final` before batch 1. Each batch is one revertible commit on `dev`; `main` is untouched
until batch 6, so a consumer needs no re-sync before then. The pinned controller releases, launchers and old live
state stay until D5's endpoint: two further consumer Changes merged on the new engine.

## 4. Recommendation, Confidence, and Limits

Recommend **C** (§3.4) on the route of §3.3. The main morning decision and three questions:

- **D** — approve revised C: batches in `dev` after PR #449 is approved and merged, one `main` sync after the last
  batch, the tag and retention as in §3.4?
- **Q1** — `interactive-browser-tools` (unadmitted draft design): carry it as a brief to the new engine, keep it as a
  backlog idea, or drop it?
- **Q2** — `h-decision-requests` and `h-process-observations` serve purposes outside Delivery: for each, which
  surviving purpose and where does it live after batch 3, or is it retired?
- **Q3** — the old live state (`.owlbear/delivery/`, 3.0 GB of worktrees; `owlbear/delivery-state`; 23
  `refs/owlbear/*`; the blocked `pr-feedback-replay-safe-resume` worktree): keep it until D5's endpoint (two consumer
  Changes merged on the new engine), or another condition?

Confidence: high for §3.1–§3.2 facts (each re-checked against S2–S4; Sol verified the module and Cockpit claims);
medium for the batch order (no dry-run deletion). Limits: line counts are D5's of 2026-10-10; G4–G6 not checked.

## 5. Sol Challenge

Sol (2026-10-16, 90% on the facts; three blocking, three should-fix): the way into `dev` and `main` was missing; the
batches deleted tests before the code they protect; rollback for several PRs was undefined; the inventory was grouped,
not every artifact; "4 reused" confused filenames with reuse; completed was promoted into cutover-ready. All six are
addressed above (§3.1, §3.2 row 1b and counts, §3.3, §3.4 batches and rollback, §4 D and Q2/Q3).
