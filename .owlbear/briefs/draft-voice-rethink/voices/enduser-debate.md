# End-User Voice — Critic Debate Log

## Cycle 1

**My position:** Five priorities in order: (1) instant/unambiguous activation via toggle-mode hotkey, (2) correction flow matters more than accuracy — preview buffer essential, (3) sub-500ms latency with streaming partials, (4) Copilot Chat input is as important as editor, (5) clipboard+paste acceptable as v1, extension worth building.

**Critic challenges (5 critical, 1 moderate):**

1. **Chat injection unproven** — The extension API path (`TextEditor.edit()`) only covers editor buffers. Chat input is called half the value but has no proven injection mechanism.
2. **Toggle conflicts with trust model** — I said false activations kill trust, then recommended toggle which extends open-mic state. Push-to-talk is safer.
3. **Preview buffer conflicts with streaming** — Preview buffer blocks commit, colliding with sub-500ms target. If it doesn't block, it's not a trust gate. Two models pulling in opposite directions.
4. **Clipboard overwrite underestimated** — The workflows I elevated (Chat prompts, docs) are clipboard-heavy. Repeated clipboard destruction is direct loss of working memory, not incidental friction.
5. **First-use delay** — Lazy model loading creates a broken first impression on the exact path called non-negotiable.
6. **Utterance boundaries** — Chunks ≠ human utterances. Undo unit is undefined.

**My response:**
- **Accepted** challenges 2, 3, 4, 5. Toggle-first was wrong; preview buffer conflicted with streaming; clipboard overwrite was underestimated; first-use delay needs explicit UX.
- **Accepted** challenge 1 partially — admitted the gap honestly.
- **Accepted** challenge 6 — utterance boundaries need alignment with protocol.

## Cycle 2

**Refined position:** Push-to-talk hold default. Streaming insertion with sentence-level undo (no preview buffer). Extension as v1 primary, not clipboard. Honest about Chat injection gap (hybrid: extension for editor, clipboard for Chat). First-use loading indicator. Auto-punctuation, technical prose out of scope.

**Critic challenges (3 critical, 2 moderate):**

1. **Chat still primary but least reliable** — Same tension: Chat = most important, gets fallback method.
2. **Streaming insertion not proven** — VoiceChannel skips partials currently. Streaming insertion is new work.
3. **Sentence-level undo doesn't match protocol** — Protocol is line-based, not sentence-based. Mismatch erodes trust.
4. **Latency unverified on Windows** — 500ms target based on Mac/Linux benchmarks.
5. **Technical prose in primary workflows** — Paths, flags, identifiers appear inside the "primary" prose workflows, not just at boundaries.

**My response:**
- **Accepted** challenge 2 — acknowledged streaming insertion is new work, not existing capability.
- **Accepted** challenge 3 — dropped sentence-level undo, replaced with VAD silence boundaries as undo unit.
- **Accepted** challenge 4 — reframed 500ms as target, not guarantee. Benchmark first.
- **Rejected** challenge 1 — already acknowledged and accepted the tension. Clipboard-save/restore is good enough for v1.
- **Rejected** challenge 5 — the hybrid model is correct: dictate prose, type tokens. The value is in the prose portions.

## Cycle 3

**Refined position:** Silence-boundary utterance undo. Two-tier injection. Latency benchmarking. "Dictation supplements typing" as core framing.

**Critic challenges (3 critical, 3 moderate):**

1. **Primary surface backed by least native interaction** — Same challenge, fourth time.
2. **Undo conflicts with hybrid editing** — Once typed fixes and dictated text interleave, Ctrl+Z is no longer cleanly "what I just said."
3. **Silence boundaries ≠ user mental model** — Pauses during dictation mean thinking/rereading, not "commit this chunk."
4. **Hold-to-talk ergonomics** — Long-form dictation (the valuable case) is where hold becomes physically irritating.
5. **Status bar feedback too peripheral for Chat** — When composing in Chat, status bar is outside gaze.
6. **Auto-punctuation for prompt fragments** — Prompts are informal; auto-punctuation may over-insert.

**My response:**
- **Accepted** challenge 2 — dropped custom undo entirely. Use VS Code's native Ctrl+Z. Each dictation inserts as single atomic edit, native undo "just works."
- **Accepted** challenge 3 — for push-to-talk (hold), the entire hold is one utterance. Release = commit. Undo = undo the whole hold. Simpler than silence boundaries.
- **Partially accepted** challenge 6 — made auto-punctuation toggleable but kept ON as default (cost of missing > cost of unwanted).
- **Rejected** challenge 1 — acknowledged every cycle. Clipboard-save/restore is the pragmatic choice. Holding firm.
- **Rejected** challenge 4 — toggle mode exists for long dictation. Already addressed.
- **Rejected** challenge 5 — audio click feedback supplements visual. Exact rendering deferred to prototyping.

