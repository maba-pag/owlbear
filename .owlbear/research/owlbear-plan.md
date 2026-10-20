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

**Runtime.** `~/.owlbear/runtime` is a clone at `origin/main` (the latest runtime merge), deployed by hand after each merge
(TD-289, TD-309): stop, check out `origin/main`, `uv sync --locked`, start as it was (`owlbear start`, with
`--paused` if it was paused; TD-350).

**Versions.** The release workflow tags labelled merges (`release:minor`, `release:major`) once their push `CI`
passes; the switch `RELEASE_TAGS` is on since 2026-10-19 14:39Z. Tags `v0.1` to `v0.9` exist (`v0.9` is #499). The
walk creates tags through the REST API with the owner's fine-grained token `RELEASE_TOKEN` (Contents and Workflows
write, TD-404), since GitHub refuses the workflow token tags on commits whose workflow files differ from every branch
tip; a major gets `vN.0` and `vN` (TD-392). The token expires; the owner renews it.
Renovate's pull requests are left alone until the old engine is gone (owner, 2026-10-19).

**Built, by build document:**

| Area | Build document | Pull requests |
| --- | --- | --- |
| The engine and the whole journey, shaping to cleanup, visual check, design pack | [architecture](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/delivery-next-architecture.md), [design skill](delivery-next-design-skill.md) | #449 |
| Review and challenge rounds for every role (TD-208, steps 1 to 8) | [challenge rounds](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/challenge-rounds-build.md) | #449; steps 6 to 8 as commits before the PR route |
| Pull requests with required CI (TD-278) | [PR, CI, merge queue](pr-ci-merge-queue-build.md) | #455 to #458 |
| Merge-queue support (TD-226) | [PR, CI, merge queue](pr-ci-merge-queue-build.md) | commits before the PR route, `0d4272eef` and its repairs |
| Per-role session time limits, doubled (TD-286) | — | #460 |
| Pages on lit-html (TD-264), machine host, one UI, Global memory, SQLite stores, settings across projects | [machine host](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/machine-host-build.md) | #461 to #469, #471 |
| Self-update steps 1 to 3b: machine settings, Pause, paused maintenance, PR labels, push CI, release walk | [self-update](self-update-build.md) | #473, #476, #478, #480 to #482 |
| Test curation of delivery-next (TD-311, TD-312) | — | #477 |
| Decision review TD-319..TD-381: Snyk Code and Renovate, Cyclopts, subagents per role, owner notes as written | the record | #483, #487 to #489, #492, #494, #495 |
| The machine preference layer and session limits (TD-336) | [settings scopes](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/settings-scopes-build.md) | #496, #497 |
| The test review from the Maintenance page (C-26) | [test review](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/test-review-build.md) | #498, #499 |

## 2. The Plan

The order is the owner's (TD-394): TD-358's build work, the research move, self-update steps 3c to 5, the old
engine's removal, v1.0, TD-318's memory work, the window-step gate, the watcher; TD-403 places the build work of
TD-392..TD-402; TD-338 puts the watcher before any real project. Item numbers are stable names, not positions:
the table lists the items in their order.

