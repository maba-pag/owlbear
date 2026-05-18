# First-Principles Stance — Cockpit Ideas Notebook

## Irreducible Claim

**The user needs a low-friction way to capture pre-task ideas before they evaporate.**

That's the actual need. Everything else in the proposal is implementation structure that was chosen, not earned.

## Assumptions Challenged

### 1. "Ideas get lost" — is this evidenced or felt?

The `.owlbear/briefs/` directory already contains 5 brief files — `memory-voting.md`, `cockpit-browser-notifications.md`, `cockpit-board-grouping.md`, `cockpit-search-and-cross-refs.md`, `sequencing.md`. These are all pre-task ideas that survived to written form. The `sequencing.md` file even inventories 10 brief inputs. Ideas are clearly being captured *somewhere*.

The real complaint may not be "ideas get lost" but "capturing ideas requires context-switching to a filesystem action." That's a friction problem, not a loss problem. The distinction matters because a friction problem has a lower bar for solution.

**Challenge:** Name three specific ideas that were lost. If the answer is "I don't know, they were lost" — that's unfalsifiable. If the user can name friction moments, the solution should target those moments specifically.

### 2. The cockpit is assumed to be the capture surface — but is it where ideas happen?

OwlBear is a VS Code-resident system. The user's primary surface is the editor, not the browser-based cockpit. The cockpit is opened to inspect the board, check sessions, resolve DRs — it's a monitoring/intervention tool.

Ideas likely occur in three places:
- While reading code in VS Code
- While reviewing agent output in VS Code
- While looking at the board in the cockpit

The proposal only covers the third scenario. For the first two (arguably more frequent), the user still context-switches — now from VS Code to a *browser tab* instead of to a *file*. That may be a lateral move, not an improvement.

**Challenge:** The cockpit is being chosen because it exists and is getting tabs, not because it's where ideas originate. A VS Code command or keybinding that opens `.owlbear/ideas.md` in the editor would cover all three scenarios with zero new code.

### 3. A custom editor is assumed necessary — but VS Code already edits markdown.

The proposal builds:
- A FastAPI GET/PUT route pair
- A React page component with textarea, markdown preview toggle, save button
- Route config, navigation entry, tests for both layers

All to edit a single markdown file. VS Code has native markdown editing with live preview (`Cmd+Shift+V`), auto-save, and richer editing features than a `<textarea>`. The cockpit version is *strictly less capable* than the tool the user already has open.

The only thing the cockpit version adds is "don't leave the cockpit." But the cockpit is a secondary surface. The user already leaves it to do actual work.

**Challenge:** What does a browser-based textarea + markdown preview provide that VS Code's native markdown editor doesn't, beyond co-location with the board?

### 4. "Reuse the TaskFieldsEditor pattern" is borrowed structure, not earned design.

TaskFieldsEditor exists to edit structured task fields with dirty-state tracking, conflict detection, and save-to-engine semantics. The Ideas page would use approximately 5% of that pattern (a textarea, a toggle, a save button). Calling this "reuse" flatters the similarity — in practice it's a new component with coincidentally similar controls.

The actual implementation will be a new page component from scratch. The "reuse" framing makes the scope feel smaller than it is.

### 5. The tab system dependency makes this feel free — but it isn't.

The proposal leans on "the tab system is already planned (#1638), so adding a tab is just a route config entry + component." This makes the marginal cost *feel* low. But the tab system has 11 decomposed tasks (#1639-1649) that aren't done yet. The Ideas tab's true cost includes its share of that infrastructure.

More importantly: "the tab system makes it cheap to add tabs" is a reason tabs *will accumulate*, not a reason this particular tab *should exist*. Cheap affordance is how dashboards bloat.

## What Would Earn This Feature

The proposal passes the cost/benefit test **only if** the cockpit is genuinely the user's primary working surface when ideas occur. If the user spends 70%+ of idea-capture moments in the cockpit, a dedicated tab is the right answer. If the cockpit is a monitoring surface visited for minutes at a time, then this is furniture for a room the user rarely sits in.

One honest test: for two weeks, place a `.owlbear/ideas.md` file and a VS Code keybinding to open it. If the user reaches for the cockpit version anyway, build it. If the file in VS Code is sufficient, skip the feature.

## Verdict

The irreducible need (low-friction idea capture) is real. The proposed solution (cockpit tab with custom editor) may be the wrong surface. The simplest intervention — a markdown file with a fast way to open it in VS Code — solves the same problem at zero maintenance cost and covers more capture scenarios.

If built anyway, the feature is small and harmless. But "small and harmless" is how optional features accumulate into maintenance surface area. The question is whether this tab will be *used weekly* or *exist politely*.

**Confidence: 0.72** — The friction claim is plausible but unevidenced. The cockpit-as-capture-surface assumption is the weakest link. The feature is low-risk but may not be the right shape for the actual need.