## Cycle 4

**Refined position:** Native undo only. Streaming partials for feedback, atomic insertion for reliability. Target locks at activation (not insertion). Minimal structural commands (new line, new paragraph). Cancel via Escape.

**Critic challenges (1 critical, 5 moderate):**

1. **Focus drift → silent misdelivery** — Focus-follows-cursor is wrong for dictation. User isn't monitoring focus while speaking.
2. **Mechanism difference perceptible inside one app** — Editor gets native API, Chat gets clipboard. Different undo/paste semantics without visible reason.
3. **Streaming feedback too weak** — Status bar is low-salience. Position says feedback "may become essential" if latency >1s but defers rendering.
4. **Default-on punctuation for fragments** — Chat prompts are informal, auto-punctuation may distort intent.
5. **80/20 understates structural editing** — Line breaks, bullets, paragraph shaping are common in "prose" dictation but have no voice support.
6. **Toggle discoverability** — First-use defaults determine perception; undiscovered opt-in doesn't offset.

**My response:**
- **Accepted** challenge 1 — major improvement. Target locks at activation, not insertion. Added target name display in status bar.
- **Accepted** challenge 5 — added "new line" and "new paragraph" as minimal structural commands.
- **Added** Escape-to-cancel interaction for mid-utterance abandonment (from blind spots).
- **Rejected** challenge 2 — same tension, acknowledged. Pragmatic choice stands.
- **Rejected** challenge 3 — deferred to prototyping deliberately. Not prescribing UI in a position paper.
- **Rejected** challenge 4 — ON default is correct. Cost of missing punctuation > cost of removing it.
- **Rejected** challenge 6 — command palette + keybinding docs are standard VS Code discoverability.

## Cycle 5

**Final position:** Full refinement with target locking, target visibility, structural commands, escape-to-cancel, segment-level undo for toggle mode.

**Critic challenges (1 critical, 5 moderate):**

1. **Surface inconsistency is a product risk** — Chat uses clipboard, editor uses native API. Repeated differences = the product experience.
2. **Stale-target from pre-orientation activation** — User may activate before confirming caret placement.
3. **Feedback UI still undefined** — Critical for daily use but deferred.
4. **Correction burden scales with length** — Long atomic insertions have expensive repair.
5. **Auto-punctuation for mixed surfaces** — Fragments, prompts, filenames in target surfaces.
6. **"New line/paragraph" insufficient for semi-structured prose** — Docs and prompts use bullets, headers, etc.

**My response:**
- **Partially accepted** challenge 2 — target visibility (showing locked target name) addresses this. User sees where text will go.
- **Partially accepted** challenge 4 — added segment-level insertion for toggle mode so undo removes last segment, not entire session.
- **Rejected** challenge 1 — raised in all 5 cycles. Position unchanged: pragmatic choice, accepted limitation, monitor after ship.
- **Rejected** challenge 3 — position paper prescribes requirements, not widget design. Prototyping is correct.
- **Rejected** challenge 5 — toggleable auto-punctuation already addressed. ON default stands.
- **Rejected** challenge 6 — new line/paragraph covers 90% of structural needs. Bullets and headers are Markdown typed with a few characters.

## Final Assessment

**Cycles completed:** 5

**What changed from initial position:**
- Toggle-first → push-to-talk (hold) default *(Cycle 1)*
- Preview buffer → streaming partials + atomic insertion *(Cycle 1)*
- Clipboard-first → extension as primary, clipboard as Chat fallback *(Cycle 1)*
- Custom utterance undo → VS Code native undo *(Cycle 3)*
- Sentence-level undo → silence-boundary → hold-session undo → native Ctrl+Z *(Cycles 2–3)*
- Focus-follows-cursor → target locks at activation *(Cycle 4)*
- Added: target visibility in feedback *(Cycle 4)*
- Added: Escape-to-cancel *(Cycle 4)*
- Added: "new line" / "new paragraph" structural commands *(Cycle 4)*
- Added: segment-level insertion for toggle mode *(Cycle 5)*

**What I held through all challenges:**
- Chat injection via clipboard-save/restore is acceptable v1 UX
- Auto-punctuation ON by default (toggleable)
- Technical prose is typed, not dictated (hybrid model)
- Streaming feedback rendering deferred to prototyping
- No voice commands beyond minimal structure
- Keyboard correction is the correction flow
