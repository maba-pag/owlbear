# OwlBear Plan and Status

> **Owning task:** owner request 2026-10-19: one document that grounds any session in what is built, what comes
> next and where the code differs from the decisions
> **Date:** 2026-10-19, status at `main` `8248e1e97` (#500), decisions to TD-403
> **Question:** Where does OwlBear stand, in what order does the remaining work come, and where does the code
> differ from the decisions in force?

Read this first when you start or resume work, and again after a context compaction. The owner's decisions are
in [the decision record](delivery-liveness-first-rebuild.md) (topics C-01 to C-31 and the standalone decisions);
how each part is built is in its build document (§6). This file holds only status, order and gaps. Keep it current
as §7 says.

## 1. Status Quo

**Product.** OwlBear Delivery (`serve/delivery-next`, package `owlbear_delivery_next`) is the only Delivery that
runs: one machine host serves every registered project with one UI (Changes, Backlog, Memory, Settings, Maintenance).
The old engine is retired (TD-202) but its source is still in the repository: `serve/delivery`, `serve/delivery-mcp`,
`serve/delivery-github`, the controller tools, Cockpit's Changes surface and the old agents, skills and prompts in
`share/`. Its deletion is plan item 7.

**Use.** No real project uses OwlBear (TD-338); this laptop is the only instance. Two sandbox projects are
registered: `owlbear-sandbox` and `owlbear-sandbox-protected`. OwlBear itself is developed in chat (TD-319 allows
both), through pull requests to `main` with the required `CI` check, strictly up to date, merged as merge commits.

**Runtime.** `~/.owlbear/runtime` is a clone at `origin/main` (`23bd7c1ab`), deployed by hand after each merge
(TD-289, TD-309): stop, check out `origin/main`, `uv sync --locked`, start, Resume. Every start is paused today,
against TD-350 (§4).

**Versions.** The release workflow tags labelled merges (`release:minor`, `release:major`) once their push `CI`
passes; the switch `RELEASE_TAGS` is on since 2026-10-19 14:39Z. Tags `v0.1` to `v0.9` exist (`v0.9` is #499). The
walk creates tags through the REST API with the owner's fine-grained token `RELEASE_TOKEN` (Contents and Workflows
write, TD-404), since GitHub refuses the workflow token tags on commits whose workflow files differ from every branch
tip; a major gets `vN.0` and `vN` (TD-392). The token expires; the owner renews it.
Renovate's pull requests are left alone until the old engine is gone (owner, 2026-10-19).

**Built, by build document:**

| Area | Build document | Pull requests |
| --- | --- | --- |
| The engine and the whole journey, shaping to cleanup, visual check, design pack | [architecture](delivery-next-architecture.md), [design skill](delivery-next-design-skill.md) | #449 |
| Review and challenge rounds for every role (TD-208, steps 1 to 8) | [challenge rounds](challenge-rounds-build.md) | #449; steps 6 to 8 as commits before the PR route |
| Pull requests with required CI (TD-278) | [PR, CI, merge queue](pr-ci-merge-queue-build.md) | #455 to #458 |
| Merge-queue support (TD-226) | [PR, CI, merge queue](pr-ci-merge-queue-build.md) | commits before the PR route, `0d4272eef` and its repairs |
| Per-role session time limits, doubled (TD-286) | — | #460 |
| Pages on lit-html (TD-264), machine host, one UI, Global memory, SQLite stores, settings across projects | [machine host](machine-host-build.md) | #461 to #469, #471 |
| Self-update steps 1 to 3b: machine settings, Pause, paused maintenance, PR labels, push CI, release walk | [self-update](self-update-build.md) | #473, #476, #478, #480 to #482 |
| Test curation of delivery-next (TD-311, TD-312) | — | #477 |
| Decision review TD-319..TD-381: Snyk Code and Renovate, Cyclopts, subagents per role, owner notes as written | the record | #483, #487 to #489, #492, #494, #495 |
| The machine preference layer and session limits (TD-336) | [settings scopes](settings-scopes-build.md) | #496, #497 |
| The test review from the Maintenance page (C-26) | [test review](test-review-build.md) | #498, #499 |

## 2. The Plan

The order is the owner's (TD-394): TD-358's build work, the research move, self-update steps 3c to 5, the old
engine's removal, v1.0, TD-318's memory work, the window-step gate, the watcher; TD-403 places the build work of
TD-392..TD-402; TD-338 puts the watcher before any real project. Item numbers are stable names, not positions:
the table lists the items in their order.

| # | Work | Decided by | Build document | Status |
| --- | --- | --- | --- | --- |
| 1 | TD-358's rest (TD-330, TD-334, TD-335, TD-345, TD-350); built: TD-328, TD-341, TD-347's skill, TD-392, TD-396, TD-397, TD-399 (§3.1) | TD-358, TD-403 | none yet; TD-330 extends [challenge rounds](challenge-rounds-build.md) | In progress |
| 6 | Research move: OwlBear's research into `owlbear-data`; the decision record, this plan and build designs of unbuilt work stay (§3.3) | TD-227, TD-347, TD-395, TD-394 | none yet | Not started |
| 2 | Self-update step 3c: design pack updates through a pull request, with C-15's updater and challenger rules | TD-325, TD-357, TD-368, TD-194, TD-177 | [self-update §8](self-update-build.md) "Step 3c build" | Planned, Sol-challenged |
| 3 | Self-update step 4: `repo.git`, versions, never backwards, selfcheck, standby, handover, Run updates now | TD-239, TD-299, TD-300, TD-352..TD-354, TD-369 | [self-update §3–§5, §11](self-update-build.md) | Not started |
| 4 | Self-update step 5: idle, use, announcement, automatic updates | TD-301, TD-288 | [self-update §7, §11](self-update-build.md) | Not started |
| 7 | Old engine removal: tag `delivery-v1-final`, five dependency-closed batches, three skills retired with batch 3, docs rewritten | TD-199, TD-201, TD-203, TD-394 | [transfer ledger §3.4](delivery-next-transfer-ledger.md), [cutover §3.3, §3.6, §3.7](delivery-next-cutover.md) | Not started |
| 11 | Pages: the PDS fallback and notice removed, browser tests on the real CDN; then pages, scripts and styles split to the 500-line limit (§3.4) | TD-39, TD-398, TD-401, TD-403 | [visual baseline §3.6](delivery-next-visual-baseline.md) for the removal | Not started; any time before item 12 |
| 12 | v1.0: the first `release:major` merge, tagged `v1.0` and `v1` | TD-393, TD-392 | [self-update §4, §8](self-update-build.md) | After items 1, 6, 2, 3, 4, 7 and 11 |
| 5 | After v1.0: project agents and skills off in steps (TD-274's gap); the memory work: curator modes and threshold (95%), moving an entry back, the saver's pre-set, sorting existing project memories once | TD-317, TD-329; TD-292, TD-293, TD-318, TD-400 | none yet | Not started |
| 8 | Window-step gate: windows keep repository hooks and user MCP servers out, subagents detected and counted, judge effects contained | TD-223, TD-145, TD-342 | none yet | Not started; no design |
| 9 | Watcher: TD-27's benchmark, then the design session (O1–O6) with the owner, then the build and its proof | TD-224, TD-316, TD-365, TD-378, TD-47 | [watcher design](delivery-next-watcher-design.md), [options](delivery-next-watcher-options.md) | Not started; the draft needs revising (§3.5) |
| 10 | First real project: the per-project GitHub account setting first; memory publication and curation (F17) fixed; two Changes merged in consumer projects; OwlBear builds itself through Delivery | TD-338, TD-402, TD-90, TD-319 | none yet | Waits for item 9 |

**Not yet placed** (decided or planned, no position in the order):

- Visual baseline: "before" captured in shaping, retake, preview ports (TD-38, TD-40); its PDS part is item 11. The
  repair plan of 2026-10-11 put it after the watcher, because its live proof needs a runtime the owner can follow.
  [Plan](delivery-next-visual-baseline.md), nothing built.
- The amendment design (TD-185): its design session with the owner comes before any amendment code (C-14).
- The quality service (TD-89): [research](repo-quality-service.md), not built.
- Contradicting findings of the two visual judges go to the owner ([design skill §3.5](delivery-next-design-skill.md));
  they are not detected (§3.7 there).
- An organisation with the merge queue for OwlBear's `main`, once someone else contributes or Delivery builds
  OwlBear (TD-326).
- The "align" fixes of §4 that belong to no item above: small, each its own pull request.

**The old roadmap.** The roadmap M0–M7 and the repair plan of 2026-10-11 are history at `04b1d8ec4` (§3.7 and §3.12
of the old record). Older documents still name their milestones: M0 to M4 are done (M4 is #449 and what followed);
E1 is part of item 7; M5 is item 10; M6 is item 7; M7's size and style rules are C-28. The repair plan's phases 1
and 2 are done, phase 3 is item 9, phase 4 is the visual baseline, phase 5 was replaced by the runtime design, and
of phase 6 the collision rule (C3, TD-12) is built and the change of mind (C5) is the amendment design.

## 3. Next Steps in Detail

### 3.1 Item 1: TD-358's remaining build work and TD-403's small items

TD-358 ("All of it now, before self-update step 3b") was recorded after step 3b had merged (#481), so it is read as
"before the rest of the self-update"; TD-394 confirms it comes first. The audit of §4 found the eight below unbuilt;
the range's other rows are built, history, or part of steps 3c and 4 (TD-325, TD-352, TD-353, TD-357). TD-403 adds
the small items of 2026-10-19. Built since: TD-392 (#502), TD-328, TD-341, TD-347's skill, TD-396, TD-397 and TD-399,
with the C-02 catalogue text. Remaining:

| Decision | What is missing |
| --- | --- |
| TD-330 | Every loop's last round gets one rejections-only check outside the round count; all five loops still follow TD-218 |
| TD-334 | Each project's live database lives under `~/.owlbear`, one folder per project; it is still in the clone's Git folder |
| TD-335 | `owlbear install` asks for the `~/.copilot` shaper links and uninstall removes them; neither does today |
| TD-345 | Backlog repeats merge only when they name the same projects (or both none); they merge by origin today |
| TD-350 | Only a login-item start and a start after a crash are paused; `owlbear restart` keeps its state; a `--paused` start; every start pauses today |

### 3.2 Items 2 to 4: the self-update

[Self-update §8](self-update-build.md) "Step 3c build" is the plan for item 2. It also brings the updater and
challenger in line with C-15: the updater may change its whole candidate in its own folder, a detector code change
waits for the owner's approval (TD-194); a change to expected evidence asks the owner instead of failing the run
(TD-177); the challenger checks that each change is needed and lists every changed file (TD-194). Steps 4 and 5 are
§3–§5 and §7 there.

### 3.3 Items 6 and 7: research move, then (after the self-update) the old engine

The research move needs a short design: which documents move (TD-395 keeps the decision record, this plan and the
build designs of unbuilt work here, since GitHub's agents and reviewer read only this repository; they move once
history), how links from kept files and agents point there, and where agents write research from then on (C-09:
never into a consumer project). The removal follows the self-update (TD-394) and the ledger's batches 1 to 5 (the
`main` sync batch is gone, TD-203) with the tag first; its precondition for batch 2 (the new Changes page reachable)
holds. It rewrites the documentation v1.0 needs (TD-393). Open issues #225 and #400 and pull requests #405 and #412
belong to the old engine and close with it; Renovate's pull requests come back after it.

### 3.4 Items 11 and 12: pages, then v1.0

The PDS fallback goes as the [visual-baseline plan §3.6](delivery-next-visual-baseline.md) lists: the 3-second
decision, the `pds` flag, every native-control branch, the `.no-pds` CSS and its notice; the browser tests let
`cdn.ui.porsche.com` through instead of aborting it (TD-398). Then the module test covers pages, scripts and styles
and the large pages split by section (TD-401): `changes.html` 1517 lines, `config.html` 1121, `backlog.html` 544.
v1.0 is the first merge labelled `release:major` after items 1, 6, 2, 3, 4, 7 and 11; it is tagged `v1.0` and `v1`.

### 3.5 Items 8 and 9: gate, then watcher

Neither has a build design. The watcher draft predates TD-320 and TD-365: it assumes the SDK guard denies outside
writes (TD-45, replaced), while now nothing blocks them and the watcher judges each one afterwards. It must be revised
before the owner's design session, which comes when window steps are about to return (TD-224, TD-316). TD-27's
benchmark runs before the watcher's model is chosen (TD-378).

## 4. Where the Code Differs From the Decisions

Audit of every in-force line of the record against `main` `23bd7c1ab` on 2026-10-19 (eight read-only reviews,
key gaps confirmed in the code), updated for the owner's answers TD-392..TD-403 the same day. Only gaps are listed;
every other line is built as decided. Action: **align** the code to the decision, **build** planned work, **keep**
as is for the reason given. Item: the plan item of §2 that picks it up.

| Line | Decision | Code today | Action | Item |
| --- | --- | --- | --- | --- |
| C-01 | Read-backs offer close variants and other directions, the opposite among them, then "take your recommendation (…)" | `w-idea-refinement` offers no opposite and no named recommendation | align | — |
| C-01 | A question shows the record's words and what changed | The shaping skill and `w-idea-refinement` say never to quote the record | align | — |
| C-01 | In doubt, ask about the direction first and say why | The shaper does not say why | align | — |
| C-01 | "Take your recommendation" is recorded `autonomous` with its reason | Brief decisions have no reason field | align | — |
| C-03 | TD-27's benchmark, then the watcher's model | Not run | build | 9 |
| C-04 | The watcher reads, judges and stops every runtime; it is on the real-use list | Not built | build | 9 |
| C-04 | Window steps reopen only after the gate | Gate not built, no design | build | 8 |
| C-04 | A missing tool reruns once in a runtime that has it | No other runtime while window steps are paused | keep | 8 |
| C-05 | The repository's instructions apply, Delivery's format wins, a clash asks | Agents are not told which wins | align | — |
| C-05 | Project agents and skills off in steps after self-update step 5 | Discoverable, allowed until then (TD-329) | build | 5 |
| C-06, C-08 | The `~/.copilot` shaper links are asked at install and removed at uninstall (TD-335) | Not handled by install or uninstall | align | 1 |
| C-08, C-19 | Live databases under `~/.owlbear`, one folder per project (TD-334) | In the clone's Git folder | align | 1 |
| C-09 | `owlbear-data` holds OwlBear's research too; the record, the plan and unbuilt build designs stay (TD-227, TD-395) | Still in this repository | build | 6 |
| C-11 | Shaping captures the target pages; approval waits for them (TD-38) | "Before" is taken at the check | build | visual baseline |
| C-11 | A target whose UI changed since shaping gets a retake | Partly | build | visual baseline |
| C-12, C-15 | Last round's rejections get one rejections-only check outside the count (TD-330) | TD-218's behaviour in all five loops | align | 1 |
| C-14 | Bounded delegation, the "weaker" rule, the amendment process, fields and baseline | Partly; blocked by the open design TD-185 | keep | not placed |
| C-15 | The updater may change its whole candidate; a code change waits for approval (TD-194) | It may edit only skills | align | 2 |
| C-15 | A change to expected evidence asks the owner (TD-177) | The run ends failed | align | 2 |
| C-15 | The challenger checks each change is needed, listing every file (TD-194) | Missing | align | 2 |
| C-15, C-16 | Every pack update opens a labelled PR, merges on green and becomes a version | Pushes a branch | build | 2 |
| C-16 | OwlBear's own project sets `release:minor` | OwlBear is not a registered project | keep | 10 |
| C-16 | Chat-authored PRs get `release:minor` for runtime changes (TD-314) | Written nowhere agents read | align | — |
| C-16 | v1.0 after the self-update and the old engine's removal, docs rewritten (TD-393) | Not yet | build | 12 |
| C-17 | Take the newest version, never backwards, idle updates, Run updates now, back as it was | Steps 4 and 5 | build | 3, 4 |
| C-18 | Only login and post-crash starts pause; restarts keep their state (TD-350) | Every start pauses | align | 1 |
| C-18 | Paused pages offer Run updates now; the stop-when-idle choice hides with Update while paused off | Step 4 | build | 3 |
| C-18 | The Pause tooltip says plain Pause may still update | Missing | align | 3 |
| C-19 | The maintenance overview includes the engine update | Step 4 | build | 3 |
| C-19 | Linux and Windows stated as not supported yet | `README-consumer.md` and `setup/setup-guide.md` claim Linux support | align | 7 |
| C-20 | OwlBear builds itself through its own Delivery (TD-319) | Developed in chat only | keep | 10 |
| C-21 | Old engine batches with the tag first; three skills retire with batch 3 | Not started | build | 7 |
| C-24 | Backlog repeats merge only for the same named projects (TD-345) | Merged by origin | align | 1 |
| C-25 | The saver recommends a scope (TD-293) | Missing | align | 5 |
| C-25 | A Global entry can move back to a project (TD-292) | The page says it does not move back | align | 5 |
| C-25 | Curator modes and the Global threshold, 95% at first (TD-292, TD-400) | Missing | build | 5 |
| C-25, C-27 | The watcher saves lessons and infers stages | Not built | build | 9 |
| C-26 | Tests do not assert prose wording | Workspace tests assert skill prose (`tests/test_agent_ecosystem_validation.py`) | align | — |
| C-28 | Tool use is measured, success rates included (T8) | Success rates are not counted | align | — |
| C-28 | The 500-line limit covers pages, scripts and styles; tests do not (TD-401) | Only Python sources are checked (`changes.html` has 1517 lines) | align | 11 |
| C-28 | Default rules guide, never gate | Ruff's complexity rule fails CI; `noqa` is the escape | keep | — |
| C-30 | Every role may use built-in subagents | Not in window steps | keep | 8 |
| S | A project setting names the account for GitHub writes, by default the owner's when `gh` has it (TD-402) | `maba-pag` does everything; both sandboxes are `boecht`'s | build | 10 |
| S | PDS only from its CDN, no own fallback; browser tests reach the real CDN (TD-39, TD-398) | Pages have a fallback and a notice; the browser tests abort the CDN and run on the fallback | align | 11 |
| S | A quality service runs linters and judges exceptions (TD-89) | Not built | build | not placed |
| C-31 | In-force lines at most two lines; quotes one line | Seven lines and six quotes are longer | align | — |

Record repairs made with this document: the trim of 2026-10-19 had listed TD-228, TD-250 and TD-358 as spent,
dropped C-21's lines for TD-199 and TD-201 and cut TD-318's schedule to one of its four parts; they are back in force.

## 5. Open Questions for the Owner

Ask each with the question tool in the owner's format (workspace instructions, "Asking the Owner"). Answered on
2026-10-19 as TD-392..TD-403: the v1.0 tags and timing, the order of the remaining work, which saves confirm, the
test review while paused, the research move's timing and scope, the PDS fallback, which roles save memory, the
curator's threshold, what the line limit covers and the GitHub account.

1. When to hold the amendment design session (TD-185)?

## 6. Documents

| Document | Role | Status |
| --- | --- | --- |
| [Decision record](delivery-liveness-first-rebuild.md) | The owner's decisions in force, by topic | Current; the authority for intent |
| This file | Status, order, gaps, open questions | Current |
| [Self-update](self-update-build.md) | Build design of items 2 to 4 | Steps 1 to 3b built; 3c planned; 4 and 5 open |
| [Settings scopes](settings-scopes-build.md) | Machine layer and session limits | Built (#496, #497) |
| [Test review](test-review-build.md) | C-26's test review | Built (#499) |
| [Machine host](machine-host-build.md) | One host, one UI, SQLite, settings scopes | Built; TD-334 and TD-350 re-decided parts open (item 1) |
| [PR, CI, merge queue](pr-ci-merge-queue-build.md) | Pull request route and queue support | Built; its open pack route is item 2 |
| [Challenge rounds](challenge-rounds-build.md) | Review and challenge loops | Built; TD-330 open (item 1) |
| [Design skill](delivery-next-design-skill.md) | Design pack and screenshot judges | Built; contradicting findings not detected |
| [Visual baseline](delivery-next-visual-baseline.md) | TD-38 to TD-40 | Plan; not built; its PDS part is item 11, the rest not placed |
| [Watcher design](delivery-next-watcher-design.md), [options](delivery-next-watcher-options.md) | The watcher | Draft for the owner's session; to revise (§3.5) |
| [Transfer ledger](delivery-next-transfer-ledger.md) | What the old engine leaves; the deletion batches | Decided as TD-199 to TD-201; plan of item 7 |
| [Cutover](delivery-next-cutover.md) | D5: coexistence, E1, deletion list, docs list | Partly replaced by TD-199 and TD-203; input to item 7 |
| [Quality service](repo-quality-service.md) | TD-89's service | Research; not built |
| [Charter](delivery-next-charter.md) | The approved charter of 2026-10-10 | In force only where no later decision replaced it (TD-23); the record wins |
| [Architecture](delivery-next-architecture.md), [status and exits](delivery-next-status-and-exits.md), [journey](delivery-next-journey-and-failure-modes.md), [glossary](delivery-next-glossary.md) | The design of 2026-10-10..14 | History; the record and the code win |
| [Ownership map](delivery-next-ownership-map.md), [route comparison](delivery-next-route-comparison.md), [platform probe](delivery-next-platform-probe.md), [agent runtime](delivery-next-agent-runtime.md), [tool surface](delivery-tool-surface-audit.md), [reuse study](delivery-next-reuse-study-v2.md), [agents from old](delivery-next-agents-from-old.md), [ECC](ecc-evaluation.md) | Research behind the design | History |
| [Redesign execution plan](delivery-redesign-execution-plan.md) | The old engine's programme | Superseded (TD-202); history |
| Old record at `04b1d8ec4` | Every decision row as first recorded; roadmap M0–M7; repair plan | History: `git show 04b1d8ec4:.owlbear/research/delivery-liveness-first-rebuild.md` |

## 7. Keeping This File Current

- A pull request that starts or finishes an item, closes a gap of §4 or answers a question of §5 updates this file
  in the same pull request; the date and the `main` commit at the top move with it.
- A decision goes to the record (C-31), never here; an order the owner decides is cited here by its number.
- Build details stay in the build documents; this file links to them and holds no second copy.
- A new build document gets a row in §6 and its item in §2.
