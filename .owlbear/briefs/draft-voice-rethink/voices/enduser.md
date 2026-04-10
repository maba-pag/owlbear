# End-User Voice — Dictation UX Position

## User Experience Stance

**Dictation in VS Code becomes daily-usable when it works as a hybrid input model — not a keyboard replacement.** The user dictates natural language (Copilot Chat prompts, documentation, comments, commit messages) and types technical tokens (paths, flags, identifiers). The value proposition is: dictate the 80% that's prose, type the 20% that's code. This framing drives every design decision below.

The minimum viable experience is: hold a hotkey, speak, release, text appears where you intended — in the editor or Copilot Chat — with auto-punctuation, native undo, and clear feedback. Anything short of this gets abandoned after a week.

## Usability Reasoning

### 1. Push-to-talk (hold) default, toggle opt-in

Hold = listening, release = commit. Audio click on both transitions. Status bar shows recording state plus the locked target name (see §3). This gives unambiguous activation state — the user always knows whether they're being recorded.

Toggle mode is available for longer dictation sessions (documentation, multi-paragraph prompts), discoverable via command palette. Users judge comfort on the default path first, so the default must be the trust-safe option.

**Escape to cancel:** Press Escape during a hold to discard without inserting. This prevents committed mistakes when the user realizes mid-utterance that the target, wording, or context is wrong.

### 2. Target locks at activation, not at insertion

When the hotkey is pressed, the extension captures which VS Code surface currently has focus and locks it as the insertion target. If focus drifts during speech (accidental click, notification popup), text still goes where the user intended. Silent misdelivery — text landing in the wrong place — is a trust-destroying failure that must be prevented structurally.

**Target visibility:** The status bar feedback should show the locked target: "Dictating → Editor (file.ts)" or "Dictating → Copilot Chat". This closes the stale-target blind spot where the user activates before fully confirming caret placement.

### 3. Two-tier injection: extension API for editor, clipboard-save/restore for Chat

- **Editor buffer:** `TextEditor.edit()` — native, clean, no side effects.
- **Copilot Chat / webview inputs:** Save clipboard → set clipboard to transcript → fire Ctrl+V → restore clipboard. Effectively transparent to the user.

The tension is real and accepted: Chat is arguably the highest-value target but gets the fallback injection method. This is the pragmatic choice because blocking on unproven Chat injection APIs delays the entire tool. Clipboard-save/restore is "good enough" — the user experiences "text appeared where I wanted it" in both cases. If the mechanism difference surfaces in subtle undo or paste semantics, that's signal to invest in native Chat injection later.

### 4. Native undo, no custom mechanism

Each dictation result inserts as a single atomic edit operation. Ctrl+Z undoes it using VS Code's native undo. No custom utterance tracking, no undo conflicts with interleaved typing.

**For toggle mode (long dictation):** Insert in segments at natural silence boundaries so undo removes the last segment, not everything from a multi-minute session. This keeps undo granularity proportional to what the user perceives as "what I just said."

### 5. Streaming partials for confidence, atomic insertion for reliability

Show partial recognition results as real-time feedback so the user sees the system is working. Insert only the final transcript into the target. This gives streaming confidence without polluting undo history.

The exact feedback rendering (status bar text, inline ghost text, dedicated widget) should be prototyped on the actual target hardware, not prescribed here — but it must be prominent enough to be noticed during dictation. Status bar alone may be too peripheral when the user is composing in Chat.

### 6. Auto-punctuation ON by default, toggleable, conservative

Periods at clear sentence ends. Commas at natural pauses. Sentence-initial capitalization. Conservative mode: don't over-insert in fragment-like input (Chat prompts are often informal).

Default ON because the cost of manually adding punctuation everywhere is higher than occasionally deleting an unwanted period. User can toggle OFF for contexts where fragments dominate. This is table stakes for natural language input.

### 7. Minimal structural commands: "new line" and "new paragraph"

These bridge the gap between dictation and prose structure. Without them, every line break requires reaching for the keyboard, which breaks dictation flow for multi-line content. No other voice commands in v1 — anything more is Talon territory.

### 8. First-use and failure states are explicit UX

- **First activation:** "Loading voice model..." with progress indicator. ~3-5 seconds, once. Subsequent activations: instant. The first impression determines whether the user tries again tomorrow.
- **Wrong/missing mic:** Actionable notification with device selection.
- **No audio after 3 seconds of activation:** "No audio detected — check microphone."
- **Model download failure:** Clear retry prompt with diagnostics.
- **Misrecognition:** Fix via keyboard. This IS the correction flow in a hybrid model. Dictate, scan, fix.

### 9. Latency: 500ms target, benchmark on actual hardware first

The first engineering task should benchmark Moonshine STT on the locked-down Windows laptop. Existing benchmarks are Mac/Linux. If latency exceeds 1 second, the streaming-partials feedback becomes critical to perceived responsiveness. If it exceeds 2 seconds, the whole approach needs rethinking.

## Key Trade-offs

| Choice | Cost | Avoids |
|--------|------|--------|
| Push-to-talk default | Ergonomic cost for long dictation | False activations, missed deactivations, trust erosion |
| Clipboard fallback for Chat | Subtle undo/paste semantic differences between surfaces | Blocking on unproven Chat injection APIs; shipping without Chat support |
| Atomic insertion + native undo | Long dictation = large undo units (mitigated by segment insertion in toggle mode) | Custom undo complexity, utterance tracking bugs, undo conflicts with typing |
| Target lock at activation | Cannot change target mid-dictation without reactivating | Silent misdelivery, wrong-target insertion |
| Auto-punctuation ON default | Occasional unwanted punctuation in Chat fragments | Manual punctuation burden that makes dictation slower than typing |
| No voice commands beyond structure | Must type corrections, cannot navigate by voice | Scope creep toward Talon-like complexity |
| Streaming partials as feedback only | User sees words they can't interact with until final insert | Polluted undo history, partial-text artifacts in target |

## Warnings

1. **Chat injection is the weakest link.** The highest-value target uses the fallback injection method. If clipboard-save/restore feels brittle or introduces perceptible behavior differences (undo semantics, paste formatting), daily usage will erode. Monitor this closely after ship.

2. **Windows latency is unverified.** All Moonshine benchmarks are non-Windows. If the corporate laptop can't hit sub-1s recognition, the experience will feel broken regardless of other UX work. Benchmark before building.

3. **Streaming feedback UI is unprescribed.** The position deliberately defers the exact rendering to prototyping, but if the feedback ends up in the status bar only, it may be too low-salience for trust during Chat composition. This needs real user testing.

4. **Correction burden scales with utterance length.** Short push-to-talk dictation has cheap correction (undo and retype). Long toggle-mode dictation can have expensive correction if misrecognition occurs mid-paragraph. The segment-level undo helps but the hybrid model's "fix by typing" story gets harder with length.

5. **Selection replacement is implicit.** When text is selected and the user dictates, the dictation replaces the selection (standard text input behavior). This is correct but may surprise users who expected append. No special handling needed, but worth noting in documentation.

## Confidence

0.78
