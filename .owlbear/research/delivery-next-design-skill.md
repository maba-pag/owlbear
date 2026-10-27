# Design Skill and Screenshot Judgement for Delivery Next

> **Owning task:** Delivery rebuild, owner questions of 2026-10-14 ([rebuild §3.8](https://github.com/maba-pag/owlbear/blob/04b1d8ec4f288aa56b1128149d5cb0ac825f1575/.owlbear/research/delivery-liveness-first-rebuild.md#38-decisions-in-force-by-topic-td-359))
> **Date:** 2026-10-14
> **Question:** Should Delivery adopt Impeccable for UI builds and for judging screenshots, by installing it
> unmodified or by extracting its useful parts? And how should screenshots be judged when one model may miss
> that a technically correct change looks bad?
> **Status 2026-10-19:** built (§3.6 to §3.8, #449); contradicting findings are not detected (§3.7). Design pack
> updates move to pull requests with self-update step 3c ([the plan](https://github.com/maba-pag/owlbear/blob/4461a7972278a44a530f92b9c8908564d9a49622/.owlbear/research/owlbear-plan.md) item 2).

## 1. Context and Question

- **Builds.** UI tasks run on the builder role (Opus `medium`). It preloads `owlbear-module-design` and
  `owlbear-acceptance`, but no design skill.
- **Screenshot judgement.** After publication, Delivery captures the brief's visual states and errors (TD-49, R8).
  The reviewer role (Sol `xhigh`) then judges them with the same two skills, again without a design skill. Its
  verdict decides the merge, and an unsure verdict waits for the owner (N6).
- **The owner's concern.** Sol may pass a change that works but looks worse; Opus is thought to be better at UI.
  He wants that found out rather than assumed.
- **What is decided.** No "accept" for this judgement (TD-75). Whether it is a review or the judging part of the
  visual check is open ([glossary](delivery-next-glossary.md) §3.1).
- **What OwlBear already has.** `share/skills/h-frontend-design` was adapted from Impeccable and Anthropic's
  frontend-design skill on 2026-03-22 (task #929, `.owlbear/sources/overview.md`). That was before Impeccable
  gained its commands, detector and engine.

## 2. Sources Studied

| # | Source | Fact used | Limit |
| --- | --- | --- | --- |
| I1 | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) README, fetched 2026-10-14 | Apache-2.0; 80.5k stars, 83 releases, the latest 4.5.2 four days earlier, commits daily. One skill with 24 commands (`craft`, `shape`, `critique`, `audit`, `polish`, `typeset`, `layout`, …). An anti-pattern catalogue. 59 deterministic detector rules in a Rust engine; `npx impeccable detect <dir\|file\|url> --json` runs them "with no LLM and no API key" (exit 2 on findings). `init` asks questions and writes `PRODUCT.md`, `DESIGN.md` and `.impeccable/` into the project. The installer for GitHub Copilot writes `.github/skills/impeccable` and a committed hook `.github/hooks/impeccable.json` that runs the engine on UI edits. The engine binary is downloaded on first use into `~/.impeccable/bin/`. Starting a new design calls a roll API at impeccable.style; anonymous telemetry is on unless `IMPECCABLE_NO_TELEMETRY=1` or `DO_NOT_TRACK=1` | README only; the skill text, rules and engine were not read |
| I2 | `share/skills/h-frontend-design/SKILL.md` (154 lines) and `.owlbear/sources/overview.md` (task #929) | OwlBear's adapted design guidance with NOTICE-based attribution | Seven months behind upstream |
| I3 | Delivery Next: `preload.py`, `roles.py`, TD-49, TD-55, TD-69, TD-72, D4 | Worker skills are preloaded per role from the package, and an agent's tools are its file's list. The SDK guard denies URL-reaching shell calls. Consumer repositories get no OwlBear files (TD-72's aim). Workers run autopilot | — |

## 3. Analysis

### 3.1 Two ways to adopt Impeccable

| | Install unmodified (installer, plugin or submodule; no fork) | Extract: a pinned, adapted copy of selected text and the unmodified engine for detection |
| --- | --- | --- |
| **Pro** | Always current; the whole command set; no maintenance of our own copy; the author's intended flow | Fits Delivery's flow: no interactive `init`, no slash commands, preloaded like the other worker skills. Nothing is written into the project. No roll API or telemetry from the text. Updates are deliberate: diff upstream, adopt what helps. The deterministic detector is still used as is, pinned |
| **Con** | Built for a person at the keyboard: `init` asks questions, commands are slash commands, live mode iterates in a browser. Writes `PRODUCT.md`, `DESIGN.md`, `.impeccable/` and a committed hook into the project. Two design vocabularies beside OwlBear's own skill | Our copy ages, as I2 did; someone must re-sync it. We give up the commands' choreography (comp-first build, decision rounds) unless rebuilt in Delivery's terms |
| **Risk** | Daily upstream change: behaviour of the builder changes without a decision of ours. A hook running a downloaded binary inside workers' sessions, outside Delivery's guard and the watcher's view. Network calls with telemetry from company machines. Conflicts with TD-72's aim and with the SDK guard (the roll call would be denied) | A wrong extraction (missing context the upstream text relied on). Licence duties (Apache-2.0 NOTICE), which I2 already handles |

### 3.2 Per use case

| Use case | Recommendation | Why |
| --- | --- | --- |
| **UI builds** | Extract. Refresh I2 from current Impeccable into a Delivery worker skill (working name `owlbear-ui-design`), preloaded for UI tasks only. Cover principles, anti-patterns, typography, colour, layout, and the `polish` and `harden` checklists. Give the builder the pinned detector as a check it can run on its own preview | The builder needs the knowledge, not the interactive choreography. Preloading keeps it out of the ~80% of non-UI steps (§3.13 Q-B). Nothing lands in the project |
| **Screenshot judgement** | Use the detector unmodified as a mechanical check inside the visual check: pinned version, checksum, telemetry off, run by Delivery against the preview. New findings since "before" count, like console errors (R8). Plus the same extracted skill's `critique` rubric for the model that judges design quality | The detector is cheap and deterministic, and it catches exactly the "works but looks AI-generic" class. Builder and judge share one rubric |

Confidence: medium-high for the direction; whether the detector's rules match the owner's taste is unmeasured.

### 3.3 How to judge screenshots

| Option | What it does | Pro | Con |
| --- | --- | --- | --- |
| J1 One judge (today) | Sol `xhigh` judges all states | Simple | One model's blind spots, the owner's worry |
| J2 Panel | Two or three models judge the same question in parallel; any evidenced fail sends work back | Redundancy; cheap, since images are reused and the task is short | Same question twice; disagreement needs a rule |
| J3 Two lenses | In parallel: a **correctness** judge (Sol: do the states match the brief, any new errors) and a **design** judge (Opus with the design skill and the detector's findings: is "after" at least as good as "before", and which anti-pattern appears) | Each model does what it is thought best at; findings must name a rule or principle, not only taste | Two prompts to maintain |
| J4 Owner's second opinion | On the Change page, "Another verdict": the owner picks a model (and lens), and the new verdict is added beside the others, never replacing them | Cheap, on demand | Only when the owner looks |
| J5 Blind A/B | The design judge sees "before" and "after" unlabelled, in random order, and says which is better and why | Counters the bias that "after" was made to pass | Needs "before"; static states only |
| J6 Calibration | Each time the owner decides, Delivery records which verdicts agreed with him; Cockpit shows agreement per model and lens | Turns "Sol or Opus?" into evidence over time (as N2 does for cost) | Needs a few dozen decisions |

**Recommendation (`autonomous`, for the owner):** J3 by default, with J5 inside the design lens. When the lenses
disagree or either is unsure, the owner decides (N6) on a side-by-side page with both verdicts. J4 is always
available there, and J6 records every decision, so the default models can change on evidence.

### 3.4 The owner's decisions, 2026-10-14

TD-74 amended, TD-76 to TD-79 in the decisions:
- The screenshot judgement is a review. Delivery has three: after each task, at the end of a Change, and the
  visual review.
- Impeccable is extracted, not installed. "The runner and the extracted design rules" are updated together and
  regularly, by a structured plan (§3.5). "Runner" is read as the detector engine together with Delivery's code
  that runs it; the pack covers both.
- Two judges always judge: correctness and design. There is no "another verdict" button.
- The detector's findings are evidence for the judges, never a fail on their own.
- A correctness fail goes back to the build automatically. A design fail goes back or to the owner, by a setting.
- The owner decides on one page: the screenshot comparison, both verdicts, then Pass or Fail, with finding
  checkboxes and an optional comment. A Fail comment becomes a criterion of the next visual review; a Pass
  comment is kept as a note.

### 3.5 Plan

Sol challenged the first version of this plan; its 20 findings are folded in.

**The design pack.** One versioned unit in Delivery's package that changes only as a whole:
- the engine executable per platform Delivery supports (macOS arm64 and x86_64 first), with its checksum from the
  release's own published checksums. If a release publishes none, the pack records hashes reviewed at extraction;
- the upstream tag, commit and engine version (`ENGINE_VERSION`);
- Delivery's detector adapter;
- the extracted skill with its critique rubric;
- the map from detector rule IDs to skill sections, and the default ignores;
- the licence material: upstream `LICENSE` and `NOTICE`, plus an attribution and modification notice for the
  extracted text.

The pack's identity is a hash over all of it. Every visual review records the pack it used, and a review in
progress keeps that pack even if a new one is activated.

**Verdict matrix.** Each judge ends in pass, fail, unsure, or no verified result.

| Correctness | Design | Round ends in |
| --- | --- | --- |
| pass | pass | merge |
| fail | anything verified | back to the build with the correctness findings, plus the design findings when the setting is `back`. With `ask`, a design fail is judged again in the next round |
| pass | fail | `back`: back to the build with the design findings. `ask`: the owner decides |
| pass or unsure | unsure | the owner decides (N6) |
| unsure | pass or fail | the owner decides (N6) |
| findings that contradict each other (one asks to change what the other requires) | | the owner decides |
| no verified result from either judge | | that judge reruns under the existing budgets. Unread usage only reruns (TD-54, TD-75), and unconfirmed termination stops. A round is decided only on two verified verdicts |

Repeated fails are bounded by the existing repair budget, which then asks the owner. A missing or
non-comparable "before" is never read as an improvement: the design judge then judges the state against the
rubric alone and says so.

**Update procedure.** Monthly, and at once on a security advisory:
1. **Notice.** Delivery's readiness check compares the pinned tag with upstream's latest release; offline means
   "unknown", never a failure. The config page shows "design pack N releases behind".
2. **Diff and choice.** In a direct chat, never through Delivery itself, the assistant lists new, changed and
   removed rules and skill text between the tags. The owner approves what to adopt or skip.
3. **Engine.** The assistant downloads the assets and verifies them against the published checksums.
4. **Golden pages.** A fixture set of good and bad pages with expected findings. The new engine must produce
   exactly the expected changes.
5. **Calibration replay.** With a fixed model and inputs, the design judge reruns on stored decided rounds.
   Below 20 rounds the result is advisory. Above, agreement with the owner must not drop by more than a set
   margin, or activation waits for the owner.
6. **Activation.** The new pack becomes active in one switch. Rollback restores the whole previous pack.

**Build slices** (each test-first and Sol-reviewed, with live proof where marked):
1. **Extraction study, read-only.** At a pinned tag, read the skill text, the 59 rules, the release assets and
   checksums, and the engine's options: page width, hidden browser, scanning a page Delivery already rendered.
2. **Pack and detector adapter.**
   - The skill file, licence material and golden pages.
   - The adapter: download at setup, checksum, store outside every project; run with `IMPECCABLE_BIN`,
     `IMPECCABLE_BROWSER` (Playwright's Chromium), `IMPECCABLE_NO_UPDATE_CHECK=1` and `IMPECCABLE_NO_TELEMETRY=1`.
   - Exit 0 and 2 both yield findings. Exit 1, a timeout or malformed output is an operational failure with
     bounded retries, never a clean scan.
   - Live: one scan of a sandbox preview.
3. **Records and setting.**
   - One record per judge per round: verdict, findings with IDs, model and effort, usage check, capture and pack
     identity, the setting in force.
   - Owner criteria with their origin.
   - The calibration store in the shared repository's project folder, outside consumer repositories. It keeps the
     last 50 decided rounds with images; older rounds keep verdicts only.
   - `design_failures` as a nullable setting in the layers (TD-52), resolved with its source and shown on the
     config page as inherit, back or ask. The default `ask` is `autonomous`.
4. **Detector in the visual check.**
   - URL scans of each static state at the capture widths, on "before" and "after".
   - Source scans of the changed UI files on the target and on the Change, under the same pack and ignores.
   - Findings are new, existing or unknown. States reached by clicks and typing are scanned in the page Delivery
     rendered if the engine allows it; otherwise "not scanned" is recorded.
   - New browser errors still fail the check on their own (R8).
5. **Design judge.**
   - A new session role with its own agent file, tools list and preloaded skill, carried through both runtimes.
     A new model label alone would still run the reviewer's agent.
   - Both judges get the screenshots, errors, detector findings and owner criteria. The design judge also gets
     "before", in a blind order with neutral IDs whose mapping Delivery keeps.
   - Images are budgeted per judge. If a judge's images exceed the limit, it judges in batches by state, never
     dropping one.
   - SDK judges run in parallel. Window judges run one after the other, because their window files share one
     worktree. State writes are serialized under the Change lock.
6. **Routing and decision page, switched on together.**
   - The matrix above, plus the page: screenshot pairs per state and width, findings, errors, both verdicts with
     checkboxes, Pass or Fail, and a comment.
   - The server checks that a Fail has a finding or a comment, and refuses an answer whose capture or pack
     changed since the page was shown.
   - On Fail, the ticked findings and the comment become the fix task. The comment becomes an owner criterion
     until the owner withdraws it.
7. **Calibration view and the builder's scan.**
   - Agreement per judge, beside the setting.
   - A Delivery tool `scan_design` for the builder on UI tasks, bounded to its worktree and preview, so the SDK
     guard need not widen.
8. **Update tooling,** before the first pack update: the notice, diff report, golden-page run, replay and
   activation switch.

Proof: in a sandbox project, a change that is correct but looks worse. The design judge fails it, the owner
decides on the page, the fix task carries the comment, and the next review checks it.

### 3.6 Slice 1 findings, 2026-10-14

Read at tag `skill-v4.5.2` (commit `d631a88`, engine `0.1.14`) from a shallow clone in
`.owlbear/scratch/research/impeccable`. Live checks used a sample page with known faults, served on localhost.

- **Engine release.** `engine-v0.1.14`, published 2026-10-09. Its assets per platform carry GitHub's own sha256
  digests and a `.sha256` sidecar file each:

  | Asset | sha256 |
  | --- | --- |
  | `impeccable-darwin-arm64` | `abbd69d5…f4f87c` |
  | `impeccable-darwin-x64` | `dfa45703…28aa0f5` |
  | `impeccable-linux-arm64` | `396263ee…6208c948` |
  | `impeccable-linux-x64` | `3d31ec1a…4368efb6` |

  The upstream launcher refuses a download whose sidecar is missing. The darwin-arm64 binary downloaded here
  matched its digest.
- **Detect options.** `detect --json --no-config [--viewport WxH]`, with the default viewport 1280x800, so R7's
  widths work. URL scans start the browser named by `IMPECCABLE_BROWSER` headless (`--headless=new`). It took
  2 to 3 s per scan, and no browser was left running.
- **Network.** In the `detect` code path, only the scanned page itself is fetched. The update check lives in the
  `context` command, and the roll API in the skill's design flow. Source scans work offline.
- **Rules.** 59: 31 "slop" (9 advisory) and 28 "quality" (4 advisory, 2 errors: `script-error` and
  `content-hidden-at-rest`). Each names a skill section: Typography 11, Layout & Space 10, Colour & Contrast 8,
  Visual Details 6, Motion 4, Imagery 4, Copy 4, none 12. The list is kept in
  `.owlbear/scratch/research/impeccable-rules.tsv`.
- **In-page detector.** The tag ships a built bundle, `crates/live/assets/detect-antipatterns-browser.js`
  (2.8 MB, sha256 `d71d1c76…55939bbd9483`). It exposes `window.impeccableDetectAsync()`; setting
  `window.__IMPECCABLE_CONFIG__ = {autoScan: false}` first keeps its overlay off.
  - Live, injected into a Playwright page after its screenshot, it found the same four rules as the engine's URL
    scan, grouped by element with selector and position.
  - A screenshot taken after the scan was identical, byte for byte.
  - It needs WebAssembly allowed by the page's Content-Security-Policy (`'wasm-unsafe-eval'`); otherwise it
    throws "detector core unavailable". The engine's URL scan runs the rules outside the page and is not
    affected.
- **Upstream's own critique** (`reference/critique.md`) runs two isolated assessments, a design review and the
  detector evidence. The design review must finish before the detector findings reach the verdict, because
  "deterministic output still anchors judgment". It scores Nielsen's ten heuristics 0 to 4 (n/a allowed),
  rates findings P0 to P3, and starts with a "design specificity" verdict.
- **Licence.** Apache-2.0 (`LICENSE` sha256 `02bb8c3b…`). `NOTICE.md` names one third-party source,
  `platform-design-skills` (MIT), used only in the iOS and Android references, which Delivery does not extract.

Consequences for the plan:
- **Slice 4.** Rendered scans run in-page in Delivery's own capture page: each state, stepped ones included, at
  each width, after the screenshot. No second browser is needed. Where the page's CSP blocks WebAssembly, a
  static state falls back to the engine's URL scan, and a stepped state is recorded "not scanned (CSP)". Source
  scans use the engine.
- **The pack** holds the engine digests, the in-page bundle with its digest, and the licence files.
- **Slice 5.** The design judge works in two phases, as upstream's critique does: first an unanchored verdict,
  then the detector's findings arrive and it gives its final verdict, naming agreements and false positives.
  Both are recorded.
- **The extracted skills.**
  - `owlbear-ui-design`, for UI builds and the design judge: the brief wins; refinement preserves and redesign
    replaces; the four modes; the craft floor's checks and refusals; and the typography, layout, colour and
    polish essentials.
  - `owlbear-ui-review`, for the design judge only: specificity verdict, heuristics 0 to 4, P0 to P3, the
    cognitive load checklist, and the before/after comparison.
  - Both build on OwlBear's `h-frontend-design` (TD-58).

### 3.7 Build progress, slices 2 to 8, 2026-10-14

Built on the PR branch `next/m4-slice1` (PR #449), each slice test-first, Sol-reviewed with its findings fixed
under tests, then pushed. The package suite went from 815 to 876 tests.

| Slice | Commit | Result | Live proof |
| --- | --- | --- | --- |
| 2. Pack and adapter | `a808988c0` | Two extracted skills with licence and NOTICE; pins in `design_pack.json`; private install outside every project; source, URL and in-page scans | Install verified; the three scans of a sample page agree |
| 3. Records and setting | `0d6585719` | Rounds, verdicts, owner decisions and criteria; `design_failures`; calibration store with 50 rounds of local screenshots | Config page saves and reloads the setting |
| 4. Detector in the check | `0d5578fad` | In-page scans after each screenshot, CSP fallback, source scans on both sides, findings new, existing or unknown | Scans, CSP fallback and a hung scan ended in time |
| 5. Design judge | `13522198a` | `designer` role in both runtimes, two phases in one session, blind A/B, image batches | A real SDK designer session through both phases |
| 6. Routing and decision page | `f3caf83e5` | Verdict matrix; Pass or Fail page with findings and comment; stale or empty answers refused; owner criteria | Page renders and posts a Fail with a ticked finding |
| 7. Agreement and builder scan | `687899845` | Agreement per judge and model on the settings page; `scan_design` for UI builders | Agreement table from two decided rounds |
| 8. Update tooling | `043bbdab6` | Notice, field-level rule diff, golden pages, calibration replay, activation by manifest | Engine and bundle on the golden pages; parser on upstream's 59 rules |

Choices made during the build, all `autonomous`:
- **Delivery derives the design verdict** from the blind evidence mapped back to "before" and "after": a state
  made worse, or a serious or owner-criterion problem that "before" did not have. The judge's own verdict is
  kept beside it.
- **`scan_design` scans sources only.** The engine's own browser runs outside Delivery's guard, so a page the
  builder made could reach outside. Rendered pages are scanned in Delivery's capture page instead.
- **A judge without a verified verdict** reruns both judges on a new capture, within the step's budget.
- **Notice.** The readiness check, run by setup and at every host start, refreshes it at most daily with one
  10-second request. Offline clears it to "unknown"; the settings page only reads it.
- **Golden pages** are checked twice: by the engine on their source and by the pack's bundle in the rendered page.
- **Calibration replay** reruns only rounds judged by the same model and effort, so only the pack differs. Each
  round keeps the design judge's messages, detector reveals and image names for it. Not fixed: the judge's
  worktree is empty and its memory is today's.
- **Activation** is one reviewed commit of the manifest and skills. Reverting it rolls the whole pack back;
  each pack installs into its own folder, so a rollback downloads nothing.

Known gaps:
- Findings that contradict each other are not detected.
- The window runtime's two-phase turn has not run live.
- `sdk_adapter.py` is at the 500-line module limit.

### 3.8 End-to-end proof and owner feedback, 2026-10-13

**Proof** in the sandbox (`promo-hero`, PR merged): the brief asked for gray `#9ca3af` text on indigo, which is
correct but hard to read.
- Round 1: correctness pass; design fail on a 2.5:1 contrast the Change introduced (detector: the same four
  rules, new). The owner failed it on the decision page with the contrast findings and a comment.
- The fix task carried both; the comment became `owner-1`. Round 2's design judge received `owner-1`. The
  contrast rules were gone, and Delivery derived pass: the judge's own "fail" rested on "before"-only problems.
  Both judges passed, and the Change merged and was cleaned up. Round 1 is kept for calibration in the shared
  repository.

**Owner feedback** after deciding, built in `2716f9c3b`:
- Screenshots above the decision. A screenshot enlarges in place and steps before, then after, at each width,
  with side, commit, width and size shown.
- One readable row per problem instead of a checkbox per finding and width. "Before"-only problems are collapsed
  and never sent.
- Pass, Fail and New Change ask first.
- Settings offer the models, efforts and context sizes this machine's Copilot lists.

**Decisions:**
- `decided` (2026-10-13): a Fail pre-ticks what a failing judge found the Change introduced at P0 to P2. The
  owner unticks what he disagrees with, and the `back` setting sends the same set.
- `decided`: Pass, Fail and New Change all confirm first.
- `autonomous`: a missed owner criterion is always proposed, whatever its severity. A design fail with nothing
  to fix goes to the owner even under `back`. `auto` and disabled models are not offered, because Delivery
  pins each role's model and checks the billed one. An effort the chosen model does not offer is refused.

**Context tiers**, built in `f00e2f928`:
- **Source.** The Copilot runtime's `models.list` gives each model a default context tier and, for many models, a
  long one, each with its own size and rates in AI credits per 1M tokens. Opus 5.5 goes from 200K to 1M at the
  same rates. GPT-6.1 Sol goes from 272K to 922K at input ×2 and output ×1.5. Haiku 4.5 has one tier only.
- **Sessions.** The SDK pins a tier with `context_tier`. Before this change Delivery never set it, so every
  session ran on the default tier. A VS Code window session takes the tier as the model's `contextSize`. The
  agent host defaults `claude-opus-5.5` to 1M, so Delivery has sent the size since `37e915828`.
- **Settings.** Each agent has a two-way switch labelled with the real sizes. An up arrow marks the long side
  when its rates are higher, and a rates column shows the credits per 1M tokens for the chosen model and tier.
  - `decided` (2026-10-13): the owner chose this layout, with no popover.
  - `autonomous`: Sol's alternative put the rate change on a line under the switch. It was not chosen because
    it would leave only the context cell with an extra line.
- **Default tier.** `decided` (2026-10-13): every role starts on the default tier. The watcher recommends the
  long tier from early compactions ([watcher design §3.4a](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/delivery-next-watcher-design.md)).
- **Replay.** Verdicts record the tier, and the calibration replay compares only rounds judged on the same model,
  effort and tier.

## 4. Recommendation, Confidence, and Limits

- Extract for builds and judging. Adopt the detector unmodified and pinned, as a mechanical check that only
  supplies evidence. Keep detector and rules in one pack that is updated together (§3.5).
- Judge screenshots with two judges every time. The owner decides on one page with Pass or Fail, findings and a
  comment. Design fails are routed by a setting, and agreement is recorded.
- Limits:
  - Impeccable was read from its README, privacy page and npm page only. The skill text, the 59 rules and
    the engine's behaviour (widths, hidden browser) are read in slice 1, with a pinned run on a real preview in
    slice 2.
  - "Opus is better at UI" is the owner's expectation; calibration measures it.