| # | Work | Decided by | Build document | Status |
| --- | --- | --- | --- | --- |
| 1 | TD-358's rest: none; built: TD-328, TD-330, TD-334, TD-335, TD-341, TD-345 (with TD-405, TD-406), TD-347's skill, TD-350, TD-392, TD-396, TD-397, TD-399 (§3.1) | TD-358, TD-403 | TD-330 in [challenge rounds](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/challenge-rounds-build.md) §3.4; TD-334 in [machine host](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/machine-host-build.md) | Done |
| 6 | Research move: OwlBear's research into `owlbear-data`; the decision record, this plan and build designs of unbuilt work stay (§3.3) | TD-227, TD-347, TD-395, TD-394 | §3.3 | Done |
| 2 | Self-update step 3c: design pack updates through a pull request, with C-15's updater and challenger rules | TD-325, TD-357, TD-368, TD-194, TD-177 | [self-update §8](self-update-build.md) "Step 3c build" | Done |
| 3 | Self-update step 4: `repo.git`, versions, never backwards, selfcheck, standby, handover, Run updates now | TD-239, TD-299, TD-300, TD-352..TD-354, TD-369 | [self-update §3–§5, §11](self-update-build.md) | Done (#517 to #519; this machine's first update to v0.20 on 2026-10-20, TD-415) |
| 4 | Self-update step 5: idle, use, announcement, automatic updates | TD-301, TD-288 | [self-update §7, §11](self-update-build.md) | Done (#520; this machine runs v0.21) |
| 7 | Old engine removal: tag `delivery-v1-final`, five dependency-closed batches, three skills retired with batch 3, docs rewritten | TD-199, TD-201, TD-203, TD-394 | [transfer ledger §3.4](delivery-next-transfer-ledger.md), [cutover §3.3, §3.6, §3.7](delivery-next-cutover.md) | Tag `delivery-v1-final` set; batches 1 to 5 built (#521 to #524); the documentation rewrite, closing the old engine's issues and pull requests, and moving the ledger and cutover left |
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
- The quality service (TD-89): [research](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/repo-quality-service.md), not built.
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
with the C-02 catalogue text (#506), TD-345 with TD-405 and TD-406 (#508), TD-350 (#509), TD-335 (#510), TD-330
(#511) and TD-334: item 1 is done. TD-334 moves a store still in the clone into `~/.owlbear/projects/<id>` on its
first open; the clone keeps its id and a format marker that every older runtime refuses.

### 3.2 Items 2 to 4: the self-update

Item 2, [self-update §8](self-update-build.md) "Step 3c build", is built. A pack update commits on `pack/<run>`
from a clean checkout of `main`, opens a labelled pull request, waits for the required checks, brings the branch up to
date and merges it; whatever stops it asks the owner, and a host restart during publication waits for him instead of
failing. In line with C-15 the updater may change the pinned skills, the golden pages and the detector's glue; anything
else, changed expected evidence, a change the challenger is unsure the upgrade needs and a glue change go to the owner,
the glue checked with the running code (TD-414); the challenger judges every changed file. Steps 4 and 5 are §3–§5 and
§7 there.

### 3.3 Items 6 and 7: research moved, then (after the self-update) the old engine

The research moved on 2026-10-20: 1,156 documents went to `owlbear-data/owlbear/research/`, with a README there that
says how their relative links resolve. Here stay the decision record, this plan and the build designs of work not
yet built (TD-395): self-update, PR/CI/merge queue (its pack route), design skill (judge conflicts), visual
baseline, watcher design and options,
transfer ledger and cutover. A design moves there once its work is built. Links from what stays point at the moved
documents' GitHub pages. Agents write research to the project's folder in the data repository (`w-research` Step 6,
`r-workspace-governance`), OwlBear's included; `.owlbear/research/` takes only the record, the plan and new build
designs. The old engine's designer went with batch 3 of item 7.

The removal follows the self-update (TD-394) and the ledger's batches 1 to 5 (the
`main` sync batch is gone, TD-203) with the tag first; its precondition for batch 2 (the new Changes page reachable)
holds. It rewrites the documentation v1.0 needs (TD-393). Open issues #225 and #400 and pull requests #405 and #412
belong to the old engine and close with it; Renovate's pull requests come back after it. Batch 5 also retired the
four seeded hooks only the old agents registered; `deny-src-writes.py` stays for the test curator. The old live state
(`.owlbear/delivery/`, `.owlbear/controller/`) stays on disk until D5's endpoint, two consumer Changes merged on the
new engine (item 10).

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
| C-11 | Shaping captures the target pages; approval waits for them (TD-38) | "Before" is taken at the check | build | visual baseline |
| C-11 | A target whose UI changed since shaping gets a retake | Partly | build | visual baseline |
| C-14 | Bounded delegation, the "weaker" rule, the amendment process, fields and baseline | Partly; blocked by the open design TD-185 | keep | not placed |
| C-16 | OwlBear's own project sets `release:minor` | OwlBear is not a registered project | keep | 10 |
| C-16 | Chat-authored PRs get `release:minor` for runtime changes (TD-314) | Written nowhere agents read | align | — |
| C-16 | v1.0 after the self-update and the old engine's removal, docs rewritten (TD-393) | Not yet | build | 12 |
| C-19 | Linux and Windows stated as not supported yet | `README-consumer.md` and `setup/setup-guide.md` claim Linux support | align | 7 |
| C-20 | OwlBear builds itself through its own Delivery (TD-319) | Developed in chat only | keep | 10 |
| C-21 | Old engine batches with the tag first; three skills retire with batch 3 | Batches built; documentation rewrite left | build | 7 |
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

Links to GitHub pages point into `owlbear-data/owlbear/research/`, where the built designs and the research live
since item 6; the others are in this folder.

| Document | Role | Status |
| --- | --- | --- |
| [Decision record](delivery-liveness-first-rebuild.md) | The owner's decisions in force, by topic | Current; the authority for intent |
| This file | Status, order, gaps, open questions | Current |
| [Self-update](self-update-build.md) | Build design of items 2 to 4 | Steps 1 to 3b built; 3c planned; 4 and 5 open |
| [Settings scopes](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/settings-scopes-build.md) | Machine layer and session limits | Built (#496, #497) |
| [Test review](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/test-review-build.md) | C-26's test review | Built (#499) |
| [Machine host](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/machine-host-build.md) | One host, one UI, SQLite, settings scopes | Built |
| [PR, CI, merge queue](pr-ci-merge-queue-build.md) | Pull request route and queue support | Built; its open pack route is item 2 |
| [Challenge rounds](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/challenge-rounds-build.md) | Review and challenge loops | Built |
| [Design skill](delivery-next-design-skill.md) | Design pack and screenshot judges | Built; contradicting findings not detected |
| [Visual baseline](delivery-next-visual-baseline.md) | TD-38 to TD-40 | Plan; not built; its PDS part is item 11, the rest not placed |
| [Watcher design](delivery-next-watcher-design.md), [options](delivery-next-watcher-options.md) | The watcher | Draft for the owner's session; to revise (§3.5) |
| [Transfer ledger](delivery-next-transfer-ledger.md) | What the old engine leaves; the deletion batches | Decided as TD-199 to TD-201; plan of item 7 |
| [Cutover](delivery-next-cutover.md) | D5: coexistence, E1, deletion list, docs list | Partly replaced by TD-199 and TD-203; input to item 7 |
| [Quality service](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/repo-quality-service.md) | TD-89's service | Research; not built |
| [Charter](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/delivery-next-charter.md) | The approved charter of 2026-10-10 | In force only where no later decision replaced it (TD-23); the record wins |
| [Architecture](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/delivery-next-architecture.md), [status and exits](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/delivery-next-status-and-exits.md), [journey](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/delivery-next-journey-and-failure-modes.md), [glossary](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/delivery-next-glossary.md) | The design of 2026-10-10..14 | History; the record and the code win |
| [Ownership map](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/delivery-next-ownership-map.md), [route comparison](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/delivery-next-route-comparison.md), [platform probe](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/delivery-next-platform-probe.md), [agent runtime](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/delivery-next-agent-runtime.md), [tool surface](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/delivery-tool-surface-audit.md), [reuse study](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/delivery-next-reuse-study-v2.md), [agents from old](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/delivery-next-agents-from-old.md), [ECC](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/ecc-evaluation.md) | Research behind the design | History |
| [Redesign execution plan](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/delivery-redesign-execution-plan.md) | The old engine's programme | Superseded (TD-202); history |
| Old record at `04b1d8ec4` | Every decision row as first recorded; roadmap M0–M7; repair plan | History: `git show 04b1d8ec4:.owlbear/research/delivery-liveness-first-rebuild.md` |

## 7. Keeping This File Current

- A pull request that starts or finishes an item, closes a gap of §4 or answers a question of §5 updates this file
  in the same pull request; the date and the `main` commit at the top move with it.
- A decision goes to the record (C-31), never here; an order the owner decides is cited here by its number.
- Build details stay in the build documents; this file links to them and holds no second copy.
- A new build document gets a row in §6 and its item in §2.
