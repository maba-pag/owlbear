# Delivery-next: "before" in shaping, PDS loading, preview ports

> **Owning task:** owner decisions TD-38 to TD-40 of 2026-10-11, follow-up to PR #449
> **Date:** 2026-10-11
> **Question:** How do the three decisions fit the approved journey end to end, what must change in
> code and docs, and in what order is it built and proven?
> **Status:** plan, revised after Sol challenges (§6); one decision open for the owner (§5, D-A);
> nothing built

## 1. Context, decisions and gaps

Decisions, all `decided` by the owner on 2026-10-11; they are added as TD-38 to TD-40 to the
[rebuild research §3.8](delivery-liveness-first-rebuild.md) table with this plan:

- **TD-38.** "Before" screenshots are part of shaping. Once it is clear that a Change alters what a
  page shows, shaping establishes the render recipe, captures the current pages from the target and
  writes the visual states and their expectations against them. The comparison is design state
  against overall result, per Change, not per task. This replaces the charter's "before the first
  build task"; TD-24 stays (the screenshots never interrupt the run).
- **TD-39.** The Changes page loads the Porsche Design System the way PDS documents it, from its CDN,
  without an own fallback rendering.
- **TD-40.** Every preview run gets a free port chosen by Delivery; recipes take the port as a
  placeholder.

Gaps between the approved design and the code at `600636899`, found while grounding this plan:

