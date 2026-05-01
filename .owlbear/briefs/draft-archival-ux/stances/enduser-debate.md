# End User Debate Log — Archival UX (Task 1231)

_Full Critic dialogue. One cycle completed._

---

## Cycle 1

### Draft Stance Sent to Critic

> The archival modal design is structurally sound: trigger (→ archived only), conditional refs show/hide (visible only for deprecated/duplicate), and ResolveModal precedent are correct UX decisions. However four concrete risks are unresolved:
>
> 1. Plain-text refs — acceptable but under-specified. User must look up task IDs while modal blocks the board. Without placeholder hints and actionable 422 error messages, server validation is a black box.
> 2. Stale refs on reason-switch — spec gap. If user selects deprecated, enters refs "1230", then switches to dropped, the refs field hides. Spec does not say whether to clear refs value from state or just hide it. If value persists AND payload includes hidden-field refs, backend returns ERR_ARCHIVAL_REFS_FORBIDDEN.
> 3. Submit-disabled without guidance — discoverability failure. User who selects deprecated but hasn't typed refs cannot tell why the button is grey. No inline hint text is required by the spec.
> 4. Accessibility beyond role="dialog" — incomplete spec. Also requires aria-modal="true", aria-labelledby, and focus trap. Without focus trap, keyboard users can tab outside the modal.
> 5. Dropdown ordering — current order (completed, deprecated, dropped, duplicate, wontfix) mixes resolution/redirection/rejection reasons. Recommended: completed → dropped → wontfix → deprecated → duplicate.
>
> Confidence: 0.79

---

### Critic Challenges Received

The critic returned eight challenges and three blind spots. Summarised below with my assessment of each.

**Challenge 1 — Plain-text reversal not acknowledged.**
The M1/M2 framing chose autocomplete; D4 switched to plain text under challenger pressure. My draft treated plain text as the settled baseline without naming the reversal or defending the change.

*Assessment: Sustained. My draft should have named the D4 reversal and defended from that position rather than treating plain text as self-evident.*

**Challenge 2 — "Server validation is a black box" overstated.**
The engine error messages are specific, and `mutation.py` forwards them via `detail=exc.user_message`. The critique ignored this live evidence.

*Assessment: Sustained. The concern should be narrowed to: the frontend must render the error message text, not just set an error state. The pipeline exists; the frontend rendering is the open question.*

**Challenge 3 — "Must look up task IDs externally" unproven.**
The frontend already loads `/api/tasks` into memory. The draft assumed fully blocking lookup with no in-modal context, but the source evidence only proves plain text was chosen — not that external lookup is inevitable.

*Assessment: Sustained. Revised to "no in-modal discovery affordance" — which is the actual, provable gap.*

**Challenge 4 — Stale refs overclaims.**
The draft presented the hidden-field-payload path as a confirmed failure. The task materials establish conditional show/hide (D4) and parse-on-submit (I2), but do not establish that hidden refs will be included in the payload. This is a contingent implementation bug hypothesis.

*Assessment: Sustained in part. The concern remains valid as a spec gap that must be resolved; the failure framing was too strong. Revised to "implementation must explicitly handle."*

**Challenge 5 — Submit-disabled not confirmed in the brief documents.**
The brief documents only specify "form valid before move fires" — not a disabled-button pattern specifically.

*Assessment: Not sustained. The user prompt for this evaluation explicitly states "Submit button (disabled until form is valid)." The user prompt is the controlling spec, not the brief documents. Position stands.*

**Challenge 6 — ResolveModal accessibility contradiction (CRITICAL).**
The draft calls ResolveModal a "correct UX decision" for structure AND argues it lacks aria-modal/aria-labelledby/focus trap. These positions are in tension: if the precedent is sound, why is the a11y analysis wrong? If the a11y analysis is correct, the precedent is incomplete.

*Assessment: Sustained. This was the most important challenge. Revised: ResolveModal is a structural precedent (state pattern, async submit, inline error) — not an a11y model. ArchivalModal must implement a11y independently and should exceed the precedent.*

**Challenge 7 — Dropdown ordering weakly grounded.**
My recommended reorder is taxonomy-preference, not evidence of user harm or conflict with configured semantics.

*Assessment: Partially sustained. The observation stands as a minor UX improvement; the confidence in it is reduced. Kept in the stance as a low-weight item.*

**Challenge 8 — Trigger ambiguity not resolved.**
The source task text still asks whether the prompt is tied to "moving to done" vs. an "explicit archive action."

*Assessment: Not sustained. context.md V2 explicitly resolves this (only status == "archived" triggers archival in the engine), and D3 confirms it as a locked M1 decision. The trigger decision is correctly labelled as resolved.*

---

### Critic Blind Spots Incorporated

**Self-reference and cycle detection:** Engine validates that archival_refs cannot include the task itself and cannot form a dependency cycle. These are real 422 scenarios users will hit with plain-text input. The stance was silent on them. **Added to item 1 as a required UX treatment.**

**Hardcoded reason list vs. config drift:** D4 chose to hardcode the default reason list in the frontend. If a board's `config.pipeline.archival_reasons` differs, the frontend silently shows the wrong list. The brief should document this as a known limitation. **Added as item 6.**

**Hardcoded "done" assumption:** D5 hardcodes `"done"` as terminal_status in the frontend for the completed-filter. If a project uses a different terminal_status, the filter is silently wrong. Not incorporated as a new stance point (D5 explicitly resolved this and the End User panelist does not override decided questions), but noted here as evidence that the "stable defaults" pattern carries compounding silent-drift risk.

---

### Refinement Summary

| Draft Item | Outcome |
|------------|---------|
| 1 — Plain-text refs | Revised: reframed from "must look up externally" to "no in-modal discovery affordance." Named the D4 reversal. Added self-reference/cycle 422 as required UX treatment. |
| 2 — Stale refs | Revised: framed as contingent implementation bug hypothesis requiring explicit spec resolution, not a confirmed failure path. |
| 3 — Submit-disabled | Held: user prompt confirms the pattern. Inline guidance requirement stands. |
| 4 — Accessibility | Revised: ResolveModal is structural precedent only, not a11y model. ArchivalModal must implement a11y independently. |
| 5 — Dropdown ordering | Held as minor. Confidence reduced. |
| 6 — Hardcoded list drift | Added from blind spots. |

---

### Post-Cycle Confidence

**0.76** (down from 0.79 draft)

Reduced because the ResolveModal accessibility contradiction was a genuine structural flaw in my initial framing, and the "black box" overstatement weakened two arguments I was treating as strong. The core positions (stale refs spec gap, submit guidance, focus trap required, self-reference/cycle error rendering) are all well-grounded.
