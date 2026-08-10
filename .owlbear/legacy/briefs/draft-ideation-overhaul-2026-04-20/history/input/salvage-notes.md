# Ideation Overhaul — Salvage Notes for Fresh Session

## 1. The four user-reported symptoms

These are the named failures the user wants fixed. Original framing from the user, preserved intact.

### Symptom 1 — Critic under-cadence

The Critic subagent is invoked too rarely. When the Mediator drifts mid-conversation (multiple direction changes within a single moment), there is no mechanism to trigger Critic to challenge the drift. The current `w-ideation` skill has Critic invocation rules but they are bound to fixed moment boundaries (M1, M2, M4, M5) — within-moment drift slips through.

**Real-world example (just observed in the prior attempt):** the Mediator made 8 unilateral "corrections" to decisions.md in a single M4 session without triggering Critic, and only the user's manual demand for a Critic audit caught it.

### Symptom 2a — Opaque decisions

The Mediator presents decisions to the user without showing options, pros/cons, risks, or confidence per option. The user cannot tell what choice is being made on their behalf, or what was rejected and why. When the Mediator drafts a decision and asks for a yes/no, that is decision-laundering, not decision-presenting.

**Real-world example (just observed in the prior attempt):** the Mediator typed "Correction 7-final — drop hooks entirely" and asked the user to confirm, after the user had said "hooks are the stupidest use I have ever seen." The user's input was a steer; the Mediator silently converted it into a complete design decision and presented it as already-locked.

### Symptom 2b — Invisible decisions

The Mediator just makes decisions without asking the user, especially after getting other agent's feedback. ALL questions have to go through the user.

### Symptom 3 — Late research causing brownfield failure

The Mediator does not read existing code at M1 (Understanding) or even M3 (Landscape) when the topic touches existing code. The result is Briefs that treat brownfield problems as greenfield design exercises.

**Real-world example:** Brief B for `serve/kanban/` was drafted without ever opening `serve/kanban/src/owlbear_kanban/engine.py`. 41 discrepancies between Brief and reality were caught at M5 review.

---

## 2. The underlying problem (M1 root cause, Critic-validated)

The four symptoms above are **manifestations of a single root cause**: Mediator authority fragmentation + role bloat.

**Authority fragmentation:** the rules governing Mediator behavior are scattered across multiple files (`share/agents/ideator.agent.md`, `share/skills/w-ideation/SKILL.md`, `share/skills/h-ideation-panel/SKILL.md`, `share/instructions/agent-common.instructions.md`, plus user memory and research notes). When the Mediator should defer to a rule, it is not always clear which file is canonical. When rules conflict, the Mediator picks the most convenient interpretation.

**Role bloat:** the Mediator is simultaneously responsible for: user-facing dialogue, panel orchestration, decision drafting, blackboard file writing, Critic invocation, summary writing, and Brief drafting. This makes it the single bottleneck and the single point of failure.
