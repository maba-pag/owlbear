---
description: "Temporary recovery/exception: diagnose and resolve one exact Delivery attention"
---

> **Status:** Temporary recovery/exception surface. This is not part of the normal Delivery path.
>
> **Retirement condition:** Remove this prompt only after Cockpit and Delivery provide guided,
> tested routes for every recovery operation currently reachable only through this workflow:
> external Change-head adoption and promotion, publication-baseline recovery, and retained
> Integration-repair claim recovery. The replacement must also preserve exact identity binding,
> user decisions, provider actions, and explicit authority-gap reporting. Keep this prompt while any
> one of those capabilities still depends on it; ordinary Change attention controls are not enough
> to satisfy this condition.

Attention: ${input:attention:Change ID followed by either a 64-character attention ID or an OUT-nnn outcome ID}

Read and follow `../skills/w-delivery-attention-resolution/SKILL.md`. Bind the supplied change and
attention identities before inspecting current evidence. Present every material user choice with
pros, cons, risks, confidence, and expected outcomes, then use `askQuestions` for exactly one
decision at a time. Perform only the selected operation that current Delivery authority explicitly
permits; report an authority gap instead of substituting destructive Git or filesystem commands.

For a repairable remote-state condition, use `delivery_health` as the read-only diagnosis surface.
Present the exact Change ID, diagnostic code, and observed remote state-branch head, ask for explicit
confirmation, re-read the same evidence, and call `repair_delivery_state` only with
`confirmed_repair=true` and the exact values. Verify the returned receipt with a fresh health and
Change projection; never hand-edit local Delivery state or the remote state branch.
