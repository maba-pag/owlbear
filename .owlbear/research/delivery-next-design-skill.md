# Design Skill and Screenshot Judgement for Delivery Next

> **Owning task:** Delivery rebuild, owner questions of 2026-10-14 ([rebuild §3.8](delivery-liveness-first-rebuild.md))
> **Date:** 2026-10-14
> **Question:** Should Delivery adopt Impeccable for UI builds and for judging screenshots, by installing it
> unmodified or by extracting its useful parts? And how should screenshots be judged when one model may miss
> that a technically correct change looks bad?

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

## 4. Recommendation, Confidence, and Limits

- Extract for builds and judging. Adopt the detector unmodified and pinned, as a mechanical check.
- Judge screenshots with two lenses, add the owner's "Another verdict" with a model choice, and record
  agreement.
- Limits:
  - Impeccable was read from its README only. The skill text, the 59 rules and the engine's network
    behaviour must be read before adoption, together with a pinned run of `detect` on a real preview.
  - "Opus is better at UI" is the owner's expectation; J6 measures it.