| # | Gap | Evidence |
| --- | --- | --- |
| G1 | The brief has no render recipe, although shaping must establish it before approval | `models.py:120` `Brief`; [charter §3.10](delivery-next-charter.md#L227); [architecture](delivery-next-architecture.md#L283) |
| G2 | The chat's `save_brief` tool passes only title, outcome, criteria, scope, person checks and change; `ui` and `visual` never reach a brief shaped in chat, although skill step 4 asks for them and the HTTP endpoint accepts them | `mcp_server.py:111`; `skills/delivery/SKILL.md:19`; `tools.py` `BriefDraft` |
| G3 | The host's "after" launch does not check that something else already answers at the URL; only the "before" capture does | `host.py:286`, start at `:303`; `steps/before.py` `_serve` |
| G4 | The visual reviewer receives only the "after" screenshots | `runner.py:237` |
| G5 | The M4 sandbox preview hard-codes its port (`server.listen(4173, "127.0.0.1")`) | `owlbear-sandbox` `a6eb298`, `packages/app/src/preview.ts` |
| G6 | An approved brief cannot be changed: saving refuses outside Shape and the API knows only pause, resume and abandon, while the journey's D6 defines a change-of-mind route | `briefs.py:87`; `api.py:84`; [journey D6](delivery-next-journey-and-failure-modes.md#L219) |

G2 means no UI Change shaped in chat can have visual states today; slice 3 fixes it. G6 predates
this plan and stays out of its scope; it is listed because a revised brief after approval is part of
the owner's journey and has no route yet.

## 2. Sources studied

| # | Source | What it establishes |
| --- | --- | --- |
| S1 | Charter §3.10, journey J2/J4/J7, B24/B25, DR3, D6, architecture "Visual check", status-and-exits "Check environment" | Approved design: recipe in the brief from shaping; Builder verifies it at the check; same-origin captures; project installs inside agent tasks (DR3) |
| S2 | Code at `next/m4-slice1` `600636899`: `models.py`, `tools.py`, `briefs.py`, `mcp_server.py`, `api.py`, `host.py`, `runner.py`, `store.py`, `steps/before.py`, `steps/check.py`, `steps/visual.py`, `permissions.py`, `prompts.py`, `skills/delivery/SKILL.md`, `web/changes.html` | As-built behaviour and the gaps G1–G4, G6; the runner holds the Change lock for its whole run (`runner.py:331`) |
| S3 | `boecht/owlbear-sandbox` `a6eb298` | M4 target: one nested package; a hand-written Node preview on fixed port 4173 (G5) |
| S4 | [PDS v4 initialization, vanilla JS](https://designsystem.porsche.com/v4/must-know/initialization/vanilla-js/) | Documented setup: load the npm package's loader on the page; `load()` fetches the core chunk, which registers every tag, and loads each component chunk from the CDN on use; hide undefined tags with `:not(:defined)` |
| S5 | [PDS v4 performance, CDN](https://designsystem.porsche.com/v4/must-know/performance/cdn/) | Components, icons, fonts and styles come from `cdn.ui.porsche.com` (shared cache across Porsche apps); only `cdn: 'auto' \| 'cn'` is configurable |
| S6 | [PDS v4 components ready](https://designsystem.porsche.com/v4/developing/components-ready/) | `componentsReady()` resolves when all used components are loaded; `whenDefined` proves registration only |
| S7 | [PDS issue #4730](https://github.com/porsche-design-system/porsche-design-system/issues/4730) | CDN-free local delivery is a goal of an open v5 spike, not a v4 option |
| S8 | Repo research [1495](1495-pds-v4-local-hosting.md), [1510](1510-pds-asset-sync.md), [1591](1591-pds-global-styles-test-approach.md), [936](936-sidecar-green-gaps.md) | Cockpit mirrors PDS chunks through an internal `cdn` property trap; 936 recommended its strict CSP (0.75); 1591 quotes the owner's D6 approving CDN fonts. The D6 record itself was not located |
| S9 | [Vite server options](https://vite.dev/config/server-options#server-strictport), [Vite CLI](https://vite.dev/guide/cli) | `--port`, `--strictPort`; without it Vite moves to the next free port |
| S10 | [Next.js CLI](https://nextjs.org/docs/app/api-reference/cli/next) | `-p/--port` or `PORT` env; `npm run` needs `--` to forward flags |
| S11 | [Playwright web server](https://playwright.dev/docs/test-webserver) | Prior art: with `reuseExistingServer: false` it refuses when the URL already answers, then waits for the URL; no ownership check |

## 3. Design

### 3.1 The owner's journey after the change

| Stage | Owner does | Owner sees | Delivery does |
| --- | --- | --- | --- |
| J2 Shape | Describes the idea; answers questions | When the Change alters a page: "rendering the current pages…", then each named state at 1280 and 390 px, in chat (links) and on the draft brief in the Changes page | The agent establishes the recipe from repository evidence and saves it with draft states; Delivery captures them from the target on a free port; the agent and the owner write each expectation against the screenshots |
| J2 Approve | Approves the brief | Each state: path, expectation, current screenshots, or the reason none exist | Records the approved version's capture as the design reference |
| J4 Build | Nothing | Unchanged | No per-task screenshots |
| J7 Visual check | Nothing, unless the brief declares a person-only check | Design reference and result side by side on the card | Builder verifies the brief's recipe in the worktree on a port Delivery gives it; Delivery launches it on a free port; the reviewer judges "after" against the expectations with the design reference as context |

### 3.2 The render recipe in the brief (closes G1, G2)

- `Brief.recipe`: `command`, `directory`, `ready_url`, part of each approved version. `ready_url` is
  `http://127.0.0.1:{port}/…` or `http://localhost:{port}/…`; `command` may contain `{port}`; Delivery
  also sets `PORT`. The command starts with an allowed launch prefix (`allow:check`), as check
  recipes do today.
- A UI brief needs a recipe and at least one visual state, or a person-only check marked visual
  (unchanged rule).
- The chat tool `save_brief` gains `ui`, `visual` and `recipe` (G2).
- Skill step 4: establish the recipe from the repository, save the draft, wait for the current pages,
  then write each state's expectation against them with the owner. When the target cannot render (no
  preview yet, or one on a fixed port), the capture ends with that reason and shaping offers:
  1. **Add or fix the preview in this Change** (as the skill offers today): the recipe describes the
     preview as it will be after the Change; there is no design reference (noted on the card, B25);
     the visual check still runs at J7.
  2. A small first Change that adds or fixes the preview, then this Change with a reference.
  3. A person-only visual check instead.

### 3.3 "Before" in shaping (TD-38)

- **Trigger.** A brief draft with `ui`, a recipe and states, whose capture key has no capture yet. The
  key is the target commit, the recipe and the ordered state paths; editing expectations alone does
  not recapture.
- **Dispatch.** Ordinary dispatch cannot start it: while shaping waits on the owner, `loop.next_step`
  returns nothing. So the host has one capture rule beside the step runners: a shaping Change whose
  latest draft's key has no capture attempt, and no runner alive, gets a capture runner. It is not a
  product step kind; the Change stays in Shape.
- **Attempts.** Each attempt is recorded on the Change with its key, start, end and result. The runner
  writes the attempt's start and its end under short Change-lock acquisitions, and journals each
  started PID the same way (`Store.log` requires the lock), so the host can still find a dead
  runner's processes. Between those writes it holds no lock, so the owner can save a revision
  meanwhile.
- **Completion.** When a capture runner disappears without ending its attempt, the host disposes of
  the groups the attempt journaled (installers and preview run in their own sessions) with the same
  `check.dispose` it uses for check environments, then verifies with `_survivors`. If nothing remains,
  it ends the attempt as "capture interrupted"; it is not charged as a step failure and not
  relaunched automatically. If something remains, the Change is blocked as today.
- **Retry.** A successful attempt is reused for its key. An unsuccessful or interrupted one is not:
  the owner retries it with "Capture again" on the draft brief, or by saving the draft again in chat
  (for example after fixing the profile's install command). Nothing retries on its own, so a broken
  install cannot loop.
- **Superseded.** An attempt whose key no longer matches the latest draft finishes, is kept for reuse,
  and is not shown as current; the latest key is captured next.
- **Mechanism.** The capture of `600636899` (temporary detached worktree at a commit, profile
  installs, launch, capture, disposal of every journaled PID), pointed at the tip of the tracking
  target, and launched through §3.5. Installs: see D-A in §5.
- **Storage.** Each successful set is immutable under `changes/<slug>/before/<key-hash>/`, its files
  named by state path and viewport, so a renamed state keeps its pictures. The Change records the set
  of each draft version; the approved version's set is the design reference. Before and after are
  paired by path and viewport, labelled with the current state names.
- **Approval.** Approval is offered once the latest key's capture has finished, successfully or with
  a reason. The API's approve action and the inbox fold both refuse an earlier approval, with that
  reason.
- Findings are B25 notes; a capture never fails the brief.

### 3.4 Visual check and review (closes G4)

- The check-preparation Builder receives the brief's recipe and a concrete free port from Delivery,
  verifies the recipe in the worktree on that port, and may return an adjusted recipe (for example a
  renamed script) that keeps `{port}`. Person-check preparation also receives a port.
- No retake. The design reference stays the shaping capture, as the owner asked ("compare design
  phase versus overall result"). The capture at the visual check of `7f8a72077` is removed.
- The reviewer receives the "after" screenshots and the design reference, labelled `before/…` and
  `after/…` per state and viewport. Prompt: judge "after" against each expectation; the design
  reference shows the starting point and is not judged, since the target may have moved since
  shaping.
- Budget: "after" images come first within the 12 MB review cap. "Before" images are downscaled, then
  omitted, with a named note when they do not fit. A "before" image never causes a finding, so a full
  budget never becomes a product fix task.

### 3.5 Preview ports (TD-40, closes G3)

- One launch function serves every preview: the shaping capture, the "after" preview and person-check
  environments (H1). It binds `127.0.0.1:0`, reads the port, releases it, substitutes `{port}`, sets
  `PORT`, refuses when the URL already answers, starts the recipe and waits for readiness at that URL
  only.
- `Environment` keeps the recipe template and the resolved port separately. A relaunch after an
  interruption allocates a fresh port and updates the URL shown to the owner. Person-check answers
  stay valid: their validity depends on file fingerprints, not on the URL (`steps/check.py`).
- A lost race (another process takes the port first) fails loudly when the recipe uses its server's
  strict flag (Vite `--strictPort`); Delivery then allocates once more. Other failures are not retried.
- A server that ignores the port does not answer at the assigned URL: the launch fails with "the
  preview did not answer on the assigned port; it may use a fixed port", and its group is disposed.
- `{port}` passes the command allow-list (braces are not shell operators in `permissions.metachars`);
  `tools.LOCAL_URL` changes from digits to the placeholder.
- Stored records: no migration. Delivery-next has no real Changes yet (pre-M4); new fields default to
  empty, and the test records in the sandboxes are disposable ("no legacy", system instructions §1).

### 3.6 Changes page on PDS (TD-39)

- Keep: the vendored loader and stylesheet of `@porsche-design-system/components-js` 4.8.0 (the
  documented no-bundler setup, S4), `:not(:defined) { visibility: hidden; }` (S4),
  `scheme-light-dark`.
- Remove: the 3-second decision, the `pds` flag and every native-control branch (`button`, `field`,
  `choice`, `external`, `pullbackNote`, the row button), the `.no-pds` CSS and its notice.
- Diagnostic only: if `componentsReady()` (S6) has not resolved 10 seconds after a render, show one
  plain line: "The Porsche Design System did not load from cdn.ui.porsche.com; check the network and
  reload." This catches a failed core and a failed component chunk alike; it is a message, not an
  alternative rendering.
- Cockpit is unchanged; whether its own mirror (S8) should follow PDS is a separate question.

### 3.7 Removed as-built behaviour

- The capture at the visual check (`before.due` at CHECK) and its host rules.
- The free choice of the visual check's recipe by the preparing Builder.
- The page's native fallback.

## 4. Build slices and proof

Each slice is one commit on `next/m4-slice1` with the smallest tests that fail without it, a Sol
review of the diff, and the doc updates of its behaviour. Existing maintained tests are extended
before new files are added.

| Slice | Content | Proof |
| --- | --- | --- |
| 1 Ports | §3.5, with check preparation receiving a port (§3.4 first bullet) and the template/port split | Two concurrent launches of a real `python -m http.server {port}`, each serving different content, render their own content; a server ignoring the port fails with the named reason and is disposed; the host's "after" launch refuses an answering URL; a relaunch gets a new port and keeps the check's answer |
| 2 PDS | §3.6 | Page test; browser check with the CDN reachable, with the core blocked, and with one component chunk blocked (diagnostic shown in both failure cases) |
| 3 Recipe and shaping capture | §3.2, §3.3, G2 | `save_brief` over MCP stores `ui`, `visual`, `recipe`; through the host's capture rule, a shaping draft gets one capture at the target tip whose PNG shows the target's content (as `test_before.py` does today); a revision saved during a running capture succeeds; an expectations-only edit or a state rename does not recapture and keeps the pictures; a killed capture runner ends its attempt as interrupted while its preview is alive, leaves no process and is not relaunched; "Capture again" retries a failed attempt; approval before the capture finishes is refused by API and fold; the page shows each state with its screenshots |
| 4 Visual check | §3.4 | Preparation prompt carries the brief's recipe and port; reviewer attachments carry labelled before and after; an over-budget "before" is downscaled or omitted with a note and never yields a fix task |
| 5 Live | One UI Change in `owlbear-sandbox` from chat: shaping meets G5 and offers the three choices; the Change fixes the preview in itself; a second Change gets a design reference; its visual check fails once on a deliberately broken layout, returns a fix task and then passes (the M4 proof); an owner's own server on 4173 stays untouched and uncaptured | Card with both sets; page screenshots; activity log |

Docs updated with the slices: the TD-24 sentence of [charter §3.10](delivery-next-charter.md#L227);
J2, J4, J7, B24, B25 of the [journey](delivery-next-journey-and-failure-modes.md); "Visual check" and
the "Before" paragraph of the [architecture](delivery-next-architecture.md); the brief row, "Check
environment" and "Before capture" of [status and exits](delivery-next-status-and-exits.md); DR3 if
D-A takes option 1.

## 5. Decision for the owner, risks and confidence

**D-A: who runs the project's install for the shaping capture?** The approved design says project
installs run inside agent tasks with a fix loop (DR3), so a failing install gets repaired by an agent.
The capture built yesterday runs the profile's install commands directly in its temporary checkout,
and the plan reuses it.

| Option | Meaning | Pros | Cons and risks | Confidence |
| --- | --- | --- | --- | --- |
| 1. Exception to DR3 for the disposable baseline (recommended) | Delivery runs the profile's install commands directly in the temporary checkout; a failure is a B25 note with the command's last line and "Capture again", no repair | No agent session per capture (no credits; likely faster, not measured); the screenshots show exactly the target commit on the card; the checkout is thrown away, so a repair would not persist anyway | A target that needs a repair to install gets no design reference until the owner fixes it (for example the profile's install command); DR3 gains one named exception | 0.8 |
| 2. Follow DR3 | An agent session installs, and may repair, in the temporary checkout before each capture | No exception; a broken install can still yield a reference | A paid agent session per capture and retry; a repair that touches tracked source or generated UI makes the screenshots show the repaired target, not the commit named on the card, unless repairs are limited to the environment or the reference is marked as adjusted; repairs are lost with the checkout | 0.2 |

| # | Risk | Why it matters | Settled by |
| --- | --- | --- | --- |
| R1 | Whether the shaping agent in VS Code chat can view the PNGs | Writing expectations with the agent needs it; otherwise only the owner looks and describes | Verified in slice 3; if not, the skill says so and the owner describes |
| R2 | The review cap of 12 MB with before and after | Today's cap names over-budget states as findings, which can become fix tasks | §3.4 budget rule; measured in slice 4 |
| R3 | Install and start time at shaping | The owner waits before approving | Background capture, key reuse; slice 5 measures only a small project |
| R4 | A project whose preview cannot take a port | No design reference until it can | §3.2 choices; M4 meets it on purpose (G5) |
| R5 | The target moves between shaping and the visual check | The design reference may differ from the result in ways this Change did not cause | The reviewer does not judge the reference (§3.4); the card labels it with its commit and date |

Confidence that the plan implements TD-38 to TD-40 without contradicting the approved journey, given
D-A option 1: 0.8. Lowest: R1 (unverified) and the capture scheduling rule in §3.3 (new host
behaviour).

## 6. Challenge record

Sol (GPT-6.1 Sol), one round on the first draft, 2026-10-11. Verdict: ready after the should-fix
items; no reversal of TD-38 to TD-40 proposed. Dispositions:

| # | Finding | Disposition |
| --- | --- | --- |
| 1 | TD table reference, S10 conditional, S7 provenance, pin capture to `600636899` | Accepted: §1, S8, S11, §3.3 |
| 2 | `whenDefined` does not prove PDS loaded | Accepted: `componentsReady()` (S6), chunk-blocked proof |
| 3 | No-preview choice lacked an "after" route and dropped "add in this Change" | Accepted: §3.2 three choices |
| 4 | Capture vs Change lock, scheduling while waiting on the owner, approval enforcement, D6 | Accepted for the first three (§3.3); D6 is pre-existing, recorded as G6, out of scope |
| 5 | Check preparation has no port | Accepted: §3.4 |
| 6 | Stored records and relaunch | Template/port split and fresh port accepted (§3.5); migration rejected: no real records before M4, no-legacy rule |
| 7 | Cache key wider than storage; one `before` record; retakes | Accepted by simplification: immutable sets per key, labelled attachments, retake removed (owner's own words) |
| 8 | Direct installs contradict DR3 | Raised to the owner as D-A |
| 9 | Slice boundaries and discriminating proof | Accepted: preparation in slice 1; content-specific proofs; M4 broken-layout and owner-server cases in slice 5 |
| 10 | R2 overstated; no combined budget | Accepted: R2 corrected, §3.4 budget rule |

Second round on the revision: findings 1, 2, 3, 5, 9 and 10 closed; both scope limits upheld; verdict
not ready until the capture lifecycle and D-A's framing were complete. Dispositions:

| # | Finding | Disposition |
| --- | --- | --- |
| 2.1 | PID journaling needs the Change lock the revision released | Accepted: short lock acquisitions for journal writes (§3.3 Attempts) |
| 2.2 | No dispatch while shaping waits; crashed captures relaunch without a record | Accepted: host capture rule, attempt records, "capture interrupted" (§3.3) |
| 2.3 | A failed capture was cached for good | Accepted: owner-triggered retry, no automatic retry (§3.3) |
| 2.4 | Renamed states lose their pictures | Accepted: files and pairing by path and viewport (§3.3 Storage) |
| 2.5 | D-A option 2 omits that repairs can alter the reference | Accepted: D-A table; timings marked unmeasured |

Third round on §3.3 and D-A: 2.1 to 2.5 closed; no new defect except one. Disposition:

| # | Finding | Disposition |
| --- | --- | --- |
| 3.1 | `_survivors` only finds processes; the host blocks instead of disposing a killed capture's groups | Accepted: explicit `check.dispose` of journaled groups before verification (§3.3 Completion); slice 3's killed-runner proof runs while a preview is alive |
